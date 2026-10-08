#pragma once

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"

class Application
{
public:
    static constexpr auto ACCOUNT_OPTION = "--account"sv;

    // Without an account path, every enabled account file in scripting.accountsDirectory runs.
    Application(const std::filesystem::path& configPath, std::optional<std::filesystem::path> accountPath, std::shared_ptr<Logger> logger = Logger::GetDefault());

    [[nodiscard]] int Run();

private:
    [[nodiscard]] std::vector<AccountConfig_s> LoadAccounts() const;

    std::shared_ptr<Logger> m_logger;
    std::shared_ptr<const Config_s> m_config;
    std::optional<std::filesystem::path> m_accountPath;
};
