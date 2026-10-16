#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Config/AccountConfig_s.hpp"
#include "../Config/Config_s.hpp"
#include "../Console/ConsoleInput.hpp"
#include "../Console/LogFile.hpp"
#include "../Console/Logger.hpp"
#include "../Game/Nav/Navigation.hpp"
#include "CommandLine.hpp"

class Application
{
public:
    // Takes over the logger's sink for as long as the logger lives.
    explicit Application(CommandLine_s commandLine, std::shared_ptr<Logger> logger = Logger::GetDefault());

    [[nodiscard]] int Run();

private:
    [[nodiscard]] std::vector<AccountConfig_s> LoadAccounts() const;
    void InstallLogSink(std::shared_ptr<ConsoleInput> console);

    std::shared_ptr<Logger> m_logger;
    CommandLine_s m_commandLine;
    std::shared_ptr<const Config_s> m_config;
    std::shared_ptr<const GameCache_s> m_cache;
    std::shared_ptr<const Navigation> m_navigation;
    std::shared_ptr<LogFile> m_logFile;
};
