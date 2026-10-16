#include "pch.hpp"
#include "IdleSummary.hpp"

#include "../Console/Logger.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Stat_e.hpp"
#include "../Game/State/Stat_s.hpp"
#include "../Game/Tile_s.hpp"

namespace
{
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
}

void IdleSummary::Log(Logger& logger, const GameState_s& state)
{
    const auto& tile = state.localPlayer.tile;
    const auto& hitpoints = state.GetStat(Stat_e::Hitpoints);
    logger.Info("Tick {}: player {} at ({}, {}, {}), hitpoints {}/{}, run energy {}%, weight {} kg",
                state.tick, state.pid, tile.x, tile.z, tile.level, hitpoints.level, hitpoints.baseLevel, state.runEnergy, state.runWeight);
    logger.Info("In view: {} players, {} NPCs, {} ground items, {} changed locs; {} inventories, {} varps",
                state.players.size(), state.npcs.size(), state.groundItems.size(), state.locChanges.size(), state.inventories.size(), state.varps.size());
    logger.Info("Nearest NPCs: {}", DescribeNearestNpcs(state));

    const auto& interfaces = state.interfaces;
    logger.Info("Interfaces: main {}, side {}, chat {}, overlay {}", interfaces.mainModal, interfaces.sideModal, interfaces.chatModal, interfaces.overlay);
}
