#pragma once

#include "IdleSummaryNpc_s.hpp"
#include "Game/Type/Tile_s.hpp"

#include <nlohmann/json.hpp>

struct IdleSummary_s
{
    static constexpr std::size_t MAX_NEAREST_NPCS = 5;

    u64 tick = 0;
    u16 pid = 0;
    Tile_s tile;
    s32 hitpoints = 0;
    s32 baseHitpoints = 0;
    u8 runEnergy = 0;
    s32 weight = 0;
    std::size_t players = 0;
    std::size_t npcs = 0;
    std::size_t groundItems = 0;
    std::size_t changedLocs = 0;
    std::size_t inventories = 0;
    std::size_t varps = 0;
    std::vector<IdleSummaryNpc_s> nearestNpcs;
    s32 mainInterface = -1;
    s32 sideInterface = -1;
    s32 chatInterface = -1;
    s32 overlayInterface = -1;
};

inline void to_json(nlohmann::json& value, const IdleSummary_s& summary)
{
    value = {
        {"tick", summary.tick},
        {"pid", summary.pid},
        {"tile", {{"x", summary.tile.x}, {"z", summary.tile.z}, {"level", summary.tile.level}}},
        {"hitpoints", {{"current", summary.hitpoints}, {"base", summary.baseHitpoints}}},
        {"runEnergy", summary.runEnergy},
        {"weight", summary.weight},
        {"inView", {{"players", summary.players}, {"npcs", summary.npcs}, {"groundItems", summary.groundItems}, {"changedLocs", summary.changedLocs}, {"inventories", summary.inventories}, {"varps", summary.varps}}},
        {"nearestNpcs", summary.nearestNpcs},
        {"interfaces", {{"main", summary.mainInterface}, {"side", summary.sideInterface}, {"chat", summary.chatInterface}, {"overlay", summary.overlayInterface}}}};
}
