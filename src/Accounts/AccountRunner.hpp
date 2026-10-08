#pragma once

#include "../Core/ConfigFile.hpp"
#include "../Core/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "Account.hpp"

// Runs many accounts on one thread. Every account's script loads on construction, so a broken script
// stops everything before the first login. Run then starts the logins loginIntervalSeconds apart and
// steps every account on each pass, waiting between passes until the next loop() is due, but at most
// pollIntervalMs.
class AccountRunner
{
public:
    using Clock = std::chrono::steady_clock;
    // How many interrupts (Ctrl+C presses) there have been so far; each new one interrupts every account.
    using InterruptCount = std::function<u32()>;

    AccountRunner(std::shared_ptr<const Config_s> config, std::vector<AccountConfig_s> accounts, ScriptRuntime& runtime, std::shared_ptr<Logger> logger = Logger::GetDefault(), GameClientOptions_s clientOptions = {});

    AccountRunner(const AccountRunner&) = delete;
    AccountRunner& operator=(const AccountRunner&) = delete;

    // Returns once every started account has finished; after an interrupt, accounts not yet started
    // never are. True when every started account logged out cleanly.
    [[nodiscard]] bool Run(const InterruptCount& interrupts);

    [[nodiscard]] std::size_t GetAccountCount() const;
    [[nodiscard]] const Account& GetAccount(std::size_t index) const;

private:
    void Wait(Clock::time_point now, std::optional<Clock::time_point> nextLogin) const;
    [[nodiscard]] bool LogOutcomes() const;

    std::shared_ptr<const Config_s> m_config;
    std::shared_ptr<Logger> m_logger;
    std::vector<std::unique_ptr<Account>> m_accounts;
};
