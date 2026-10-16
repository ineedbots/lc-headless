#include "pch.hpp"
#include "../Support/Game/QueryWorld.hpp"

#include "Game/Map/InteractionRoutes.hpp"
#include "Game/Tile_s.hpp"

#include <catch2/catch_test_macros.hpp>

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
