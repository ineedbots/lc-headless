#include "pch.hpp"
#include "Game/Nav/NavJson.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <nlohmann/json.hpp>

using Catch::Matchers::ContainsSubstring;
using Json = nlohmann::json;

TEST_CASE("Minimal navigation JSON preserves unset state and policy", "[NavJson]")
{
    const auto request = NavJson::ParseRequest(R"({"from":[1,2,0],"to":[3,4,1]})");
    CHECK(request.from == NavPoint_s{.x = 1, .z = 2, .level = 0});
    CHECK(request.to == NavPoint_s{.x = 3, .z = 4, .level = 1});
    CHECK(request.options.maxExpansions == NavFindOptions_s::MAX_EXPANSIONS);
    CHECK(request.options.avoidDoors.empty());
    CHECK(request.options.avoidZones.empty());
    CHECK_FALSE(request.options.state.has_value());
    CHECK_FALSE(request.options.useTeleportCatalog.has_value());
    CHECK_FALSE(request.options.policy.useTeleports.has_value());
    CHECK_FALSE(request.options.policy.useShips.has_value());
    CHECK_FALSE(request.options.policy.useShortcuts.has_value());
}

TEST_CASE("Navigation JSON reads explicit policy and state without losing false or zero", "[NavJson]")
{
    const auto request = NavJson::ParseRequest(R"({
        "from":[1,2,0], "to":[3,4,1], "use_teleport_catalog":false,
        "avoid_zones":[{"min_x":1,"max_x":2,"min_z":3,"max_z":4,"level":0}],
        "policy":{"use_teleports":true,"use_ships":false,"use_shortcuts":false,
            "distance_before_teleport":100,"allow_teleport_ids":["varrock"],"deny_teleport_ids":["falador"]},
        "state":{"members":true,"worn":{"Boots":1,"boots":2},"free_slots":0,
            "entrana_restricted_gear":true,"can_slash_web":false,"essence_exit_return":null}
    })");
    CHECK(request.options.useTeleportCatalog == false);
    REQUIRE(request.options.avoidZones.size() == 1);
    const auto& zone = request.options.avoidZones.front();
    CHECK(zone.minX == 1);
    CHECK(zone.maxX == 2);
    CHECK(zone.minZ == 3);
    CHECK(zone.maxZ == 4);
    CHECK(zone.level == 0);
    const auto& policy = request.options.policy;
    CHECK(policy.useTeleports == true);
    CHECK(policy.useShips == false);
    CHECK(policy.useShortcuts == false);
    CHECK(policy.distanceBeforeTeleport == 100);
    CHECK(policy.allowTeleportIds == std::vector<std::string>{"varrock"});
    CHECK(policy.denyTeleportIds == std::vector<std::string>{"falador"});
    REQUIRE(request.options.state.has_value());
    const auto& state = *request.options.state;
    CHECK(state.members);
    CHECK(state.worn.at("boots") == 3);
    CHECK(state.freeSlots == 0);
    CHECK(state.entranaRestrictedGear);
    CHECK(state.canSlashWeb == false);
    CHECK_FALSE(state.essenceExitReturn.has_value());
}

TEST_CASE("Navigation JSON reports malformed nested fields as invalid requests", "[NavJson]")
{
    auto json = Json{{"from", {1, 2, 0}}, {"to", {3, 4, 0}}};
    SECTION("missing destination") { json.erase("to"); }
    SECTION("wrong coordinate type") { json["from"][0] = "west"; }
    SECTION("short door") { json["avoid_doors"] = Json::array({Json::array({1})}); }
    SECTION("missing zone coordinate") { json["avoid_zones"] = Json::array({Json{{"min_x", 1}}}); }
    SECTION("wrong optional boolean") { json["policy"]["use_ships"] = "yes"; }
    SECTION("wrong skill count") { json["state"]["skills"]["Agility"] = "ten"; }
    SECTION("wrong quest status") { json["state"]["quests"]["Cook's Assistant"] = 2; }
    CHECK_THROWS_WITH(NavJson::ParseRequest(json.dump()), ContainsSubstring("a route request is malformed:"));
    CHECK_THROWS_AS(NavJson::ParseRequest("{"), std::invalid_argument);
}

TEST_CASE("Navigation JSON serialises optional edge destinations and identifiers", "[NavJson]")
{
    auto edge = NavEdge_s{.kind = "door", .cost = 4, .locName = "Gate", .action = "Open",
        .locX = 3200, .locZ = 3201, .locId = 10, .openLocId = 11,
        .toLevel = 0, .toTile = std::pair{3202, 3203}, .acceptAnyLanding = true};
    auto path = NavPath_s{.ok = true, .cost = 4, .expanded = 12};
    path.waypoints = {{.point = {.x = 3200, .z = 3201, .level = 0}},
        {.point = {.x = 3202, .z = 3203, .level = 0}, .edge = &edge}};
    const auto withIds = GENERATE(false, true);
    if (!withIds)
    {
        edge.locId.reset();
        edge.openLocId.reset();
        edge.toLevel.reset();
        edge.toTile.reset();
    }
    const auto json = Json::parse(NavJson::ToJson(path));
    CHECK(json.at("ok") == true);
    CHECK(json.at("cost") == 4);
    CHECK(json.at("expanded") == 12);
    REQUIRE(json.at("waypoints").size() == 2);
    CHECK_FALSE(json["waypoints"][0].contains("transport"));
    const auto& transport = json["waypoints"][1].at("transport");
    CHECK(transport.at("kind") == "door");
    CHECK(transport.at("loc_name") == "Gate");
    CHECK(transport.at("action") == "Open");
    CHECK(transport.at("loc_x") == 3200);
    CHECK(transport.at("loc_z") == 3201);
    CHECK(transport.at("accept_any_landing") == true);
    CHECK(transport.at("edge_cost") == 4);
    CHECK(transport.contains("loc_id") == withIds);
    CHECK(transport.contains("open_loc_id") == withIds);
    CHECK(transport.contains("to_level") == withIds);
    CHECK(transport.contains("to_tile") == withIds);
    if (withIds)
    {
        CHECK(transport.at("loc_id") == 10);
        CHECK(transport.at("open_loc_id") == 11);
        CHECK(transport.at("to_level") == 0);
        CHECK(transport.at("to_tile") == Json::array({3202, 3203}));
    }
}

TEST_CASE("Navigation JSON distinguishes spell and jewellery teleports", "[NavJson]")
{
    const auto spell = GENERATE(false, true);
    auto teleport = NavTeleport_s{.id = "test", .family = spell ? "spell" : "jewellery",
        .label = "Destination", .to = {.x = 3200, .z = 3201, .level = 0}, .cost = 15};
    auto path = NavPath_s{.ok = true, .cost = 15};
    path.waypoints = {{.point = teleport.to, .teleport = &teleport}};
    const auto json = Json::parse(NavJson::ToJson(path));
    REQUIRE(json["waypoints"].size() == 1);
    const auto& waypoint = json["waypoints"][0];
    CHECK(waypoint.at("x") == 3200);
    CHECK(waypoint.at("z") == 3201);
    CHECK(waypoint.at("level") == 0);
    const auto& transport = waypoint.at("transport");
    CHECK(transport.at("kind") == "teleport");
    CHECK(transport.at("action") == (spell ? "Cast" : "Rub"));
    CHECK(transport.at("family") == teleport.family);
    CHECK(transport.at("teleport_id") == "test");
    CHECK(transport.at("loc_name") == "Destination");
    CHECK(transport.at("to_tile") == Json::array({3200, 3201}));
    CHECK(transport.at("accept_any_landing") == true);
    CHECK(transport.at("edge_cost") == 15);
}
