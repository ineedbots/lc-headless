#include "pch.hpp"

#include "Game/Map/CollisionMap.hpp"
#include "Game/Map/LineOfSight.hpp"
#include "Game/Map/LocShape.hpp"

#include <catch2/catch_test_macros.hpp>

// rs2b0t's test/event/webwalk/geometry/lineOfSight.test.ts, on a 16x16 collision map.
namespace
{
    constexpr auto SIZE = 16;
    constexpr auto WEST = u8{0};
    constexpr auto NORTH = u8{1};
    constexpr auto SOUTH = u8{3};

    Footprint_s One(s32 x, s32 z)
    {
        return {.x = x, .z = z};
    }

    bool Sees(const CollisionMap& map, const Footprint_s& source, const Footprint_s& target)
    {
        return LineOfSight::Has(map, source, target);
    }

    CollisionMap WithWall(s32 x, s32 z, u8 angle, bool blockRange)
    {
        auto map = CollisionMap{SIZE};
        map.AddWall(x, z, LocShape::WALL_STRAIGHT, angle, blockRange);
        return map;
    }

    CollisionMap WithLoc(s32 x, s32 z, bool blockRange)
    {
        auto map = CollisionMap{SIZE};
        map.AddLoc(x, z, 1, 1, 0, blockRange);
        return map;
    }
}

TEST_CASE("A shallow sight ray checks the tile entered when it crosses a row boundary", "[LineOfSight][CompletionCoverage]")
{
    CHECK(Sees(CollisionMap{SIZE}, One(1, 1), One(8, 4)));
    CHECK_FALSE(Sees(WithLoc(3, 2, true), One(1, 1), One(8, 4)));
    CHECK(Sees(WithLoc(3, 2, false), One(1, 1), One(8, 4)));
}

TEST_CASE("Open ground is seen along a row, a column and a diagonal", "[LineOfSight]")
{
    const auto open = CollisionMap{SIZE};
    CHECK(Sees(open, One(1, 1), One(8, 1)));
    CHECK(Sees(open, One(1, 1), One(1, 8)));
    CHECK(Sees(open, One(1, 1), One(6, 6)));
    CHECK(Sees(open, One(8, 8), One(2, 3)));
    CHECK(Sees(open, One(3, 3), One(3, 3)));
}

TEST_CASE("A wall that blocks range stops the ray, and one that only blocks walking doesn't", "[LineOfSight]")
{
    CHECK_FALSE(Sees(WithWall(5, 1, WEST, true), One(1, 1), One(8, 1)));
    CHECK(Sees(WithWall(5, 1, WEST, false), One(1, 1), One(8, 1)));
    CHECK_FALSE(Sees(WithWall(1, 5, SOUTH, true), One(1, 1), One(1, 8)));
    CHECK_FALSE(Sees(WithWall(1, 5, NORTH, true), One(1, 8), One(1, 1)));
}

TEST_CASE("Scenery that blocks range stops the ray, but not what stands on it", "[LineOfSight]")
{
    CHECK_FALSE(Sees(WithLoc(5, 1, true), One(1, 1), One(8, 1)));
    CHECK(Sees(WithLoc(5, 1, false), One(1, 1), One(8, 1)));
    CHECK_FALSE(Sees(WithLoc(4, 4, true), One(1, 1), One(6, 6)));
    CHECK(Sees(WithLoc(8, 1, true), One(1, 1), One(8, 1)));

    // Standing on scenery sees nothing.
    CHECK_FALSE(Sees(WithLoc(1, 1, false), One(1, 1), One(8, 1)));
}

TEST_CASE("The edge of the map is opaque", "[LineOfSight]")
{
    CHECK_FALSE(Sees(CollisionMap{SIZE}, One(14, 1), One(20, 1)));
}

// The ray aims at the corner of a large footprint nearest the viewer, so scenery behind that corner is inside the
// body and never blocks.
TEST_CASE("A large body is seen at its nearest corner", "[LineOfSight]")
{
    const auto three = Footprint_s{.x = 3, .z = 3, .size = 3};
    CHECK(Sees(WithLoc(4, 4, true), One(8, 8), three));
    CHECK_FALSE(Sees(WithLoc(6, 6, true), One(8, 8), three));
    CHECK_FALSE(Sees(WithLoc(7, 4, true), One(9, 4), three));
    CHECK(Sees(WithLoc(2, 4, true), One(9, 4), three));

    const auto four = Footprint_s{.x = 5, .z = 5, .size = 4};
    CHECK_FALSE(Sees(WithLoc(3, 3, true), One(1, 1), four));
    CHECK(Sees(WithLoc(7, 7, true), One(1, 1), four));
}
