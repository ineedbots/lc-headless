#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Config/AccountConfig_s.hpp"
#include "../Config/Config_s.hpp"
#include "../Console/ConsoleCommand_s.hpp"
#include "../Console/ConsoleInput.hpp"
#include "../Console/Logger.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "Account.hpp"
#include "AccountCommands.hpp"

// Every account's script loads on construction, so a broken script stops everything before the first login.
class AccountRunner
{
public:
    using Clock = std::chrono::steady_clock;
    // Ctrl+C presses so far; each new one interrupts every account.
    using InterruptCount = std::function<u32()>;

    AccountRunner(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, std::vector<AccountConfig_s> accounts, ScriptRuntime& runtime, std::shared_ptr<Logger> logger = Logger::GetDefault(), AccountOptions_s options = {});

    AccountRunner(const AccountRunner&) = delete;
    AccountRunner& operator=(const AccountRunner&) = delete;

    // After an interrupt, accounts not yet started never are. True when every started account logged out cleanly.
    [[nodiscard]] bool Run(const InterruptCount& interrupts, ConsoleInput* console = nullptr);
    // help, status, quit (or exit, which is a Ctrl+C), loglevel and say are the runner's own; any other command
    // goes to every running script that added it. "@<account> <command>" sends a line to one account, named by
    // its file or its username, in any case; quit then stops just that account.
    void HandleCommand(std::string_view line);

    [[nodiscard]] std::size_t GetAccountCount() const;
    [[nodiscard]] const Account& GetAccount(std::size_t index) const;

private:
    void StartNextLogin(Clock::time_point now);
    void InterruptAll();
    void Quit(Account* target);
    void Wait(Clock::time_point now, ConsoleInput* console) const;
    [[nodiscard]] bool LogOutcomes() const;

    std::shared_ptr<const Config_s> m_config;
    std::shared_ptr<const GameCache_s> m_cache;
    std::shared_ptr<Logger> m_logger;
    // Declared before the accounts, which unregister from it as they go.
    BotMessenger m_messenger;
    std::vector<std::unique_ptr<Account>> m_accounts;
    AccountCommands m_commands;
    // How many of the accounts have had their turn to log in, and when the next one does.
    std::size_t m_loginTurns = 0;
    std::optional<Clock::time_point> m_nextLogin;
    // Accounts quit from the console before their turn, which never log in.
    std::unordered_set<const Account*> m_cancelled;
};
