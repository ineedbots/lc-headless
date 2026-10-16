#include "pch.hpp"
#include "CommandLine.hpp"

CommandLine_s CommandLine::Parse(std::span<char* const> args)
{
    auto commandLine = CommandLine_s{};
    for (auto i = std::size_t{0}; i < args.size(); ++i)
    {
        const auto arg = std::string_view{args[i]};
        if (arg == ACCOUNT_OPTION)
        {
            if (i + 1 >= args.size())
            {
                throw std::invalid_argument{std::format("{} needs an account file path", ACCOUNT_OPTION)};
            }

            commandLine.accountPath = args[++i];
        }
        else if (arg == WATCH_OPTION)
        {
            commandLine.watch = true;
        }
        else if (arg == DEBUGGER_OPTION)
        {
            commandLine.debugger = true;
        }
        else if (arg == RAW_CONSOLE_OPTION)
        {
            commandLine.rawConsole = true;
        }
        else if (arg.starts_with("--"))
        {
            throw std::invalid_argument{std::format("Unknown option {}; {}", arg, USAGE)};
        }
        else
        {
            commandLine.configPath = arg;
        }
    }

    if (commandLine.watch && commandLine.debugger)
    {
        throw std::invalid_argument{std::format("{} and {} can't be combined: a reload would replace the script the debugger is attached to", WATCH_OPTION, DEBUGGER_OPTION)};
    }

    if (commandLine.debugger && !commandLine.accountPath)
    {
        throw std::invalid_argument{std::format("{} needs {}: a script paused in the debugger pauses every account in the process", DEBUGGER_OPTION, ACCOUNT_OPTION)};
    }

    return commandLine;
}
