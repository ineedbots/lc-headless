#include "pch.hpp"
#include "AccountDataLog.hpp"

#include "../Application/Events/ApplicationEventPublisher.hpp"
#include "../Cache/Type/GameCache_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/GameClient.hpp"
#include "../Game/State/Type/GameState_s.hpp"
#include "../Game/Query/PlayerQuery.hpp"
#include "../Game/State/Type/Entity_s.hpp"
#include "../Game/State/Type/Player_s.hpp"
#include "../Game/State/Type/Stat_e.hpp"
#include "../Game/State/Type/Stat_s.hpp"
#include "../Game/Type/Tile_s.hpp"
#include "Type/FleetAccountDataLog_s.hpp"

namespace
{
    constexpr u16 SPECIAL_ENERGY_VARP = 300;
    constexpr u16 SPECIAL_ARMED_VARP = 301;

    std::string_view StatusName(ClientStatus_e status)
    {
        switch (status)
        {
        case ClientStatus_e::Disconnected:
            return "disconnected";
        case ClientStatus_e::Connecting:
            return "connecting";
        case ClientStatus_e::InGame:
            return "ingame";
        case ClientStatus_e::LoggingOut:
            return "logging out";
        case ClientStatus_e::LoggedOut:
            return "logged out";
        }

        return "unknown";
    }

    FleetLogTile_s Tile(const Tile_s& tile)
    {
        return {.x = tile.x, .z = tile.z, .level = tile.level};
    }

    FleetLogStat_s Stat(const Stat_s& stat)
    {
        return {.current = stat.level, .base = stat.baseLevel};
    }
}

AccountDataLog::AccountDataLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::shared_ptr<FleetDatabase> database, std::chrono::seconds interval, std::shared_ptr<ApplicationEventPublisher> events)
    : m_cache{cache}
    , m_logger{std::move(logger)}
    , m_accountName{std::move(accountName)}
    , m_database{std::move(database)}
    , m_interval{interval}
    , m_events{std::move(events)}
{
}

FleetAccountDataLog_s AccountDataLog::Read(const GameState_s& state, ClientStatus_e status) const
{
    const auto settled = status == ClientStatus_e::InGame && state.IsSettled();
    auto sample = FleetAccountDataLog_s{
        .account = m_accountName,
        .state = std::string{StatusName(status)},
        .settled = settled,
        .tick = state.tick};
    if (!settled)
    {
        return sample;
    }

    sample.pid = state.pid;
    sample.tile = Tile(state.localPlayer.tile);

    if (state.walkDestination)
    {
        sample.destination = Tile(*state.walkDestination);
    }

    if (state.localPlayer.faceEntity)
    {
        const auto& target = *state.localPlayer.faceEntity;
        sample.target = FleetLogTarget_s{
            .kind = target.type == EntityType_e::Npc ? "npc" : "player",
            .index = target.index};
    }
    else if (state.localPlayer.faceCoord)
    {
        // Facing coordinates have half-tile precision and no object identity.
        const auto& target = *state.localPlayer.faceCoord;
        sample.target = FleetLogTarget_s{
            .kind = "tile",
            .tile = Tile({.x = target.x / 2, .z = target.z / 2, .level = state.localPlayer.tile.level})};
    }

    sample.hp = Stat(state.GetStat(Stat_e::Hitpoints));
    sample.energy = state.runEnergy;
    sample.prayer = Stat(state.GetStat(Stat_e::Prayer));

    const auto energy = state.varps.find(SPECIAL_ENERGY_VARP);
    // Missing on revisions/servers without a special bar; do not invent an empty bar.
    if (energy != state.varps.end())
    {
        sample.specialAttack = FleetLogSpecialAttack_s{.energy = energy->second, .armed = state.GetVarp(SPECIAL_ARMED_VARP) == 1};
    }

    const auto player = PlayerQuery{state, m_cache};
    sample.running = player.IsRunning();
    sample.moving = player.IsMoving();
    sample.inCombat = player.InCombat();
    sample.weight = state.runWeight;
    return sample;
}

void AccountDataLog::Step(Clock::time_point now, const GameState_s& state, ClientStatus_e status)
{
    try
    {
        auto sample = Read(state, status);
        if (m_lastSample && sample == *m_lastSample)
        {
            return;
        }

        const auto sessionChanged = !m_lastSample || sample.state != m_lastSample->state || sample.settled != m_lastSample->settled;
        if (!sessionChanged && m_nextSample && now < *m_nextSample)
        {
            return;
        }

        // Retry failed writes on the interval, including the first sample and session changes.
        if (m_writeFailed && m_nextSample && now < *m_nextSample)
        {
            return;
        }

        m_nextSample = now + m_interval;

        sample.time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now()));
        m_database->Append(sample);
        m_lastSample = sample;

        if (m_events)
        {
            m_events->Publish(m_accountName, sample);
        }

        if (m_writeFailed)
        {
            m_logger->Info("Writing account data to {} again", m_database->GetPath().string());
            m_writeFailed = false;
        }
    }
    catch (const std::exception& e)
    {
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The account data log wasn't saved: {}", e.what());
        }
    }
}
