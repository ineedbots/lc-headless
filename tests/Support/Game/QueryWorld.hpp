#pragma once

#include "Cache/GameCache_s.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/Tile_s.hpp"

// A player placed at Fixtures::HOME on tick 100, with NPCs, ground items, a backpack and scenery around them.
// Chicken 10 is penned in by blocked tiles, a door and a tree stand nearby, and the server has removed a
// second tree. NPC 900 isn't in the cache.
class QueryWorld
{
public:
    static constexpr auto CHICKEN = u16{41};
    static constexpr auto COW = u16{81};
    static constexpr auto UNKNOWN_NPC = u16{900};
    static constexpr auto BONES = 526;
    static constexpr auto COINS = 995;
    static constexpr auto DOOR = u16{1530};
    static constexpr auto TREE = u16{1276};

    QueryWorld();

    [[nodiscard]] static Tile_s Offset(s32 dx, s32 dz, s32 level = 0);
    [[nodiscard]] static Npc_s MakeNpc(u16 index, u16 type, const Tile_s& tile);
    [[nodiscard]] static std::vector<u16> GetIndices(const std::vector<Npc_s>& npcs);

    std::shared_ptr<const GameCache_s> cache;
    GameState_s state;
    WorldMap map;
};
