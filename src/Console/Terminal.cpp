#include "pch.hpp"
#include "Terminal.hpp"

#ifdef _WIN32
#include <Windows.h>
#include <io.h>
#else
#include <cerrno>
#include <termios.h>
#include <unistd.h>
#endif

namespace
{
    constexpr std::size_t READ_SIZE = 256;
}

#ifdef _WIN32
bool Terminal::CanColor(std::FILE* stream)
{
    // https://no-color.org: set and not empty. The size counts the terminating null.
    if (GetEnvironmentVariableA("NO_COLOR", nullptr, 0) > 1)
    {
        return false;
    }

    const auto handle = GetStdHandle(stream == stderr ? STD_ERROR_HANDLE : STD_OUTPUT_HANDLE);
    auto mode = DWORD{0};
    if (!GetConsoleMode(handle, &mode))
    {
        return false;
    }

    return (mode & ENABLE_VIRTUAL_TERMINAL_PROCESSING) != 0 || SetConsoleMode(handle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING) != 0;
}

bool Terminal::IsInputConsole()
{
    return _isatty(_fileno(stdin)) != 0;
}

std::function<void()> Terminal::EnterRawMode()
{
    const auto input = GetStdHandle(STD_INPUT_HANDLE);
    const auto output = GetStdHandle(STD_OUTPUT_HANDLE);
    auto inputMode = DWORD{0};
    auto outputMode = DWORD{0};
    if (!GetConsoleMode(input, &inputMode) || !GetConsoleMode(output, &outputMode))
    {
        return {};
    }

    if (!SetConsoleMode(output, outputMode | ENABLE_PROCESSED_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    {
        return {};
    }

    const auto raw = (inputMode & ~static_cast<DWORD>(ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT)) | ENABLE_PROCESSED_INPUT | ENABLE_VIRTUAL_TERMINAL_INPUT;
    if (!SetConsoleMode(input, raw))
    {
        SetConsoleMode(output, outputMode);
        return {};
    }

    const auto codePage = GetConsoleOutputCP();
    SetConsoleOutputCP(CP_UTF8);
    return [input, output, inputMode, outputMode, codePage]
    {
        SetConsoleMode(input, inputMode);
        SetConsoleMode(output, outputMode);
        SetConsoleOutputCP(codePage);
    };
}

std::optional<std::string> Terminal::ReadKeys()
{
    auto buffer = std::array<wchar_t, READ_SIZE>{};
    auto count = DWORD{0};
    if (!ReadConsoleW(GetStdHandle(STD_INPUT_HANDLE), buffer.data(), static_cast<DWORD>(buffer.size()), &count, nullptr))
    {
        if (GetLastError() == ERROR_OPERATION_ABORTED)
        {
            return std::string{};
        }

        return std::nullopt;
    }

    const auto wide = static_cast<int>(count);
    const auto size = WideCharToMultiByte(CP_UTF8, 0, buffer.data(), wide, nullptr, 0, nullptr, nullptr);
    auto text = std::string(static_cast<std::size_t>(std::max(size, 0)), '\0');
    WideCharToMultiByte(CP_UTF8, 0, buffer.data(), wide, text.data(), size, nullptr, nullptr);
    return text;
}
#else
bool Terminal::CanColor(std::FILE* stream)
{
    const auto* const noColor = std::getenv("NO_COLOR");
    const auto* const term = std::getenv("TERM");
    return (noColor == nullptr || *noColor == '\0') && isatty(fileno(stream)) != 0 && (term == nullptr || std::string_view{term} != "dumb");
}

bool Terminal::IsInputConsole()
{
    return isatty(STDIN_FILENO) != 0;
}

std::function<void()> Terminal::EnterRawMode()
{
    const auto* const term = std::getenv("TERM");
    if (isatty(STDIN_FILENO) == 0 || isatty(STDOUT_FILENO) == 0 || (term != nullptr && std::string_view{term} == "dumb"))
    {
        return {};
    }

    auto original = termios{};
    if (tcgetattr(STDIN_FILENO, &original) != 0)
    {
        return {};
    }

    auto raw = original;
    raw.c_lflag &= ~static_cast<tcflag_t>(ICANON | ECHO);
    raw.c_cc[VMIN] = 1;
    raw.c_cc[VTIME] = 0;
    if (tcsetattr(STDIN_FILENO, TCSANOW, &raw) != 0)
    {
        return {};
    }

    return [original]
    {
        tcsetattr(STDIN_FILENO, TCSANOW, &original);
    };
}

std::optional<std::string> Terminal::ReadKeys()
{
    auto buffer = std::array<char, READ_SIZE>{};
    while (true)
    {
        const auto count = read(STDIN_FILENO, buffer.data(), buffer.size());
        if (count > 0)
        {
            return std::string(buffer.data(), static_cast<std::size_t>(count));
        }

        if (count < 0 && errno == EINTR)
        {
            continue;
        }

        return std::nullopt;
    }
}
#endif
