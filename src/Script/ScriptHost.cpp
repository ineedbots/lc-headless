#include "pch.hpp"
#include "ScriptHost.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Core/FileWatcher.hpp"
#include "../Core/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/State/GameEvent_s.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Social_s.hpp"
#include "BotMessenger.hpp"
#include "ProgressReport_s.hpp"
#include "PyConvert.hpp"
#include "ScriptApi.hpp"
#include "ScriptBindings.hpp"
#include "ScriptError.hpp"
#include "ScriptRuntime.hpp"
#include "ScriptVm.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto LOOP = "loop"sv;
    constexpr auto START = "on_start"sv;
    constexpr auto PROGRESS_REPORT = "on_progress_report"sv;
    constexpr auto BOT_MESSAGE = "on_bot_message"sv;
    constexpr auto REPORT_ROWS = "_report_rows"sv;
    constexpr auto HOOK_PREFIX = "on_"sv;
    constexpr auto MILLISECONDS_PER_TICK = 600;
    constexpr auto MILLISECONDS_PER_SECOND = 1000;

    std::string_view GetTypeName(py_Ref value)
    {
        return py_tpname(py_typeof(value));
    }

    bool CollectHookName(py_Name name, py_Ref value, void* context) noexcept
    {
        const auto text = py_name2sv(name);
        const auto view = std::string_view{text.data, static_cast<std::size_t>(text.size)};
        if (view.starts_with(HOOK_PREFIX) && py_callable(value))
        {
            static_cast<std::vector<std::string>*>(context)->emplace_back(view);
        }

        return true;
    }
}

ScriptHost::ScriptHost(ScriptRuntime& runtime, GameClient& client, ScriptHostOptions_s options, std::shared_ptr<Logger> logger)
    : m_runtime{runtime}
    , m_client{client}
    , m_actions{client}
    , m_api{client.GetState(), client.GetMap(), m_actions, options.messenger, options.username}
    , m_logger{std::move(logger)}
    , m_options{std::move(options)}
{
    Load();
    if (m_options.progressInterval > std::chrono::minutes::zero() && !HasHook(PROGRESS_REPORT))
    {
        m_logger->Warning("{} has no on_progress_report(), so progressReportMinutes has no effect", m_options.file.generic_string());
    }

    if (m_options.watchFiles)
    {
        m_watcher.emplace(m_vm->GetFiles());
    }

    m_logger->Info("Loaded script {}", m_options.file.generic_string());
}

ScriptHost::~ScriptHost()
{
    Unload();
}

void ScriptHost::Step(Clock::time_point now)
{
    CheckForChanges(now);
    if (m_status != ScriptStatus_e::Running)
    {
        return;
    }

    if (!m_client.IsInGame())
    {
        if (m_connected)
        {
            m_connected = false;
            CallHook("on_disconnect");
        }

        return;
    }

    const auto& state = m_client.GetState();
    SyncLogin(state);
    if (!state.placed)
    {
        return;
    }

    if (!m_started)
    {
        Start(now);
    }

    if (m_reconnectPending)
    {
        m_reconnectPending = false;
        CallHook("on_reconnect");
    }

    DispatchEvents(state);
    DispatchMessages(state);
    DispatchBotMessages();
    if (state.tick != m_lastTick)
    {
        m_lastTick = state.tick;
        if (HasHook("on_server_tick"))
        {
            m_vm->Activate();
            py_newint(py_r0(), static_cast<s64>(state.tick));
            CallHook("on_server_tick", std::array{py_r0()});
        }
    }

    if (m_nextReport && now >= *m_nextReport)
    {
        m_nextReport = now + m_options.progressInterval;
        RunProgressReport(now);
    }

    if (now >= m_nextLoop)
    {
        RunLoop(now);
    }
}

bool ScriptHost::HandlesKillSignal() const
{
    return m_status == ScriptStatus_e::Running && HasHook("on_kill_signal");
}

void ScriptHost::SignalKill()
{
    CallHook("on_kill_signal");
}

bool ScriptHost::ReceiveBotMessage(BotMessage_s message)
{
    if (m_status != ScriptStatus_e::Running || !HasHook(BOT_MESSAGE) || m_botMessages.size() >= MAX_BOT_MESSAGES)
    {
        return false;
    }

    m_botMessages.push_back(std::move(message));
    return true;
}

ScriptStatus_e ScriptHost::GetStatus() const
{
    return m_status;
}

std::optional<ScriptHost::Clock::time_point> ScriptHost::GetNextLoop() const
{
    if (!m_started || m_status != ScriptStatus_e::Running)
    {
        return std::nullopt;
    }

    return m_nextLoop;
}

void ScriptHost::Load()
{
    m_vm.emplace(m_runtime, ScriptVmOptions_s{.scriptsDirectory = m_options.scriptsDirectory, .callTimeout = m_options.callTimeout}, m_logger);
    ScriptBindings::Bind(*m_vm, m_api);
    try
    {
        ScriptBindings::SetSettings(*m_vm, m_options.settings);
        if (m_options.waitForDebugger)
        {
            m_vm->WaitForDebugger();
        }

        m_vm->RunFile(m_options.file);
        if (!m_vm->HasFunction(LOOP))
        {
            throw ScriptError{std::format("{} has no loop() function", m_options.file.generic_string())};
        }

        FindHooks();
    }
    catch (const std::exception&)
    {
        ScriptBindings::Unbind(*m_vm);
        throw;
    }
}

void ScriptHost::Unload()
{
    m_hooks.clear();
    if (!m_vm)
    {
        return;
    }

    ScriptBindings::Unbind(*m_vm);
    m_vm.reset();
}

void ScriptHost::Reload()
{
    m_logger->Info("The script's files changed; reloading {}", m_options.file.generic_string());
    Unload();
    SkipToPresent();
    m_status = ScriptStatus_e::Running;
    m_started = false;
    static_cast<void>(m_api.TakeStopRequest());

    auto files = std::vector<std::filesystem::path>{};
    try
    {
        Load();
        files = m_vm->GetFiles();
    }
    catch (const std::exception& e)
    {
        files = m_vm ? m_vm->GetFiles() : std::vector{m_options.scriptsDirectory / m_options.file};
        Unload();
        m_status = ScriptStatus_e::Failed;
        m_logger->Error("The changed script can't run, so it waits for its files to change again:\n{}", e.what());
    }

    m_watcher.emplace(std::move(files));
}

void ScriptHost::CheckForChanges(Clock::time_point now)
{
    if (!m_watcher || now < m_nextWatch)
    {
        return;
    }

    m_nextWatch = now + WATCH_INTERVAL;
    if (m_watcher->Check())
    {
        Reload();
    }
}

// A reloaded script starts from now: what happened before it loaded isn't passed to it.
void ScriptHost::SkipToPresent()
{
    const auto& state = m_client.GetState();
    m_lastEvent = state.eventCount;
    m_lastMessage = state.messageCount;
    m_lastTick = state.tick;
    m_loginCount = m_client.GetLoginCount();
    m_connected = false;
    m_reconnectPending = false;
}

void ScriptHost::FindHooks()
{
    auto defined = std::vector<std::string>{};
    py_applydict(m_vm->GetMain(), CollectHookName, &defined);
    for (const auto& name : defined)
    {
        const auto hook = std::ranges::find(HOOKS, std::string_view{name});
        if (hook == HOOKS.end())
        {
            m_logger->Warning("{} defines {}(), which isn't a hook the client calls", m_options.file.generic_string(), name);
            continue;
        }

        m_hooks.push_back(*hook);
    }
}

void ScriptHost::SyncLogin(const GameState_s& state)
{
    m_connected = true;
    const auto loginCount = m_client.GetLoginCount();
    if (loginCount == m_loginCount)
    {
        return;
    }

    const auto reconnected = m_loginCount != 0;
    m_loginCount = loginCount;

    // A fresh login resets the state, so its numbering and ticks start over.
    if (state.eventCount < m_lastEvent || state.messageCount < m_lastMessage || state.tick < m_lastTick)
    {
        m_lastEvent = 0;
        m_lastMessage = 0;
        m_lastTick = 0;
    }

    // A reconnect that became a fresh login, as after a server restart, isn't placed yet, so the hook
    // waits until it is and the script sees where the player is.
    m_reconnectPending = reconnected && m_started;
}

void ScriptHost::Start(Clock::time_point now)
{
    m_started = true;
    m_nextLoop = now;
    if (!m_startTime)
    {
        m_startTime = now;
        if (m_options.progressInterval > std::chrono::minutes::zero())
        {
            m_nextReport = now + m_options.progressInterval;
        }
    }

    CallHook(START);
}

void ScriptHost::DispatchEvents(const GameState_s& state)
{
    const auto events = state.GetEventsAfter(m_lastEvent);
    if (!events.empty() && events.front()->sequence != m_lastEvent + 1)
    {
        m_logger->Warning("{} game events were dropped before the script saw them", events.front()->sequence - m_lastEvent - 1);
    }

    for (const auto* event : events)
    {
        m_lastEvent = event->sequence;
        if (m_status == ScriptStatus_e::Running)
        {
            DispatchEvent(*event, state);
        }
    }
}

void ScriptHost::DispatchEvent(const GameEvent_s& event, const GameState_s& state)
{
    const auto& data = event.data;
    const auto tick = state.tick;
    const auto& cache = m_client.GetCache();
    m_vm->Activate();
    const auto one = std::array{py_r0()};
    const auto two = std::array{py_r0(), py_r1()};

    if (const auto* added = std::get_if<NpcAdded_s>(&data); added && HasHook("on_npc_spawned"))
    {
        const auto* current = state.FindNpc(added->npc.index);
        PyConvert::FromNpc(py_r0(), current ? *current : added->npc, tick, cache);
        CallHook("on_npc_spawned", one);
    }
    else if (const auto* removed = std::get_if<NpcRemoved_s>(&data); removed && HasHook("on_npc_despawned"))
    {
        PyConvert::FromNpc(py_r0(), removed->npc, tick, cache);
        CallHook("on_npc_despawned", one);
    }
    else if (const auto* npcHit = std::get_if<NpcHit_s>(&data); npcHit && HasHook("on_npc_damaged"))
    {
        const auto* npc = state.FindNpc(npcHit->index);
        if (npc == nullptr)
        {
            py_newnone(py_r0());
        }
        else
        {
            PyConvert::FromNpc(py_r0(), *npc, tick, cache);
        }

        py_newint(py_r1(), npcHit->hit.damage);
        CallHook("on_npc_damaged", two);
    }
    else if (const auto* playerAdded = std::get_if<PlayerAdded_s>(&data); playerAdded && HasHook("on_player_spawned"))
    {
        const auto* current = state.FindPlayer(playerAdded->player.index);
        PyConvert::FromPlayer(py_r0(), current ? *current : playerAdded->player, tick);
        CallHook("on_player_spawned", one);
    }
    else if (const auto* playerRemoved = std::get_if<PlayerRemoved_s>(&data); playerRemoved && HasHook("on_player_despawned"))
    {
        PyConvert::FromPlayer(py_r0(), playerRemoved->player, tick);
        CallHook("on_player_despawned", one);
    }
    else if (const auto* playerHit = std::get_if<PlayerHit_s>(&data); playerHit && HasHook("on_player_damaged"))
    {
        const auto* player = state.FindPlayer(playerHit->index);
        if (player == nullptr)
        {
            py_newnone(py_r0());
        }
        else
        {
            PyConvert::FromPlayer(py_r0(), *player, tick);
        }

        py_newint(py_r1(), playerHit->hit.damage);
        CallHook("on_player_damaged", two);
    }
    else if (const auto* localHit = std::get_if<LocalHit_s>(&data); localHit && HasHook("on_damaged"))
    {
        py_newint(py_r0(), localHit->hit.damage);
        CallHook("on_damaged", one);
    }
    else if (const auto* itemAdded = std::get_if<GroundItemAdded_s>(&data); itemAdded && HasHook("on_ground_item_spawned"))
    {
        PyConvert::FromGroundItem(py_r0(), itemAdded->item, cache);
        CallHook("on_ground_item_spawned", one);
    }
    else if (const auto* itemRemoved = std::get_if<GroundItemRemoved_s>(&data); itemRemoved && HasHook("on_ground_item_despawned"))
    {
        PyConvert::FromGroundItem(py_r0(), itemRemoved->item, cache);
        CallHook("on_ground_item_despawned", one);
    }
    else if (const auto* itemCount = std::get_if<GroundItemCountChanged_s>(&data); itemCount && HasHook("on_ground_item_changed"))
    {
        PyConvert::FromGroundItem(py_r0(), itemCount->item, cache);
        py_newint(py_r1(), itemCount->previousCount);
        CallHook("on_ground_item_changed", two);
    }
    else if (const auto* loc = std::get_if<LocChanged_s>(&data); loc && HasHook("on_loc_changed"))
    {
        const auto& change = loc->change;
        const auto scene = SceneLoc_s{.tile = change.tile, .layer = change.layer, .id = change.id, .shape = change.shape, .angle = change.angle, .changed = true};
        PyConvert::FromLoc(py_r0(), scene, cache);
        CallHook("on_loc_changed", one);
    }
    else if (const auto* inventory = std::get_if<InventoryChanged_s>(&data); inventory && HasHook("on_inventory_changed"))
    {
        py_newint(py_r0(), inventory->com);
        CallHook("on_inventory_changed", one);
    }
    else if (const auto* stat = std::get_if<StatChanged_s>(&data); stat && HasHook("on_stat_changed"))
    {
        py_newint(py_r0(), stat->stat);
        CallHook("on_stat_changed", one);
    }
    else if (const auto* varp = std::get_if<VarpChanged_s>(&data); varp && HasHook("on_varp_changed"))
    {
        py_newint(py_r0(), varp->varp);
        py_newint(py_r1(), varp->value);
        CallHook("on_varp_changed", two);
    }
    else if (std::holds_alternative<ModalChanged_s>(data))
    {
        CallHook("on_interface_changed");
    }
    else if (const auto* reboot = std::get_if<RebootStarted_s>(&data); reboot && HasHook("on_system_update"))
    {
        py_newint(py_r0(), reboot->ticks * MILLISECONDS_PER_TICK / MILLISECONDS_PER_SECOND);
        CallHook("on_system_update", one);
    }
}

void ScriptHost::DispatchMessages(const GameState_s& state)
{
    for (const auto* message : state.GetMessagesAfter(m_lastMessage))
    {
        m_lastMessage = message->sequence;
        if (m_status != ScriptStatus_e::Running)
        {
            continue;
        }

        m_vm->Activate();
        PyConvert::FromString(py_r0(), message->text);
        PyConvert::FromString(py_r1(), message->sender);
        switch (message->type)
        {
        case MessageType_e::Game:
            CallHook("on_server_message", std::array{py_r0()});
            break;
        case MessageType_e::Public:
            CallHook("on_chat_message", std::array{py_r0(), py_r1()});
            break;
        case MessageType_e::Private:
            CallHook("on_private_message", std::array{py_r0(), py_r1()});
            break;
        case MessageType_e::TradeRequest:
            CallHook("on_trade_request", std::array{py_r1()});
            break;
        case MessageType_e::DuelRequest:
            CallHook("on_duel_request", std::array{py_r1()});
            break;
        case MessageType_e::Say:
            break;
        }
    }
}

// Messages that arrive while these are handled, including any the script sends itself, wait for the next Step.
void ScriptHost::DispatchBotMessages()
{
    const auto messages = std::exchange(m_botMessages, {});
    for (const auto& message : messages)
    {
        if (m_status != ScriptStatus_e::Running || !HasHook(BOT_MESSAGE))
        {
            return;
        }

        // Registers belong to the current VM, so they're named only once LoadJson has switched to this one.
        auto value = py_GlobalRef{};
        try
        {
            value = m_vm->LoadJson(message.json);
        }
        catch (const ScriptError& e)
        {
            m_logger->Warning("Dropped a bot message from {} that couldn't be read:\n{}", message.sender, e.what());
            continue;
        }

        py_assign(py_r1(), value);
        PyConvert::FromString(py_r0(), message.sender);
        CallHook(BOT_MESSAGE, std::array{py_r0(), py_r1()});
    }
}

void ScriptHost::RunProgressReport(Clock::time_point now)
{
    if (m_status != ScriptStatus_e::Running || !HasHook(PROGRESS_REPORT))
    {
        return;
    }

    const auto result = Invoke(PROGRESS_REPORT);
    if (!result)
    {
        return;
    }

    auto report = ProgressReport_s{.runTime = std::chrono::floor<std::chrono::seconds>(now - *m_startTime)};
    try
    {
        // The prelude checks the result and turns it into text, so a failing __str__ has a traceback.
        m_vm->Activate();
        py_assign(py_r0(), *result);
        const auto rows = m_vm->CallBuiltin(REPORT_ROWS, std::array{py_r0()});
        for (auto i = 0; i < py_list_len(rows); ++i)
        {
            const auto row = py_list_getitem(rows, i);
            report.rows.emplace_back(PyConvert::ToString(py_list_getitem(row, 0), "name"), PyConvert::ToString(py_list_getitem(row, 1), "value"));
        }
    }
    catch (const ScriptError& e)
    {
        Fail(PROGRESS_REPORT, e.what());
        return;
    }

    if (m_options.onProgressReport)
    {
        m_options.onProgressReport(report);
    }
}

void ScriptHost::RunLoop(Clock::time_point now)
{
    if (m_status != ScriptStatus_e::Running)
    {
        return;
    }

    const auto result = Invoke(LOOP);
    if (!result || m_status != ScriptStatus_e::Running)
    {
        return;
    }

    if (!py_isint(*result))
    {
        Fail(LOOP, std::format("loop() must return how many milliseconds to wait, as an int, not {}", GetTypeName(*result)));
        return;
    }

    const auto delay = py_toint(*result);
    if (delay < 0)
    {
        Fail(LOOP, std::format("loop() returned {}; return 0 or more milliseconds", delay));
        return;
    }

    m_nextLoop = now + std::chrono::milliseconds{delay};
}

bool ScriptHost::HasHook(std::string_view name) const
{
    return std::ranges::find(m_hooks, name) != m_hooks.end();
}

void ScriptHost::CallHook(std::string_view name, std::span<const py_Ref> args)
{
    if (m_status != ScriptStatus_e::Running || !HasHook(name))
    {
        return;
    }

    static_cast<void>(Invoke(name, args));
}

std::optional<py_GlobalRef> ScriptHost::Invoke(std::string_view name, std::span<const py_Ref> args)
{
    try
    {
        const auto result = m_vm->Call(name, args);
        ApplyStopRequest();
        return result;
    }
    catch (const ScriptError& e)
    {
        Fail(name, e.what());
        return std::nullopt;
    }
}

void ScriptHost::Fail(std::string_view function, std::string_view message)
{
    m_status = ScriptStatus_e::Failed;
    if (m_watcher)
    {
        m_logger->Error("Script error in {}(), so the script has stopped until its files change:\n{}", function, message);
        return;
    }

    m_logger->Error("Script error in {}(), so the script has stopped:\n{}", function, message);
}

void ScriptHost::ApplyStopRequest()
{
    switch (m_api.TakeStopRequest())
    {
    case StopRequest_e::None:
        return;
    case StopRequest_e::Script:
        m_status = ScriptStatus_e::Stopped;
        m_logger->Info("The script stopped itself; the account stays logged in");
        return;
    case StopRequest_e::Account:
        m_status = ScriptStatus_e::AccountStopped;
        m_logger->Info("The script asked to log the account out");
        return;
    }
}
