#pragma once

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"

struct CommandLine_s
{
    std::filesystem::path configPath{ConfigFile::DEFAULT_PATH};
    // Without one, every enabled account file in scripting.accountsDirectory runs.
    std::optional<std::filesystem::path> accountPath;
    // Reload scripts when their files change.
    bool watch = false;
    // Wait for VS Code's pocketpy debugger before running the account's script.
    bool debugger = false;
};

class Application
{
public:
    static constexpr auto ACCOUNT_OPTION = "--account"sv;
    static constexpr auto WATCH_OPTION = "--watch"sv;
    static constexpr auto DEBUGGER_OPTION = "--debugger"sv;
    static constexpr auto USAGE = "usage: rs2004-headless [client.jsonc] [--account accounts/name.jsonc] [--watch] [--debugger]"sv;

    // The arguments after the program's name. Throws std::invalid_argument for ones it can't use.
    [[nodiscard]] static CommandLine_s ParseCommandLine(std::span<char* const> args);

    explicit Application(CommandLine_s commandLine, std::shared_ptr<Logger> logger = Logger::GetDefault());

    [[nodiscard]] int Run();

private:
    [[nodiscard]] std::vector<AccountConfig_s> LoadAccounts() const;

    std::shared_ptr<Logger> m_logger;
    CommandLine_s m_commandLine;
    std::shared_ptr<const Config_s> m_config;
};
