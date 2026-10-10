#include "pch.hpp"

#include "Cache/GameCache_s.hpp"
#include "Cache/MapSquare.hpp"
#include "Game/Nav/NavGraph.hpp"
#include "Game/Nav/WorldPathFinder.hpp"
#include "Script/NavJson.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    constexpr auto SQUARE = 50;
    constexpr auto BASE = SQUARE * MapSquare::SIZE;
    constexpr auto BOOTH = 40;

    NavPoint_s At(s32 x, s32 z, s32 level = 0)
    {
        return {.x = BASE + x, .z = BASE + z, .level = level};
    }

    // One open square with a floor on every level, but for one blocked tile, the booth.
    GameCache_s MakeCache()
    {
        auto cache = GameCache_s{};
        auto blocked = MapSquare::BlockedTiles{};
        blocked.set(MapSquare::GetBit(0, BOOTH, BOOTH));
        cache.squares.try_emplace(MapSquare::GetId(SQUARE, SQUARE), static_cast<u8>(SQUARE), static_cast<u8>(SQUARE), blocked, std::vector<MapLoc_s>{});
        return cache;
    }

    // A staircase up to level 1 from (10, 10), which needs Agility 10, and a spell that lands far off, which
    // needs a law rune. The square is (3200, 3200) to (3263, 3263).
    constexpr auto EDGES = R"json([
        {"kind": "stair", "from": {"x": 3210, "z": 3210, "level": 0}, "to": {"x": 3210, "z": 3211, "level": 1}, "cost": 6,
         "locName": "Staircase", "action": "Climb-up", "locX": 3210, "locZ": 3209, "toLevel": 1,
         "requires": {"skills": [{"name": "agility", "level": 10}]}}
    ])json";

    constexpr auto TELEPORTS = R"json([
        {"teleportId": "far", "family": "spell", "label": "Far teleport", "to": {"x": 3262, "z": 3202, "level": 0}, "cost": 10,
         "requires": {"items": [{"name": "Law rune", "count": 1}]}}
    ])json";

    NavState_s MakeState(s32 agility, s32 laws)
    {
        auto state = NavState_s{};
        state.skills["agility"] = agility;
        state.items["law rune"] = laws;
        return state;
    }

    class Fixture
    {
    public:
        Fixture()
            : m_navigation{m_cache, EDGES, TELEPORTS}
        {
        }

        [[nodiscard]] NavPath_s Find(NavPoint_s from, NavPoint_s to, NavFindOptions_s options = {}) const
        {
            if (!options.policy.useTeleports)
            {
                options.policy.useTeleports = false;
            }

            return WorldPathFinder::FindPath(m_navigation, from, to, options);
        }

    private:
        GameCache_s m_cache = MakeCache();
        Navigation_s m_navigation;
    };

    bool Visits(const NavPath_s& path, const std::function<bool(const NavPoint_s&)>& test)
    {
        for (std::size_t i = 1; i < path.waypoints.size(); ++i)
        {
            auto from = path.waypoints[i - 1].point;
            const auto to = path.waypoints[i].point;
            if (from.level != to.level || path.waypoints[i].edge != nullptr)
            {
                continue;
            }

            while (true)
            {
                if (test(from))
                {
                    return true;
                }

                if (from == to)
                {
                    break;
                }

                from.x += (to.x > from.x) - (to.x < from.x);
                from.z += (to.z > from.z) - (to.z < from.z);
            }
        }

        return false;
    }
}

TEST_CASE("WorldPathFinder walks across open ground, keeping only the turns", "[WorldPathFinder]")
{
    const auto fixture = Fixture{};
    const auto path = fixture.Find(At(5, 5), At(20, 5));
    REQUIRE(path.ok);
    // A step costs the same straight or diagonal, so a route of the least cost may weave.
    CHECK(path.cost == 15);
    CHECK(path.waypoints.size() <= 4);
    CHECK(path.waypoints.front().point == At(5, 5));
    CHECK(path.waypoints.back().point == At(20, 5));
}

TEST_CASE("WorldPathFinder routes round avoided zones, though it may leave one it starts in", "[WorldPathFinder]")
{
    const auto fixture = Fixture{};
    auto options = NavFindOptions_s{};
    options.avoidZones.push_back({.minX = BASE + 15, .maxX = BASE + 15, .minZ = BASE + 0, .maxZ = BASE + 20, .level = 0});
    const auto path = fixture.Find(At(5, 10), At(25, 10), options);
    REQUIRE(path.ok);
    CHECK(path.cost > 20);
    CHECK_FALSE(Visits(path, [](const NavPoint_s& tile) { return tile.x == BASE + 15 && tile.z <= BASE + 20; }));

    const auto escaping = fixture.Find(At(15, 10), At(25, 10), options);
    REQUIRE(escaping.ok);
    CHECK(escaping.cost == 10);
}

TEST_CASE("WorldPathFinder takes a hop to another level when the account meets its requirements", "[WorldPathFinder]")
{
    const auto fixture = Fixture{};
    auto options = NavFindOptions_s{.state = MakeState(10, 0)};
    const auto path = fixture.Find(At(5, 5), At(10, 20, 1), options);
    REQUIRE(path.ok);
    const auto hop = std::ranges::find_if(path.waypoints, [](const NavWaypoint_s& waypoint) { return waypoint.edge != nullptr; });
    REQUIRE(hop != path.waypoints.end());
    CHECK(hop->edge->action == "Climb-up");
    CHECK((hop - 1)->point == At(10, 10));
    CHECK(hop->point == At(10, 11, 1));
    CHECK(path.waypoints.back().point == At(10, 20, 1));

    SECTION("an unmet requirement fails closed")
    {
        options.state = MakeState(9, 0);
        const auto refused = fixture.Find(At(5, 5), At(10, 20, 1), options);
        CHECK_FALSE(refused.ok);
        CHECK(refused.reason == "unreachable");
    }

    SECTION("without a state, gated hops are planned, as rs2b0t plans offline")
    {
        CHECK(fixture.Find(At(5, 5), At(10, 20, 1)).ok);
    }

    SECTION("a refused hop can be avoided by its loc")
    {
        options.avoidDoors.emplace_back(BASE + 10, BASE + 9);
        CHECK_FALSE(fixture.Find(At(5, 5), At(10, 20, 1), options).ok);
    }
}

TEST_CASE("WorldPathFinder plans a teleport only when the policy and the account allow it", "[WorldPathFinder]")
{
    const auto fixture = Fixture{};
    auto options = NavFindOptions_s{.state = MakeState(1, 1)};
    options.policy.useTeleports = true;
    const auto path = fixture.Find(At(1, 1), At(60, 1), options);
    REQUIRE(path.ok);
    REQUIRE(path.waypoints.size() >= 2);
    CHECK(path.waypoints[1].teleport != nullptr);
    CHECK(path.cost < 20);

    options.state = MakeState(1, 0);
    const auto walking = fixture.Find(At(1, 1), At(60, 1), options);
    REQUIRE(walking.ok);
    CHECK(walking.cost == 59);

    options.state = MakeState(1, 1);
    options.policy.denyTeleportIds = {"far"};
    CHECK(fixture.Find(At(1, 1), At(60, 1), options).cost == 59);
}

TEST_CASE("WorldPathFinder ends beside a goal that can't be stood on, and reports what stops it", "[WorldPathFinder]")
{
    const auto fixture = Fixture{};
    const auto booth = fixture.Find(At(30, 40), At(BOOTH, BOOTH));
    REQUIRE(booth.ok);
    const auto end = booth.waypoints.back().point;
    CHECK(std::max(std::abs(end.x - (BASE + BOOTH)), std::abs(end.z - (BASE + BOOTH))) == 1);

    auto options = NavFindOptions_s{.maxExpansions = 10};
    const auto budget = fixture.Find(At(1, 1), At(60, 60), options);
    CHECK_FALSE(budget.ok);
    CHECK_THAT(budget.reason, ContainsSubstring("budget"));

    const auto offMap = fixture.Find(At(1, 1), {.x = 100, .z = 100, .level = 0});
    CHECK_FALSE(offMap.ok);
    const auto start = fixture.Find({.x = 100, .z = 100, .level = 0}, At(1, 1));
    CHECK_THAT(start.reason, ContainsSubstring("not walkable"));
}

TEST_CASE("NavJson reads route requests and writes routes", "[WorldPathFinder]")
{
    const auto request = NavJson::ParseRequest(R"json({
        "from": [3205, 3205, 0], "to": [3210, 3211, 1], "max_expansions": 500, "avoid_doors": [[3210, 3209]],
        "use_teleport_catalog": null, "avoid_zones": [{"min_x": 1, "max_x": 2, "min_z": 3, "max_z": 4, "level": null}],
        "policy": {"use_teleports": false, "deny_teleport_ids": ["varrock"]},
        "state": {"members": true, "skills": {"Agility": 10}, "items": {"Coins": 5, "coins": 5}, "quests": {"Cook's Assistant": "complete"}, "free_slots": 3}
    })json");
    CHECK(request.from == At(5, 5));
    CHECK(request.to == At(10, 11, 1));
    CHECK(request.options.maxExpansions == 500);
    CHECK(request.options.avoidDoors == std::vector<std::pair<s32, s32>>{{3210, 3209}});
    CHECK_FALSE(request.options.useTeleportCatalog.has_value());
    REQUIRE(request.options.avoidZones.size() == 1);
    CHECK_FALSE(request.options.avoidZones[0].level.has_value());
    CHECK(request.options.policy.useTeleports == false);
    CHECK(request.options.policy.denyTeleportIds == std::vector<std::string>{"varrock"});
    REQUIRE(request.options.state.has_value());
    CHECK(request.options.state->skills.at("agility") == 10);
    CHECK(request.options.state->items.at("coins") == 10);
    CHECK(request.options.state->quests.at("cook's assistant") == "complete");
    CHECK_THROWS_AS(NavJson::ParseRequest(R"json({"from": [1, 2]})json"), std::invalid_argument);

    const auto fixture = Fixture{};
    auto options = NavFindOptions_s{.state = MakeState(10, 0)};
    const auto json = NavJson::ToJson(fixture.Find(At(5, 5), At(10, 20, 1), options));
    CHECK_THAT(json, ContainsSubstring(R"("ok":true)"));
    CHECK_THAT(json, ContainsSubstring(R"("action":"Climb-up")"));
    CHECK_THAT(json, ContainsSubstring(R"("to_level":1)"));
}
