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
    static constexpr u16 INVENTORY = 3214;
    static constexpr s32 INVENTORY_SIZE = 28;
    static constexpr u16 EQUIPMENT = 1688;
    static constexpr u16 BANK = 5382;
    static constexpr u16 BANK_INVENTORY = 2006;
    static constexpr u16 RUN_OFF_BUTTON = 152;
    static constexpr u16 RUN_ON_BUTTON = 153;
    static constexpr u16 RUN_VARP = 173;

    TestCache() = delete;

    static NpcType_s& AddNpc(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {});
    static ObjType_s& AddObj(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {}, std::initializer_list<std::string_view> inventoryOps = {});
    static LocType_s& AddLoc(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {});
    // Gives the cache the 289 cache's components and run varp, as the constants above.
    static void SetComponents(GameCache_s& cache);
    // Replaces the map with squares holding these locs and blocked tiles.
    static void SetMap(GameCache_s& cache, std::span<const TestLoc_s> locs, std::span<const Tile_s> blocked = {});
};
