#pragma once

#include "../Core/Logger.hpp"
#include "../Game/GameActions.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/State/GameEvent_s.hpp"
#include "../Game/State/GameState_s.hpp"
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
    // A script error stopped it; the account should log out.
    Failed,
};

struct ScriptHostOptions_s
{
    std::filesystem::path scriptsDirectory;
    std::filesystem::path file;
    std::string settings = "{}";
    std::chrono::milliseconds callTimeout = 1000ms;
};

// Runs one account's script against its client, on the caller's thread between pumps. The script is
// loaded on construction, so a broken script fails before login. Once the local player is placed it
// calls on_start, then on every Step passes new events and messages to the script's hooks and calls
// loop() whenever the delay it last returned has passed.
class ScriptHost
{
public:
    using Clock = std::chrono::steady_clock;

    static constexpr std::array HOOKS = {
        "on_start"sv,
        "on_server_tick"sv,
        "on_server_message"sv,
        "on_chat_message"sv,
        "on_private_message"sv,
        "on_trade_request"sv,
        "on_duel_request"sv,
        "on_npc_spawned"sv,
        "on_npc_despawned"sv,
        "on_npc_damaged"sv,
        "on_player_spawned"sv,
        "on_player_despawned"sv,
        "on_player_damaged"sv,
        "on_damaged"sv,
        "on_ground_item_spawned"sv,
        "on_ground_item_despawned"sv,
        "on_ground_item_changed"sv,
        "on_loc_changed"sv,
        "on_inventory_changed"sv,
        "on_stat_changed"sv,
        "on_varp_changed"sv,
        "on_interface_changed"sv,
        "on_system_update"sv,
        "on_disconnect"sv,
        "on_reconnect"sv,
        "on_kill_signal"sv,
    };

    ScriptHost(ScriptRuntime& runtime, GameClient& client, ScriptHostOptions_s options, std::shared_ptr<Logger> logger = Logger::GetDefault());
    ~ScriptHost();

    ScriptHost(const ScriptHost&) = delete;
    ScriptHost& operator=(const ScriptHost&) = delete;

    void Step(Clock::time_point now);
    [[nodiscard]] bool HandlesKillSignal() const;
    void SignalKill();
    [[nodiscard]] ScriptStatus_e GetStatus() const;
    [[nodiscard]] std::optional<Clock::time_point> GetNextLoop() const;

private:
    void FindHooks();
    void SyncLogin(const GameState_s& state);
    void DispatchEvents(const GameState_s& state);
    void DispatchEvent(const GameEvent_s& event, const GameState_s& state);
    void DispatchMessages(const GameState_s& state);
    void RunLoop(Clock::time_point now);
    [[nodiscard]] bool HasHook(std::string_view name) const;
    void CallHook(std::string_view name, std::span<const py_Ref> args = {});
    std::optional<py_GlobalRef> Invoke(std::string_view name, std::span<const py_Ref> args = {});
    void Fail(std::string_view function, std::string_view message);
    void ApplyStopRequest();

    GameClient& m_client;
    GameActions m_actions;
    ScriptApi m_api;
    std::shared_ptr<Logger> m_logger;
    ScriptVm m_vm;
    std::filesystem::path m_file;
    std::vector<std::string_view> m_hooks;
    ScriptStatus_e m_status = ScriptStatus_e::Running;
    bool m_started = false;
    bool m_connected = false;
    // Set by a reconnect and cleared once the player is placed again, when on_reconnect is called.
    bool m_reconnectPending = false;
    u32 m_loginCount = 0;
    u64 m_lastEvent = 0;
    u64 m_lastMessage = 0;
    u64 m_lastTick = 0;
    Clock::time_point m_nextLoop;
};
