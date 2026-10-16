#include "pch.hpp"
#include "AccountRunner.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Config/AccountConfig_s.hpp"
#include "../Config/Config_s.hpp"
#include "../Console/ConsoleCommandParser.hpp"
#include "../Console/ConsoleCommand_s.hpp"
#include "../Console/ConsoleInput.hpp"
#include "../Console/Logger.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "../Utils/StringUtils.hpp"
#include "Account.hpp"
#include "AccountCommands.hpp"

namespace
{
    constexpr auto TARGET_PREFIX = ConsoleCommandParser::TARGET_PREFIX;

}

AccountRunner::AccountRunner(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, std::vector<AccountConfig_s> accounts, ScriptRuntime& runtime, std::shared_ptr<Logger> logger, AccountOptions_s options)
    : m_config{std::move(config)}
    , m_cache{std::move(cache)}
    , m_logger{std::move(logger)}
    , m_commands{m_accounts, *m_logger}
{
    assert(m_cache && "AccountRunner needs a cache");

    for (auto& account : accounts)
    {
        m_accounts.push_back(std::make_unique<Account>(m_config, m_cache, std::move(account), runtime, m_logger, options, &m_messenger));
    }
}

bool AccountRunner::Run(const InterruptCount& interrupts, ConsoleInput* console)
{
    m_loginTurns = 0;
    m_nextLogin = m_accounts.empty() ? std::nullopt : std::optional{Clock::now()};

    auto handledInterrupts = interrupts();

    m_logger->Info("Running {} account{}", m_accounts.size(), m_accounts.size() == 1 ? "" : "s");

    while (true)
    {
        // Before the steps, so a command queued for a script runs in this pass.
        if (console != nullptr)
        {
            for (const auto& line : console->TakeLines())
            {
                HandleCommand(line);
            }
        }

        const auto now = Clock::now();
        if (m_nextLogin && now >= *m_nextLogin)
        {
            StartNextLogin(now);
        }

        for (const auto& account : m_accounts)
        {
            account->Step(0ms);
        }

        for (const auto count = interrupts(); handledInterrupts < count; ++handledInterrupts)
        {
            InterruptAll();
        }

        const auto running = std::ranges::any_of(m_accounts, [](const std::unique_ptr<Account>& account)
        {
            return account->IsStarted() && !account->IsFinished();
        });

        if (!running && !m_nextLogin)
        {
            break;
        }

        Wait(now, console);
    }

    return LogOutcomes();
}

void AccountRunner::HandleCommand(std::string_view line)
{
    const auto parsed = ConsoleCommandParser::Parse(line);
    if (!parsed)
    {
        return;
    }

    Account* target = nullptr;

    if (const auto& name = parsed->target)
    {
        target = m_commands.FindAccount(*name);
        if (target == nullptr)
        {
            auto names = std::vector<std::string>{};
            for (const auto& account : m_accounts)
            {
                names.push_back(account->GetName());
            }

            m_logger->Warning("No account is named {}; the accounts are {}", *name, StringUtils::Join(names, ", "));
            return;
        }

        if (parsed->command.name.empty())
        {
            m_logger->Warning("{}{} needs a command after it, such as {}{} {}", TARGET_PREFIX, *name, TARGET_PREFIX, *name, AccountCommands::HELP);
            return;
        }
    }

    const auto& command = parsed->command;
    if (command.name == AccountCommands::HELP)
    {
        m_commands.ShowHelp(target);
    }
    else if (command.name == AccountCommands::STATUS)
    {
        m_commands.ShowStatus(target);
    }
    else if (command.name == AccountCommands::QUIT || command.name == AccountCommands::EXIT)
    {
        Quit(target);
    }
    else if (command.name == AccountCommands::LOG_LEVEL)
    {
        m_commands.SetLogLevel(target, command.args);
    }
    else if (command.name == AccountCommands::SAY)
    {
        m_commands.Say(target, command.text);
    }
    else
    {
        m_commands.SendToScripts(target, command);
    }
}

std::size_t AccountRunner::GetAccountCount() const
{
    return m_accounts.size();
}

const Account& AccountRunner::GetAccount(std::size_t index) const
{
    assert(index < m_accounts.size() && "Account index out of range");
    return *m_accounts[index];
}

// Accounts quit from the console before their turn give it up to the next.
void AccountRunner::StartNextLogin(Clock::time_point now)
{
    while (m_loginTurns < m_accounts.size() && m_cancelled.contains(m_accounts[m_loginTurns].get()))
    {
        ++m_loginTurns;
    }

    if (m_loginTurns < m_accounts.size())
    {
        m_accounts[m_loginTurns]->Start();
        ++m_loginTurns;
    }

    const auto waiting = m_loginTurns < m_accounts.size();
    m_nextLogin = waiting ? std::optional{now + m_config->scripting.loginIntervalSeconds} : std::nullopt;
}

void AccountRunner::InterruptAll()
{
    if (m_nextLogin)
    {
        const auto waiting = m_accounts.size() - m_loginTurns;
        m_logger->Info("Interrupted; {} account{} won't log in", waiting, waiting == 1 ? "" : "s");
        m_nextLogin.reset();
    }

    for (const auto& account : m_accounts)
    {
        account->Interrupt();
    }
}

void AccountRunner::Quit(Account* target)
{
    if (target == nullptr)
    {
        InterruptAll();
        return;
    }

    if (target->IsStarted())
    {
        target->Interrupt();
        return;
    }

    if (m_cancelled.insert(target).second)
    {
        m_logger->Info("{} won't log in", target->GetName());
    }
}

void AccountRunner::Wait(Clock::time_point now, ConsoleInput* console) const
{
    auto wake = now + m_config->scripting.pollIntervalMs;
    if (m_nextLogin)
    {
        wake = std::min(wake, *m_nextLogin);
    }

    for (const auto& account : m_accounts)
    {
        if (const auto nextLoop = account->GetNextLoop())
        {
            wake = std::min(wake, *nextLoop);
        }
    }

    if (console != nullptr)
    {
        console->WaitUntil(wake);
        return;
    }

    std::this_thread::sleep_until(wake);
}

bool AccountRunner::LogOutcomes() const
{
    auto succeeded = true;
    for (const auto& account : m_accounts)
    {
        if (!account->IsStarted())
        {
            continue;
        }

        succeeded = succeeded && account->Succeeded();
        m_logger->Info("{}: {}", account->GetName(), account->DescribeOutcome());
    }

    return succeeded;
}
