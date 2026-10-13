#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Core/ConfigFile.hpp"
#include "../Core/ConsoleInput.hpp"
#include "../Core/Logger.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/ConsoleCommand_s.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "Account.hpp"

// Runs many accounts on one thread. Every account's script loads on construction, so a broken script
// stops everything before the first login. Run then starts the logins loginIntervalSeconds apart and
// steps every account on each pass, waiting between passes until the next loop() is due, but at most
// pollIntervalMs. Its accounts' scripts can send each other bot messages, and lines typed into the console
// reach them as commands.
class AccountRunner
{
public:
    using Clock = std::chrono::steady_clock;
    // How many interrupts (Ctrl+C presses) there have been so far; each new one interrupts every account.
    using InterruptCount = std::function<u32()>;

    AccountRunner(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, std::vector<AccountConfig_s> accounts, ScriptRuntime& runtime, std::shared_ptr<Logger> logger = Logger::GetDefault(), AccountOptions_s options = {});

    AccountRunner(const AccountRunner&) = delete;
    AccountRunner& operator=(const AccountRunner&) = delete;

    static constexpr auto COMMAND_HELP = "help"sv;
    static constexpr auto COMMAND_STATUS = "status"sv;
    static constexpr auto COMMAND_QUIT = "quit"sv;
    static constexpr auto COMMAND_EXIT = "exit"sv;
    static constexpr auto COMMAND_LOG_LEVEL = "loglevel"sv;
    static constexpr auto COMMAND_SAY = "say"sv;

    // Returns once every started account has finished; after an interrupt, accounts not yet started
    // never are. True when every started account logged out cleanly. With a console, each line typed is
    // handled as HandleCommand describes, at the start of the next pass.
    [[nodiscard]] bool Run(const InterruptCount& interrupts, ConsoleInput* console = nullptr);
    // A line typed into the console. help, status, quit (or exit, which is a Ctrl+C), loglevel and say
    // (public chat from every account in game) are the runner's own; any other command goes to every running script that added it. "@<account> <command>"
    // sends a line to one account, named by its file or its username, in any case; quit then stops just
    // that account. Mistakes are logged as warnings.
    void HandleCommand(std::string_view line);

    [[nodiscard]] std::size_t GetAccountCount() const;
    [[nodiscard]] const Account& GetAccount(std::size_t index) const;

private:
    void StartNextLogin(Clock::time_point now);
    void InterruptAll();
    [[nodiscard]] Account* FindAccount(std::string_view name) const;
    void ShowHelp(const Account* target) const;
    void ShowStatus(const Account* target) const;
    void Quit(Account* target);
    void SetLogLevel(const Account* target, std::span<const std::string> args);
    void Say(Account* target, std::string_view text);
    void SendToScripts(Account* target, const ConsoleCommand_s& command);
    void Wait(Clock::time_point now, ConsoleInput* console) const;
    [[nodiscard]] bool LogOutcomes() const;

    std::shared_ptr<const Config_s> m_config;
    std::shared_ptr<const GameCache_s> m_cache;
    std::shared_ptr<Logger> m_logger;
    // Declared before the accounts, which unregister from it as they go.
    BotMessenger m_messenger;
    std::vector<std::unique_ptr<Account>> m_accounts;
    // How many of the accounts have had their turn to log in, and when the next one does.
    std::size_t m_loginTurns = 0;
    std::optional<Clock::time_point> m_nextLogin;
    // Accounts quit from the console before their turn, which never log in.
    std::unordered_set<const Account*> m_cancelled;
};
