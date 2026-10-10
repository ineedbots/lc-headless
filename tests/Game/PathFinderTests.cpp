#include "pch.hpp"
#include "../Cache/TestCache.hpp"
#include "Fixtures.hpp"

#include "Cache/GameCache_s.hpp"
#include "Game/Map/CollisionFlag.hpp"
#include "Game/Map/CollisionMap.hpp"
#include "Game/Map/PathFinder.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/Tile_s.hpp"

#include <catch2/catch_test_macros.hpp>

// Where a test gives exact waypoints, they're what the webclient's tryMove, run on its own CollisionMap,
// gives for the same map.
namespace
{
    constexpr auto DOOR = u16{1530};
    constexpr auto TREE = u16{1276};
    constexpr auto WALL = u8{0};
    constexpr auto WEST = u8{0};
    constexpr auto CENTREPIECE = u8{10};
    constexpr auto APPROACH_SOUTH = u8{0x4};

    Tile_s Local(s32 x, s32 z)
    {
        return {.x = Fixtures::BASE + x, .z = Fixtures::BASE + z, .level = 0};
    }

    std::vector<Tile_s> Locals(std::initializer_list<std::pair<s32, s32>> tiles)
    {
        auto absolute = std::vector<Tile_s>{};
        for (const auto& [x, z] : tiles)
        {
            absolute.push_back(Local(x, z));
        }

        return absolute;
    }

    // A wall of blocked tiles from (x1, z1) to (x2, z2), inclusive.
    void AddBlock(std::vector<Tile_s>& blocked, s32 x1, s32 z1, s32 x2, s32 z2)
    {
        for (auto x = x1; x <= x2; ++x)
        {
            for (auto z = z1; z <= z2; ++z)
            {
                blocked.push_back(Local(x, z));
            }
        }
    }

    WorldMap MakeMap(std::span<const TestLoc_s> locs, std::span<const Tile_s> blocked)
    {
        auto cache = GameCache_s{};
        TestCache::AddLoc(cache, DOOR, "Door", {"Open"});
        auto& tree = TestCache::AddLoc(cache, TREE, "Tree", {"Chop down"});
        tree.width = 2;
        tree.length = 2;
        TestCache::SetMap(cache, locs, blocked);

        auto map = WorldMap{std::make_shared<const GameCache_s>(std::move(cache))};
        auto state = Fixtures::PlacedState();
        state.sceneChangeCount = 1;
        map.Update(state);
        return map;
    }

    WorldMap MakeMap(std::span<const Tile_s> blocked)
    {
        return MakeMap({}, blocked);
    }

    // Whether a single step is one the search could take, by the webclient's rules.
    bool CanStep(const CollisionMap& collision, s32 x, s32 z, s32 dx, s32 dz)
    {
        const auto enters = [&collision](s32 tileX, s32 tileZ, s32 fromX, s32 fromZ)
        {
            auto mask = CollisionFlag::BLOCKED;
            mask |= fromX < 0 ? CollisionFlag::WALL_WEST : (fromX > 0 ? CollisionFlag::WALL_EAST : 0);
            mask |= fromZ < 0 ? CollisionFlag::WALL_SOUTH : (fromZ > 0 ? CollisionFlag::WALL_NORTH : 0);
            if (fromX != 0 && fromZ != 0)
            {
                mask |= fromX < 0 ? (fromZ < 0 ? CollisionFlag::WALL_SOUTH_WEST : CollisionFlag::WALL_NORTH_WEST) : (fromZ < 0 ? CollisionFlag::WALL_SOUTH_EAST : CollisionFlag::WALL_NORTH_EAST);
            }

            return (collision.GetFlags(tileX, tileZ) & mask) == 0;
        };

        // The side of the entered tile the step comes in from is opposite its direction.
        if (!enters(x + dx, z + dz, -dx, -dz))
        {
            return false;
        }

        return dx == 0 || dz == 0 || (enters(x + dx, z, -dx, 0) && enters(x, z + dz, 0, -dz));
    }

    // Walks each leg one step at a time, checking every step and that each waypoint turns.
    void CheckRoute(const WorldMap& map, const Tile_s& start, const std::vector<Tile_s>& waypoints)
    {
        const auto& collision = map.GetCollision(start.level);
        auto x = start.x - Fixtures::BASE;
        auto z = start.z - Fixtures::BASE;
        auto lastDirection = std::pair{0, 0};
        for (const auto& waypoint : waypoints)
        {
            const auto targetX = waypoint.x - Fixtures::BASE;
            const auto targetZ = waypoint.z - Fixtures::BASE;
            const auto direction = std::pair{(targetX > x) - (targetX < x), (targetZ > z) - (targetZ < z)};
            CAPTURE(x, z, targetX, targetZ);
            REQUIRE((targetX == x || targetZ == z || std::abs(targetX - x) == std::abs(targetZ - z)));
            CHECK(direction != lastDirection);
            while (x != targetX || z != targetZ)
            {
                REQUIRE(CanStep(collision, x, z, direction.first, direction.second));
                x += direction.first;
                z += direction.second;
            }

            lastDirection = direction;
        }
    }

    std::optional<std::vector<Tile_s>> FindTilePath(const WorldMap& map, const Tile_s& start, const Tile_s& target, bool tryNearest = false)
    {
        return PathFinder::FindPath(map, start, {.kind = RouteKind_e::Tile, .tile = target, .tryNearest = tryNearest});
    }
}

TEST_CASE("PathFinder walks straight lines in the open", "[PathFinder]")
{
    const auto map = MakeMap({});
    CHECK(FindTilePath(map, Local(20, 20), Local(20, 30)) == Locals({{20, 30}}));
    CHECK(FindTilePath(map, Local(20, 20), Local(25, 25)) == Locals({{25, 25}}));
    CHECK(FindTilePath(map, Local(20, 20), Local(12, 20)) == Locals({{12, 20}}));

    SECTION("a start on the target is the one waypoint")
    {
        CHECK(FindTilePath(map, Local(20, 20), Local(20, 20)) == Locals({{20, 20}}));
    }

    SECTION("a start or target outside the area has no route")
    {
        CHECK_FALSE(FindTilePath(map, Local(20, 20), Local(120, 20)).has_value());
        CHECK_FALSE(FindTilePath(map, Local(-5, 20), Local(20, 20)).has_value());
    }
}

TEST_CASE("PathFinder goes round obstacles, keeping only the turns", "[PathFinder]")
{
    auto blocked = std::vector<Tile_s>{};
    AddBlock(blocked, 15, 25, 25, 25);
    const auto map = MakeMap(blocked);

    const auto route = FindTilePath(map, Local(20, 20), Local(20, 30));
    REQUIRE(route.has_value());
    CHECK(*route == Locals({{18, 20}, {14, 24}, {14, 26}, {16, 26}, {20, 30}}));
    CheckRoute(map, Local(20, 20), *route);
}

TEST_CASE("PathFinder breaks ties between equal routes as the webclient does", "[PathFinder]")
{
    auto blocked = std::vector<Tile_s>{};
    AddBlock(blocked, 47, 53, 53, 53);
    const auto map = MakeMap(blocked);

    CHECK(FindTilePath(map, Local(50, 50), Local(50, 56)) == Locals({{48, 50}, {46, 52}, {46, 54}, {48, 54}, {50, 56}}));
    CHECK(FindTilePath(map, Local(20, 20), Local(22, 27)) == Locals({{20, 25}, {22, 27}}));
}

TEST_CASE("PathFinder won't cut a corner diagonally", "[PathFinder]")
{
    const auto blocked = Locals({{21, 20}});
    const auto map = MakeMap(blocked);
    CHECK(FindTilePath(map, Local(20, 20), Local(21, 21)) == Locals({{20, 21}, {21, 21}}));
}

TEST_CASE("PathFinder reports what it can't reach", "[PathFinder]")
{
    auto blocked = std::vector<Tile_s>{};
    AddBlock(blocked, 29, 29, 31, 29);
    AddBlock(blocked, 29, 31, 31, 31);
    AddBlock(blocked, 29, 30, 29, 30);
    AddBlock(blocked, 31, 30, 31, 30);
    AddBlock(blocked, 40, 40, 40, 40);
    const auto map = MakeMap(blocked);

    CHECK_FALSE(FindTilePath(map, Local(20, 30), Local(30, 30)).has_value());
    CHECK_FALSE(FindTilePath(map, Local(20, 30), Local(30, 30), true).has_value());

    SECTION("tryNearest stops on the reachable tile around the target with the fewest steps")
    {
        const auto route = FindTilePath(map, Local(40, 30), Local(40, 40), true);
        REQUIRE(route.has_value());
        CHECK(*route == Locals({{40, 38}, {39, 39}}));
        CheckRoute(map, Local(40, 30), *route);
    }
}

TEST_CASE("PathFinder reaches walls from either side", "[PathFinder]")
{
    const auto locs = std::to_array<TestLoc_s>({{.id = DOOR, .tile = Local(40, 40), .shape = WALL, .angle = WEST}});
    const auto map = MakeMap(locs, {});
    const auto door = RouteTarget_s{.kind = RouteKind_e::Wall, .tile = Local(40, 40), .shape = WALL, .angle = WEST};

    CHECK(PathFinder::FindPath(map, Local(35, 40), door) == Locals({{39, 40}}));

    CHECK(PathFinder::FindPath(map, Local(45, 40), door) == Locals({{40, 40}}));

    SECTION("but not through it")
    {
        const auto inside = FindTilePath(map, Local(39, 40), Local(40, 40));
        REQUIRE(inside.has_value());
        CHECK(*inside == Locals({{39, 39}, {40, 39}, {40, 40}}));
        CheckRoute(map, Local(39, 40), *inside);
    }
}

TEST_CASE("PathFinder reaches areas from any side forceApproach allows", "[PathFinder]")
{
    const auto locs = std::to_array<TestLoc_s>({{.id = TREE, .tile = Local(60, 60), .shape = CENTREPIECE}});
    const auto map = MakeMap(locs, {});
    auto tree = RouteTarget_s{.kind = RouteKind_e::Area, .tile = Local(60, 60), .width = 2, .length = 2};

    CHECK(PathFinder::FindPath(map, Local(60, 55), tree) == Locals({{60, 59}}));
    CHECK(PathFinder::FindPath(map, Local(66, 61), tree) == Locals({{62, 61}}));

    tree.forceApproach = APPROACH_SOUTH;
    const auto route = PathFinder::FindPath(map, Local(60, 55), tree);
    REQUIRE(route.has_value());
    CHECK(*route == Locals({{60, 58}, {59, 59}, {59, 60}}));
    CheckRoute(map, Local(60, 55), *route);
}

TEST_CASE("PathFinder cuts a long route to 25 waypoints", "[PathFinder]")
{
    // A corridor that doubles back on itself every other row, from the bottom to the top.
    auto blocked = std::vector<Tile_s>{};
    AddBlock(blocked, 9, 9, 41, 9);
    AddBlock(blocked, 9, 9, 9, 50);
    AddBlock(blocked, 41, 9, 41, 50);
    for (auto row = 0; row < 20; ++row)
    {
        const auto z = 11 + row * 2;
        if (row % 2 == 0)
        {
            AddBlock(blocked, 10, z, 39, z);
        }
        else
        {
            AddBlock(blocked, 11, z, 40, z);
        }
    }

    const auto map = MakeMap(blocked);
    const auto target = Local(10, 50);
    const auto route = FindTilePath(map, Local(10, 10), target);
    REQUIRE(route.has_value());
    CHECK(route->size() == PathFinder::MAX_WAYPOINTS);
    CHECK(route->front() == Local(40, 10));
    CHECK(route->back() == Local(40, 34));
    CheckRoute(map, Local(10, 10), *route);
}

TEST_CASE("PathFinder's single steps agree with the search's rules", "[PathFinder]")
{
    const auto locs = std::to_array<TestLoc_s>({{.id = DOOR, .tile = Local(40, 40), .shape = WALL, .angle = WEST}});
    const auto blocked = Locals({{42, 41}});
    const auto map = MakeMap(locs, blocked);
    const auto& collision = map.GetCollision(0);

    for (auto x = 38; x <= 43; ++x)
    {
        for (auto z = 38; z <= 43; ++z)
        {
            for (auto dx = -1; dx <= 1; ++dx)
            {
                for (auto dz = -1; dz <= 1; ++dz)
                {
                    if (dx == 0 && dz == 0)
                    {
                        continue;
                    }

                    CAPTURE(x, z, dx, dz);
                    CHECK(PathFinder::CanStep(map, Local(x, z), Local(x + dx, z + dz)) == CanStep(collision, x, z, dx, dz));
                }
            }
        }
    }

    // The door's west wall stops a step through it, and only that.
    CHECK_FALSE(PathFinder::CanStep(map, Local(39, 40), Local(40, 40)));
    CHECK(PathFinder::CanStep(map, Local(40, 41), Local(40, 40)));
    CHECK_FALSE(PathFinder::CanStep(map, Local(20, 20), Local(22, 20)));
    CHECK_FALSE(PathFinder::CanStep(map, Local(20, 20), Local(20, 20)));
    CHECK_FALSE(PathFinder::CanStep(map, Local(20, 20), Tile_s{.x = Fixtures::BASE + 21, .z = Fixtures::BASE + 20, .level = 1}));
}
