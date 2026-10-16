#include "pch.hpp"
#include "AccountRunner.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Config/AccountConfig_s.hpp"
#include "../Config/Config_s.hpp"
#include "../Console/ConsoleCommandParser.hpp"
#include "../Console/ConsoleCommand_s.hpp"
#include "../Console/ConsoleInput.hpp"
#include "../Console/LogLevelNames.hpp"
#include "../Console/LogLevel_e.hpp"
#include "../Console/Logger.hpp"
#include "../Game/Protocol/WordPack.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/ScriptCommand_s.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "../Utils/StringUtils.hpp"
#include "Account.hpp"

namespace
{
    constexpr auto TARGET_PREFIX = ConsoleCommandParser::TARGET_PREFIX;

    bool HasCommand(const std::vector<ScriptCommand_s>& commands, std::string_view name)
    {
        return std::ranges::find(commands, name, &ScriptCommand_s::name) != commands.end();
    }
}

AccountRunner::AccountRunner(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, std::vector<AccountConfig_s> accounts, ScriptRuntime& runtime, std::shared_ptr<Logger> logger, AccountOptions_s options)
    : m_config{std::move(config)}
    , m_cache{std::move(cache)}
    , m_logger{std::move(logger)}
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
        target = FindAccount(*name);
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
            m_logger->Warning("{}{} needs a command after it, such as {}{} {}", TARGET_PREFIX, *name, TARGET_PREFIX, *name, COMMAND_HELP);
            return;
        }
    }

    const auto& command = parsed->command;
    if (command.name == COMMAND_HELP)
    {
        ShowHelp(target);
    }
    else if (command.name == COMMAND_STATUS)
    {
        ShowStatus(target);
    }
    else if (command.name == COMMAND_QUIT || command.name == COMMAND_EXIT)
    {
        Quit(target);
    }
    else if (command.name == COMMAND_LOG_LEVEL)
    {
        SetLogLevel(target, command.args);
    }
    else if (command.name == COMMAND_SAY)
    {
        Say(target, command.text);
    }
    else
    {
        SendToScripts(target, command);
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

Account* AccountRunner::FindAccount(std::string_view name) const
{
    for (const auto& account : m_accounts)
    {
        if (StringUtils::EqualsIgnoringCase(account->GetName(), name) || StringUtils::EqualsIgnoringCase(account->GetUsername(), name))
        {
            return account.get();
        }
    }

    return nullptr;
}

void AccountRunner::ShowHelp(const Account* target) const
{
    if (target == nullptr)
    {
        m_logger->Info("Console commands: {}, {}, {} (or {}; as Ctrl+C), {} [verbose|info|warning|error], {} <text>. Start a line with {}<account> to send it to that account only",
                       COMMAND_HELP, COMMAND_STATUS, COMMAND_QUIT, COMMAND_EXIT, COMMAND_LOG_LEVEL, COMMAND_SAY, TARGET_PREFIX);
    }

    auto any = false;
    for (const auto& account : m_accounts)
    {
        if (target != nullptr && account.get() != target)
        {
            continue;
        }

        for (const auto& command : account->GetCommands())
        {
            any = true;

            if (command.help.empty())
            {
                m_logger->Info("{}: {}", account->GetName(), command.name);
            }
            else
            {
                m_logger->Info("{}: {} - {}", account->GetName(), command.name, command.help);
            }
        }
    }

    if (any)
    {
        return;
    }

    if (target == nullptr)
    {
        m_logger->Info("No script has added a console command");
    }
    else
    {
        m_logger->Info("{}: no console commands", target->GetName());
    }
}

void AccountRunner::ShowStatus(const Account* target) const
{
    for (const auto& account : m_accounts)
    {
        if (target == nullptr || account.get() == target)
        {
            m_logger->Info("{}: {}", account->GetName(), account->DescribeStatus());
        }
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

void AccountRunner::SetLogLevel(const Account* target, std::span<const std::string> args)
{
    if (target != nullptr)
    {
        m_logger->Warning("{} applies to every account; leave out the {}", COMMAND_LOG_LEVEL, TARGET_PREFIX);
        return;
    }

    if (args.empty())
    {
        m_logger->Warning("The log level is {}", LogLevelNames::GetName(m_logger->GetLevel()));
        return;
    }

    const auto chosen = LogLevelNames::Find(StringUtils::ToLower(args.front()));
    if (args.size() > 1 || !chosen)
    {
        m_logger->Warning("{} takes one of {}", COMMAND_LOG_LEVEL, LogLevelNames::CHOICES);
        return;
    }

    m_logger->SetLevel(*chosen);
    // A warning, so it shows at every level but error.
    m_logger->Warning("The log level is now {}", LogLevelNames::GetName(*chosen));
}

void AccountRunner::Say(Account* target, std::string_view text)
{
    if (text.empty())
    {
        m_logger->Warning("{} needs the text to say", COMMAND_SAY);
        return;
    }

    if (text.size() > WordPack::MAX_PACK_LENGTH)
    {
        m_logger->Warning("Public chat holds {} characters; the rest is cut off", WordPack::MAX_PACK_LENGTH);
        text = text.substr(0, WordPack::MAX_PACK_LENGTH);
    }

    if (target != nullptr)
    {
        if (target->Say(text))
        {
            m_logger->Info("{} says: {}", target->GetName(), text);
        }
        else
        {
            m_logger->Warning("{} isn't in game to say it", target->GetName());
        }

        return;
    }

    auto said = false;
    for (const auto& account : m_accounts)
    {
        if (account->Say(text))
        {
            said = true;
            m_logger->Info("{} says: {}", account->GetName(), text);
        }
    }

    if (!said)
    {
        m_logger->Warning("No account is in game to say it");
    }
}

void AccountRunner::SendToScripts(Account* target, const ConsoleCommand_s& command)
{
    if (target != nullptr)
    {
        if (!HasCommand(target->GetCommands(), command.name))
        {
            m_logger->Warning("{} has no console command {}; type {}{} {} for its commands", target->GetName(), command.name, TARGET_PREFIX, target->GetName(), COMMAND_HELP);
        }
        else if (!target->SendCommand(command))
        {
            m_logger->Warning("{} can't take more console commands until it has run the ones waiting", target->GetName());
        }

        return;
    }

    auto found = false;
    for (const auto& account : m_accounts)
    {
        if (!HasCommand(account->GetCommands(), command.name))
        {
            continue;
        }

        found = true;

        if (!account->SendCommand(command))
        {
            m_logger->Warning("{} can't take more console commands until it has run the ones waiting", account->GetName());
        }
    }

    if (!found)
    {
        m_logger->Warning("Unknown command {}; type {} for the commands", command.name, COMMAND_HELP);
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
