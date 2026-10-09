#include "pch.hpp"
#include "CollisionMap.hpp"

#include "CollisionFlag.hpp"
#include "LocShape.hpp"

namespace
{
    constexpr auto ANGLE_WEST = u8{0};
    constexpr auto ANGLE_NORTH = u8{1};
    constexpr auto ANGLE_EAST = u8{2};
    constexpr auto ANGLE_SOUTH = u8{3};
    constexpr auto ANGLE_MASK = u8{0x3};
    constexpr auto HALF_TURN = u8{2};

    constexpr auto APPROACH_NORTH = u8{0x1};
    constexpr auto APPROACH_EAST = u8{0x2};
    constexpr auto APPROACH_SOUTH = u8{0x4};
    constexpr auto APPROACH_WEST = u8{0x8};

    std::size_t GetIndex(s32 x, s32 z)
    {
        return static_cast<std::size_t>(x * CollisionMap::SIZE + z);
    }

    bool IsOpen(u32 flags, u32 mask)
    {
        return (flags & mask) == CollisionFlag::OPEN;
    }

    bool IsAllowed(u8 forceApproach, u8 side)
    {
        return (forceApproach & side) == 0;
    }

    // A wall's flags for each side and corner, for walking or, shifted up, for projectiles.
    struct WallFlags_s
    {
        u32 west;
        u32 east;
        u32 north;
        u32 south;
        u32 northWest;
        u32 southEast;
        u32 northEast;
        u32 southWest;
    };

    WallFlags_s GetWallFlags(bool blockRange)
    {
        const auto shift = blockRange ? CollisionFlag::RANGE_SHIFT : 0;
        return {
            .west = CollisionFlag::WALL_WEST << shift,
            .east = CollisionFlag::WALL_EAST << shift,
            .north = CollisionFlag::WALL_NORTH << shift,
            .south = CollisionFlag::WALL_SOUTH << shift,
            .northWest = CollisionFlag::WALL_NORTH_WEST << shift,
            .southEast = CollisionFlag::WALL_SOUTH_EAST << shift,
            .northEast = CollisionFlag::WALL_NORTH_EAST << shift,
            .southWest = CollisionFlag::WALL_SOUTH_WEST << shift,
        };
    }
}

CollisionMap::CollisionMap()
    : m_flags(static_cast<std::size_t>(SIZE * SIZE))
{
    Reset();
}

void CollisionMap::Reset()
{
    for (auto x = 0; x < SIZE; ++x)
    {
        for (auto z = 0; z < SIZE; ++z)
        {
            const auto onEdge = x == 0 || z == 0 || x == SIZE - 1 || z == SIZE - 1;
            m_flags[GetIndex(x, z)] = onEdge ? CollisionFlag::BOUNDS : CollisionFlag::OPEN;
        }
    }
}

void CollisionMap::BlockGround(s32 x, s32 z)
{
    Add(x, z, CollisionFlag::GROUND);
}

void CollisionMap::AddLoc(s32 x, s32 z, s32 width, s32 length, u8 angle, bool blockRange)
{
    auto flags = CollisionFlag::LOC;
    if (blockRange)
    {
        flags |= CollisionFlag::RANGE_LOC;
    }

    if (angle == ANGLE_NORTH || angle == ANGLE_SOUTH)
    {
        std::swap(width, length);
    }

    for (auto tileX = x; tileX < x + width; ++tileX)
    {
        for (auto tileZ = z; tileZ < z + length; ++tileZ)
        {
            Add(tileX, tileZ, flags);
        }
    }
}

void CollisionMap::AddWall(s32 x, s32 z, u8 shape, u8 angle, bool blockRange)
{
    const auto wall = GetWallFlags(blockRange);
    if (shape == LocShape::WALL_STRAIGHT)
    {
        if (angle == ANGLE_WEST)
        {
            Add(x, z, wall.west);
            Add(x - 1, z, wall.east);
        }
        else if (angle == ANGLE_NORTH)
        {
            Add(x, z, wall.north);
            Add(x, z + 1, wall.south);
        }
        else if (angle == ANGLE_EAST)
        {
            Add(x, z, wall.east);
            Add(x + 1, z, wall.west);
        }
        else if (angle == ANGLE_SOUTH)
        {
            Add(x, z, wall.south);
            Add(x, z - 1, wall.north);
        }
    }
    else if (shape == LocShape::WALL_DIAGONAL_CORNER || shape == LocShape::WALL_SQUARE_CORNER)
    {
        if (angle == ANGLE_WEST)
        {
            Add(x, z, wall.northWest);
            Add(x - 1, z + 1, wall.southEast);
        }
        else if (angle == ANGLE_NORTH)
        {
            Add(x, z, wall.northEast);
            Add(x + 1, z + 1, wall.southWest);
        }
        else if (angle == ANGLE_EAST)
        {
            Add(x, z, wall.southEast);
            Add(x + 1, z - 1, wall.northWest);
        }
        else if (angle == ANGLE_SOUTH)
        {
            Add(x, z, wall.southWest);
            Add(x - 1, z - 1, wall.northEast);
        }
    }
    else if (shape == LocShape::WALL_L)
    {
        if (angle == ANGLE_WEST)
        {
            Add(x, z, wall.north | wall.west);
            Add(x - 1, z, wall.east);
            Add(x, z + 1, wall.south);
        }
        else if (angle == ANGLE_NORTH)
        {
            Add(x, z, wall.north | wall.east);
            Add(x, z + 1, wall.south);
            Add(x + 1, z, wall.west);
        }
        else if (angle == ANGLE_EAST)
        {
            Add(x, z, wall.south | wall.east);
            Add(x + 1, z, wall.west);
            Add(x, z - 1, wall.north);
        }
        else if (angle == ANGLE_SOUTH)
        {
            Add(x, z, wall.south | wall.west);
            Add(x, z - 1, wall.north);
            Add(x - 1, z, wall.east);
        }
    }

    // A wall that blocks projectiles blocks walking too.
    if (blockRange)
    {
        AddWall(x, z, shape, angle, false);
    }
}

bool CollisionMap::Contains(s32 x, s32 z)
{
    return x >= 0 && z >= 0 && x < SIZE && z < SIZE;
}

u32 CollisionMap::GetFlags(s32 x, s32 z) const
{
    assert(Contains(x, z) && "Tile outside the collision map");
    return m_flags[GetIndex(x, z)];
}

// Ported branch for branch from the webclient's testWall, so each case can be checked against it.
bool CollisionMap::CanReachWall(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, u8 shape, u8 angle) const
{
    if (srcX == dstX && srcZ == dstZ)
    {
        return true;
    }

    const auto flags = GetFlags(srcX, srcZ);
    if (shape == LocShape::WALL_STRAIGHT)
    {
        if (angle == ANGLE_WEST)
        {
            if (srcX == dstX - 1 && srcZ == dstZ)
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ + 1 && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_SOUTH))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ - 1 && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_NORTH))
            {
                return true;
            }
        }
        else if (angle == ANGLE_NORTH)
        {
            if (srcX == dstX && srcZ == dstZ + 1)
            {
                return true;
            }

            if (srcX == dstX - 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_EAST))
            {
                return true;
            }

            if (srcX == dstX + 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_WEST))
            {
                return true;
            }
        }
        else if (angle == ANGLE_EAST)
        {
            if (srcX == dstX + 1 && srcZ == dstZ)
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ + 1 && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_SOUTH))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ - 1 && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_NORTH))
            {
                return true;
            }
        }
        else if (angle == ANGLE_SOUTH)
        {
            if (srcX == dstX && srcZ == dstZ - 1)
            {
                return true;
            }

            if (srcX == dstX - 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_EAST))
            {
                return true;
            }

            if (srcX == dstX + 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_WEST))
            {
                return true;
            }
        }
    }
    else if (shape == LocShape::WALL_L)
    {
        if (angle == ANGLE_WEST)
        {
            if (srcX == dstX - 1 && srcZ == dstZ)
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ + 1)
            {
                return true;
            }

            if (srcX == dstX + 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_WEST))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ - 1 && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_NORTH))
            {
                return true;
            }
        }
        else if (angle == ANGLE_NORTH)
        {
            if (srcX == dstX - 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_EAST))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ + 1)
            {
                return true;
            }

            if (srcX == dstX + 1 && srcZ == dstZ)
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ - 1 && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_NORTH))
            {
                return true;
            }
        }
        else if (angle == ANGLE_EAST)
        {
            if (srcX == dstX - 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_EAST))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ + 1 && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_SOUTH))
            {
                return true;
            }

            if (srcX == dstX + 1 && srcZ == dstZ)
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ - 1)
            {
                return true;
            }
        }
        else if (angle == ANGLE_SOUTH)
        {
            if (srcX == dstX - 1 && srcZ == dstZ)
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ + 1 && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_SOUTH))
            {
                return true;
            }

            if (srcX == dstX + 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::BLOCK_ENTER_FROM_WEST))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ - 1)
            {
                return true;
            }
        }
    }
    else if (shape == LocShape::WALL_DIAGONAL)
    {
        if (srcX == dstX && srcZ == dstZ + 1 && IsOpen(flags, CollisionFlag::WALL_SOUTH))
        {
            return true;
        }

        if (srcX == dstX && srcZ == dstZ - 1 && IsOpen(flags, CollisionFlag::WALL_NORTH))
        {
            return true;
        }

        if (srcX == dstX - 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::WALL_EAST))
        {
            return true;
        }

        if (srcX == dstX + 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::WALL_WEST))
        {
            return true;
        }
    }

    return false;
}

// Ported branch for branch from the webclient's testWDecor.
bool CollisionMap::CanReachWallDecor(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, u8 shape, u8 angle) const
{
    if (srcX == dstX && srcZ == dstZ)
    {
        return true;
    }

    const auto flags = GetFlags(srcX, srcZ);
    if (shape == LocShape::WALLDECOR_DIAGONAL_OFFSET || shape == LocShape::WALLDECOR_DIAGONAL_NOOFFSET)
    {
        if (shape == LocShape::WALLDECOR_DIAGONAL_NOOFFSET)
        {
            angle = static_cast<u8>((angle + HALF_TURN) & ANGLE_MASK);
        }

        if (angle == ANGLE_WEST)
        {
            if (srcX == dstX + 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::WALL_WEST))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ - 1 && IsOpen(flags, CollisionFlag::WALL_NORTH))
            {
                return true;
            }
        }
        else if (angle == ANGLE_NORTH)
        {
            if (srcX == dstX - 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::WALL_EAST))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ - 1 && IsOpen(flags, CollisionFlag::WALL_NORTH))
            {
                return true;
            }
        }
        else if (angle == ANGLE_EAST)
        {
            if (srcX == dstX - 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::WALL_EAST))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ + 1 && IsOpen(flags, CollisionFlag::WALL_SOUTH))
            {
                return true;
            }
        }
        else if (angle == ANGLE_SOUTH)
        {
            if (srcX == dstX + 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::WALL_WEST))
            {
                return true;
            }

            if (srcX == dstX && srcZ == dstZ + 1 && IsOpen(flags, CollisionFlag::WALL_SOUTH))
            {
                return true;
            }
        }
    }
    else if (shape == LocShape::WALLDECOR_DIAGONAL_BOTH)
    {
        if (srcX == dstX && srcZ == dstZ + 1 && IsOpen(flags, CollisionFlag::WALL_SOUTH))
        {
            return true;
        }

        if (srcX == dstX && srcZ == dstZ - 1 && IsOpen(flags, CollisionFlag::WALL_NORTH))
        {
            return true;
        }

        if (srcX == dstX - 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::WALL_EAST))
        {
            return true;
        }

        if (srcX == dstX + 1 && srcZ == dstZ && IsOpen(flags, CollisionFlag::WALL_WEST))
        {
            return true;
        }
    }

    return false;
}

// Ported from the webclient's testLoc.
bool CollisionMap::CanReachArea(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, s32 width, s32 length, u8 forceApproach) const
{
    const auto maxX = dstX + width - 1;
    const auto maxZ = dstZ + length - 1;
    if (srcX >= dstX && srcX <= maxX && srcZ >= dstZ && srcZ <= maxZ)
    {
        return true;
    }

    const auto flags = GetFlags(srcX, srcZ);
    const auto besideX = srcZ >= dstZ && srcZ <= maxZ;
    const auto besideZ = srcX >= dstX && srcX <= maxX;
    if (srcX == dstX - 1 && besideX && IsOpen(flags, CollisionFlag::WALL_EAST) && IsAllowed(forceApproach, APPROACH_WEST))
    {
        return true;
    }

    if (srcX == maxX + 1 && besideX && IsOpen(flags, CollisionFlag::WALL_WEST) && IsAllowed(forceApproach, APPROACH_EAST))
    {
        return true;
    }

    if (srcZ == dstZ - 1 && besideZ && IsOpen(flags, CollisionFlag::WALL_NORTH) && IsAllowed(forceApproach, APPROACH_SOUTH))
    {
        return true;
    }

    return srcZ == maxZ + 1 && besideZ && IsOpen(flags, CollisionFlag::WALL_SOUTH) && IsAllowed(forceApproach, APPROACH_NORTH);
}

void CollisionMap::Add(s32 x, s32 z, u32 flags)
{
    if (!Contains(x, z))
    {
        return;
    }

    m_flags[GetIndex(x, z)] |= flags;
}
