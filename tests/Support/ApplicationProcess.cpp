#include "pch.hpp"
#include "ApplicationProcess.hpp"

#include "Utils/FileUtils.hpp"

#include <fstream>

#ifdef _WIN32
#include <Windows.h>
#else
#include <cerrno>
#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

ApplicationResult_s RunApplication(const std::filesystem::path& directory, const std::vector<std::string>& arguments, std::string_view input)
{
    const auto inputPath = directory / "stdin.txt";
    const auto outputPath = directory / "output.txt";
    {
        auto file = std::ofstream{inputPath, std::ios::binary};
        file << input;
        if (!file)
        {
            throw std::runtime_error{"Couldn't write application input"};
        }
    }
    auto exitCode = int{-1};
#ifdef _WIN32
    auto quote = [](const std::wstring& argument)
    {
        auto result = std::wstring{L"\""};
        auto slashes = std::size_t{0};
        for (const auto ch : argument)
        {
            if (ch == L'\\')
            {
                ++slashes;
                continue;
            }
            result.append(ch == L'"' ? 2 * slashes + 1 : slashes, L'\\');
            slashes = 0;
            result += ch;
        }
        result.append(2 * slashes, L'\\');
        return result + L'"';
    };
    const auto executable = std::filesystem::path{RS2004_APPLICATION_PATH}.wstring();
    auto command = quote(executable);
    for (const auto& argument : arguments)
    {
        command += L' ' + quote(std::filesystem::path{argument}.wstring());
    }
    auto attributes = SECURITY_ATTRIBUTES{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    const auto in = CreateFileW(inputPath.c_str(), GENERIC_READ, FILE_SHARE_READ, &attributes, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    const auto out = CreateFileW(outputPath.c_str(), GENERIC_WRITE, FILE_SHARE_READ, &attributes, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (in == INVALID_HANDLE_VALUE || out == INVALID_HANDLE_VALUE)
    {
        if (in != INVALID_HANDLE_VALUE) CloseHandle(in);
        if (out != INVALID_HANDLE_VALUE) CloseHandle(out);
        throw std::runtime_error{"Couldn't redirect application streams"};
    }
    auto startup = STARTUPINFOW{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdInput = in;
    startup.hStdOutput = out;
    startup.hStdError = out;
    auto process = PROCESS_INFORMATION{};
    const auto created = CreateProcessW(executable.c_str(), command.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW, nullptr, directory.c_str(), &startup, &process);
    CloseHandle(in);
    CloseHandle(out);
    if (!created)
    {
        throw std::runtime_error{"Couldn't start application"};
    }
    const auto wait = WaitForSingleObject(process.hProcess, 15000);
    if (wait != WAIT_OBJECT_0)
    {
        TerminateProcess(process.hProcess, 1);
        WaitForSingleObject(process.hProcess, INFINITE);
    }
    auto status = DWORD{0};
    GetExitCodeProcess(process.hProcess, &status);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    if (wait != WAIT_OBJECT_0)
    {
        throw std::runtime_error{"Application timed out"};
    }
    exitCode = static_cast<int>(status);
#else
    auto argv = std::vector<char*>{const_cast<char*>(RS2004_APPLICATION_PATH)};
    for (const auto& argument : arguments)
    {
        argv.push_back(const_cast<char*>(argument.c_str()));
    }
    argv.push_back(nullptr);
    const auto child = fork();
    if (child < 0)
    {
        throw std::runtime_error{"Couldn't fork application"};
    }
    if (child == 0)
    {
        const auto in = open(inputPath.c_str(), O_RDONLY);
        const auto out = open(outputPath.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (in < 0 || out < 0 || chdir(directory.c_str()) != 0 || dup2(in, STDIN_FILENO) < 0 || dup2(out, STDOUT_FILENO) < 0 || dup2(out, STDERR_FILENO) < 0)
        {
            _exit(127);
        }
        close(in);
        close(out);
        execv(argv.front(), argv.data());
        _exit(127);
    }
    const auto deadline = std::chrono::steady_clock::now() + 15s;
    auto status = int{0};
    while (true)
    {
        const auto result = waitpid(child, &status, WNOHANG);
        if (result == child) break;
        if (result < 0 && errno != EINTR)
        {
            throw std::runtime_error{"Couldn't wait for application"};
        }
        if (std::chrono::steady_clock::now() >= deadline)
        {
            kill(child, SIGKILL);
            while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
            throw std::runtime_error{"Application timed out"};
        }
        std::this_thread::sleep_for(10ms);
    }
    exitCode = WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
#endif
    return {exitCode, FileUtils::ReadText(outputPath).value_or("")};
}
