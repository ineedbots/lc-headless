#include "pch.hpp"

#include "Cache/MapSquare.hpp"
#include "Cache/Type/GameCache_s.hpp"
#include "Game/Map/WalkMap.hpp"
#include "Game/Nav/NavGraph.hpp"
#include "Game/Nav/NavGraphJson.hpp"
#include "Game/Nav/Type/NavEdge_s.hpp"
#include "Game/Nav/Type/NavPoint_s.hpp"
#include "Game/Nav/Type/NavRequires_s.hpp"
#include "Game/Nav/Type/NavTeleport_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <nlohmann/json.hpp>

using Catch::Matchers::ContainsSubstring;

TEST_CASE("Graph decoding filters unwalkable edges before optional metadata", "[NavGraph][WorldPathFinder]")
{
    auto cache = GameCache_s{};
    cache.squares.try_emplace(MapSquare::GetId(50, 50), u8{50}, u8{50}, MapSquare::BlockedTiles{}, std::vector<MapLoc_s>{});
    const auto map = WalkMap{cache};
    auto edge = nlohmann::json{{"kind", "door"}, {"from", {{"x", 3201}, {"z", 3201}}}, {"to", {{"x", 100}, {"z", 100}}}, {"cost", 2}, {"locId", "bad"}};

    CHECK(NavGraphJson::ReadEdges(map, nlohmann::json::array({edge}).dump()).empty());

    edge["to"] = {{"x", 3202}, {"z", 3201}};
    CHECK_THROWS_WITH(NavGraphJson::ReadEdges(map, nlohmann::json::array({edge}).dump()), ContainsSubstring("edges.json:"));

    edge["locId"] = 0;
    edge["openLocId"] = 0;
    edge["toLevel"] = 0;
    edge["toTile"] = {{"x", 3202}, {"z", 3201}};
    edge["acceptAnyLanding"] = false;
    const auto text = nlohmann::json::array({edge}).dump();
    const auto edges = NavGraphJson::ReadEdges(map, text);
    REQUIRE(edges.size() == 1);
    CHECK(edges[0].from.level == 0);
    CHECK(edges[0].locId == 0);
    CHECK(edges[0].openLocId == 0);
    CHECK(edges[0].toLevel == 0);
    CHECK(edges[0].toTile == std::pair<s32, s32>{3202, 3201});
    CHECK_FALSE(edges[0].acceptAnyLanding);

    const auto graph = NavGraph{map, text, "[]"};
    CHECK(graph.GetEdgeCount() == 1);
    CHECK(graph.GetDoorCount() == 1);
    CHECK_FALSE(graph.HasLongEdges());
    REQUIRE(graph.GetEdgesFrom(NavGraph::GetNodeId(3201, 3201, 0)).size() == 1);
    CHECK(graph.GetEdgesFrom(NavGraph::GetNodeId(3201, 3201, 0))[0]->locId == 0);

    edge["to"] = {{"x", 100}, {"z", 100}};
    edge.erase("cost");
    CHECK_THROWS_WITH(NavGraphJson::ReadEdges(map, nlohmann::json::array({edge}).dump()), ContainsSubstring("edges.json:"));
}

TEST_CASE("Graph teleport decoding preserves contextual defaults and requirement amounts", "[NavGraph][WorldPathFinder]")
{
    const auto teleports = NavGraphJson::ReadTeleports(R"([
        {"teleportId":"spell","to":{"x":3201,"z":3202}},
        {"teleportId":"ring","family":"jewellery","to":{"x":3201,"z":3202},
         "origin":{"maxWildernessLevel":0},"itemNameMatch":["Ring"],
         "requires":{"skills":[{"name":"magic","level":10}],"items":[{"name":"Law rune","count":2}],
                     "currency":{"name":"Coins","amount":3},"quests":[{"quest":"test"}]}},
        {"teleportId":"free","cost":0,"requires":null,"to":{"x":3201,"z":3202,"level":1}}
    ])");
    REQUIRE(teleports.size() == 3);
    CHECK(teleports[0].family == "spell");
    CHECK(teleports[0].cost == 10);
    CHECK(teleports[0].to.level == 0);
    CHECK_FALSE(teleports[0].requirement);
    CHECK(teleports[1].cost == 8);
    CHECK(teleports[1].maxWildernessLevel == 0);
    CHECK(teleports[1].itemNameMatch == std::vector<std::string>{"Ring"});
    REQUIRE(teleports[1].requirement);
    const auto& requirement = *teleports[1].requirement;
    REQUIRE(requirement.skills.size() == 1);
    REQUIRE(requirement.items.size() == 1);
    REQUIRE(requirement.currency);
    REQUIRE(requirement.quests.size() == 1);
    CHECK(requirement.skills[0].count == 10);
    CHECK(requirement.items[0].count == 2);
    CHECK(requirement.currency->count == 3);
    CHECK(requirement.quests[0].minStatus.empty());
    CHECK(requirement.quests[0].maxStatus.empty());
    CHECK(teleports[2].cost == 0);
    CHECK(teleports[2].to.level == 1);
    CHECK_FALSE(teleports[2].requirement);
    CHECK_THROWS_WITH(NavGraphJson::ReadTeleports(R"([{"to":{"x":1,"z":2}}])"), ContainsSubstring("teleports.json:"));
    CHECK_THROWS_WITH(NavGraphJson::ReadTeleports(R"([{"teleportId":"bad","to":[1,2,0]}])"), ContainsSubstring("teleports.json:"));
}
