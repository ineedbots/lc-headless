#include "pch.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/Game/QueryWorld.hpp"

#include "Game/Query/EntityQuery.hpp"
#include "Game/State/EntityStatus.hpp"
#include "Game/State/Zone_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using W = QueryWorld;
}

TEST_CASE("EntityQuery compares multiple scenery candidates when selecting the nearest", "[EntityQuery][CompletionCoverage]")
{
    auto world = QueryWorld{};
    world.state.locChanges.push_back({.tile = W::Offset(0, 8), .layer = LocLayer_e::Ground, .id = W::TREE, .shape = 10});
    ++world.state.sceneChangeCount;
    world.map.Update(world.state);
    const auto query = EntityQuery{world.state, world.map};
    const auto candidates = query.GetLocs({}, std::nullopt);
    REQUIRE(candidates.size() > 1);
    const auto nearest = query.GetNearestLoc({}, std::nullopt, false);
    REQUIRE(nearest.has_value());
    CHECK(nearest->tile != W::Offset(0, 8));
}

TEST_CASE("EntityQuery finds NPCs by id and radius", "[EntityQuery]")
{
    auto world = QueryWorld{};
    const auto query = EntityQuery{world.state, world.map};

    CHECK(W::GetIndices(query.GetNpcs({})) == std::vector<u16>{10, 11, 12, 13});
    CHECK(W::GetIndices(query.GetNpcs({.ids = {W::CHICKEN}})) == std::vector<u16>{10, 12, 13});
    CHECK(W::GetIndices(query.GetNpcs({.ids = {W::CHICKEN}, .radius = 3})) == std::vector<u16>{10, 12});
    CHECK(W::GetIndices(query.GetNpcs({.ids = {W::CHICKEN, W::COW}, .radius = 1})) == std::vector<u16>{11});
    CHECK(query.GetNpcs({.ids = {9999}}).empty());
    CHECK(query.GetNpc(11)->type == W::COW);
    CHECK_FALSE(query.GetNpc(99).has_value());

    SECTION("the nearest is by tiles in either direction, and ties go to the first in server order")
    {
        REQUIRE(query.GetNearestNpc({.ids = {W::CHICKEN}}, std::nullopt).has_value());
        CHECK(query.GetNearestNpc({.ids = {W::CHICKEN}}, std::nullopt)->index == 10);
        CHECK(query.GetNearestNpc({}, std::nullopt)->index == 11);
        CHECK_FALSE(query.GetNearestNpc({.ids = {W::CHICKEN}, .radius = 2}, std::nullopt).has_value());
    }

    SECTION("a radius only counts NPCs on the local player's level")
    {
        world.state.npcs.push_back(W::MakeNpc(14, W::CHICKEN, W::Offset(0, 0, 1)));
        CHECK(W::GetIndices(query.GetNpcs({.ids = {W::CHICKEN}, .radius = 0})).empty());
        CHECK(W::GetIndices(query.GetNpcs({.ids = {W::CHICKEN}})).back() == 14);
    }

    SECTION("in combat means hit within the last few ticks")
    {
        world.state.npcs[0].hits.push_back({.damage = 1, .health = 2, .maxHealth = 3, .tick = 100 - EntityStatus::COMBAT_TICKS});
        world.state.npcs[2].hits.push_back({.damage = 1, .tick = 100 - EntityStatus::COMBAT_TICKS - 1});
        CHECK(query.GetNearestNpc({.ids = {W::CHICKEN}}, false)->index == 12);
        CHECK(query.GetNearestNpc({.ids = {W::CHICKEN}}, true)->index == 10);
    }
}

TEST_CASE("EntityQuery finds NPCs and ground items by name", "[EntityQuery]")
{
    auto world = QueryWorld{};
    const auto query = EntityQuery{world.state, world.map};
    world.state.npcs.push_back(W::MakeNpc(14, W::UNKNOWN_NPC, W::Offset(1, 0)));

    CHECK(W::GetIndices(query.GetNpcs({.names = {"chicken"}})) == std::vector<u16>{10, 12, 13});
    CHECK(W::GetIndices(query.GetNpcs({.names = {"Cow", "CHICKEN"}, .radius = 3})) == std::vector<u16>{10, 11, 12});
    CHECK(query.GetNpcs({.names = {""}}).empty());
    CHECK(query.GetNearestNpc({.names = {"Cow"}}, std::nullopt)->index == 11);
    CHECK(query.GetNearestGroundItem({.names = {"bones"}})->id == W::BONES);
    CHECK_FALSE(query.GetNearestGroundItem({.names = {"Logs"}}).has_value());
}

TEST_CASE("EntityQuery reads ground items", "[EntityQuery]")
{
    const auto world = QueryWorld{};
    const auto query = EntityQuery{world.state, world.map};

    CHECK(query.GetNearestGroundItem({})->id == W::COINS);
    CHECK(query.GetNearestGroundItem({.ids = {W::BONES}})->tile == W::Offset(2, 2));
    CHECK_FALSE(query.GetNearestGroundItem({.ids = {W::BONES}, .radius = 1}).has_value());
    CHECK(query.HasGroundItem(W::BONES, W::Offset(2, 2)));
    CHECK_FALSE(query.HasGroundItem(W::BONES, W::Offset(0, 1)));
}

TEST_CASE("EntityQuery sees the cache's scenery and the server's changes", "[EntityQuery]")
{
    const auto world = QueryWorld{};
    const auto query = EntityQuery{world.state, world.map};

    const auto door = query.GetLocAt(W::Offset(1, -2), std::nullopt);
    REQUIRE(door.has_value());
    CHECK(door->id == W::DOOR);
    CHECK(door->layer == LocLayer_e::Wall);
    CHECK_FALSE(door->changed);
    CHECK_FALSE(query.GetLocAt(W::Offset(1, -2), LocLayer_e::Ground).has_value());

    const auto removed = query.GetLocAt(W::Offset(8, 8), std::nullopt);
    REQUIRE(removed.has_value());
    CHECK(removed->id == -1);
    CHECK(removed->changed);

    const auto locs = query.GetLocs({}, std::nullopt);
    REQUIRE(locs.size() == 2);
    CHECK(locs[0].id == W::DOOR);
    CHECK(locs[1].id == W::TREE);
    CHECK(query.GetLocs({.ids = {W::TREE}, .radius = 2}, std::nullopt).empty());
    CHECK(query.GetLocs({}, LocLayer_e::Ground).size() == 1);
    CHECK(query.GetNearestLoc({.names = {"tree"}}, std::nullopt)->tile == W::Offset(-3, -3));
    CHECK_FALSE(query.GetNearestLoc({.names = {"Bank booth"}}, std::nullopt).has_value());
}

TEST_CASE("EntityQuery skips what can't be reached when asked to", "[EntityQuery]")
{
    const auto world = QueryWorld{};
    const auto query = EntityQuery{world.state, world.map};

    CHECK(query.GetNearestNpc({.ids = {W::CHICKEN}}, std::nullopt)->index == 10);
    CHECK(query.GetNearestNpc({.ids = {W::CHICKEN}}, std::nullopt, true)->index == 12);
    CHECK(query.GetNearestLoc({.ids = {W::DOOR}}, std::nullopt, true)->id == W::DOOR);
    CHECK(query.GetNearestGroundItem({.ids = {W::BONES}}, true)->id == W::BONES);
}
