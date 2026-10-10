#include "pch.hpp"
#include "PathFinder.hpp"

#include "../State/GameState_s.hpp"
#include "../Tile_s.hpp"
#include "CollisionFlag.hpp"
#include "CollisionMap.hpp"
#include "LocShape.hpp"
#include "WorldMap.hpp"

namespace
{
    constexpr auto SIZE = CollisionMap::SIZE;
    constexpr auto LAST = SIZE - 1;

    // Each reached tile records the way back toward the start, as the webclient's dirMap does.
    constexpr auto UNREACHED = u8{0};
    constexpr auto BACK_NORTH = u8{0x1};
    constexpr auto BACK_EAST = u8{0x2};
    constexpr auto BACK_SOUTH = u8{0x4};
    constexpr auto BACK_WEST = u8{0x8};
    constexpr auto START = u8{99};
    constexpr auto NO_DISTANCE = 99999999;
    constexpr auto MAX_NEAREST_DISTANCE = 100;
    constexpr auto NEAREST_PADDING = 1;

    struct LocalTile_s
    {
        s32 x = 0;
        s32 z = 0;
    };

    std::size_t GetIndex(s32 x, s32 z)
    {
        return static_cast<std::size_t>(x * SIZE + z);
    }

    bool IsOpen(u32 flags, u32 mask)
    {
        return (flags & mask) == CollisionFlag::OPEN;
    }

    // The search's working state, local to one call: about 50 KB.
    class Search
    {
    public:
        explicit Search(const CollisionMap& collision)
            : m_collision{collision}
            , m_directions(static_cast<std::size_t>(SIZE * SIZE), UNREACHED)
            , m_distances(static_cast<std::size_t>(SIZE * SIZE), NO_DISTANCE)
        {
            m_queue.reserve(static_cast<std::size_t>(SIZE * SIZE));
        }

        void Start(LocalTile_s tile)
        {
            m_directions[GetIndex(tile.x, tile.z)] = START;
            m_distances[GetIndex(tile.x, tile.z)] = 0;
            m_queue.push_back(tile);
        }

        [[nodiscard]] std::optional<LocalTile_s> Next()
        {
            if (m_head == m_queue.size())
            {
                return std::nullopt;
            }

            return m_queue[m_head++];
        }

        // Neighbours in the webclient's order, so routes of equal length tie the same way.
        void Expand(LocalTile_s tile)
        {
            const auto x = tile.x;
            const auto z = tile.z;
            const auto distance = m_distances[GetIndex(x, z)] + 1;
            if (x > 0 && CanEnter(x - 1, z, CollisionFlag::BLOCK_ENTER_FROM_EAST))
            {
                Reach(x - 1, z, BACK_EAST, distance);
            }

            if (x < LAST && CanEnter(x + 1, z, CollisionFlag::BLOCK_ENTER_FROM_WEST))
            {
                Reach(x + 1, z, BACK_WEST, distance);
            }

            if (z > 0 && CanEnter(x, z - 1, CollisionFlag::BLOCK_ENTER_FROM_NORTH))
            {
                Reach(x, z - 1, BACK_NORTH, distance);
            }

            if (z < LAST && CanEnter(x, z + 1, CollisionFlag::BLOCK_ENTER_FROM_SOUTH))
            {
                Reach(x, z + 1, BACK_SOUTH, distance);
            }

            if (x > 0 && z > 0 && CanEnter(x - 1, z - 1, CollisionFlag::BLOCK_ENTER_FROM_NORTH_EAST) && IsOpenTo(x - 1, z, CollisionFlag::BLOCK_ENTER_FROM_EAST) && IsOpenTo(x, z - 1, CollisionFlag::BLOCK_ENTER_FROM_NORTH))
            {
                Reach(x - 1, z - 1, BACK_NORTH | BACK_EAST, distance);
            }

            if (x < LAST && z > 0 && CanEnter(x + 1, z - 1, CollisionFlag::BLOCK_ENTER_FROM_NORTH_WEST) && IsOpenTo(x + 1, z, CollisionFlag::BLOCK_ENTER_FROM_WEST) && IsOpenTo(x, z - 1, CollisionFlag::BLOCK_ENTER_FROM_NORTH))
            {
                Reach(x + 1, z - 1, BACK_NORTH | BACK_WEST, distance);
            }

            if (x > 0 && z < LAST && CanEnter(x - 1, z + 1, CollisionFlag::BLOCK_ENTER_FROM_SOUTH_EAST) && IsOpenTo(x - 1, z, CollisionFlag::BLOCK_ENTER_FROM_EAST) && IsOpenTo(x, z + 1, CollisionFlag::BLOCK_ENTER_FROM_SOUTH))
            {
                Reach(x - 1, z + 1, BACK_SOUTH | BACK_EAST, distance);
            }

            if (x < LAST && z < LAST && CanEnter(x + 1, z + 1, CollisionFlag::BLOCK_ENTER_FROM_SOUTH_WEST) && IsOpenTo(x + 1, z, CollisionFlag::BLOCK_ENTER_FROM_WEST) && IsOpenTo(x, z + 1, CollisionFlag::BLOCK_ENTER_FROM_SOUTH))
            {
                Reach(x + 1, z + 1, BACK_SOUTH | BACK_WEST, distance);
            }
        }

        // tryMove's fallback: the reachable tile in the 3x3 around the target with the fewest steps,
        // below 100, scanning x then z.
        [[nodiscard]] std::optional<LocalTile_s> FindNearest(LocalTile_s target) const
        {
            auto nearest = std::optional<LocalTile_s>{};
            auto fewest = MAX_NEAREST_DISTANCE;
            for (auto x = target.x - NEAREST_PADDING; x <= target.x + NEAREST_PADDING; ++x)
            {
                for (auto z = target.z - NEAREST_PADDING; z <= target.z + NEAREST_PADDING; ++z)
                {
                    if (!CollisionMap::Contains(x, z) || m_distances[GetIndex(x, z)] >= fewest)
                    {
                        continue;
                    }

                    fewest = m_distances[GetIndex(x, z)];
                    nearest = LocalTile_s{.x = x, .z = z};
                }
            }

            return nearest;
        }

        // The tiles where the route changes direction, from the stop tile back to the start's first turn.
        [[nodiscard]] std::vector<LocalTile_s> TraceBack(LocalTile_s stop, LocalTile_s start) const
        {
            auto turns = std::vector<LocalTile_s>{stop};
            auto x = stop.x;
            auto z = stop.z;
            auto direction = m_directions[GetIndex(x, z)];
            auto next = direction;
            while (x != start.x || z != start.z)
            {
                if (next != direction)
                {
                    direction = next;
                    turns.push_back({.x = x, .z = z});
                }

                if ((next & BACK_EAST) != 0)
                {
                    ++x;
                }
                else if ((next & BACK_WEST) != 0)
                {
                    --x;
                }

                if ((next & BACK_NORTH) != 0)
                {
                    ++z;
                }
                else if ((next & BACK_SOUTH) != 0)
                {
                    --z;
                }

                next = m_directions[GetIndex(x, z)];
            }

            return turns;
        }

    private:
        [[nodiscard]] bool CanEnter(s32 x, s32 z, u32 mask) const
        {
            return m_directions[GetIndex(x, z)] == UNREACHED && IsOpenTo(x, z, mask);
        }

        [[nodiscard]] bool IsOpenTo(s32 x, s32 z, u32 mask) const
        {
            return IsOpen(m_collision.GetFlags(x, z), mask);
        }

        void Reach(s32 x, s32 z, u8 back, s32 distance)
        {
            m_directions[GetIndex(x, z)] = back;
            m_distances[GetIndex(x, z)] = distance;
            m_queue.push_back({.x = x, .z = z});
        }

        const CollisionMap& m_collision;
        std::vector<u8> m_directions;
        std::vector<s32> m_distances;
        std::vector<LocalTile_s> m_queue;
        std::size_t m_head = 0;
    };

    // tryMove's arrival tests, in its order. Its shape + 1 encoding works out to wall tests for shapes 0
    // to 3 and 9, and wall decor tests for shapes 0 to 8.
    bool HasArrived(const CollisionMap& collision, LocalTile_s tile, LocalTile_s target, const RouteTarget_s& route)
    {
        if (tile.x == target.x && tile.z == target.z)
        {
            return true;
        }

        switch (route.kind)
        {
        case RouteKind_e::Tile:
            return false;
        case RouteKind_e::Wall:
        {
            const auto testsWall = route.shape <= LocShape::WALL_SQUARE_CORNER || route.shape == LocShape::WALL_DIAGONAL;
            if (testsWall && collision.CanReachWall(tile.x, tile.z, target.x, target.z, route.shape, route.angle))
            {
                return true;
            }

            return route.shape <= LocShape::WALLDECOR_DIAGONAL_BOTH && collision.CanReachWallDecor(tile.x, tile.z, target.x, target.z, route.shape, route.angle);
        }
        case RouteKind_e::Area:
            return collision.CanReachArea(tile.x, tile.z, target.x, target.z, route.width, route.length, route.forceApproach);
        }

        assert(false && "Unhandled RouteKind_e");
        return false;
    }
}

bool PathFinder::CanStep(const WorldMap& map, const Tile_s& from, const Tile_s& to)
{
    const auto dx = to.x - from.x;
    const auto dz = to.z - from.z;
    if (from.level != to.level || std::max(std::abs(dx), std::abs(dz)) != 1 || !map.Contains(from) || !map.Contains(to))
    {
        return false;
    }

    const auto& area = map.GetBuildArea();
    const auto& collision = map.GetCollision(from.level);
    const auto x = from.x - area.baseX;
    const auto z = from.z - area.baseZ;
    const auto open = [&collision](s32 tileX, s32 tileZ, u32 mask)
    {
        return IsOpen(collision.GetFlags(tileX, tileZ), mask);
    };

    // The side of each tile the step comes in from.
    const auto fromX = dx < 0 ? CollisionFlag::BLOCK_ENTER_FROM_EAST : CollisionFlag::BLOCK_ENTER_FROM_WEST;
    const auto fromZ = dz < 0 ? CollisionFlag::BLOCK_ENTER_FROM_NORTH : CollisionFlag::BLOCK_ENTER_FROM_SOUTH;
    if (dz == 0)
    {
        return open(x + dx, z, fromX);
    }

    if (dx == 0)
    {
        return open(x, z + dz, fromZ);
    }

    const auto diagonal = dx < 0
        ? (dz < 0 ? CollisionFlag::BLOCK_ENTER_FROM_NORTH_EAST : CollisionFlag::BLOCK_ENTER_FROM_SOUTH_EAST)
        : (dz < 0 ? CollisionFlag::BLOCK_ENTER_FROM_NORTH_WEST : CollisionFlag::BLOCK_ENTER_FROM_SOUTH_WEST);
    return open(x + dx, z + dz, diagonal) && open(x + dx, z, fromX) && open(x, z + dz, fromZ);
}

std::optional<std::vector<Tile_s>> PathFinder::FindPath(const WorldMap& map, const Tile_s& start, const RouteTarget_s& target)
{
    const auto targetOnStartLevel = Tile_s{.x = target.tile.x, .z = target.tile.z, .level = start.level};
    if (!map.Contains(start) || !map.Contains(targetOnStartLevel))
    {
        return std::nullopt;
    }

    const auto& area = map.GetBuildArea();
    const auto& collision = map.GetCollision(start.level);
    const auto from = LocalTile_s{.x = start.x - area.baseX, .z = start.z - area.baseZ};
    const auto to = LocalTile_s{.x = target.tile.x - area.baseX, .z = target.tile.z - area.baseZ};

    auto search = Search{collision};
    search.Start(from);
    auto stop = std::optional<LocalTile_s>{};
    while (const auto tile = search.Next())
    {
        if (HasArrived(collision, *tile, to, target))
        {
            stop = tile;
            break;
        }

        search.Expand(*tile);
    }

    if (!stop && target.kind == RouteKind_e::Tile && target.tryNearest)
    {
        stop = search.FindNearest(to);
    }

    if (!stop)
    {
        return std::nullopt;
    }

    auto turns = search.TraceBack(*stop, from);
    std::ranges::reverse(turns);
    if (turns.size() > MAX_WAYPOINTS)
    {
        turns.resize(MAX_WAYPOINTS);
    }

    auto waypoints = std::vector<Tile_s>{};
    waypoints.reserve(turns.size());
    for (const auto& turn : turns)
    {
        waypoints.push_back({.x = turn.x + area.baseX, .z = turn.z + area.baseZ, .level = start.level});
    }

    return waypoints;
}
