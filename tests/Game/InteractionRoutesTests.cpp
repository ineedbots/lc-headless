#include "pch.hpp"
#include "../Support/Game/QueryWorld.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/Fixtures.hpp"

#include "Game/Map/InteractionRoutes.hpp"
#include "Game/Map/LocShape.hpp"
#include "Game/Tile_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

namespace
{
    using W = QueryWorld;
}

TEST_CASE("InteractionRoutes walks to a tile, or as near to it as can be reached", "[InteractionRoutes]")
{
    const auto world = QueryWorld{};
    const auto here = W::Offset(0, 0);

    CHECK(InteractionRoutes::FindWalkRoute(world.map, here, W::Offset(0, 5)) == std::vector<Tile_s>{W::Offset(0, 5)});
    CHECK_FALSE(InteractionRoutes::FindWalkRoute(world.map, here, W::Offset(3, 0)).has_value());
}

TEST_CASE("InteractionRoutes reaches each kind of target by its own rule", "[InteractionRoutes]")
{
    const auto world = QueryWorld{};
    const auto here = W::Offset(0, 0);

    CHECK_FALSE(InteractionRoutes::FindEntityRoute(world.map, here, W::Offset(3, 0)).has_value());
    CHECK(InteractionRoutes::FindEntityRoute(world.map, here, W::Offset(-3, 2)).has_value());
    CHECK(InteractionRoutes::FindGroundItemRoute(world.map, here, W::Offset(2, 2)).has_value());
    CHECK(InteractionRoutes::FindLocRoute(world.map, here, W::Offset(1, -2), W::DOOR).has_value());
}

TEST_CASE("InteractionRoutes needs the loc on its tile", "[InteractionRoutes]")
{
    const auto world = QueryWorld{};
    const auto here = W::Offset(0, 0);

    CHECK(InteractionRoutes::FindLocTarget(world.map, W::Offset(1, -2), W::DOOR).has_value());
    CHECK_FALSE(InteractionRoutes::FindLocTarget(world.map, W::Offset(1, -2), W::TREE).has_value());
    CHECK_FALSE(InteractionRoutes::FindLocRoute(world.map, here, W::Offset(0, 3), W::DOOR).has_value());
}

TEST_CASE("InteractionRoutes turns scenery dimensions and forbidden approach sides", "[InteractionRoutes]")
{
    const auto shape = GENERATE(LocShape::CENTREPIECE_STRAIGHT, LocShape::CENTREPIECE_DIAGONAL, LocShape::GROUND_DECOR);
    const auto angle = GENERATE(u8{0}, u8{1}, u8{2}, u8{3});
    auto cache = std::make_shared<GameCache_s>();
    auto& type = TestCache::AddLoc(*cache, 1, "Counter", {"Use"});
    type.width = 2;
    type.length = 3;
    type.forceApproach = 9; // North and west, before rotation.
    const auto tile = W::Offset(2, 2);
    const auto locs = std::to_array<TestLoc_s>({{.id = 1, .tile = tile, .shape = shape, .angle = angle}});
    TestCache::SetMap(*cache, locs);
    auto map = WorldMap{cache};
    map.Update(Fixtures::PlacedState());

    const auto target = InteractionRoutes::FindLocTarget(map, tile, 1);
    REQUIRE(target.has_value());
    CHECK(target->kind == RouteKind_e::Area);
    CHECK(target->tile == tile);
    const auto widths = std::array<u8, 4>{2, 3, 2, 3};
    const auto lengths = std::array<u8, 4>{3, 2, 3, 2};
    const auto forbiddenSides = std::array<u8, 4>{9, 3, 6, 12};
    CHECK(target->width == widths[angle]);
    CHECK(target->length == lengths[angle]);
    CHECK(target->forceApproach == forbiddenSides[angle]);
    CHECK(InteractionRoutes::FindLocRoute(map, W::Offset(0, 0), tile, 1).has_value());
}

TEST_CASE("InteractionRoutes preserves wall shape and angle instead of using type dimensions", "[InteractionRoutes]")
{
    const auto shape = GENERATE(LocShape::WALL_STRAIGHT, LocShape::WALL_L, LocShape::WALLDECOR_DIAGONAL_BOTH);
    const auto angle = GENERATE(u8{0}, u8{1}, u8{2}, u8{3});
    auto world = QueryWorld{};
    const auto tile = W::Offset(0, 2);
    world.state.locChanges.push_back({.tile = tile, .layer = LocShape::GetLayer(shape), .id = W::DOOR, .shape = shape, .angle = angle});
    ++world.state.sceneChangeCount;
    world.map.Update(world.state);
    const auto target = InteractionRoutes::FindLocTarget(world.map, tile, W::DOOR);
    REQUIRE(target.has_value());
    CHECK(target->kind == RouteKind_e::Wall);
    CHECK(target->tile == tile);
    CHECK(target->shape == shape);
    CHECK(target->angle == angle);
}

TEST_CASE("InteractionRoutes falls back to an adjacent tile for blocked ground items", "[InteractionRoutes]")
{
    auto cache = std::make_shared<GameCache_s>();
    const auto tile = W::Offset(0, 3);
    const auto blocked = std::to_array<Tile_s>({tile});
    TestCache::SetMap(*cache, {}, blocked);
    auto map = WorldMap{cache};
    map.Update(Fixtures::PlacedState());
    const auto start = W::Offset(0, 0);
    CHECK_FALSE(PathFinder::FindPath(map, start, {.tile = tile}).has_value());
    const auto route = InteractionRoutes::FindGroundItemRoute(map, start, tile);
    REQUIRE(route.has_value());
    REQUIRE_FALSE(route->empty());
    CHECK(route->back() == W::Offset(0, 2));
}

TEST_CASE("InteractionRoutes uses the first reachable target and rejects an empty target list", "[InteractionRoutes]")
{
    const auto world = QueryWorld{};
    const auto start = W::Offset(0, 0);
    const auto first = W::Offset(0, 3);
    const auto second = W::Offset(-2, 0);
    const auto unreachable = W::Offset(3, 0);
    CHECK(InteractionRoutes::FindRoute(world.map, start, {{.tile = unreachable}, {.tile = first}, {.tile = second}})
          == std::vector<Tile_s>{first});
    CHECK_FALSE(InteractionRoutes::FindRoute(world.map, start, {}).has_value());
    CHECK_FALSE(InteractionRoutes::FindRoute(world.map, start, {{.tile = unreachable}}).has_value());
}
