#pragma once

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Core/ConsoleInput.hpp"
#include "Core/LogFile.hpp"
#include "Core/Logger.hpp"
#include "Game/Nav/NavGraph.hpp"

struct CommandLine_s
{
    std::filesystem::path configPath{ConfigFile::DEFAULT_PATH};
    // Without one, every enabled account file in scripting.accountsDirectory runs.
    std::optional<std::filesystem::path> accountPath;
    // Reload scripts when their files change.
    bool watch = false;
    // Wait for VS Code's pocketpy debugger before running the account's script.
    bool debugger = false;
    // Plain log lines with no VT100 codes, and no console input, for a program reading the output or a
    // terminal that can't show them.
    bool rawConsole = false;
};

class Application
{
public:
    static constexpr auto ACCOUNT_OPTION = "--account"sv;
    static constexpr auto WATCH_OPTION = "--watch"sv;
    static constexpr auto DEBUGGER_OPTION = "--debugger"sv;
    static constexpr auto RAW_CONSOLE_OPTION = "--raw-console"sv;
    static constexpr auto USAGE = "usage: rs2004-headless [client.jsonc] [--account accounts/name.jsonc] [--watch] [--debugger] [--raw-console]"sv;

    // The arguments after the program's name. Throws std::invalid_argument for ones it can't use.
    [[nodiscard]] static CommandLine_s ParseCommandLine(std::span<char* const> args);

    // Takes over the logger's sink, sending its lines to the console and the config's log file, for as
    // long as the logger lives.
    explicit Application(CommandLine_s commandLine, std::shared_ptr<Logger> logger = Logger::GetDefault());

    [[nodiscard]] int Run();

private:
    [[nodiscard]] std::vector<AccountConfig_s> LoadAccounts() const;
    // The log file, if there is one, and the console: above its prompt while it has one, plain with a raw
    // console, and otherwise in color where the terminal shows it.
    void InstallLogSink(std::shared_ptr<ConsoleInput> console);

    std::shared_ptr<Logger> m_logger;
    CommandLine_s m_commandLine;
    std::shared_ptr<const Config_s> m_config;
    std::shared_ptr<const GameCache_s> m_cache;
    std::shared_ptr<const Navigation_s> m_navigation;
    std::shared_ptr<LogFile> m_logFile;
};
