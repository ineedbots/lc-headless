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
    // The standard library's runtime (rs2004/_runtime.py), as the bootstrap names it in builtins.
    constexpr auto LOAD_BOT = "_rt_load"sv;
    constexpr auto SETTING_DEFAULTS = "_rt_setting_defaults"sv;
    constexpr auto START_BOT = "_rt_start"sv;
    constexpr auto DISPATCH = "_rt_dispatch"sv;
    constexpr auto STEP = "_rt_step"sv;
    constexpr auto CONFIGURE = "_rt_configure"sv;
    constexpr auto UPKEEP = "_rt_upkeep"sv;
    constexpr auto FINISH = "_rt_finish"sv;
    constexpr auto LISTENING = "_listening";
    constexpr auto SETTINGS = "settings";
    constexpr auto REPORT_ROWS = "_report_rows"sv;

    constexpr auto PROGRESS_REPORT = "progress_report"sv;
    constexpr auto BOT_MESSAGE = "bot_message"sv;
    constexpr auto INVENTORY_CHANGED = "inventory_changed"sv;
    constexpr auto WAIT_MS = "ms"sv;
    constexpr auto WAIT_UPDATE = "update"sv;
    constexpr auto MILLISECONDS_PER_TICK = 600;
    constexpr auto HITPOINTS = u8{3};
    constexpr auto MILLISECONDS_PER_SECOND = 1000;

    // rs2b0t's ChatLine type, as names rather than the webclient's numbers.
    std::optional<std::string_view> DescribeChatType(MessageType_e type)
    {
        switch (type)
        {
        case MessageType_e::Game:
            return "game"sv;
        case MessageType_e::Public:
            return "public"sv;
        case MessageType_e::Private:
            return "private"sv;
        case MessageType_e::TradeRequest:
            return "trade_request"sv;
        case MessageType_e::DuelRequest:
            return "duel_request"sv;
        case MessageType_e::Say:
            return std::nullopt;
        }

        return std::nullopt;
    }

    void FromOptionalString(py_OutRef out, std::string_view text)
    {
        if (text.empty())
        {
            py_newnone(out);
            return;
        }

        PyConvert::FromString(out, text);
    }
}

ScriptHost::ScriptHost(ScriptRuntime& runtime, GameClient& client, ScriptHostOptions_s options, std::shared_ptr<Logger> logger)
    : m_runtime{runtime}
    , m_client{client}
    , m_actions{client}
    , m_api{client.GetState(), client.GetMap(), m_actions, options.messenger, options.username, options.navigation}
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
    m_api.SetStepTime(std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count());
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
            CallHook("disconnect");
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
        CallHook("reconnect");
    }

    DispatchEvents(state);
    DispatchMessages(state);
    DispatchBotMessages();
    if (state.tick != m_lastTick)
    {
        m_lastTick = state.tick;
        if (m_status == ScriptStatus_e::Running && HasHook("tick"))
        {
            m_vm->Activate();
            py_newint(py_r0(), static_cast<s64>(state.tick));
            CallHook("tick", std::array{py_r0()});
        }

        if (m_status == ScriptStatus_e::Running)
        {
            RunUpkeep(now);
        }
    }

    if (m_nextReport && now >= *m_nextReport)
    {
        m_nextReport = now + m_options.progressInterval;
        RunProgressReport(now);
    }

    if (m_status == ScriptStatus_e::Running && IsLoopDue(now, state))
    {
        RunLoop(now);
    }
}

void ScriptHost::Finish(std::string_view reason)
{
    if (m_finished || !m_started || !m_vm)
    {
        return;
    }

    m_finished = true;
    m_vm->Activate();
    PyConvert::FromString(py_r0(), reason);
    try
    {
        static_cast<void>(m_vm->CallBuiltin(FINISH, std::array{py_r0()}));
    }
    catch (const ScriptError& e)
    {
        m_logger->Error("Script error while the script stopped, in on_stop() or a script_finish callback:\n{}", e.what());
    }

    // A stop asked for while stopping changes nothing.
    static_cast<void>(m_api.TakeStopRequest());
}

bool ScriptHost::HandlesKillSignal() const
{
    return m_status == ScriptStatus_e::Running && HasHook("kill_signal");
}

void ScriptHost::SignalKill()
{
    CallHook("kill_signal");
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

std::optional<std::chrono::seconds> ScriptHost::TakeRelogRequest()
{
    return m_api.TakeRelogRequest();
}

std::optional<ScriptHost::Clock::time_point> ScriptHost::GetNextLoop() const
{
    if (!m_started || m_status != ScriptStatus_e::Running)
    {
        return std::nullopt;
    }

    // A wait for the server has no time, unless it has a timeout too.
    if (m_wait == LoopWait_e::Ticks || (m_wait == LoopWait_e::Update && !m_waitHasTimeout))
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
        LoadBot();
    }
    catch (const std::exception&)
    {
        ScriptBindings::Unbind(*m_vm);
        throw;
    }
}

// The runtime makes the bot, from BOT or from the module's loop() and hooks, and checks its settings.
void ScriptHost::LoadBot()
{
    const auto main = m_vm->GetMain();
    if (py_getdict(main, py_name("BOT")) == nullptr && !m_vm->HasFunction("loop"))
    {
        throw ScriptError{std::format("{} has neither BOT = define_bot(...) nor a loop() function", m_options.file.generic_string())};
    }

    m_vm->Activate();
    py_assign(py_r0(), main);
    py_assign(py_r1(), py_getdict(m_vm->GetBuiltins(), py_name(SETTINGS)));
    auto warnings = std::vector<std::string>{};
    try
    {
        const auto result = m_vm->CallBuiltin(LOAD_BOT, std::array{py_r0(), py_r1()});
        for (auto i = 0; i < py_list_len(result); ++i)
        {
            warnings.push_back(PyConvert::ToString(py_list_getitem(result, i), "warning"));
        }
    }
    catch (const ScriptError& e)
    {
        throw ScriptError{std::format("{} can't run:\n{}", m_options.file.generic_string(), e.what())};
    }

    for (const auto& warning : warnings)
    {
        m_logger->Warning("{} {}", m_options.file.generic_string(), warning);
    }

    if (m_options.onSettingDefaults)
    {
        m_vm->Activate();
        const auto defaults = m_vm->CallBuiltin(SETTING_DEFAULTS);
        if (!py_isnone(defaults))
        {
            const auto botName = PyConvert::ToString(py_list_getitem(defaults, 0), "the bot's name");
            const auto settingsJson = PyConvert::ToString(py_list_getitem(defaults, 1), "the default settings");
            m_options.onSettingDefaults(botName, settingsJson);
        }
    }

    m_vm->Activate();
    py_newbool(py_r0(), m_options.randomEvents);
    py_newint(py_r1(), m_options.stallMinutes.count());
    py_newbool(py_r2(), m_options.runAuto);
    py_newint(py_r3(), m_options.runEnergyMin);
    static_cast<void>(m_vm->CallBuiltin(CONFIGURE, std::array{py_r0(), py_r1(), py_r2(), py_r3()}));
}

void ScriptHost::Unload()
{
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
    if (m_status == ScriptStatus_e::Running)
    {
        Finish("the script's files changed");
    }

    Unload();
    SkipToPresent();
    m_status = ScriptStatus_e::Running;
    m_started = false;
    m_finished = false;
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
    const auto* backpack = state.FindInventory(m_client.GetCache().inventoryComponent);
    m_backpack = backpack ? backpack->slots : std::vector<Item_s>{};
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

    // A fresh login resets the state, so its numbering, ticks and backpack start over.
    if (state.eventCount < m_lastEvent || state.messageCount < m_lastMessage || state.tick < m_lastTick)
    {
        m_lastEvent = 0;
        m_lastMessage = 0;
        m_lastTick = 0;
        m_backpack.clear();
    }

    // A reconnect that became a fresh login, as after a server restart, isn't placed yet, so the hook
    // waits until it is and the script sees where the player is.
    m_reconnectPending = reconnected && m_started;
}

void ScriptHost::Start(Clock::time_point now)
{
    m_started = true;
    m_wait = LoopWait_e::Time;
    m_nextLoop = now;
    if (!m_startTime)
    {
        m_startTime = now;
        if (m_options.progressInterval > std::chrono::minutes::zero())
        {
            m_nextReport = now + m_options.progressInterval;
        }
    }

    // An on_start that's a generator runs as the bot's first step.
    try
    {
        static_cast<void>(m_vm->CallBuiltin(START_BOT));
        ApplyStopRequest();
    }
    catch (const ScriptError& e)
    {
        Fail("on_start", e.what());
    }
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
    const auto three = std::array{py_r0(), py_r1(), py_r2()};

    if (const auto* added = std::get_if<NpcAdded_s>(&data); added && HasHook("npc_spawned"))
    {
        const auto* current = state.FindNpc(added->npc.index);
        PyConvert::FromNpc(py_r0(), current ? *current : added->npc, tick, cache);
        CallHook("npc_spawned", one);
    }
    else if (const auto* removed = std::get_if<NpcRemoved_s>(&data); removed && HasHook("npc_despawned"))
    {
        PyConvert::FromNpc(py_r0(), removed->npc, tick, cache);
        CallHook("npc_despawned", one);
    }
    else if (const auto* npcHit = std::get_if<NpcHit_s>(&data); npcHit && HasHook("npc_damaged"))
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
        CallHook("npc_damaged", two);
    }
    else if (const auto* playerAdded = std::get_if<PlayerAdded_s>(&data); playerAdded && HasHook("player_spawned"))
    {
        const auto* current = state.FindPlayer(playerAdded->player.index);
        PyConvert::FromPlayer(py_r0(), current ? *current : playerAdded->player, tick);
        CallHook("player_spawned", one);
    }
    else if (const auto* playerRemoved = std::get_if<PlayerRemoved_s>(&data); playerRemoved && HasHook("player_despawned"))
    {
        PyConvert::FromPlayer(py_r0(), playerRemoved->player, tick);
        CallHook("player_despawned", one);
    }
    else if (const auto* playerHit = std::get_if<PlayerHit_s>(&data); playerHit && HasHook("player_damaged"))
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
        CallHook("player_damaged", two);
    }
    else if (const auto* localHit = std::get_if<LocalHit_s>(&data); localHit && HasHook("damaged"))
    {
        py_newint(py_r0(), localHit->hit.damage);
        CallHook("damaged", one);
    }
    else if (const auto* itemAdded = std::get_if<GroundItemAdded_s>(&data); itemAdded && HasHook("ground_item_spawned"))
    {
        PyConvert::FromGroundItem(py_r0(), itemAdded->item, cache);
        CallHook("ground_item_spawned", one);
    }
    else if (const auto* itemRemoved = std::get_if<GroundItemRemoved_s>(&data); itemRemoved && HasHook("ground_item_despawned"))
    {
        PyConvert::FromGroundItem(py_r0(), itemRemoved->item, cache);
        CallHook("ground_item_despawned", one);
    }
    else if (const auto* itemCount = std::get_if<GroundItemCountChanged_s>(&data); itemCount && HasHook("ground_item_changed"))
    {
        PyConvert::FromGroundItem(py_r0(), itemCount->item, cache);
        py_newint(py_r1(), itemCount->previousCount);
        CallHook("ground_item_changed", two);
    }
    else if (const auto* loc = std::get_if<LocChanged_s>(&data); loc && HasHook("loc_changed"))
    {
        const auto& change = loc->change;
        const auto scene = SceneLoc_s{.tile = change.tile, .layer = change.layer, .id = change.id, .shape = change.shape, .angle = change.angle, .changed = true};
        PyConvert::FromLoc(py_r0(), scene, cache);
        CallHook("loc_changed", one);
    }
    else if (const auto* inventory = std::get_if<InventoryChanged_s>(&data); inventory && inventory->com == cache.inventoryComponent)
    {
        DispatchBackpack(state);
    }
    else if (const auto* said = std::get_if<NpcSaid_s>(&data); said && HasHook("npc_say"))
    {
        const auto* npc = state.FindNpc(said->index);
        if (npc == nullptr)
        {
            py_newnone(py_r0());
        }
        else
        {
            PyConvert::FromNpc(py_r0(), *npc, tick, cache);
        }

        PyConvert::FromString(py_r1(), said->text);
        CallHook("npc_say", two);
    }
    else if (const auto* projectile = std::get_if<ProjectileLaunched_s>(&data); projectile && HasHook("projectile"))
    {
        PyConvert::FromProjectile(py_r0(), projectile->projectile);
        CallHook("projectile", one);
    }
    else if (const auto* stat = std::get_if<StatChanged_s>(&data))
    {
        // death.rs2 empties hitpoints before it says "Oh dear you are dead!"; the stat is the surer sign.
        if (stat->stat == HITPOINTS && stat->previous.level > 0 && stat->current.level == 0)
        {
            CallHook("death");
            m_vm->Activate();
        }

        if (stat->current.xp != stat->previous.xp && HasHook("skill_xp"))
        {
            py_newint(py_r0(), stat->stat);
            py_newint(py_r1(), stat->current.xp);
            py_newint(py_r2(), stat->current.xp - stat->previous.xp);
            CallHook("skill_xp", three);
        }

        if (stat->current.baseLevel != stat->previous.baseLevel && HasHook("skill_level"))
        {
            m_vm->Activate();
            py_newint(py_r0(), stat->stat);
            py_newint(py_r1(), stat->current.baseLevel);
            py_newint(py_r2(), stat->previous.baseLevel);
            CallHook("skill_level", three);
        }
    }
    else if (const auto* varp = std::get_if<VarpChanged_s>(&data); varp && HasHook("varp_changed"))
    {
        py_newint(py_r0(), varp->varp);
        py_newint(py_r1(), varp->value);
        py_newint(py_r2(), varp->previous);
        CallHook("varp_changed", three);
    }
    else if (std::holds_alternative<ModalChanged_s>(data))
    {
        CallHook("interface_changed");
    }
    else if (const auto* reboot = std::get_if<RebootStarted_s>(&data); reboot && HasHook("system_update"))
    {
        py_newint(py_r0(), reboot->ticks * MILLISECONDS_PER_TICK / MILLISECONDS_PER_SECOND);
        CallHook("system_update", one);
    }
}

// The backpack's changes since the bot last saw it, one call per slot, as rs2b0t's inventory.changed.
void ScriptHost::DispatchBackpack(const GameState_s& state)
{
    const auto& cache = m_client.GetCache();
    const auto* inventory = state.FindInventory(cache.inventoryComponent);
    const auto previous = std::exchange(m_backpack, inventory ? inventory->slots : std::vector<Item_s>{});
    if (!HasHook(INVENTORY_CHANGED))
    {
        return;
    }

    const auto& current = m_backpack;
    const auto size = std::max(current.size(), previous.size());
    for (auto slot = std::size_t{0}; slot < size && m_status == ScriptStatus_e::Running; ++slot)
    {
        const auto now = slot < current.size() ? current[slot] : Item_s{};
        const auto before = slot < previous.size() ? previous[slot] : Item_s{};
        if (now.id == before.id && now.count == before.count)
        {
            continue;
        }

        const auto* type = cache.FindObj(now.id);
        m_vm->Activate();
        py_newint(py_r0(), static_cast<s64>(slot));
        py_newint(py_r1(), now.id);
        FromOptionalString(py_r2(), type ? type->name : std::string_view{});
        py_newint(py_r3(), now.count);
        py_newint(py_r4(), before.id);
        py_newint(py_r5(), before.count);
        CallHook(INVENTORY_CHANGED, std::array{py_r0(), py_r1(), py_r2(), py_r3(), py_r4(), py_r5()});
    }
}

void ScriptHost::DispatchMessages(const GameState_s& state)
{
    for (const auto* message : state.GetMessagesAfter(m_lastMessage))
    {
        m_lastMessage = message->sequence;
        const auto type = DescribeChatType(message->type);
        if (m_status != ScriptStatus_e::Running || !type)
        {
            continue;
        }

        if (HasHook("chat_message"))
        {
            m_vm->Activate();
            PyConvert::FromString(py_r0(), *type);
            FromOptionalString(py_r1(), message->sender);
            PyConvert::FromString(py_r2(), message->text);
            CallHook("chat_message", std::array{py_r0(), py_r1(), py_r2()});
        }

        m_vm->Activate();
        PyConvert::FromString(py_r0(), message->sender);
        PyConvert::FromString(py_r1(), message->text);
        switch (message->type)
        {
        case MessageType_e::Game:
            CallHook("server_message", std::array{py_r1()});
            break;
        case MessageType_e::Private:
            CallHook("private_message", std::array{py_r0(), py_r1()});
            break;
        case MessageType_e::TradeRequest:
            CallHook("trade_request", std::array{py_r0()});
            break;
        case MessageType_e::DuelRequest:
            CallHook("duel_request", std::array{py_r0()});
            break;
        case MessageType_e::Public:
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

    const auto result = Dispatch(PROGRESS_REPORT);
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
        Fail("on_progress_report", e.what());
        return;
    }

    if (m_options.onProgressReport)
    {
        m_options.onProgressReport(report);
    }
}

bool ScriptHost::IsLoopDue(Clock::time_point now, const GameState_s& state) const
{
    switch (m_wait)
    {
    case LoopWait_e::Time:
        return now >= m_nextLoop;
    case LoopWait_e::Update:
        return state.updateCount != m_waitUpdateCount || (m_waitHasTimeout && now >= m_nextLoop);
    case LoopWait_e::Ticks:
        // A fresh login starts the tick count over, which ends the wait too.
        return state.tick >= m_waitTick || state.tick < m_waitTickStart;
    }

    return true;
}

// Once a server tick: when the random event guardian or the stall guard takes over, it has dropped the bot's
// step in progress for its own, which runs from the next step, now.
void ScriptHost::RunUpkeep(Clock::time_point now)
{
    try
    {
        const auto took = m_vm->CallBuiltin(UPKEEP);
        m_vm->Activate();
        if (py_isbool(took) && py_tobool(took))
        {
            m_wait = LoopWait_e::Time;
            m_nextLoop = now;
        }

        ApplyStopRequest();
    }
    catch (const ScriptError& e)
    {
        Fail("upkeep (the random event guardian, stall guard or run manager)", e.what());
    }
}

// The runtime steps the bot's loop, generator or not, and returns how to wait before the next step.
void ScriptHost::RunLoop(Clock::time_point now)
{
    auto wait = py_GlobalRef{};
    try
    {
        wait = m_vm->CallBuiltin(STEP);
        m_vm->Activate();
        py_assign(py_r0(), wait);
        ApplyStopRequest();
    }
    catch (const ScriptError& e)
    {
        Fail("loop", e.what());
        return;
    }

    if (m_status != ScriptStatus_e::Running)
    {
        return;
    }

    ScheduleLoop(now, py_r0());
}

void ScriptHost::ScheduleLoop(Clock::time_point now, py_Ref wait)
{
    const auto kind = PyConvert::ToString(py_tuple_getitem(wait, 0), "wait");
    const auto value = py_toint(py_tuple_getitem(wait, 1));
    const auto& state = m_client.GetState();
    if (kind == WAIT_MS)
    {
        m_wait = LoopWait_e::Time;
        m_nextLoop = now + std::chrono::milliseconds{value};
        return;
    }

    if (kind == WAIT_UPDATE)
    {
        m_wait = LoopWait_e::Update;
        m_waitUpdateCount = state.updateCount;
        m_waitHasTimeout = value >= 0;
        m_nextLoop = now + std::chrono::milliseconds{std::max<s64>(value, 0)};
        return;
    }

    m_wait = LoopWait_e::Ticks;
    m_waitTickStart = state.tick;
    m_waitTick = state.tick + static_cast<u64>(value);
}

// Another account's script can ask this from inside its own VM, through send_bot_message, so the VM that
// was current is current again afterward.
bool ScriptHost::HasHook(std::string_view name) const
{
    if (!m_vm)
    {
        return false;
    }

    const auto previous = py_currentvm();
    const auto listening = py_getdict(m_vm->GetBuiltins(), py_name(LISTENING));
    auto found = 0;
    if (listening != nullptr)
    {
        const auto key = std::string{name};
        found = py_dict_getitem_by_str(listening, key.c_str());
        if (found < 0)
        {
            py_clearexc(nullptr);
        }
    }

    py_switchvm(previous);
    return found == 1;
}

void ScriptHost::CallHook(std::string_view name, std::span<const py_Ref> args)
{
    if (m_status != ScriptStatus_e::Running || !HasHook(name))
    {
        return;
    }

    static_cast<void>(Dispatch(name, args));
}

std::optional<py_GlobalRef> ScriptHost::Dispatch(std::string_view name, std::span<const py_Ref> args)
{
    // The event's name goes first, in a register the arguments don't use.
    m_vm->Activate();
    PyConvert::FromString(py_r7(), name);
    auto all = std::vector<py_Ref>{py_r7()};
    all.insert(all.end(), args.begin(), args.end());
    try
    {
        const auto result = m_vm->CallBuiltin(DISPATCH, all);
        ApplyStopRequest();
        return result;
    }
    catch (const ScriptError& e)
    {
        Fail(std::format("on_{}", name), e.what());
        return std::nullopt;
    }
}

void ScriptHost::Fail(std::string_view function, std::string_view message)
{
    if (m_watcher)
    {
        m_logger->Error("Script error in {}(), so the script has stopped until its files change:\n{}", function, message);
    }
    else
    {
        m_logger->Error("Script error in {}(), so the script has stopped:\n{}", function, message);
    }

    Stop(ScriptStatus_e::Failed, "the script failed");
}

void ScriptHost::Stop(ScriptStatus_e status, std::string_view reason)
{
    m_status = status;
    Finish(reason);
}

void ScriptHost::ApplyStopRequest()
{
    switch (m_api.TakeStopRequest())
    {
    case StopRequest_e::None:
        return;
    case StopRequest_e::Script:
        m_logger->Info("The script stopped itself; the account stays logged in");
        Stop(ScriptStatus_e::Stopped, "the script stopped");
        return;
    case StopRequest_e::Account:
        m_logger->Info("The script asked to log the account out");
        Stop(ScriptStatus_e::AccountStopped, "the script stopped the account");
        return;
    }
}
