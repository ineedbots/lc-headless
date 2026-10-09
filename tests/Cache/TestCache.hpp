#pragma once

#include "Cache/GameCache_s.hpp"
#include "Cache/LocType_s.hpp"
#include "Cache/NpcType_s.hpp"
#include "Cache/ObjType_s.hpp"
#include "Game/Tile_s.hpp"

// A loc in a map square, by absolute tile, on the level it's seen on.
struct TestLoc_s
{
    u16 id = 0;
    Tile_s tile;
    u8 shape = 10;
    u8 angle = 0;
};

// Builds a GameCache_s's contents in place, without files. Names must be string literals, which outlive
// the cache; an empty option is a slot the menu doesn't show.
class TestCache
{
public:
    TestCache() = delete;

    static NpcType_s& AddNpc(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {});
    static ObjType_s& AddObj(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {}, std::initializer_list<std::string_view> inventoryOps = {});
    static LocType_s& AddLoc(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {});
    // Replaces the map with squares holding these locs and blocked tiles.
    static void SetMap(GameCache_s& cache, std::span<const TestLoc_s> locs, std::span<const Tile_s> blocked = {});
};
