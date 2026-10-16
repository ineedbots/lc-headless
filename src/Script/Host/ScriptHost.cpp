#include "pch.hpp"
#include "ScriptHost.hpp"

#include "../../Accounts/ProgressReport_s.hpp"
#include "../../Cache/GameCache_s.hpp"
#include "../../Console/Logger.hpp"
#include "../../Game/GameClient.hpp"
#include "../../Game/GameTick.hpp"
#include "../../Game/Map/WorldMap.hpp"
#include "../../Game/State/GameEvent_s.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../../Game/State/Social_s.hpp"
#include "../../Game/State/Stat_e.hpp"
#include "../../Utils/FileWatcher.hpp"
#include "../Bindings/ScriptBindings.hpp"
#include "../BotMessenger.hpp"
#include "../Convert/PyObjects.hpp"
#include "../Convert/PyValue.hpp"
#include "../Error/ScriptError.hpp"
#include "../ScriptCommand_s.hpp"
#include "../ScriptContext.hpp"
#include "../ScriptControl.hpp"
#include "../ScriptRuntime.hpp"
#include "../ScriptVm.hpp"
#include "EventDispatcher.hpp"
#include "LoopSchedule.hpp"
#include "ScriptHooks.hpp"

#include <pocketpy.h>

namespace
{
    // The standard library's runtime (rs2004/_runtime.py), as the bootstrap names it in builtins.
    constexpr auto LOAD_BOT = "_rt_load"sv;
    constexpr auto SETTING_DEFAULTS = "_rt_setting_defaults"sv;
    constexpr auto START_BOT = "_rt_start"sv;
    constexpr auto STEP = "_rt_step"sv;
    constexpr auto CONFIGURE = "_rt_configure"sv;
    constexpr auto UPKEEP = "_rt_upkeep"sv;
    constexpr auto FINISH = "_rt_finish"sv;
    constexpr auto RUN_COMMAND = "_rt_command"sv;
    constexpr auto SETTINGS = "settings";
    constexpr auto REPORT_ROWS = "_report_rows"sv;

    constexpr auto PROGRESS_REPORT = "progress_report"sv;
    constexpr auto BOT_MESSAGE = "bot_message"sv;

}

ScriptHost::ScriptHost(ScriptRuntime& runtime, GameClient& client, ScriptHostOptions_s options, std::shared_ptr<Logger> logger)
    : m_runtime{runtime}
    , m_client{client}
    , m_actions{client}
    , m_context{client.GetState(), client.GetMap(), m_actions, options.messenger, options.username, options.navigation}
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
    m_context.GetControl().SetStepTime(std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count());
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
    SyncLogin();

    if (!state.IsSettled())
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

    m_events.DispatchEvents(state, m_client.GetCache(), *m_hooks, *m_logger);
    m_events.DispatchMessages(state, *m_hooks);
    DispatchBotMessages();
    DispatchCommands();

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

    if (m_status == ScriptStatus_e::Running && m_schedule.IsDue(now, state))
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
    PyValue::FromString(py_r0(), reason);

    try
    {
        static_cast<void>(m_vm->CallBuiltin(FINISH, std::array{py_r0()}));
    }
    catch (const ScriptError& e)
    {
        m_logger->Error("Script error while the script stopped, in on_stop() or a script_finish callback:\n{}", e.what());
    }

    // A stop asked for while stopping changes nothing.
    static_cast<void>(m_context.GetControl().TakeStopRequest());
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

std::vector<ScriptCommand_s> ScriptHost::GetCommands() const
{
    if (!m_hooks || m_status != ScriptStatus_e::Running)
    {
        return {};
    }

    return m_hooks->GetCommands();
}

bool ScriptHost::ReceiveCommand(ConsoleCommand_s command)
{
    const auto commands = GetCommands();
    const auto added = std::ranges::find(commands, command.name, &ScriptCommand_s::name) != commands.end();
    if (!added || m_commands.size() >= MAX_COMMANDS)
    {
        return false;
    }

    m_commands.push_back(std::move(command));
    return true;
}

ScriptStatus_e ScriptHost::GetStatus() const
{
    return m_status;
}

std::optional<std::chrono::seconds> ScriptHost::TakeRelogRequest()
{
    return m_context.GetControl().TakeRelogRequest();
}

std::optional<ScriptHost::Clock::time_point> ScriptHost::GetNextLoop() const
{
    if (!m_started || m_status != ScriptStatus_e::Running)
    {
        return std::nullopt;
    }

    // A wait for the server has no time, unless it has a timeout too.
    return m_schedule.GetNextTime();
}

void ScriptHost::Load()
{
    m_vm.emplace(m_runtime, ScriptVmOptions_s{.scriptsDirectory = m_options.scriptsDirectory, .callTimeout = m_options.callTimeout}, m_logger);
    m_hooks.emplace(*m_vm, [this]
    {
        return m_status == ScriptStatus_e::Running;
    }, [this](std::string_view where, std::string_view message)
    {
        Fail(where, message);
    }, [this]
    {
        ApplyStopRequest();
    });
    ScriptBindings::Bind(*m_vm, m_context);

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
            warnings.push_back(PyValue::ToString(py_list_getitem(result, i), "warning"));
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
            const auto botName = PyValue::ToString(py_list_getitem(defaults, 0), "the bot's name");
            const auto settingsJson = PyValue::ToString(py_list_getitem(defaults, 1), "the default settings");
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
    m_hooks.reset();
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
    static_cast<void>(m_context.GetControl().TakeStopRequest());

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
    m_events.SkipToPresent(state, m_client.GetCache());
    m_lastTick = state.tick;
    m_loginCount = m_client.GetLoginCount();
    m_connected = false;
    m_reconnectPending = false;
}

void ScriptHost::SyncLogin()
{
    m_connected = true;

    const auto loginCount = m_client.GetLoginCount();
    if (loginCount == m_loginCount)
    {
        return;
    }

    const auto reconnected = m_loginCount != 0;
    m_loginCount = loginCount;

    // A reconnect that became a fresh login, as after a server restart, isn't placed yet, so the hook
    // waits until it is and the script sees where the player is.
    m_reconnectPending = reconnected && m_started;
}

void ScriptHost::Start(Clock::time_point now)
{
    m_started = true;
    m_schedule.RunAt(now);

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
        Fail("on_start()", e.what());
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
        PyValue::FromString(py_r0(), message.sender);
        CallHook(BOT_MESSAGE, std::array{py_r0(), py_r1()});
    }
}

// A command the script removed after it was queued is skipped.
void ScriptHost::DispatchCommands()
{
    const auto commands = std::exchange(m_commands, {});
    for (const auto& command : commands)
    {
        if (m_status != ScriptStatus_e::Running)
        {
            return;
        }

        m_vm->Activate();
        PyValue::FromString(py_r0(), command.name);
        PyValue::FromString(py_r1(), command.text);
        py_newlist(py_r2());

        for (const auto& arg : command.args)
        {
            PyValue::FromString(py_r3(), arg);
            py_list_append(py_r2(), py_r3());
        }

        try
        {
            static_cast<void>(m_vm->CallBuiltin(RUN_COMMAND, std::array{py_r0(), py_r1(), py_r2()}));
            ApplyStopRequest();
        }
        catch (const ScriptError& e)
        {
            Fail(std::format("the {} command", command.name), e.what());
        }
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
            report.rows.emplace_back(PyValue::ToString(py_list_getitem(row, 0), "name"), PyValue::ToString(py_list_getitem(row, 1), "value"));
        }
    }
    catch (const ScriptError& e)
    {
        Fail("on_progress_report()", e.what());
        return;
    }

    if (m_options.onProgressReport)
    {
        m_options.onProgressReport(report);
    }
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
            m_schedule.RunAt(now);
        }

        ApplyStopRequest();
    }
    catch (const ScriptError& e)
    {
        Fail("the upkeep (the random event guardian, stall guard or run manager)", e.what());
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
        Fail("loop()", e.what());
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
    const auto kind = PyValue::ToString(py_tuple_getitem(wait, 0), "wait");
    m_schedule.Schedule(now, kind, py_toint(py_tuple_getitem(wait, 1)), m_client.GetState());
}

bool ScriptHost::HasHook(std::string_view name) const
{
    return m_hooks && m_hooks->Has(name);
}

void ScriptHost::CallHook(std::string_view name, std::span<const py_Ref> args)
{
    if (m_hooks)
    {
        m_hooks->Call(name, args);
    }
}

std::optional<py_GlobalRef> ScriptHost::Dispatch(std::string_view name, std::span<const py_Ref> args)
{
    return m_hooks->Dispatch(name, args);
}

void ScriptHost::Fail(std::string_view where, std::string_view message)
{
    if (m_watcher)
    {
        m_logger->Error("Script error in {}, so the script has stopped until its files change:\n{}", where, message);
    }
    else
    {
        m_logger->Error("Script error in {}, so the script has stopped:\n{}", where, message);
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
    switch (m_context.GetControl().TakeStopRequest())
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
