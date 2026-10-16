#pragma once

#include "../Console/ConsoleCommand_s.hpp"
#include "../Console/Logger.hpp"
#include "Account.hpp"

// The console's own commands other than quit, which changes who logs in, and the script commands it passes on.
// A command given a target applies to that account only.
class AccountCommands
{
public:
    static constexpr auto HELP = "help"sv;
    static constexpr auto STATUS = "status"sv;
    static constexpr auto QUIT = "quit"sv;
    static constexpr auto EXIT = "exit"sv;
    static constexpr auto LOG_LEVEL = "loglevel"sv;
    static constexpr auto SAY = "say"sv;

    AccountCommands(const std::vector<std::unique_ptr<Account>>& accounts, Logger& logger);

    // By its file's name or its username, in any case.
    [[nodiscard]] Account* FindAccount(std::string_view name) const;
    void ShowHelp(const Account* target) const;
    void ShowStatus(const Account* target) const;
    void SetLogLevel(const Account* target, std::span<const std::string> args) const;
    void Say(Account* target, std::string_view text) const;
    void SendToScripts(Account* target, const ConsoleCommand_s& command) const;

private:
    const std::vector<std::unique_ptr<Account>>& m_accounts;
    Logger& m_logger;
};
