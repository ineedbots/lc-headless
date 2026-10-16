#include "pch.hpp"
#include "../Support/Game/QueryWorld.hpp"

#include "Game/Query/ReachQuery.hpp"
#include "Game/Tile_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using W = QueryWorld;
}

TEST_CASE("ReachQuery finds routes from the local player", "[ReachQuery]")
{
    const auto world = QueryWorld{};
    const auto query = ReachQuery{world.state, world.map};

    CHECK(query.IsReachable(W::Offset(0, 5)));
    CHECK_FALSE(query.IsReachable(W::Offset(3, 0)));
    CHECK(query.FindPath(W::Offset(0, 5)) == std::vector<Tile_s>{W::Offset(0, 5)});
    CHECK_FALSE(query.FindPath(W::Offset(3, 0)).has_value());
    CHECK(query.CanStep(W::Offset(0, 0), W::Offset(0, 1)));
    CHECK_FALSE(query.CanStep(W::Offset(1, 0), W::Offset(2, 0)));
}

TEST_CASE("ReachQuery reaches each kind of target by its own rule", "[ReachQuery]")
{
    const auto world = QueryWorld{};
    const auto query = ReachQuery{world.state, world.map};

    CHECK_FALSE(query.CanReachEntity(W::Offset(3, 0)));
    CHECK(query.CanReachEntity(W::Offset(-3, 2)));
    CHECK(query.CanReachGroundItem(W::Offset(2, 2)));
    CHECK(query.CanReachLoc(W::Offset(1, -2), W::DOOR));
    CHECK_FALSE(query.CanReachLoc(W::Offset(1, -2), W::TREE));
}
