#include "pch.hpp"
#include "Account.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Config/AccountConfig_s.hpp"
#include "../Config/AccountFile.hpp"
#include "../Config/ConfigOverrides.hpp"
#include "../Config/Config_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/Tile_s.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/Host/ScriptHost.hpp"
#include "../Script/ScriptCommand_s.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "../Utils/StringUtils.hpp"
#include "IdleSummary.hpp"
#include "ProgressReporter.hpp"

namespace
{
    constexpr auto PROGRESS_EXTENSION = ".txt";
}

Account::Account(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, AccountConfig_s account, ScriptRuntime& runtime, std::shared_ptr<Logger> logger, AccountOptions_s options, BotMessenger* messenger, std::shared_ptr<NetLoop> net)
    : m_config{ConfigOverrides::ForAccount(std::move(config), account)}
    , m_account{std::move(account)}
    , m_logger{Logger::CreateNamed(std::move(logger), m_account.name)}
    , m_options{options}
    , m_messenger{messenger}
    , m_client{m_config, std::move(cache), m_account.credentials, m_logger, m_options.client, std::move(net)}
    , m_progress{m_account.script ? m_account.script->progressReportMinutes : std::chrono::minutes{0}, std::filesystem::path{m_config->scripting.progressDirectory} / (m_account.name + PROGRESS_EXTENSION), m_logger}
{
    if (m_account.script)
    {
        const auto& scripting = m_config->scripting;
        const auto& script = *m_account.script;
        // clang-format off
        m_script.emplace(runtime, m_client,
            ScriptHostOptions_s{
                .scriptsDirectory = scripting.scriptsDirectory,
                .file = script.file,
                .settings = script.settings,
                .onSettingDefaults = [this](std::string_view botName, std::string_view settingsJson)
                {
                    AddSettingDefaults(botName, settingsJson);
                },
                .onSettingSave = [this](const SettingSave_s& save)
                {
                    SaveSetting(save);
                },
                .callTimeout = scripting.callTimeoutMs,
                .messenger = m_messenger,
                .username = m_account.credentials.username,
                .watchFiles = m_options.watchScripts,
                .waitForDebugger = m_options.waitForDebugger,
                .profileDirectory = m_options.profileDirectory.empty() ? std::filesystem::path{} : m_options.profileDirectory / m_account.name,
                .navigation = m_options.navigation,
                .randomEvents = m_account.randomEvents,
                .stallMinutes = m_account.stallMinutes,
                .runAuto = m_account.runAuto,
                .runEnergyMin = m_account.runEnergyMin,
            },
            m_logger);
        // clang-format on

        if (script.progressReportMinutes > std::chrono::minutes{0} && !m_script->HasProgressReport())
        {
            m_logger->Warning("{} has no on_progress_report(), so progressReportMinutes has no effect", std::filesystem::path{script.file}.generic_string());
        }
    }
    else if (m_account.idleSeconds > 0s)
    {
        m_logger->Info("No script; the account will idle for {} s", m_account.idleSeconds.count());
    }
    else
    {
        m_logger->Info("No script; the account will idle");
    }

    if (m_messenger != nullptr)
    {
        m_messenger->Register(m_account.credentials.username, [this](BotMessage_s message)
        {
            return m_script && m_script->ReceiveBotMessage(std::move(message));
        });
    }
}

Account::~Account()
{
    if (m_messenger != nullptr)
    {
        m_messenger->Unregister(m_account.credentials.username);
    }
}

void Account::Start()
{
    assert(!m_started && "Account started twice");
    m_started = true;
    m_nextSummary = Clock::now() + SUMMARY_INTERVAL;

    try
    {
        m_client.BeginLogin();
    }
    catch (const std::exception& e)
    {
        Fail(e.what());
    }
}

void Account::Login()
{
    Start();

    while (!m_finished && m_client.GetStatus() == ClientStatus_e::Connecting)
    {
        Step(m_config->scripting.pollIntervalMs);
    }
}

void Account::Step(std::chrono::milliseconds maxWait)
{
    if (!m_started || m_finished)
    {
        return;
    }

    // Many accounts share the caller's loop, so nothing one of them hits may reach it. While logging in, Pump
    // throws only once the client has used up its attempts, or for a refusal no attempt would change.
    const auto loggingIn = m_client.GetStatus() == ClientStatus_e::Connecting;

    try
    {
        m_client.Pump(GetWait(maxWait));
    }
    catch (const std::exception& e)
    {
        if (loggingIn)
        {
            Fail(e.what());
            return;
        }

        Recover(e.what());
        return;
    }

    try
    {
        if (StepRelog(Clock::now()))
        {
            return;
        }

        const auto ended = m_client.GetStatus() == ClientStatus_e::LoggedOut || m_client.GetStatus() == ClientStatus_e::Disconnected;
        if (ended && !IsStopping())
        {
            if (m_options.client.connectAttempts == 0)
            {
                Fail("The server ended the session; reconnecting is disabled");
                return;
            }

            m_logger->Warning("The server ended the session; logging in again in {} s", GetReloginSeconds());
            BeginRelogin();
            return;
        }

        UpdateFinished();

        const auto status = m_client.GetStatus();
        if (m_finished || status == ClientStatus_e::LoggingOut)
        {
            return;
        }

        const auto now = Clock::now();
        if (m_script)
        {
            StepScript(now);
        }
        else if (status == ClientStatus_e::InGame)
        {
            StepIdle(now);
        }

        if (!m_finished && m_killDeadline && now >= *m_killDeadline)
        {
            m_killDeadline.reset();
            LogOut("the script didn't stop within scripting.killGraceSeconds");
        }
    }
    catch (const std::exception& e)
    {
        Recover(e.what());
    }
}

void Account::Interrupt()
{
    if (!m_started || m_finished)
    {
        return;
    }

    ++m_interrupts;

    if (m_relogDelay || m_reloginAt)
    {
        m_logger->Info("Interrupted during a relog; the account stays logged out");

        const auto waiting = m_reloginAt.has_value();
        m_relogDelay.reset();
        m_reloginAt.reset();

        if (m_script)
        {
            m_script->Finish("interrupted");
        }

        // A logout under way finishes as any other does.
        if (waiting)
        {
            UpdateFinished();
        }

        return;
    }

    if (m_client.GetStatus() == ClientStatus_e::LoggingOut)
    {
        m_logger->Info("Interrupted again; closing the connection without waiting for the server");
        m_client.Disconnect();
        UpdateFinished();
        return;
    }

    if (m_interrupts > 1 || !m_client.IsInGame() || !m_script || !m_script->HandlesKillSignal())
    {
        LogOut("interrupted");
        return;
    }

    const auto grace = m_config->scripting.killGraceSeconds;
    m_logger->Info("Interrupted; the script has {} s to stop the account, or interrupt again to log out now", grace.count());
    m_killDeadline = Clock::now() + grace;
    m_script->SignalKill();

    try
    {
        StepScript(Clock::now());
    }
    catch (const std::exception& e)
    {
        Recover(e.what());
    }
}

bool Account::IsStarted() const
{
    return m_started;
}

bool Account::IsFinished() const
{
    return m_finished;
}

bool Account::Succeeded() const
{
    return m_finished && !m_failed && m_client.GetStatus() == ClientStatus_e::LoggedOut;
}

std::string_view Account::DescribeOutcome() const
{
    if (!m_started)
    {
        return "never started";
    }

    if (!m_finished)
    {
        return "still running";
    }

    if (m_failed)
    {
        return "failed";
    }

    return m_client.GetStatus() == ClientStatus_e::LoggedOut ? "logged out" : "disconnected without a confirmed logout";
}

std::string Account::DescribeStatus() const
{
    if (!m_started)
    {
        return "waiting to log in";
    }

    if (m_finished)
    {
        return std::string{DescribeOutcome()};
    }

    auto text = std::string{};
    if (m_relogDelay || m_reloginAt)
    {
        text = "relogging";
    }
    else
    {
        switch (m_client.GetStatus())
        {
        case ClientStatus_e::Connecting:
            text = m_client.GetLoginCount() == 0 ? "logging in" : "reconnecting";
            break;
        case ClientStatus_e::InGame:
        {
            const auto& tile = m_client.GetState().localPlayer.tile;
            text = std::format("in game at ({}, {}, {})", tile.x, tile.z, tile.level);
            break;
        }
        case ClientStatus_e::LoggingOut:
            text = "logging out";
            break;
        case ClientStatus_e::LoggedOut:
        case ClientStatus_e::Disconnected:
            text = "logged out";
            break;
        }
    }

    if (!m_script)
    {
        return text + ", no script";
    }

    switch (m_script->GetStatus())
    {
    case ScriptStatus_e::Running:
        return text + ", script running";
    case ScriptStatus_e::Stopped:
        return text + ", script stopped";
    case ScriptStatus_e::AccountStopped:
        return text + ", script stopped the account";
    case ScriptStatus_e::Failed:
        return text + ", script failed";
    }

    return text;
}

std::vector<ScriptCommand_s> Account::GetCommands() const
{
    if (!m_script || m_finished)
    {
        return {};
    }

    return m_script->GetCommands();
}

bool Account::SendCommand(ConsoleCommand_s command)
{
    return m_script && !m_finished && m_script->ReceiveCommand(std::move(command));
}

bool Account::Say(std::string_view text)
{
    if (m_finished || !m_client.IsInGame())
    {
        return false;
    }

    m_client.Send(m_client.GetPackets().MessagePublic(text));
    return true;
}

std::optional<Account::Clock::time_point> Account::GetNextLoop() const
{
    if (!m_script || m_finished)
    {
        return std::nullopt;
    }

    return m_script->GetNextLoop();
}

const std::string& Account::GetName() const
{
    return m_account.name;
}

const std::string& Account::GetUsername() const
{
    return m_account.credentials.username;
}

const GameClient& Account::GetClient() const
{
    return m_client;
}

std::chrono::milliseconds Account::GetWait(std::chrono::milliseconds maxWait) const
{
    const auto nextLoop = GetNextLoop();
    if (!nextLoop || !m_client.IsInGame())
    {
        return maxWait;
    }

    const auto untilLoop = std::chrono::duration_cast<std::chrono::milliseconds>(*nextLoop - Clock::now());
    return std::clamp(untilLoop, 0ms, maxWait);
}

void Account::StepScript(Clock::time_point now)
{
    m_script->Step(now);
    m_progress.Step(now, *m_script);
    m_client.Flush();

    switch (m_script->GetStatus())
    {
    case ScriptStatus_e::Running:
        if (const auto delay = m_script->TakeRelogRequest())
        {
            BeginRelog(*delay);
        }

        return;
    case ScriptStatus_e::Stopped:
        return;
    case ScriptStatus_e::AccountStopped:
        LogOut("the script stopped the account");
        return;
    case ScriptStatus_e::Failed:
        // While watching, the account waits logged in for the script to be fixed.
        if (m_options.watchScripts)
        {
            return;
        }

        m_failed = true;
        LogOut("the script failed");
        return;
    }
}

void Account::StepIdle(Clock::time_point now)
{
    // The idle time counts from the first step in game, not from the login.
    if (m_account.idleSeconds > 0s && !m_idleUntil)
    {
        m_idleUntil = now + m_account.idleSeconds;
    }

    if (m_idleUntil && now >= *m_idleUntil)
    {
        LogOut(std::format("the account has idled for its idleSeconds ({} s)", m_account.idleSeconds.count()));
        return;
    }

    if (now < m_nextSummary)
    {
        return;
    }

    IdleSummary::Log(*m_logger, m_client.GetState());
    m_nextSummary = now + SUMMARY_INTERVAL;
}

void Account::AddSettingDefaults(std::string_view botName, std::string_view settingsJson)
{
    if (m_account.file.empty())
    {
        return;
    }

    try
    {
        const auto added = AccountFile::AddScriptSettings(m_account.file, botName, settingsJson);
        if (added.empty())
        {
            return;
        }

        m_logger->Info("Added {}'s default settings to {}: {}", botName, m_account.file.string(), StringUtils::Join(added, ", "));
    }
    catch (const std::exception& e)
    {
        m_logger->Warning("{}'s default settings weren't added to the account file: {}", botName, e.what());
    }
}

void Account::SaveSetting(const SettingSave_s& save)
{
    if (m_account.file.empty())
    {
        return;
    }

    try
    {
        AccountFile::SetScriptSetting(m_account.file, save.name, save.key, save.valueJson);
        m_logger->Verbose("Saved settings[\"{}\"].{} to {}", save.name, save.key, m_account.file.string());
    }
    catch (const std::exception& e)
    {
        m_logger->Warning("settings[\"{}\"].{} wasn't saved to the account file: {}", save.name, save.key, e.what());
    }
}

void Account::LogOut(std::string_view reason)
{
    if (m_client.GetStatus() == ClientStatus_e::LoggingOut)
    {
        return;
    }

    m_logger->Info("Logging out: {}", reason);
    m_stopping = true;

    if (m_script)
    {
        m_script->Finish(reason);
    }

    m_client.RequestLogout(LOGOUT_TIMEOUT);
    UpdateFinished();
}

// The script stays loaded: its loop and hooks wait while the account is out, and on_reconnect is called once
// the player is placed again.
void Account::BeginRelog(std::chrono::seconds delay)
{
    if (!m_client.IsInGame())
    {
        return;
    }

    m_logger->Info("Relogging: logging out, then back in {} s later", delay.count());
    m_relogDelay = delay;
    m_client.RequestLogout(LOGOUT_TIMEOUT);
}

bool Account::StepRelog(Clock::time_point now)
{
    if (m_relogDelay)
    {
        const auto status = m_client.GetStatus();
        if (status != ClientStatus_e::LoggedOut && status != ClientStatus_e::Disconnected)
        {
            return true;
        }

        m_reloginAt = now + *m_relogDelay;
        m_relogDelay.reset();

        // The script sees the account go, as it would a dropped connection.
        if (m_script)
        {
            m_script->Step(now);
        }

        return true;
    }

    if (!m_reloginAt)
    {
        return false;
    }

    if (now < *m_reloginAt)
    {
        return true;
    }

    m_reloginAt.reset();
    m_logger->Info("Logging back in after the relog's wait");

    try
    {
        m_client.BeginLogin();
    }
    catch (const std::exception& e)
    {
        Fail(e.what());
    }

    return true;
}

// A failure during the session, such as a desync, logs back in unless the account is on its way out anyway.
void Account::Recover(std::string_view reason)
{
    if (IsStopping() || m_options.client.connectAttempts == 0)
    {
        Fail(reason);
        return;
    }

    m_logger->Error("{}; logging in again in {} s", reason, GetReloginSeconds());
    BeginRelogin();
}

// As a relog does, the script stays loaded, sees the account go, and gets on_reconnect once the player is
// placed again. A login that then fails for good stops the account.
void Account::BeginRelogin()
{
    m_client.Disconnect();

    const auto now = Clock::now();
    m_relogDelay.reset();
    m_reloginAt = now + m_options.reloginDelay;

    if (!m_script)
    {
        return;
    }

    try
    {
        m_script->Step(now);
    }
    catch (const std::exception& e)
    {
        m_reloginAt.reset();
        Fail(e.what());
    }
}

bool Account::IsStopping() const
{
    return m_stopping || m_interrupts > 0;
}

s64 Account::GetReloginSeconds() const
{
    return std::chrono::duration_cast<std::chrono::seconds>(m_options.reloginDelay).count();
}

void Account::Fail(std::string_view reason)
{
    m_logger->Error("The account has stopped: {}", reason);

    if (m_script)
    {
        m_script->Finish(reason);
    }

    m_failed = true;
    m_client.Disconnect();
    UpdateFinished();
}

void Account::UpdateFinished()
{
    const auto status = m_client.GetStatus();
    m_finished = status == ClientStatus_e::LoggedOut || status == ClientStatus_e::Disconnected;
}
