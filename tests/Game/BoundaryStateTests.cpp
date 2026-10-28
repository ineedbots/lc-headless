#include "pch.hpp"
#include "../Support/Game/QueryWorld.hpp"
#include "Cache/GameCache_s.hpp"
#include "Game/Decode/EntityInfo.hpp"
#include "Game/Map/WalkMap.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Query/ReachQuery.hpp"
#include "Game/State/Player_s.hpp"
#include <catch2/catch_test_macros.hpp>

TEST_CASE("Face entity sentinels distinguish no target and both index spaces", "[EntityInfo][CompletionCoverage]")
{
    CHECK_FALSE(EntityInfo::ToFaceEntity(65535).has_value());
    for (const auto index : {u16{0}, u16{32767}})
    {
        const auto npc = EntityInfo::ToFaceEntity(index);
        REQUIRE(npc.has_value());
        CHECK(npc->type == EntityType_e::Npc);
        CHECK(npc->index == index);
    }
    const auto player = EntityInfo::ToFaceEntity(32768);
    REQUIRE(player.has_value());
    CHECK(player->type == EntityType_e::Player);
    CHECK(player->index == 0);
}

TEST_CASE("State lookup finds the local player only after placement and appearance", "[GameState][CompletionCoverage]")
{
    auto world = QueryWorld{};
    world.state.localPlayer.appearance = Appearance_s{.name37 = Base37::Encode("local bot"), .name = "Local Bot"};
    CHECK(world.state.FindPlayerByName("LOCAL BOT") == &world.state.localPlayer);
    world.state.placed = false;
    CHECK(world.state.FindPlayerByName("local bot") == nullptr);
    world.state.placed = true;
    world.state.localPlayer.appearance.reset();
    CHECK(world.state.FindPlayerByName("local bot") == nullptr);
}

TEST_CASE("Reach queries reject line of sight outside the loaded area or level", "[ReachQuery][CompletionCoverage]")
{
    const auto world = QueryWorld{};
    const auto query = ReachQuery{world.state, world.map};
    const auto here = QueryWorld::Offset(0, 0);
    auto above = here;
    above.level = 1;
    CHECK_FALSE(query.HasLineOfSight(here, above, 1));
    CHECK_FALSE(query.HasLineOfSight(Tile_s{.x = 0, .z = 0}, here, 1));
    CHECK_FALSE(query.HasLineOfSight(here, Tile_s{.x = 0, .z = 0}, 1));
    CHECK(query.HasLineOfSight(here, QueryWorld::Offset(0, 1), 1));
}

TEST_CASE("World walk maps reject negative coordinates and levels outside the cache", "[WalkMap][CompletionCoverage]")
{
    const auto cache = GameCache_s{};
    const auto map = WalkMap{cache};
    for (const auto point : {Tile_s{.x = -1, .z = 0}, Tile_s{.x = 0, .z = -1}, Tile_s{.x = 0, .z = 0, .level = -1}, Tile_s{.x = 0, .z = 0, .level = 4}})
    {
        CHECK_FALSE(map.IsWalkable(point.x, point.z, point.level));
        CHECK(map.GetExits(point.x, point.z, point.level) == 0);
    }
}
