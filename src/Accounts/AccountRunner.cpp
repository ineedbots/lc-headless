#include "pch.hpp"
#include "AccountRunner.hpp"

#include "Type/AccountStatus_s.hpp"
#include "../Cache/Type/GameCache_s.hpp"
#include "../Config/Type/AccountConfig_s.hpp"
#include "../Config/Type/Config_s.hpp"
#include "../Console/ConsoleCommandParser.hpp"
#include "../Console/Type/ConsoleCommand_s.hpp"
#include "../Console/ConsoleInput.hpp"
#include "../Console/Logger.hpp"
#include "../Game/Net/LoginQueue.hpp"
#include "../Io/NetLoop.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "../Utils/StringUtils.hpp"
#include "Account.hpp"
#include "AccountCommands.hpp"

namespace
{
    constexpr auto TARGET_PREFIX = ConsoleCommandParser::TARGET_PREFIX;
    // A little over AsioLink's close timeout, so a close the server never answers still finishes.
    constexpr auto SETTLE_TIMEOUT = 2s;
    constexpr auto SLOW_STEP_THRESHOLD = 100ms;
    constexpr auto SLOW_STEP_LOG_INTERVAL = 10s;

}

AccountRunner::AccountRunner(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, std::vector<AccountConfig_s> accounts, ScriptRuntime& runtime, std::shared_ptr<Logger> logger, AccountOptions_s options, std::shared_ptr<NetLoop> net)
    : m_config{std::move(config)}
    , m_cache{std::move(cache)}
    , m_logger{std::move(logger)}
    , m_net{std::move(net)}
    , m_loginQueue{std::make_shared<LoginQueue>(m_config->scripting.loginIntervalSeconds)}
    , m_commands{m_accounts, *m_logger}
{
    assert(m_cache && "AccountRunner needs a cache");

    options.client.loginQueue = m_loginQueue;
    for (auto& account : accounts)
    {
        m_accounts.push_back(std::make_unique<Account>(m_config, m_cache, std::move(account), runtime, m_logger, options, &m_messenger, m_net));
    }
}

bool AccountRunner::Run(const InterruptCount& interrupts, ConsoleInput* console, const std::function<void(bool)>& service, const std::function<bool()>& hasIncoming, const std::function<void()>& onStopping)
{
    m_loginTurns = 0;
    m_nextLogin = m_accounts.empty() ? std::nullopt : std::optional{Clock::now()};

    auto handledInterrupts = interrupts();
    auto nextSlowStepLogs = std::unordered_map<const Account*, Clock::time_point>{};

    m_logger->Info("Running {} account{}", m_accounts.size(), m_accounts.size() == 1 ? "" : "s");

    if (console != nullptr)
    {
        console->SetOnArrived([net = m_net]
        {
            net->Wake();
        });
    }

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

        if (service)
        {
            service(true);
        }

        const auto now = Clock::now();
        if (m_nextLogin && now >= *m_nextLogin)
        {
            StartNextLogin(now);
        }

        for (const auto& account : m_accounts)
        {
            const auto stepStarted = Clock::now();
            account->Step(0ms);
            const auto stepFinished = Clock::now();
            const auto elapsed = stepFinished - stepStarted;
            if (elapsed >= SLOW_STEP_THRESHOLD)
            {
                auto& nextLog = nextSlowStepLogs[account.get()];
                if (stepFinished >= nextLog)
                {
                    nextLog = stepFinished + SLOW_STEP_LOG_INTERVAL;
                    m_logger->Warning("Account {} step took {} ms (warning threshold {} ms; warnings limited to once per account every {} s)", account->GetName(), std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count(), SLOW_STEP_THRESHOLD.count(), SLOW_STEP_LOG_INTERVAL.count());
                }
            }
        }

        for (const auto count = interrupts(); handledInterrupts < count; ++handledInterrupts)
        {
            InterruptAll();
        }

        if (service)
        {
            service(false);
        }

        const auto running = std::ranges::any_of(m_accounts, [](const std::unique_ptr<Account>& account)
        {
            return account->IsStarted() && !account->IsFinished();
        });

        if (!running && !m_nextLogin)
        {
            break;
        }

        if (!hasIncoming || !hasIncoming())
        {
            Wait(now);
        }
        else
        {
            m_net->Poll();
        }
    }

    if (console != nullptr)
    {
        console->SetOnArrived({});
    }

    if (onStopping)
    {
        onStopping();
    }

    // So every account's last close ends with a close frame rather than a dropped socket.
    if (!onStopping)
    {
        m_net->Settle(Clock::now() + SETTLE_TIMEOUT);
    }

    return LogOutcomes();
}

void AccountRunner::HandleCommand(std::string_view line, std::shared_ptr<CommandExecution> execution)
{
    const auto reject = [&execution](std::string error)
    {
        if (execution)
        {
            execution->errorCode = std::move(error);
        }
    };

    const auto parsed = ConsoleCommandParser::Parse(line);
    if (!parsed)
    {
        reject("invalid_command");
        return;
    }

    Account* target = nullptr;

    if (const auto& name = parsed->target)
    {
        target = m_commands.FindAccount(*name);
        if (target == nullptr)
        {
            reject("unknown_target");

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
            reject("invalid_command");
            m_logger->Warning("{}{} needs a command after it, such as {}{} {}", TARGET_PREFIX, *name, TARGET_PREFIX, *name, AccountCommands::HELP);
            return;
        }
    }

    const auto& command = parsed->command;
    if (execution && command.name != AccountCommands::PAUSE && command.name != AccountCommands::RESUME)
    {
        execution->started = true;
    }

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
        if (!m_commands.SetLogLevel(target, command.args))
        {
            reject("invalid_arguments");
        }
    }
    else if (command.name == AccountCommands::SAY)
    {
        if (!m_commands.Say(target, command.text))
        {
            reject("account_unavailable_or_invalid_arguments");
        }
    }
    else
    {
        if (execution)
        {
            execution->started = false;
        }

        if (!m_commands.SendToScripts(target, command, execution))
        {
            reject("command_rejected");
        }
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

void AccountRunner::Wait(Clock::time_point now) const
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

    // Wakes early for any account's I/O, and for a console line through SetOnArrived.
    m_net->Wait(wake);
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

void AccountRunner::CloseNetwork()
{
    for (const auto& account : m_accounts)
    {
        account->CloseNetwork();
    }
}

AccountStatus_s AccountRunner::GetAccountStatus(std::size_t index) const
{
    const auto& account = GetAccount(index);
    return {account.GetName(), account.IsStarted(), account.IsFinished(), account.DescribeStatus()};
}
