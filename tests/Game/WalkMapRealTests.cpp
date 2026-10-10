#include "pch.hpp"
#include "../Cache/RealCache.hpp"

#include "Cache/GameCache_s.hpp"
#include "Game/Map/WalkMap.hpp"

#include <catch2/catch_test_macros.hpp>

#include <set>

namespace
{
    struct Point_s
    {
        s32 x = 0;
        s32 z = 0;
    };

    // The tiles a walk on one level reaches from start within radius, by WalkMap's exits alone.
    std::set<std::pair<s32, s32>> Flood(const WalkMap& map, Point_s start, s32 level, s32 radius)
    {
        auto seen = std::set<std::pair<s32, s32>>{{start.x, start.z}};
        auto queue = std::deque<Point_s>{start};
        while (!queue.empty())
        {
            const auto tile = queue.front();
            queue.pop_front();
            const auto exits = map.GetExits(tile.x, tile.z, level);
            for (auto direction = 0; direction < WalkMap::DIRECTIONS; ++direction)
            {
                const auto next = Point_s{tile.x + WalkMap::DX[static_cast<std::size_t>(direction)], tile.z + WalkMap::DZ[static_cast<std::size_t>(direction)]};
                const auto far = std::max(std::abs(next.x - start.x), std::abs(next.z - start.z)) > radius;
                if ((exits & (1 << direction)) == 0 || far || !seen.insert({next.x, next.z}).second)
                {
                    continue;
                }

                queue.push_back(next);
            }
        }

        return seen;
    }
}

TEST_CASE("WalkMap builds the real cache's world, doors shut", "[RealCache]")
{
    const auto& cache = RealCache::Require();
    const auto started = std::chrono::steady_clock::now();
    const auto map = WalkMap{cache};
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started);
    UNSCOPED_INFO(std::format("WalkMap built in {} ms: {} level squares, {:.1f} MB", elapsed.count(), map.GetLevelSquareCount(), static_cast<double>(map.GetMemoryBytes()) / (1024.0 * 1024.0)));
    CHECK(map.GetLevelSquareCount() >= cache.squares.size());

    // Lumbridge castle's courtyard, and the open field beyond on level 1, where there's no floor.
    CHECK(map.IsWalkable(3222, 3218, 0));
    CHECK(map.GetExits(3222, 3218, 0) != 0);
    CHECK_FALSE(map.IsWalkable(3150, 3150, 1));
    CHECK(map.GetExits(3150, 3150, 1) == 0);
    CHECK(map.IsWalkable(3205, 3209, 1));
    CHECK_FALSE(map.IsWalkable(5000, 5000, 0));

    // The kitchen's doors are shut in the cache, so a walk from the Cook doesn't leave.
    const auto kitchen = Flood(map, {3209, 3215}, 0, 12);
    CHECK(kitchen.size() < 60);
    CHECK_FALSE(kitchen.contains({3208, 3209}));
    // South of it, the room with the staircase, shut off by its own door.
    const auto stairRoom = Flood(map, {3208, 3209}, 0, 12);
    CHECK(stairRoom.contains({3205, 3209}));
    CHECK_FALSE(stairRoom.contains({3209, 3215}));
    CHECK_FALSE(stairRoom.contains({3222, 3218}));
}
