#include "pch.hpp"
#include "WalkMap.hpp"

#include "../../Cache/MapSquare.hpp"
#include "CollisionFlag.hpp"
#include "CollisionMap.hpp"
#include "PathFinder.hpp"
#include "SquareCollision.hpp"

namespace
{
    constexpr auto SIZE = MapSquare::SIZE;
    // Locs in a neighbouring square reach this far into this one: a wall one tile, the largest locs a few.
    constexpr auto MARGIN = 5;
    constexpr auto GRID = SIZE + 2 * MARGIN;
    // The ring around the square that steps out of it land on.
    constexpr auto RING = SIZE + 2;

    bool HasFloor(const GameCache_s& cache, s32 x, s32 z, s32 level)
    {
        const auto* const square = cache.FindSquare(x / SIZE, z / SIZE);
        return square != nullptr && square->HasGround(level, x % SIZE, z % SIZE);
    }

    bool HasAnyFloor(const MapSquare& square, s32 level)
    {
        for (auto x = 0; x < SIZE; ++x)
        {
            for (auto z = 0; z < SIZE; ++z)
            {
                if (square.HasGround(level, x, z))
                {
                    return true;
                }
            }
        }

        return false;
    }
}

WalkMap::WalkMap(const GameCache_s& cache)
{
    for (const auto& [id, square] : cache.squares)
    {
        for (auto level = 0; level < LEVELS; ++level)
        {
            if (HasAnyFloor(square, level))
            {
                BuildSquare(cache, square, level);
            }
        }
    }
}

void WalkMap::BuildSquare(const GameCache_s& cache, const MapSquare& square, s32 level)
{
    const auto baseX = square.GetX() * SIZE;
    const auto baseZ = square.GetZ() * SIZE;
    auto collision = CollisionMap{GRID};
    for (auto dx = -1; dx <= 1; ++dx)
    {
        for (auto dz = -1; dz <= 1; ++dz)
        {
            if (const auto* const neighbour = cache.FindSquare(square.GetX() + dx, square.GetZ() + dz))
            {
                SquareCollision::AddSquare(collision, cache, *neighbour, level, MARGIN + dx * SIZE, MARGIN + dz * SIZE);
            }
        }
    }

    // Which tiles of the square and the ring around it have a floor; a missing square has none.
    auto floor = std::bitset<RING * RING>{};
    for (auto x = -1; x <= SIZE; ++x)
    {
        for (auto z = -1; z <= SIZE; ++z)
        {
            const auto inside = x >= 0 && z >= 0 && x < SIZE && z < SIZE;
            const auto has = inside ? square.HasGround(level, x, z) : HasFloor(cache, baseX + x, baseZ + z, level);
            floor.set(static_cast<std::size_t>((x + 1) * RING + z + 1), has);
        }
    }

    const auto hasFloor = [&floor](s32 x, s32 z)
    {
        return floor.test(static_cast<std::size_t>((x + 1) * RING + z + 1));
    };

    auto tiles = std::make_unique<LevelSquare_s>();
    for (auto x = 0; x < SIZE; ++x)
    {
        for (auto z = 0; z < SIZE; ++z)
        {
            if (!hasFloor(x, z))
            {
                continue;
            }

            const auto index = static_cast<std::size_t>(x * SIZE + z);
            const auto gridX = MARGIN + x;
            const auto gridZ = MARGIN + z;
            const auto flags = collision.GetFlags(gridX, gridZ);
            tiles->walkable.set(index, (flags & CollisionFlag::BLOCKED) == CollisionFlag::OPEN);

            auto walls = u8{0};
            walls |= (flags & CollisionFlag::WALL_NORTH) != 0 ? WALL_NORTH : 0;
            walls |= (flags & CollisionFlag::WALL_EAST) != 0 ? WALL_EAST : 0;
            walls |= (flags & CollisionFlag::WALL_SOUTH) != 0 ? WALL_SOUTH : 0;
            walls |= (flags & CollisionFlag::WALL_WEST) != 0 ? WALL_WEST : 0;
            tiles->walls[index] = walls;

            auto exits = u8{0};
            for (auto direction = 0; direction < DIRECTIONS; ++direction)
            {
                const auto dx = DX[static_cast<std::size_t>(direction)];
                const auto dz = DZ[static_cast<std::size_t>(direction)];
                if (hasFloor(x + dx, z + dz) && PathFinder::CanStep(collision, gridX, gridZ, dx, dz))
                {
                    exits |= static_cast<u8>(1 << direction);
                }
            }

            tiles->exits[index] = exits;
        }
    }

    m_squares.emplace(GetKey(baseX, baseZ, level), std::move(tiles));
}

u32 WalkMap::GetKey(s32 x, s32 z, s32 level)
{
    return static_cast<u32>((level << 16) | ((x / SIZE) << 8) | (z / SIZE));
}

const WalkMap::LevelSquare_s* WalkMap::Find(s32 x, s32 z, s32 level) const
{
    if (x < 0 || z < 0 || level < 0 || level >= LEVELS)
    {
        return nullptr;
    }

    const auto found = m_squares.find(GetKey(x, z, level));
    return found == m_squares.end() ? nullptr : found->second.get();
}

bool WalkMap::IsWalkable(s32 x, s32 z, s32 level) const
{
    const auto* const tiles = Find(x, z, level);
    return tiles != nullptr && tiles->walkable.test(static_cast<std::size_t>((x % SIZE) * SIZE + z % SIZE));
}

u8 WalkMap::GetExits(s32 x, s32 z, s32 level) const
{
    const auto* const tiles = Find(x, z, level);
    return tiles != nullptr ? tiles->exits[static_cast<std::size_t>((x % SIZE) * SIZE + z % SIZE)] : u8{0};
}

u8 WalkMap::GetWalls(s32 x, s32 z, s32 level) const
{
    const auto* const tiles = Find(x, z, level);
    return tiles != nullptr ? tiles->walls[static_cast<std::size_t>((x % SIZE) * SIZE + z % SIZE)] : u8{0};
}

std::size_t WalkMap::GetLevelSquareCount() const
{
    return m_squares.size();
}

std::size_t WalkMap::GetMemoryBytes() const
{
    return m_squares.size() * sizeof(LevelSquare_s);
}
