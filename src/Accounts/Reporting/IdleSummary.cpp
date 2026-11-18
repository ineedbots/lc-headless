#include "pch.hpp"
#include "IdleSummary.hpp"

#include "Type/IdleSummaryNpc_s.hpp"
#include "Type/IdleSummary_s.hpp"
#include "Console/Logger.hpp"
#include "Game/State/Type/GameState_s.hpp"
#include "Game/State/Type/Interfaces_s.hpp"
#include "Game/State/Type/Npc_s.hpp"
#include "Game/State/Type/Stat_e.hpp"
#include "Game/State/Type/Stat_s.hpp"
#include "Game/Type/Tile_s.hpp"

IdleSummary_s IdleSummary::Capture(const GameState_s& state)
{
    const auto& hitpoints = state.GetStat(Stat_e::Hitpoints);
    const auto& interfaces = state.interfaces;
    auto summary = IdleSummary_s{
        .tick = state.tick,
        .pid = state.pid,
        .tile = state.localPlayer.tile,
        .hitpoints = hitpoints.level,
        .baseHitpoints = hitpoints.baseLevel,
        .runEnergy = state.runEnergy,
        .weight = state.runWeight,
        .players = state.players.size(),
        .npcs = state.npcs.size(),
        .groundItems = state.groundItems.size(),
        .changedLocs = state.locChanges.size(),
        .inventories = state.inventories.size(),
        .varps = state.varps.size(),
        .mainInterface = interfaces.mainModal,
        .sideInterface = interfaces.sideModal,
        .chatInterface = interfaces.chatModal,
        .overlayInterface = interfaces.overlay};
    auto npcs = std::vector<const Npc_s*>{};
    for (const auto& npc : state.npcs)
    {
        npcs.push_back(&npc);
    }

    const auto& here = summary.tile;
    std::ranges::sort(npcs, {}, [&here](const Npc_s* npc)
    {
        return npc->tile.GetDistance(here);
    });

    for (const auto* const npc : npcs | std::views::take(IdleSummary_s::MAX_NEAREST_NPCS))
    {
        summary.nearestNpcs.push_back({npc->index, npc->type, npc->tile.GetDistance(here)});
    }

    return summary;
}

void IdleSummary::Log(Logger& logger, const IdleSummary_s& summary)
{
    auto nearestNpcs = std::string{};
    for (const auto& npc : summary.nearestNpcs)
    {
        if (!nearestNpcs.empty())
        {
            nearestNpcs += ", ";
        }

        std::format_to(std::back_inserter(nearestNpcs), "#{} type {} at {} tiles", npc.index, npc.type, npc.distance);
    }

    logger.Info("Tick {}: player {} at ({}, {}, {}), hitpoints {}/{}, run energy {}%, weight {} kg",
                summary.tick, summary.pid, summary.tile.x, summary.tile.z, summary.tile.level, summary.hitpoints, summary.baseHitpoints, summary.runEnergy, summary.weight);
    logger.Info("In view: {} players, {} NPCs, {} ground items, {} changed locs; {} inventories, {} varps",
                summary.players, summary.npcs, summary.groundItems, summary.changedLocs, summary.inventories, summary.varps);
    logger.Info("Nearest NPCs: {}", nearestNpcs.empty() ? "none" : nearestNpcs);
    logger.Info("Interfaces: main {}, side {}, chat {}, overlay {}", summary.mainInterface, summary.sideInterface, summary.chatInterface, summary.overlayInterface);
}
