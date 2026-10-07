#pragma once

#include "../Tile_s.hpp"
#include "Entity_s.hpp"

enum class LocLayer_e : u8
{
    Wall,
    WallDecor,
    Ground,
    GroundDecor,
};

struct GroundItem_s
{
    Tile_s tile;
    u16 id = 0;
    s32 count = 0;
    u64 tick = 0;
};

// A loc the server placed, replaced or removed (id -1) since the zone was last reset to its cache state.
struct LocChange_s
{
    Tile_s tile;
    LocLayer_e layer = LocLayer_e::Ground;
    s32 id = -1;
    u8 shape = 0;
    u8 angle = 0;
    u64 tick = 0;
};

struct LocAnim_s
{
    Tile_s tile;
    LocLayer_e layer = LocLayer_e::Ground;
    u8 shape = 0;
    u8 angle = 0;
    s32 seq = -1;
    u64 tick = 0;
};

struct LocMerge_s
{
    Tile_s tile;
    u16 loc = 0;
    u8 shape = 0;
    u8 angle = 0;
    u16 startCycle = 0;
    u16 endCycle = 0;
    u16 player = 0;
    Tile_s min;
    Tile_s max;
    u64 tick = 0;
};

struct MapAnim_s
{
    Tile_s tile;
    u16 spotAnim = 0;
    u8 height = 0;
    u16 delay = 0;
    u64 tick = 0;
};

struct Projectile_s
{
    Tile_s source;
    Tile_s destination;
    std::optional<EntityRef_s> target;
    u16 spotAnim = 0;
    u8 sourceHeight = 0;
    u8 destinationHeight = 0;
    u16 startDelay = 0;
    u16 endDelay = 0;
    u8 peak = 0;
    u8 arc = 0;
    u64 tick = 0;
};

// A zone is an 8x8-tile block on one level; x and z are the absolute tile of its south-west corner.
struct Zone_s
{
    static constexpr s32 SIZE = 8;

    s32 x = 0;
    s32 z = 0;
    s32 level = 0;

    [[nodiscard]] bool Contains(const Tile_s& tile) const
    {
        return tile.level == level && tile.x >= x && tile.x < x + SIZE && tile.z >= z && tile.z < z + SIZE;
    }
};
