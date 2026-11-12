#pragma once

#include "../Console/Type/CommandQueueResult_e.hpp"
#include "../Console/CommandExecution.hpp"

#include "../Cache/Type/GameCache_s.hpp"
#include "../Config/Type/AccountConfig_s.hpp"
#include "../Config/Type/Config_s.hpp"
#include "../Console/Type/ConsoleCommand_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/Nav/Navigation.hpp"
#include "../Io/NetLoop.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/Host/ScriptHost.hpp"
#include "../Script/Type/ScriptCommand_s.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "AccountLifecycle.hpp"
#include "AccountReporting.hpp"
#include "Type/ProgressReport_s.hpp"

struct AccountOptions_s
{
    GameClientOptions_s client;
    // Also keeps the account logged in while the script is failed.
    bool watchScripts = false;
    bool waitForDebugger = false;
    // Empty unless --profile enabled this run.
    std::filesystem::path profileDirectory;
    // Without it, scripts can't plan routes beyond the loaded area.
    std::shared_ptr<const Navigation> navigation;
    std::chrono::milliseconds reloginDelay = 60s;
    std::function<void(std::string_view, const ProgressReport_s&)> onProgressReport;
};

// Never throws, and never waits beyond Step's maxWait, so many accounts can share one loop. Its lifecycle is
// in docs/design/ScriptingDesign.md Â§8.
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
    void CloseNetwork();
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
    [[nodiscard]] bool SendCommand(ConsoleCommand_s command, std::shared_ptr<CommandRecipient> recipient = {});
    [[nodiscard]] CommandQueueResult_e QueueCommand(ConsoleCommand_s command, std::shared_ptr<CommandRecipient> recipient = {});
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
    void SaveSetting(const SettingSave_s& save);
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
    AccountReporting m_reporting;
    std::optional<ScriptHost> m_script;
    AccountLifecycle m_lifecycle;
    Clock::time_point m_nextSummary;
};
