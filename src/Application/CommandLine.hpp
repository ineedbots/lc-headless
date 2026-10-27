#pragma once

#include "../Config/ConfigFile.hpp"

struct CommandLine_s
{
    std::filesystem::path configPath{ConfigFile::DEFAULT_PATH};
    // Without one, every enabled account file runs.
    std::optional<std::filesystem::path> accountPath;
    bool watch = false;
    bool debugger = false;
    bool profile = false;
    // No VT100 codes and no console input, for a program reading the output.
    bool rawConsole = false;
};

class CommandLine
{
public:
    static constexpr auto ACCOUNT_OPTION = "--account"sv;
    static constexpr auto WATCH_OPTION = "--watch"sv;
    static constexpr auto DEBUGGER_OPTION = "--debugger"sv;
    static constexpr auto PROFILE_OPTION = "--profile"sv;
    static constexpr auto RAW_CONSOLE_OPTION = "--raw-console"sv;
    static constexpr auto USAGE = "usage: rs2004-headless [client.jsonc] [--account accounts/name.jsonc] [--watch] [--debugger] [--profile] [--raw-console]"sv;

    CommandLine() = delete;

    // The arguments after the program's name. Throws std::invalid_argument for options it can't use.
    [[nodiscard]] static CommandLine_s Parse(std::span<char* const> args);
};
