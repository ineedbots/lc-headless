#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Config/AccountConfig_s.hpp"
#include "../Config/Config_s.hpp"
#include "../Console/ConsoleCommand_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/Nav/Navigation.hpp"
#include "../Io/NetLoop.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/Host/ScriptHost.hpp"
#include "../Script/ScriptCommand_s.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "ProgressReporter.hpp"

struct AccountOptions_s
{
    GameClientOptions_s client;
    // Also keeps the account logged in while the script is failed.
    bool watchScripts = false;
    bool waitForDebugger = false;
    // Without it, scripts can't plan routes beyond the loaded area.
    std::shared_ptr<const Navigation> navigation;
    std::chrono::milliseconds reloginDelay = 60s;
};

// Never throws, and never waits beyond Step's maxWait, so many accounts can share one loop. Its lifecycle is
// in docs/ScriptingDesign.md §8.
class Account
{
public:
    using Clock = std::chrono::steady_clock;

    static constexpr auto SUMMARY_INTERVAL = 10s;
    // Long enough to outlast the server's refusal to log out during combat and for 10 seconds after.
    static constexpr auto LOGOUT_TIMEOUT = 30s;

    Account(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, AccountConfig_s account, ScriptRuntime& runtime, std::shared_ptr<Logger> logger = Logger::GetDefault(), AccountOptions_s options = {}, BotMessenger* messenger = nullptr, std::shared_ptr<NetLoop> net = NetLoop::Create());
    ~Account();

    Account(const Account&) = delete;
    Account& operator=(const Account&) = delete;

    // Step does the rest.
    void Start();
    // For callers that run a single account.
    void Login();
    void Step(std::chrono::milliseconds maxWait);
    // The first interrupt gives a script with on_kill_signal killGraceSeconds to stop the account, and
    // otherwise logs out. One during a logout closes the connection without waiting for the server. One
    // during a relog ends the account logged out.
    void Interrupt();

    [[nodiscard]] bool IsStarted() const;
    [[nodiscard]] bool IsFinished() const;
    // Finished with a logout the server confirmed, and no failure.
    [[nodiscard]] bool Succeeded() const;
    [[nodiscard]] std::string_view DescribeOutcome() const;
    // For the console's status command.
    [[nodiscard]] std::string DescribeStatus() const;
    [[nodiscard]] std::vector<ScriptCommand_s> GetCommands() const;
    // False without a script.
    [[nodiscard]] bool SendCommand(ConsoleCommand_s command);
    // False, sending nothing, when the account isn't in game.
    [[nodiscard]] bool Say(std::string_view text);
    [[nodiscard]] std::optional<Clock::time_point> GetNextLoop() const;
    [[nodiscard]] const std::string& GetName() const;
    [[nodiscard]] const std::string& GetUsername() const;
    [[nodiscard]] const GameClient& GetClient() const;

private:
    [[nodiscard]] std::chrono::milliseconds GetWait(std::chrono::milliseconds maxWait) const;
    void StepScript(Clock::time_point now);
    void StepIdle(Clock::time_point now);
    void AddSettingDefaults(std::string_view botName, std::string_view settingsJson);
    void LogOut(std::string_view reason);
    void BeginRelog(std::chrono::seconds delay);
    // True while a relog is under way.
    bool StepRelog(Clock::time_point now);
    void Recover(std::string_view reason);
    void BeginRelogin();
    [[nodiscard]] bool IsStopping() const;
    [[nodiscard]] s64 GetReloginSeconds() const;
    void Fail(std::string_view reason);
    void UpdateFinished();

    std::shared_ptr<const Config_s> m_config;
    AccountConfig_s m_account;
    std::shared_ptr<Logger> m_logger;
    AccountOptions_s m_options;
    BotMessenger* m_messenger;
    GameClient m_client;
    ProgressReporter m_progress;
    std::optional<ScriptHost> m_script;
    bool m_started = false;
    bool m_finished = false;
    bool m_failed = false;
    // Logging out to end the account, so a failure on the way finishes it rather than logging back in.
    bool m_stopping = false;
    u32 m_interrupts = 0;
    std::optional<Clock::time_point> m_killDeadline;
    Clock::time_point m_nextSummary;
    // Without a script: when its idleSeconds are up, from the first step in game.
    std::optional<Clock::time_point> m_idleUntil;
    // relog(): the wait still to come once its logout is done, then when to log back in.
    std::optional<std::chrono::seconds> m_relogDelay;
    std::optional<Clock::time_point> m_reloginAt;
};
