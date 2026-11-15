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
    Poll(now);

    try
    {
        auto sample = Read(state, status);
        const auto session = std::pair{sample.state, sample.settled};
        const auto sessionChanged = !m_lastObservedSession || *m_lastObservedSession != session;
        m_lastObservedSession = session;
        if (sessionChanged)
        {
            if (m_deferredSessions.size() >= FleetDatabase::MAX_PENDING_WRITES)
            {
                if (!m_writeFailed)
                {
                    m_writeFailed = true;
                    m_logger->Warning("The account data log's pending session-transition queue is full; the transition wasn't saved");
                }
            }
            else
            {
                sample.time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now()));
                m_deferredSessions.push_back(std::move(sample));
            }
        }

        if (m_write)
        {
            return;
        }

        if (!m_deferredSessions.empty())
        {
            if (m_writeFailed && m_nextSample && now < *m_nextSample)
            {
                return;
            }

            auto transition = m_deferredSessions.front();
            auto completion = m_database->Enqueue(transition);
            if (!completion)
            {
                throw std::runtime_error{"fleet database write queue is full"};
            }

            m_nextSample = now + m_interval;
            m_write.emplace(PendingWrite_s{std::move(transition), std::move(*completion), true});
            m_deferredSessions.pop_front();
            Poll(now);
            return;
        }

        if (m_lastSample && sample == *m_lastSample)
        {
            return;
        }

        if (m_nextSample && now < *m_nextSample)
        {
            return;
        }

        m_nextSample = now + m_interval;

        sample.time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now()));
        auto completion = m_database->Enqueue(sample);
        if (!completion)
        {
            throw std::runtime_error{"fleet database write queue is full"};
        }

        m_write.emplace(PendingWrite_s{std::move(sample), std::move(*completion), false});
        m_nextSample = now + m_interval;
        Poll(now);
    }
    catch (const std::exception& e)
    {
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The account data log wasn't saved: {}", e.what());
        }

        m_nextSample = now + m_interval;
    }
}

void AccountDataLog::Poll(Clock::time_point now)
{
    if (!m_write || m_write->completion.wait_for(0ms) != std::future_status::ready)
    {
        return;
    }

    auto write = std::move(*m_write);
    m_write.reset();

    try
    {
        write.completion.get();
        m_lastSample = write.record;

        if (m_events)
        {
            m_events->Publish(m_accountName, write.record);
        }

        if (m_writeFailed)
        {
            m_logger->Info("Writing account data to {} again", m_database->GetPath().string());
            m_writeFailed = false;
        }
    }
    catch (const std::exception& e)
    {
        if (write.sessionTransition)
        {
            m_deferredSessions.push_front(std::move(write.record));
        }

        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The account data log wasn't saved: {}", e.what());
        }

        m_nextSample = now + m_interval;
    }
}

void AccountDataLog::Flush()
{
    if (m_write)
    {
        m_write->completion.wait();
        Poll(Clock::now());
    }

    const auto attempts = m_deferredSessions.size();
    for (auto i = std::size_t{}; i < attempts && !m_deferredSessions.empty(); ++i)
    {
        auto transition = m_deferredSessions.front();
        auto completion = m_database->Enqueue(transition);
        if (!completion)
        {
            m_database->Flush();
            completion = m_database->Enqueue(transition);
        }

        if (!completion)
        {
            if (!m_writeFailed)
            {
                m_writeFailed = true;
                m_logger->Warning("The account data log wasn't saved: fleet database write queue is full");
            }

            return;
        }

        m_write.emplace(PendingWrite_s{std::move(transition), std::move(*completion), true});
        m_deferredSessions.pop_front();
        m_write->completion.wait();
        Poll(Clock::now());
        if (m_writeFailed)
        {
            return;
        }
    }
}
