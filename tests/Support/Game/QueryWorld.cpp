#include "pch.hpp"
#include "QueryWorld.hpp"
#include "../Cache/TestCache.hpp"
#include "Fixtures.hpp"

#include "Cache/GameCache_s.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/State/Zone_s.hpp"
#include "Game/Tile_s.hpp"

namespace
{
    constexpr auto WALL = u8{0};
    constexpr auto CENTREPIECE = u8{10};

    std::shared_ptr<const GameCache_s> MakeCache()
    {
        auto cache = GameCache_s{};
        TestCache::SetComponents(cache);
        TestCache::AddNpc(cache, QueryWorld::CHICKEN, "Chicken", {"", "Attack"});
        TestCache::AddNpc(cache, QueryWorld::COW, "Cow", {"", "Attack"});
        TestCache::AddObj(cache, QueryWorld::BONES, "Bones", {}, {"Bury"});
        TestCache::AddObj(cache, QueryWorld::COINS, "Coins");
        TestCache::AddLoc(cache, QueryWorld::DOOR, "Door", {"Open"});
        TestCache::AddLoc(cache, QueryWorld::TREE, "Tree", {"Chop down"});

        auto pen = std::vector<Tile_s>{};
        for (auto dx = 2; dx <= 4; ++dx)
        {
            for (auto dz = -1; dz <= 1; ++dz)
            {
                if (dx != 3 || dz != 0)
                {
                    pen.push_back(QueryWorld::Offset(dx, dz));
                }
            }
        }

        const auto locs = std::to_array<TestLoc_s>({
            {.id = QueryWorld::DOOR, .tile = QueryWorld::Offset(1, -2), .shape = WALL},
            {.id = QueryWorld::TREE, .tile = QueryWorld::Offset(-3, -3), .shape = CENTREPIECE},
            {.id = QueryWorld::TREE, .tile = QueryWorld::Offset(8, 8), .shape = CENTREPIECE},
        });

        TestCache::SetMap(cache, locs, pen);
        return std::make_shared<const GameCache_s>(std::move(cache));
    }
}

QueryWorld::QueryWorld()
    : cache{MakeCache()}
    , state{Fixtures::PlacedState()}
    , map{cache}
{
    state.tick = 100;
    state.npcs = {
        MakeNpc(10, CHICKEN, Offset(3, 0)),
        MakeNpc(11, COW, Offset(1, 1)),
        MakeNpc(12, CHICKEN, Offset(-3, 2)),
        MakeNpc(13, CHICKEN, Offset(6, 0)),
    };

    state.groundItems = {
        {.tile = Offset(2, 2), .id = BONES, .count = 1},
        {.tile = Offset(0, 1), .id = COINS, .count = 25},
    };

    state.inventories[TestCache::INVENTORY] = Inventory_s{
        .com = TestCache::INVENTORY,
        .slots = {{.id = COINS, .count = 100}, {}, {.id = BONES, .count = 1}, {.id = BONES, .count = 1}},
    };

    state.locChanges = {{.tile = Offset(8, 8), .layer = LocLayer_e::Ground, .id = -1, .shape = CENTREPIECE}};
    state.playerOps[1] = PlayerOp_s{.text = "Follow"};
    ++state.sceneChangeCount;
    map.Update(state);
}

Tile_s QueryWorld::Offset(s32 dx, s32 dz, s32 level)
{
    return {.x = Fixtures::HOME + dx, .z = Fixtures::HOME + dz, .level = level};
}

Npc_s QueryWorld::MakeNpc(u16 index, u16 type, const Tile_s& tile)
{
    auto npc = Npc_s{};
    npc.index = index;
    npc.type = type;
    npc.tile = tile;
    return npc;
}

std::vector<u16> QueryWorld::GetIndices(const std::vector<Npc_s>& npcs)
{
    auto indices = std::vector<u16>{};
    for (const auto& npc : npcs)
    {
        indices.push_back(npc.index);
    }

    return indices;
}
