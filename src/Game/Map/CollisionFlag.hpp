#pragma once

// The webclient's collision flags, one set per tile. A WALL_ flag blocks walking across that side or
// corner of the tile, a RANGE_ flag blocks projectiles the same way, and LOC and GROUND block the whole
// tile. The route search tests a tile's BLOCK_ENTER_FROM_ mask before stepping into it from that side.
class CollisionFlag
{
public:
    static constexpr u32 OPEN = 0;

    static constexpr u32 WALL_NORTH_WEST = 0x1;
    static constexpr u32 WALL_NORTH = 0x2;
    static constexpr u32 WALL_NORTH_EAST = 0x4;
    static constexpr u32 WALL_EAST = 0x8;
    static constexpr u32 WALL_SOUTH_EAST = 0x10;
    static constexpr u32 WALL_SOUTH = 0x20;
    static constexpr u32 WALL_SOUTH_WEST = 0x40;
    static constexpr u32 WALL_WEST = 0x80;
    static constexpr u32 LOC = 0x100;

    static constexpr u32 RANGE_SHIFT = 9;
    static constexpr u32 RANGE_WALL_NORTH_WEST = WALL_NORTH_WEST << RANGE_SHIFT;
    static constexpr u32 RANGE_WALL_NORTH = WALL_NORTH << RANGE_SHIFT;
    static constexpr u32 RANGE_WALL_NORTH_EAST = WALL_NORTH_EAST << RANGE_SHIFT;
    static constexpr u32 RANGE_WALL_EAST = WALL_EAST << RANGE_SHIFT;
    static constexpr u32 RANGE_WALL_SOUTH_EAST = WALL_SOUTH_EAST << RANGE_SHIFT;
    static constexpr u32 RANGE_WALL_SOUTH = WALL_SOUTH << RANGE_SHIFT;
    static constexpr u32 RANGE_WALL_SOUTH_WEST = WALL_SOUTH_WEST << RANGE_SHIFT;
    static constexpr u32 RANGE_WALL_WEST = WALL_WEST << RANGE_SHIFT;
    static constexpr u32 RANGE_LOC = 0x20000;

    // The webclient never sets this one, but its walking masks include it.
    static constexpr u32 NPCS_AND_PLAYERS = 0x80000;
    static constexpr u32 GROUND = 0x200000;
    static constexpr u32 BOUNDS = 0xFFFFFF;

    static constexpr u32 BLOCKED = GROUND | NPCS_AND_PLAYERS | LOC;
    static constexpr u32 BLOCK_ENTER_FROM_NORTH = BLOCKED | WALL_NORTH;
    static constexpr u32 BLOCK_ENTER_FROM_EAST = BLOCKED | WALL_EAST;
    static constexpr u32 BLOCK_ENTER_FROM_SOUTH = BLOCKED | WALL_SOUTH;
    static constexpr u32 BLOCK_ENTER_FROM_WEST = BLOCKED | WALL_WEST;
    static constexpr u32 BLOCK_ENTER_FROM_NORTH_EAST = BLOCKED | WALL_NORTH_EAST | WALL_NORTH | WALL_EAST;
    static constexpr u32 BLOCK_ENTER_FROM_SOUTH_EAST = BLOCKED | WALL_SOUTH_EAST | WALL_SOUTH | WALL_EAST;
    static constexpr u32 BLOCK_ENTER_FROM_NORTH_WEST = BLOCKED | WALL_NORTH_WEST | WALL_NORTH | WALL_WEST;
    static constexpr u32 BLOCK_ENTER_FROM_SOUTH_WEST = BLOCKED | WALL_SOUTH_WEST | WALL_SOUTH | WALL_WEST;

    CollisionFlag() = delete;
};

static_assert(CollisionFlag::RANGE_WALL_NORTH_WEST == 0x200 && CollisionFlag::RANGE_WALL_WEST == 0x10000);
static_assert(CollisionFlag::BLOCK_ENTER_FROM_NORTH == 0x280102 && CollisionFlag::BLOCK_ENTER_FROM_EAST == 0x280108);
static_assert(CollisionFlag::BLOCK_ENTER_FROM_SOUTH == 0x280120 && CollisionFlag::BLOCK_ENTER_FROM_WEST == 0x280180);
static_assert(CollisionFlag::BLOCK_ENTER_FROM_NORTH_EAST == 0x28010E && CollisionFlag::BLOCK_ENTER_FROM_SOUTH_EAST == 0x280138);
static_assert(CollisionFlag::BLOCK_ENTER_FROM_NORTH_WEST == 0x280183 && CollisionFlag::BLOCK_ENTER_FROM_SOUTH_WEST == 0x2801E0);
