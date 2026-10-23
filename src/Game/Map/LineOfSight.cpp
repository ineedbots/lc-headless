#include "pch.hpp"
#include "LineOfSight.hpp"

#include "CollisionFlag.hpp"

namespace
{
    constexpr auto SIGHT_WEST = CollisionFlag::RANGE_LOC | CollisionFlag::RANGE_WALL_WEST;
    constexpr auto SIGHT_EAST = CollisionFlag::RANGE_LOC | CollisionFlag::RANGE_WALL_EAST;
    constexpr auto SIGHT_SOUTH = CollisionFlag::RANGE_LOC | CollisionFlag::RANGE_WALL_SOUTH;
    constexpr auto SIGHT_NORTH = CollisionFlag::RANGE_LOC | CollisionFlag::RANGE_WALL_NORTH;
    constexpr auto HALF_TILE = s32{1 << 16} / 2;
    constexpr auto FINE_SHIFT = 16;

    // The edge of a footprint the ray starts from or ends on: the one facing the other body.
    s32 Facing(s32 a, s32 b, s32 size)
    {
        if (a >= b)
        {
            return a;
        }

        if (a + size - 1 <= b)
        {
            return a + size - 1;
        }

        return b;
    }

    bool Flagged(const CollisionMap& collision, s32 x, s32 z, u32 mask)
    {
        return !collision.InBounds(x, z) || (collision.GetFlags(x, z) & mask) != 0;
    }
}

bool LineOfSight::Has(const CollisionMap& collision, const Footprint_s& source, const Footprint_s& target)
{
    const auto startX = Facing(source.x, target.x, source.size);
    const auto startZ = Facing(source.z, target.z, source.size);
    const auto endX = Facing(target.x, source.x, target.size);
    const auto endZ = Facing(target.z, source.z, target.size);
    if (startX == endX && startZ == endZ)
    {
        return true;
    }

    if (Flagged(collision, startX, startZ, CollisionFlag::LOC))
    {
        return false;
    }

    const auto deltaX = endX - startX;
    const auto deltaZ = endZ - startZ;
    const auto east = deltaX >= 0;
    const auto north = deltaZ >= 0;
    auto xFlags = east ? SIGHT_WEST : SIGHT_EAST;
    auto zFlags = north ? SIGHT_SOUTH : SIGHT_NORTH;

    // The ray steps a tile at a time along the longer axis, with the other axis in 16.16 fixed point, and the
    // target tile's own scenery never hides what stands on it.
    if (std::abs(deltaX) > std::abs(deltaZ))
    {
        const auto stepX = east ? 1 : -1;
        const auto tangent = (deltaZ << FINE_SHIFT) / std::abs(deltaX);
        auto scaledZ = (startZ << FINE_SHIFT) + HALF_TILE + (north ? 0 : -1);
        for (auto x = startX; x != endX;)
        {
            x += stepX;
            const auto z = scaledZ >> FINE_SHIFT;
            if (x == endX && z == endZ)
            {
                xFlags &= ~CollisionFlag::RANGE_LOC;
            }

            if (Flagged(collision, x, z, xFlags))
            {
                return false;
            }

            scaledZ += tangent;
            const auto nextZ = scaledZ >> FINE_SHIFT;
            if (x == endX && nextZ == endZ)
            {
                zFlags &= ~CollisionFlag::RANGE_LOC;
            }

            if (nextZ != z && Flagged(collision, x, nextZ, zFlags))
            {
                return false;
            }
        }

        return true;
    }

    const auto stepZ = north ? 1 : -1;
    const auto tangent = (deltaX << FINE_SHIFT) / std::abs(deltaZ);
    auto scaledX = (startX << FINE_SHIFT) + HALF_TILE + (east ? 0 : -1);
    for (auto z = startZ; z != endZ;)
    {
        z += stepZ;
        const auto x = scaledX >> FINE_SHIFT;
        if (x == endX && z == endZ)
        {
            zFlags &= ~CollisionFlag::RANGE_LOC;
        }

        if (Flagged(collision, x, z, zFlags))
        {
            return false;
        }

        scaledX += tangent;
        const auto nextX = scaledX >> FINE_SHIFT;
        if (nextX == endX && z == endZ)
        {
            xFlags &= ~CollisionFlag::RANGE_LOC;
        }

        if (nextX != x && Flagged(collision, nextX, z, xFlags))
        {
            return false;
        }
    }

    return true;
}
