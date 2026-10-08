#pragma once

#include "../Core/ConfigFile.hpp"
#include "../Core/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Script/ScriptHost.hpp"
#include "../Script/ScriptRuntime.hpp"

// One account: its client and, when the account file names one, its script. Without a script the account
// idles and logs a summary of what it sees every SUMMARY_INTERVAL. Nothing it does waits beyond Step's
// maxWait, so many accounts can share one loop. An account finishes when it has logged out, when its
// login or connection fails for good, or when it's interrupted; failures are logged, not thrown.
class Account
{
public:
    using Clock = std::chrono::steady_clock;

    static constexpr auto SUMMARY_INTERVAL = 10s;
    // Long enough to outlast the server's refusal to log out during combat and for 10 seconds after.
    static constexpr auto LOGOUT_TIMEOUT = 30s;

    Account(std::shared_ptr<const Config_s> config, AccountConfig_s account, ScriptRuntime& runtime, std::shared_ptr<Logger> logger = Logger::GetDefault(), GameClientOptions_s clientOptions = {});

    Account(const Account&) = delete;
    Account& operator=(const Account&) = delete;

    // Starts logging in; Step does the rest.
    void Start();
    // Logs in before returning, for callers that run a single account.
    void Login();
    void Step(std::chrono::milliseconds maxWait);
    // The first interrupt gives a script with on_kill_signal killGraceSeconds to stop the account, and
    // otherwise logs out. One during a logout closes the connection without waiting for the server.
    void Interrupt();

    [[nodiscard]] bool IsStarted() const;
    [[nodiscard]] bool IsFinished() const;
    // Finished with a logout the server confirmed, and no failure.
    [[nodiscard]] bool Succeeded() const;
    [[nodiscard]] std::string_view DescribeOutcome() const;
    [[nodiscard]] std::optional<Clock::time_point> GetNextLoop() const;
    [[nodiscard]] const std::string& GetName() const;
    [[nodiscard]] const GameClient& GetClient() const;

private:
    [[nodiscard]] std::chrono::milliseconds GetWait(std::chrono::milliseconds maxWait) const;
    void StepScript(Clock::time_point now);
    void StepIdle(Clock::time_point now);
    void LogOut(std::string_view reason);
    void Fail(std::string_view reason);
    void UpdateFinished();

    std::shared_ptr<const Config_s> m_config;
    AccountConfig_s m_account;
    std::shared_ptr<Logger> m_logger;
    GameClient m_client;
    std::optional<ScriptHost> m_script;
    bool m_started = false;
    bool m_finished = false;
    bool m_failed = false;
    u32 m_interrupts = 0;
    std::optional<Clock::time_point> m_killDeadline;
    Clock::time_point m_nextSummary;
};
