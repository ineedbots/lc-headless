#include "pch.hpp"
#include "Account.hpp"

#include "../Application/Events/ApplicationEventPublisher.hpp"
#include "../Cache/Type/GameCache_s.hpp"
#include "../Config/Type/AccountConfig_s.hpp"
#include "../Config/AccountFile.hpp"
#include "../Config/ConfigOverrides.hpp"
#include "../Config/Type/Config_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/State/Type/GameState_s.hpp"
#include "../Game/Type/Tile_s.hpp"
#include "../Script/BotMessenger.hpp"
#include "../Script/Host/ScriptHost.hpp"
#include "../Script/Type/ScriptCommand_s.hpp"
#include "../Script/ScriptRuntime.hpp"
#include "../Utils/StringUtils.hpp"
#include "IdleSummary.hpp"
#include "AccountLifecycle.hpp"
#include "AccountReporting.hpp"
#include "Type/AccountPhase_e.hpp"
#include "Type/ProgressReport_s.hpp"
#include "Type/AccountLogout_s.hpp"

Account::Account(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, AccountConfig_s account, ScriptRuntime& runtime, std::shared_ptr<Logger> logger, AccountOptions_s options, BotMessenger* messenger, std::shared_ptr<NetLoop> net)
    : m_config{ConfigOverrides::ForAccount(std::move(config), account)}
    , m_account{std::move(account)}
    , m_logger{Logger::CreateNamed(std::move(logger), m_account.name)}
    , m_options{options}
    , m_messenger{messenger}
    , m_client{m_config, std::move(cache), m_account.credentials, m_logger, m_options.client, std::move(net)}
    , m_reporting{*m_config, m_account, m_client.GetCache(), m_logger, [this](const ProgressReport_s& report)
{
    if (m_options.events)
    {
        m_options.events->Publish(m_account.name, report);
    }
}, m_options.events}
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
                .world = m_config->server.world,
                .events = m_options.events,
                .accountName = m_account.name,
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
    m_lifecycle.Start();
    m_nextSummary = Clock::now() + SUMMARY_INTERVAL;

    try
    {
        m_client.BeginLogin();
        ObserveLogout();
    }
    catch (const std::exception& e)
    {
        Fail(e.what());
    }
}

void Account::Login()
{
    Start();

    while (!m_lifecycle.IsFinished() && m_client.GetStatus() == ClientStatus_e::Connecting)
    {
        Step(m_config->scripting.pollIntervalMs);
    }
}

void Account::Step(std::chrono::milliseconds maxWait)
{
    if (!m_lifecycle.IsStarted() || m_lifecycle.IsFinished())
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
        ObserveLogout();

        const auto now = Clock::now();
        const auto status = m_client.GetStatus();

        // Before the early returns below: a logout, a disconnect and a relog are states worth recording too.
        // Settled, not merely in game: the stats arrive a tick after the player is placed.
        m_reporting.ObserveSession(now, m_client.GetState(), status);

        if (StepRelog(now))
        {
            return;
        }

        const auto ended = status == ClientStatus_e::LoggedOut || status == ClientStatus_e::Disconnected;
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

        if (m_lifecycle.IsFinished() || status == ClientStatus_e::LoggingOut)
        {
            return;
        }

        if (m_script)
        {
            StepScript(now);
        }
        else if (status == ClientStatus_e::InGame)
        {
            StepIdle(now);
        }

        if (status == ClientStatus_e::InGame)
        {
            m_reporting.SampleItems(now, m_client.GetState());
        }

        if (!m_lifecycle.IsFinished() && m_lifecycle.KillGraceExpired(now))
        {
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
    if (!m_lifecycle.IsStarted() || m_lifecycle.IsFinished())
    {
        return;
    }

    m_lifecycle.Interrupt();

    if (m_lifecycle.IsRelogging())
    {
        m_logger->Info("Interrupted during a relog; the account stays logged out");

        const auto waiting = m_lifecycle.GetPhase() == AccountPhase_e::RelogWait;
        m_lifecycle.BeginStopping();

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

    if (m_lifecycle.IsEscalated() || !m_client.IsInGame() || !m_script || !m_script->HandlesKillSignal())
    {
        LogOut("interrupted");
        return;
    }

    const auto grace = m_config->scripting.killGraceSeconds;
    m_logger->Info("Interrupted; the script has {} s to stop the account, or interrupt again to log out now", grace.count());
    m_lifecycle.BeginKillGrace(Clock::now() + grace);
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
    return m_lifecycle.IsStarted();
}

bool Account::IsFinished() const
{
    return m_lifecycle.IsFinished();
}

bool Account::Succeeded() const
{
    return m_lifecycle.Succeeded();
}

std::string_view Account::DescribeOutcome() const
{
    return m_lifecycle.DescribeOutcome();
}

std::string Account::DescribeStatus() const
{
    if (!m_lifecycle.IsStarted())
    {
        return "waiting to log in";
    }

    if (m_lifecycle.IsFinished())
    {
        return std::string{DescribeOutcome()};
    }

    auto text = std::string{};
    if (m_lifecycle.IsRelogging())
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
    if (!m_script || m_lifecycle.IsFinished())
    {
        return {};
    }

    return m_script->GetCommands();
}

bool Account::SendCommand(ConsoleCommand_s command, std::shared_ptr<CommandRecipient> recipient)
{
    return QueueCommand(std::move(command), std::move(recipient)) == CommandQueueResult_e::Accepted;
}

CommandQueueResult_e Account::QueueCommand(ConsoleCommand_s command, std::shared_ptr<CommandRecipient> recipient)
{
    if (!m_script || m_lifecycle.IsFinished())
    {
        return CommandQueueResult_e::Unavailable;
    }

    return m_script->QueueCommand(std::move(command), std::move(recipient));
}

bool Account::Say(std::string_view text)
{
    if (m_lifecycle.IsFinished() || !m_client.IsInGame())
    {
        return false;
    }

    m_client.Send(text.starts_with("::") ? m_client.GetPackets().ClientCheat(text.substr(2)) : m_client.GetPackets().MessagePublic(text));
    return true;
}

std::optional<Account::Clock::time_point> Account::GetNextLoop() const
{
    if (!m_script || m_lifecycle.IsFinished())
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
    m_reporting.AfterScript(now, *m_script);
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

        m_lifecycle.MarkFailed();
        LogOut("the script failed");
        return;
    }
}

void Account::StepIdle(Clock::time_point now)
{
    // The idle time counts from the first step in game, not from the login.
    if (m_lifecycle.IdleExpired(now, m_account.idleSeconds))
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
    m_lifecycle.BeginStopping();

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
    m_lifecycle.BeginRelog(delay);
    m_client.RequestLogout(LOGOUT_TIMEOUT);
    ObserveLogout();
}

bool Account::StepRelog(Clock::time_point now)
{
    if (m_lifecycle.GetPhase() == AccountPhase_e::RelogLogout)
    {
        const auto status = m_client.GetStatus();
        if (status != ClientStatus_e::LoggedOut && status != ClientStatus_e::Disconnected)
        {
            return true;
        }

        m_lifecycle.WaitAfterLogout(now);

        // The script sees the account go, as it would a dropped connection.
        if (m_script)
        {
            m_script->Step(now);
        }

        return true;
    }

    if (m_lifecycle.GetPhase() != AccountPhase_e::RelogWait)
    {
        return false;
    }

    if (!m_lifecycle.LoginDue(now))
    {
        return true;
    }

    m_lifecycle.ResumeLogin();
    m_logger->Info("Logging back in after the relog's wait");

    try
    {
        m_client.BeginLogin();
        ObserveLogout();
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
    m_lifecycle.WaitToRecover(now + m_options.reloginDelay);

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
        Fail(e.what());
    }
}

bool Account::IsStopping() const
{
    return m_lifecycle.IsStopping();
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

    m_lifecycle.MarkFailed();
    m_client.Disconnect();
    UpdateFinished();
}

void Account::UpdateFinished()
{
    ObserveLogout();

    const auto status = m_client.GetStatus();
    if (status != ClientStatus_e::LoggedOut && status != ClientStatus_e::Disconnected)
    {
        return;
    }

    m_lifecycle.Finish(status == ClientStatus_e::LoggedOut);
    if (m_script)
    {
        m_script->CancelCommands("account_finished");
    }
}

void Account::ObserveLogout()
{
    const auto status = m_client.GetStatus();
    const auto previous = std::exchange(m_observedStatus, status);
    if (status == previous)
    {
        return;
    }

    const auto confirmed = status == ClientStatus_e::LoggedOut;
    if (m_options.events && (confirmed || (previous == ClientStatus_e::LoggingOut && status == ClientStatus_e::Disconnected)))
    {
        m_options.events->Publish(m_account.name, AccountLogout_s{confirmed});
    }
}

void Account::CloseNetwork()
{
    if (m_script)
    {
        m_script->CancelCommands("application_stopping");
    }

    m_client.Disconnect();
    UpdateFinished();
}
