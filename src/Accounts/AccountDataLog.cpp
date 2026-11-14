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
#include "../Utils/FileUtils.hpp"
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

    nlohmann::ordered_json Tile(const Tile_s& tile)
    {
        return {{"x", tile.x}, {"z", tile.z}, {"level", tile.level}};
    }

    nlohmann::ordered_json Stat(const Stat_s& stat)
    {
        return {{"current", stat.level}, {"base", stat.baseLevel}};
    }
}

AccountDataLog::AccountDataLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::filesystem::path directory, std::chrono::seconds interval, std::shared_ptr<ApplicationEventPublisher> events)
    : m_cache{cache}
    , m_logger{std::move(logger)}
    , m_accountName{std::move(accountName)}
    , m_path{std::move(directory) / (m_accountName + ".jsonl")}
    , m_interval{interval}
    , m_events{std::move(events)}
{
}

nlohmann::ordered_json AccountDataLog::Read(const GameState_s& state, ClientStatus_e status) const
{
    const auto settled = status == ClientStatus_e::InGame && state.IsSettled();
    auto sample = nlohmann::ordered_json{{"state", StatusName(status)}, {"settled", settled}, {"pid", nullptr}, {"tile", nullptr}, {"destination", nullptr}, {"target", nullptr}, {"hp", nullptr}, {"energy", nullptr}, {"prayer", nullptr}, {"specialAttack", nullptr}, {"running", nullptr}, {"moving", nullptr}, {"inCombat", nullptr}, {"weight", nullptr}};
    if (!settled)
    {
        return sample;
    }

    sample["pid"] = state.pid;
    sample["tile"] = Tile(state.localPlayer.tile);
    if (state.walkDestination)
    {
        sample["destination"] = Tile(*state.walkDestination);
    }
    if (state.localPlayer.faceEntity)
    {
        const auto& target = *state.localPlayer.faceEntity;
        sample["target"] = {{"kind", target.type == EntityType_e::Npc ? "npc" : "player"}, {"index", target.index}};
    }
    else if (state.localPlayer.faceCoord)
    {
        // Facing coordinates have half-tile precision and no object identity.
        const auto& target = *state.localPlayer.faceCoord;
        sample["target"] = {{"kind", "tile"}, {"tile", Tile({.x = target.x / 2, .z = target.z / 2, .level = state.localPlayer.tile.level})}};
    }
    sample["hp"] = Stat(state.GetStat(Stat_e::Hitpoints));
    sample["energy"] = state.runEnergy;
    sample["prayer"] = Stat(state.GetStat(Stat_e::Prayer));
    const auto energy = state.varps.find(SPECIAL_ENERGY_VARP);
    // Missing on revisions/servers without a special bar; do not invent an empty bar.
    if (energy != state.varps.end())
    {
        sample["specialAttack"] = {{"energy", energy->second}, {"armed", state.GetVarp(SPECIAL_ARMED_VARP) == 1}};
    }
    const auto player = PlayerQuery{state, m_cache};
    sample["running"] = player.IsRunning();
    sample["moving"] = player.IsMoving();
    sample["inCombat"] = player.InCombat();
    sample["weight"] = state.runWeight;
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
        const auto sessionChanged = !m_lastSample || sample["state"] != (*m_lastSample)["state"] || sample["settled"] != (*m_lastSample)["settled"];
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
        auto record = nlohmann::ordered_json{{"time", std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now()))}, {"account", m_accountName}};
        record.update(sample);
        record["tick"] = state.tick;
        const auto line = record.dump(-1, ' ', false, nlohmann::json::error_handler_t::replace) + '\n';
        FileUtils::AppendText(m_path, line);
        m_lastSample = std::move(sample);
        if (m_events)
        {
            m_events->Publish(m_accountName, FleetAccountDataLog_s{line});
        }
        if (m_writeFailed)
        {
            m_logger->Info("Writing account data to {} again", m_path.string());
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
