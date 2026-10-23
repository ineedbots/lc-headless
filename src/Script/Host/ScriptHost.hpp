#pragma once

#include "../../Accounts/ProgressReport_s.hpp"
#include "../../Console/ConsoleCommand_s.hpp"
#include "../../Console/Logger.hpp"
#include "../../Game/GameActions.hpp"
#include "../../Game/GameClient.hpp"
#include "../../Game/Nav/Navigation.hpp"
#include "../../Game/State/GameEvent_s.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../../Utils/FileWatcher.hpp"
#include "../BotMessenger.hpp"
#include "../ScriptCommand_s.hpp"
#include "../ScriptContext.hpp"
#include "../ScriptControl.hpp"
#include "../ScriptRuntime.hpp"
#include "../ScriptVm.hpp"
#include "EventDispatcher.hpp"
#include "LoopSchedule.hpp"
#include "ScriptHooks.hpp"

#include <pocketpy.h>

enum class ScriptStatus_e : u8
{
    Running,
    // stop_script(): the account stays logged in and idles.
    Stopped,
    // stop_account(): the account should log out.
    AccountStopped,
    // A script error stopped it; the account should log out, unless the host is watching its files.
    Failed,
};

struct ScriptHostOptions_s
{
    std::filesystem::path scriptsDirectory;
    std::filesystem::path file;
    std::string settings = "{}";
    // Given a define_bot script's name and its schema's defaults, as a JSON object, each time the script
    // loads, so the account file can gain the settings it lacks.
    std::function<void(std::string_view botName, std::string_view settingsJson)> onSettingDefaults;
    // Given each value settings_store.save() saved, at the end of the step, for script.settings[name][key]
    // in the account file. The host keeps it in settings too, so a reloaded script sees it.
    std::function<void(const SettingSave_s& save)> onSettingSave;
    std::chrono::milliseconds callTimeout = 1000ms;
    // Where send_bot_message sends, and the username it sends under.
    BotMessenger* messenger = nullptr;
    std::string username;
    // A script that fails then waits for the next change.
    bool watchFiles = false;
    bool waitForDebugger = false;
    // Without it, the script can't plan routes beyond the loaded area.
    std::shared_ptr<const Navigation> navigation;
    // The runtime's upkeep each server tick: the random event guardian, the stall guard (off at zero) and
    // the run manager. Off by default, so tests see only what they ask for.
    bool randomEvents = false;
    std::chrono::minutes stallMinutes{0};
    bool runAuto = false;
    s32 runEnergyMin = 20;
};

// The script is loaded on construction, so a broken script fails before login.
class ScriptHost
{
public:
    using Clock = std::chrono::steady_clock;

    static constexpr std::size_t MAX_BOT_MESSAGES = 100;
    static constexpr std::size_t MAX_COMMANDS = 100;
    static constexpr auto WATCH_INTERVAL = 500ms;

    ScriptHost(ScriptRuntime& runtime, GameClient& client, ScriptHostOptions_s options, std::shared_ptr<Logger> logger = Logger::GetDefault());
    ~ScriptHost();

    ScriptHost(const ScriptHost&) = delete;
    ScriptHost& operator=(const ScriptHost&) = delete;

    void Step(Clock::time_point now);
    // Ends the bot, once, calling on_stop(reason) and script_finish, for an account that stops for a
    // reason of its own, such as Ctrl+C. Stopping the script, or its failing, already does.
    void Finish(std::string_view reason);
    [[nodiscard]] bool HandlesKillSignal() const;
    void SignalKill();
    // Queues a message from another script for the next Step. False when the script isn't running, has no
    // on_bot_message, or already has MAX_BOT_MESSAGES waiting.
    [[nodiscard]] bool ReceiveBotMessage(BotMessage_s message);
    // None once the script has stopped.
    [[nodiscard]] std::vector<ScriptCommand_s> GetCommands() const;
    // Queues a console command for the next Step that finds the player placed. False when the script isn't
    // running, hasn't added the command, or already has MAX_COMMANDS waiting.
    [[nodiscard]] bool ReceiveCommand(ConsoleCommand_s command);
    [[nodiscard]] ScriptStatus_e GetStatus() const;
    // Started and running, with the player placed and settled: when the loop and the hooks run.
    [[nodiscard]] bool IsActive() const;
    // When on_start first ran; a reload doesn't reset it.
    [[nodiscard]] std::optional<Clock::time_point> GetStartTime() const;
    [[nodiscard]] bool HasProgressReport() const;
    // What on_progress_report returns, with the run time from GetStartTime. Nullopt without the hook, or when it
    // raised, which fails the script.
    [[nodiscard]] std::optional<ProgressReport_s> RunProgressReport(Clock::time_point now);
    [[nodiscard]] std::optional<Clock::time_point> GetNextLoop() const;
    // The script's relog(delay) since the last call, for the account to carry out.
    [[nodiscard]] std::optional<std::chrono::seconds> TakeRelogRequest();

private:
    void Load();
    void LoadBot();
    void Unload();
    void Reload();
    void CheckForChanges(Clock::time_point now);
    void SkipToPresent();
    void SyncLogin();
    void Start(Clock::time_point now);
    void DispatchBotMessages();
    void DispatchCommands();
    void RunLoop(Clock::time_point now);
    void RunUpkeep(Clock::time_point now);
    void ScheduleLoop(Clock::time_point now, py_Ref wait);
    [[nodiscard]] bool HasHook(std::string_view name) const;
    void CallHook(std::string_view name, std::span<const py_Ref> args = {});
    // Calls the runtime's dispatch for the event, which returns what its hook returned.
    std::optional<py_GlobalRef> Dispatch(std::string_view name, std::span<const py_Ref> args = {});
    // where names the code that failed, such as "loop()".
    void Fail(std::string_view where, std::string_view message);
    void Stop(ScriptStatus_e status, std::string_view reason);
    void ApplyStopRequest();
    void SaveSettings();

    ScriptRuntime& m_runtime;
    GameClient& m_client;
    GameActions m_actions;
    ScriptContext m_context;
    std::shared_ptr<Logger> m_logger;
    ScriptHostOptions_s m_options;
    // Empty only while a reload is replacing it, or after a reload failed to load. The hooks go with it.
    std::optional<ScriptVm> m_vm;
    std::optional<ScriptHooks> m_hooks;
    EventDispatcher m_events;
    LoopSchedule m_schedule;
    std::optional<FileWatcher> m_watcher;
    std::deque<BotMessage_s> m_botMessages;
    std::deque<ConsoleCommand_s> m_commands;
    ScriptStatus_e m_status = ScriptStatus_e::Running;
    bool m_started = false;
    bool m_finished = false;
    bool m_connected = false;
    // Set by a reconnect and cleared once the player is placed again, when on_reconnect is called.
    bool m_reconnectPending = false;
    u32 m_loginCount = 0;
    u64 m_lastTick = 0;
    Clock::time_point m_nextWatch;
    // When on_start first ran, which progress reports count from.
    std::optional<Clock::time_point> m_startTime;
};
