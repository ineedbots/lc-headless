#include "pch.hpp"
#include "ConsoleInput.hpp"

#include "LineEditor.hpp"

#include <iostream>

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
    // How long the line reader waits after a console read that ended without a line, so one that keeps
    // ending at once doesn't spin.
    constexpr auto READ_RETRY = 250ms;
    // Some writers, such as PowerShell's pipes, start UTF-8 input with one.
    constexpr auto BYTE_ORDER_MARK = "\xEF\xBB\xBF"sv;
    constexpr std::size_t READ_SIZE = 256;
    constexpr auto CTRL_C = '\x03';

    void Write(std::FILE* stream, std::string_view text)
    {
        std::fwrite(text.data(), 1, text.size(), stream);
        std::fflush(stream);
    }

#ifdef _WIN32
    bool IsConsole()
    {
        return _isatty(_fileno(stdin)) != 0;
    }

    // Returns how to undo it, or nothing when either side isn't a console.
    std::function<void()> EnterRawMode()
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

    // Empty after a Ctrl+C, nullopt once the console is gone.
    std::optional<std::string> ReadTerminal()
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
    bool IsConsole()
    {
        return isatty(STDIN_FILENO) != 0;
    }

    // Returns how to undo it, or nothing when either side isn't a terminal that takes VT100 codes.
    std::function<void()> EnterRawMode()
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

    // Nullopt once the terminal is gone.
    std::optional<std::string> ReadTerminal()
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
}

std::shared_ptr<ConsoleInput> ConsoleInput::ReadStdin()
{
    auto input = std::make_shared<ConsoleInput>();
    if (auto restore = EnterRawMode())
    {
        input->m_restoreTerminal = std::move(restore);
        input->m_editor.emplace();
        Write(stdout, input->m_editor->Render());
        std::thread{[input]
        {
            input->ReadKeys();
        }}.detach();

        return input;
    }

    std::thread{[input]
    {
        input->ReadLines();
    }}.detach();

    return input;
}

void ConsoleInput::Push(std::string line)
{
    {
        const auto lock = std::lock_guard{m_mutex};
        m_lines.push_back(std::move(line));
    }

    m_arrived.notify_all();
}

std::vector<std::string> ConsoleInput::TakeLines()
{
    const auto lock = std::lock_guard{m_mutex};
    return std::exchange(m_lines, {});
}

void ConsoleInput::WaitUntil(Clock::time_point time)
{
    auto lock = std::unique_lock{m_mutex};
    m_arrived.wait_until(lock, time, [this]
    {
        return !m_lines.empty();
    });
}

bool ConsoleInput::IsInteractive() const
{
    return m_editor.has_value();
}

void ConsoleInput::Print(std::FILE* stream, std::string_view text)
{
    const auto lock = std::lock_guard{m_outputMutex};
    const auto prompting = m_editor && !m_closed;
    if (prompting)
    {
        Write(stdout, LineEditor::Erase());
    }

    auto line = std::string{text};
    line += '\n';
    Write(stream, line);
    if (prompting)
    {
        Write(stdout, m_editor->Render());
    }
}

void ConsoleInput::Close()
{
    const auto lock = std::lock_guard{m_outputMutex};
    if (!m_editor || m_closed)
    {
        return;
    }

    m_closed = true;
    Write(stdout, LineEditor::Erase());
    m_restoreTerminal();
}

void ConsoleInput::ReadLines()
{
    const auto console = IsConsole();
    auto line = std::string{};
    auto first = true;
    while (true)
    {
        if (std::getline(std::cin, line))
        {
            if (std::exchange(first, false) && line.starts_with(BYTE_ORDER_MARK))
            {
                line.erase(0, BYTE_ORDER_MARK.size());
            }

            if (line.ends_with('\r'))
            {
                line.pop_back();
            }

            Push(std::move(line));
            continue;
        }

        // Piped input has ended for good. At the console, Ctrl+C and Ctrl+Z end a read as the end of the
        // input does, and the next read waits for a line again.
        if (!console)
        {
            return;
        }

        std::cin.clear();
        std::clearerr(stdin);
        std::this_thread::sleep_for(READ_RETRY);
    }
}

void ConsoleInput::ReadKeys()
{
    while (true)
    {
        const auto bytes = ReadTerminal();
        if (!bytes)
        {
            return;
        }

        auto entered = std::vector<std::string>{};
        {
            const auto lock = std::lock_guard{m_outputMutex};
            if (m_closed)
            {
                return;
            }

            entered = m_editor->Feed(*bytes);
            auto text = std::string{};
            for (const auto& line : entered)
            {
                text += LineEditor::RenderEntered(line);
            }

            text += m_editor->Render();
            Write(stdout, text);
        }

        for (auto& line : entered)
        {
            Push(std::move(line));
        }

        // A terminal normally turns Ctrl+C into a signal before it's read, but one that passes it on as
        // a key still interrupts. Escape sequences and UTF-8 never hold the byte.
        for (auto count = std::ranges::count(*bytes, CTRL_C); count > 0; --count)
        {
            std::raise(SIGINT);
        }
    }
}
