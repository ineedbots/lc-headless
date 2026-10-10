#pragma once

#include "../Core/FileWatcher.hpp"
#include "../Core/Logger.hpp"
#include "../Game/GameActions.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/Nav/NavGraph.hpp"
#include "../Game/State/GameEvent_s.hpp"
#include "../Game/State/GameState_s.hpp"
#include "BotMessenger.hpp"
#include "ProgressReport_s.hpp"
#include "ScriptApi.hpp"
#include "ScriptRuntime.hpp"
#include "ScriptVm.hpp"

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
    std::chrono::milliseconds callTimeout = 1000ms;
    // How often on_progress_report is called, with what it returns going to onProgressReport; zero for never.
    std::chrono::minutes progressInterval{0};
    std::function<void(const ProgressReport_s&)> onProgressReport;
    // Where send_bot_message sends, and the username it sends under.
    BotMessenger* messenger = nullptr;
    std::string username;
    // Reload the script when its files change. A script that fails then waits for the next change.
    bool watchFiles = false;
    // Wait for VS Code's pocketpy debugger to attach before running the script.
    bool waitForDebugger = false;
    // For routes beyond the loaded area; without it, the script can't plan them.
    std::shared_ptr<const Navigation_s> navigation;
    // Run the stdlib's random event guardian each server tick.
    bool randomEvents = false;
};

// Runs one account's bot against its client, on the caller's thread between pumps. The script is loaded
// on construction, and the standard library's runtime makes its bot and checks its settings, so a broken
// script fails before login. Once the local player is placed the bot starts; then every Step passes new
// events, messages and bot messages to its hooks and subscribers, and steps its loop whenever the wait
// it last asked for is over: a time, the next update from the server, or a number of server ticks.
class ScriptHost
{
public:
    using Clock = std::chrono::steady_clock;

    static constexpr std::size_t MAX_BOT_MESSAGES = 100;
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
    [[nodiscard]] ScriptStatus_e GetStatus() const;
    [[nodiscard]] std::optional<Clock::time_point> GetNextLoop() const;

private:
    enum class LoopWait_e : u8
    {
        Time,
        Update,
        Ticks,
    };

    void Load();
    void LoadBot();
    void Unload();
    void Reload();
    void CheckForChanges(Clock::time_point now);
    void SkipToPresent();
    void FindHooks();
    void SyncLogin(const GameState_s& state);
    void Start(Clock::time_point now);
    void DispatchEvents(const GameState_s& state);
    void DispatchEvent(const GameEvent_s& event, const GameState_s& state);
    void DispatchBackpack(const GameState_s& state);
    void DispatchMessages(const GameState_s& state);
    void DispatchBotMessages();
    void RunProgressReport(Clock::time_point now);
    [[nodiscard]] bool IsLoopDue(Clock::time_point now, const GameState_s& state) const;
    void RunLoop(Clock::time_point now);
    void RunGuard(Clock::time_point now);
    void ScheduleLoop(Clock::time_point now, py_Ref wait);
    [[nodiscard]] bool HasHook(std::string_view name) const;
    void CallHook(std::string_view name, std::span<const py_Ref> args = {});
    // Calls the runtime's dispatch for the event, which returns what its hook returned.
    std::optional<py_GlobalRef> Dispatch(std::string_view name, std::span<const py_Ref> args = {});
    void Fail(std::string_view function, std::string_view message);
    void Stop(ScriptStatus_e status, std::string_view reason);
    void ApplyStopRequest();

    ScriptRuntime& m_runtime;
    GameClient& m_client;
    GameActions m_actions;
    ScriptApi m_api;
    std::shared_ptr<Logger> m_logger;
    ScriptHostOptions_s m_options;
    // Empty only while a reload is replacing it, or after a reload failed to load.
    std::optional<ScriptVm> m_vm;
    std::optional<FileWatcher> m_watcher;
    std::deque<BotMessage_s> m_botMessages;
    // The backpack as the bot last saw it, which inventory_changed reports changes to, slot by slot.
    std::vector<Item_s> m_backpack;
    ScriptStatus_e m_status = ScriptStatus_e::Running;
    bool m_started = false;
    bool m_finished = false;
    bool m_connected = false;
    // Set by a reconnect and cleared once the player is placed again, when on_reconnect is called.
    bool m_reconnectPending = false;
    u32 m_loginCount = 0;
    u64 m_lastEvent = 0;
    u64 m_lastMessage = 0;
    u64 m_lastTick = 0;
    // What the loop waits for: until m_nextLoop; for an update after m_waitUpdateCount, or until
    // m_nextLoop when m_waitHasTimeout; or for the tick to reach m_waitTick.
    LoopWait_e m_wait = LoopWait_e::Time;
    Clock::time_point m_nextLoop;
    u64 m_waitUpdateCount = 0;
    bool m_waitHasTimeout = false;
    u64 m_waitTick = 0;
    u64 m_waitTickStart = 0;
    Clock::time_point m_nextWatch;
    // When on_start first ran, which progress reports count from.
    std::optional<Clock::time_point> m_startTime;
    std::optional<Clock::time_point> m_nextReport;
};
