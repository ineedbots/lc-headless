#include "pch.hpp"
#include "Account.hpp"

#include "../Core/ConfigFile.hpp"
#include "../Core/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/Tile_s.hpp"
#include "../Script/ScriptHost.hpp"
#include "../Script/ScriptRuntime.hpp"

namespace
{
    constexpr auto HITPOINTS_STAT = std::size_t{3};
    constexpr auto NEAREST_NPC_COUNT = std::size_t{5};

    std::string DescribeNearestNpcs(const GameState_s& state)
    {
        auto npcs = std::vector<const Npc_s*>{};
        for (const auto& npc : state.npcs)
        {
            npcs.push_back(&npc);
        }

        const auto& here = state.localPlayer.tile;
        std::ranges::sort(npcs, {}, [&here](const Npc_s* npc)
        {
            return npc->tile.GetDistance(here);
        });

        auto text = std::string{};
        for (const auto* const npc : npcs | std::views::take(NEAREST_NPC_COUNT))
        {
            if (!text.empty())
            {
                text += ", ";
            }

            std::format_to(std::back_inserter(text), "#{} type {} at {} tiles", npc->index, npc->type, npc->tile.GetDistance(here));
        }

        return text.empty() ? "none" : text;
    }

    std::shared_ptr<const Config_s> WithServer(std::shared_ptr<const Config_s> config, const std::optional<ServerSettings_s>& server)
    {
        if (!server)
        {
            return config;
        }

        auto own = *config;
        own.server = *server;
        return std::make_shared<const Config_s>(std::move(own));
    }

    void LogSummary(Logger& logger, const GameState_s& state)
    {
        const auto& tile = state.localPlayer.tile;
        const auto& hitpoints = state.stats[HITPOINTS_STAT];
        logger.Info("Tick {}: player {} at ({}, {}, {}), hitpoints {}/{}, run energy {}%, weight {} kg",
                    state.tick, state.pid, tile.x, tile.z, tile.level, hitpoints.level, hitpoints.baseLevel, state.runEnergy, state.runWeight);
        logger.Info("In view: {} players, {} NPCs, {} ground items, {} changed locs; {} inventories, {} varps",
                    state.players.size(), state.npcs.size(), state.groundItems.size(), state.locChanges.size(), state.inventories.size(), state.varps.size());
        logger.Info("Nearest NPCs: {}", DescribeNearestNpcs(state));

        const auto& interfaces = state.interfaces;
        logger.Info("Interfaces: main {}, side {}, chat {}, overlay {}", interfaces.mainModal, interfaces.sideModal, interfaces.chatModal, interfaces.overlay);
    }
}

Account::Account(std::shared_ptr<const Config_s> config, AccountConfig_s account, ScriptRuntime& runtime, std::shared_ptr<Logger> logger, GameClientOptions_s clientOptions)
    : m_config{WithServer(std::move(config), account.server)}
    , m_account{std::move(account)}
    , m_logger{Logger::CreateNamed(std::move(logger), m_account.name)}
    , m_client{m_config, m_account.credentials, m_logger, clientOptions}
{
    if (!m_account.script)
    {
        m_logger->Info("No script; the account will idle");
        return;
    }

    const auto& scripting = m_config->scripting;
    m_script.emplace(runtime, m_client,
        ScriptHostOptions_s{
            .scriptsDirectory = scripting.scriptsDirectory,
            .file = m_account.script->file,
            .settings = m_account.script->settings,
            .callTimeout = scripting.callTimeoutMs,
        },
        m_logger);
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

    try
    {
        m_client.Pump(GetWait(maxWait));
    }
    catch (const std::exception& e)
    {
        Fail(e.what());
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

void Account::Interrupt()
{
    if (!m_started || m_finished)
    {
        return;
    }

    ++m_interrupts;
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
    StepScript(Clock::now());
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
    m_client.Flush();
    switch (m_script->GetStatus())
    {
    case ScriptStatus_e::Running:
    case ScriptStatus_e::Stopped:
        return;
    case ScriptStatus_e::AccountStopped:
        LogOut("the script stopped the account");
        return;
    case ScriptStatus_e::Failed:
        m_failed = true;
        LogOut("the script failed");
        return;
    }
}

void Account::StepIdle(Clock::time_point now)
{
    if (now < m_nextSummary)
    {
        return;
    }

    LogSummary(*m_logger, m_client.GetState());
    m_nextSummary = now + SUMMARY_INTERVAL;
}

void Account::LogOut(std::string_view reason)
{
    if (m_client.GetStatus() == ClientStatus_e::LoggingOut)
    {
        return;
    }

    m_logger->Info("Logging out: {}", reason);
    m_client.RequestLogout(LOGOUT_TIMEOUT);
    UpdateFinished();
}

void Account::Fail(std::string_view reason)
{
    m_logger->Error("The account has stopped: {}", reason);
    m_failed = true;
    m_client.Disconnect();
    UpdateFinished();
}

void Account::UpdateFinished()
{
    const auto status = m_client.GetStatus();
    m_finished = status == ClientStatus_e::LoggedOut || status == ClientStatus_e::Disconnected;
}
