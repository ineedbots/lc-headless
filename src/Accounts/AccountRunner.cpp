#include "pch.hpp"
#include "AccountRunner.hpp"

#include "../Core/ConfigFile.hpp"
#include "../Core/Logger.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "Account.hpp"

AccountRunner::AccountRunner(std::shared_ptr<const Config_s> config, std::vector<AccountConfig_s> accounts, ScriptRuntime& runtime, std::shared_ptr<Logger> logger, AccountOptions_s options)
    : m_config{std::move(config)}
    , m_logger{std::move(logger)}
{
    for (auto& account : accounts)
    {
        m_accounts.push_back(std::make_unique<Account>(m_config, std::move(account), runtime, m_logger, options, &m_messenger));
    }
}

bool AccountRunner::Run(const InterruptCount& interrupts)
{
    const auto loginInterval = m_config->scripting.loginIntervalSeconds;
    auto started = std::size_t{0};
    auto nextLogin = m_accounts.empty() ? std::nullopt : std::optional{Clock::now()};
    auto handledInterrupts = interrupts();

    m_logger->Info("Running {} account{}", m_accounts.size(), m_accounts.size() == 1 ? "" : "s");
    while (true)
    {
        const auto now = Clock::now();
        if (nextLogin && now >= *nextLogin)
        {
            m_accounts[started]->Start();
            ++started;
            nextLogin = started < m_accounts.size() ? std::optional{now + loginInterval} : std::nullopt;
        }

        for (const auto& account : m_accounts)
        {
            account->Step(0ms);
        }

        for (const auto count = interrupts(); handledInterrupts < count; ++handledInterrupts)
        {
            if (nextLogin)
            {
                m_logger->Info("Interrupted; {} account{} won't log in", m_accounts.size() - started, m_accounts.size() - started == 1 ? "" : "s");
                nextLogin.reset();
            }

            for (const auto& account : m_accounts)
            {
                account->Interrupt();
            }
        }

        const auto running = std::ranges::any_of(m_accounts, [](const std::unique_ptr<Account>& account)
        {
            return account->IsStarted() && !account->IsFinished();
        });

        if (!running && !nextLogin)
        {
            break;
        }

        Wait(now, nextLogin);
    }

    return LogOutcomes();
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

void AccountRunner::Wait(Clock::time_point now, std::optional<Clock::time_point> nextLogin) const
{
    auto wake = now + m_config->scripting.pollIntervalMs;
    if (nextLogin)
    {
        wake = std::min(wake, *nextLogin);
    }

    for (const auto& account : m_accounts)
    {
        if (const auto nextLoop = account->GetNextLoop())
        {
            wake = std::min(wake, *nextLoop);
        }
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
