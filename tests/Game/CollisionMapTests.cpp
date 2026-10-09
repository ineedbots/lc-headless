#include "pch.hpp"

#include "Game/Map/CollisionFlag.hpp"
#include "Game/Map/CollisionMap.hpp"
#include "Game/Map/LocShape.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto X = 50;
    constexpr auto Z = 50;
    constexpr auto WEST = u8{0};
    constexpr auto NORTH = u8{1};
    constexpr auto EAST = u8{2};
    constexpr auto SOUTH = u8{3};

    struct TileFlags_s
    {
        s32 dx = 0;
        s32 dz = 0;
        u32 flags = 0;
    };

    struct WallCase_s
    {
        u8 shape = 0;
        u8 angle = 0;
        std::vector<TileFlags_s> tiles;
    };

    // Whether a player standing at (X + dx, Z + dz) reaches the target at (X, Z).
    struct ReachCase_s
    {
        u8 shape = 0;
        u8 angle = 0;
        s32 dx = 0;
        s32 dz = 0;
        bool reaches = false;
    };

    // From CollisionMap.ts's addWall: each shape and angle puts a flag on the wall's tile and on the tiles
    // the wall faces.
    std::vector<WallCase_s> GetWallCases()
    {
        using F = CollisionFlag;
        auto cases = std::vector<WallCase_s>{
            {LocShape::WALL_STRAIGHT, WEST, {{0, 0, F::WALL_WEST}, {-1, 0, F::WALL_EAST}}},
            {LocShape::WALL_STRAIGHT, NORTH, {{0, 0, F::WALL_NORTH}, {0, 1, F::WALL_SOUTH}}},
            {LocShape::WALL_STRAIGHT, EAST, {{0, 0, F::WALL_EAST}, {1, 0, F::WALL_WEST}}},
            {LocShape::WALL_STRAIGHT, SOUTH, {{0, 0, F::WALL_SOUTH}, {0, -1, F::WALL_NORTH}}},
            {LocShape::WALL_L, WEST, {{0, 0, F::WALL_NORTH | F::WALL_WEST}, {-1, 0, F::WALL_EAST}, {0, 1, F::WALL_SOUTH}}},
            {LocShape::WALL_L, NORTH, {{0, 0, F::WALL_NORTH | F::WALL_EAST}, {0, 1, F::WALL_SOUTH}, {1, 0, F::WALL_WEST}}},
            {LocShape::WALL_L, EAST, {{0, 0, F::WALL_SOUTH | F::WALL_EAST}, {1, 0, F::WALL_WEST}, {0, -1, F::WALL_NORTH}}},
            {LocShape::WALL_L, SOUTH, {{0, 0, F::WALL_SOUTH | F::WALL_WEST}, {0, -1, F::WALL_NORTH}, {-1, 0, F::WALL_EAST}}},
        };

        for (const auto shape : {LocShape::WALL_DIAGONAL_CORNER, LocShape::WALL_SQUARE_CORNER})
        {
            cases.push_back({shape, WEST, {{0, 0, F::WALL_NORTH_WEST}, {-1, 1, F::WALL_SOUTH_EAST}}});
            cases.push_back({shape, NORTH, {{0, 0, F::WALL_NORTH_EAST}, {1, 1, F::WALL_SOUTH_WEST}}});
            cases.push_back({shape, EAST, {{0, 0, F::WALL_SOUTH_EAST}, {1, -1, F::WALL_NORTH_WEST}}});
            cases.push_back({shape, SOUTH, {{0, 0, F::WALL_SOUTH_WEST}, {-1, -1, F::WALL_NORTH_EAST}}});
        }

        return cases;
    }

    bool ReachesWall(const CollisionMap& map, const ReachCase_s& reach)
    {
        return map.CanReachWall(X + reach.dx, Z + reach.dz, X, Z, reach.shape, reach.angle);
    }

    bool ReachesWallDecor(const CollisionMap& map, const ReachCase_s& reach)
    {
        return map.CanReachWallDecor(X + reach.dx, Z + reach.dz, X, Z, reach.shape, reach.angle);
    }
}

TEST_CASE("CollisionMap starts open inside a ring of bounds", "[CollisionMap]")
{
    auto map = CollisionMap{};
    CHECK(map.GetFlags(0, 0) == CollisionFlag::BOUNDS);
    CHECK(map.GetFlags(CollisionMap::SIZE - 1, 40) == CollisionFlag::BOUNDS);
    CHECK(map.GetFlags(40, CollisionMap::SIZE - 1) == CollisionFlag::BOUNDS);
    CHECK(map.GetFlags(1, 1) == CollisionFlag::OPEN);
    CHECK(map.GetFlags(CollisionMap::SIZE - 2, CollisionMap::SIZE - 2) == CollisionFlag::OPEN);

    map.BlockGround(X, Z);
    CHECK(map.GetFlags(X, Z) == CollisionFlag::GROUND);
    map.Reset();
    CHECK(map.GetFlags(X, Z) == CollisionFlag::OPEN);
}

TEST_CASE("CollisionMap adds walls to both sides", "[CollisionMap]")
{
    for (const auto& wall : GetWallCases())
    {
        CAPTURE(wall.shape, wall.angle);
        auto map = CollisionMap{};
        map.AddWall(X, Z, wall.shape, wall.angle, false);
        for (const auto& tile : wall.tiles)
        {
            CAPTURE(tile.dx, tile.dz);
            CHECK(map.GetFlags(X + tile.dx, Z + tile.dz) == tile.flags);
        }

        auto ranged = CollisionMap{};
        ranged.AddWall(X, Z, wall.shape, wall.angle, true);
        for (const auto& tile : wall.tiles)
        {
            CAPTURE(tile.dx, tile.dz);
            CHECK(ranged.GetFlags(X + tile.dx, Z + tile.dz) == (tile.flags | (tile.flags << CollisionFlag::RANGE_SHIFT)));
        }
    }

    SECTION("a wall on the edge doesn't write outside the area")
    {
        auto map = CollisionMap{};
        map.AddWall(0, 5, LocShape::WALL_STRAIGHT, WEST, false);
        CHECK(map.GetFlags(0, 5) == CollisionFlag::BOUNDS);
        CHECK(map.GetFlags(CollisionMap::SIZE - 1, 4) == CollisionFlag::BOUNDS);
    }
}

TEST_CASE("CollisionMap adds locs by size, turned by their angle", "[CollisionMap]")
{
    auto map = CollisionMap{};
    map.AddLoc(X, Z, 3, 1, NORTH, false);
    CHECK(map.GetFlags(X, Z) == CollisionFlag::LOC);
    CHECK(map.GetFlags(X, Z + 2) == CollisionFlag::LOC);
    CHECK(map.GetFlags(X, Z + 3) == CollisionFlag::OPEN);
    CHECK(map.GetFlags(X + 1, Z) == CollisionFlag::OPEN);

    map.AddLoc(X + 5, Z, 2, 2, WEST, true);
    CHECK(map.GetFlags(X + 6, Z + 1) == (CollisionFlag::LOC | CollisionFlag::RANGE_LOC));

    SECTION("parts outside the area are cut off")
    {
        map.AddLoc(CollisionMap::SIZE - 2, 10, 4, 1, WEST, false);
        CHECK(map.GetFlags(CollisionMap::SIZE - 2, 10) == CollisionFlag::LOC);
        CHECK(map.GetFlags(CollisionMap::SIZE - 1, 10) == CollisionFlag::BOUNDS);
    }
}

TEST_CASE("CollisionMap reaches walls as the webclient's testWall does", "[CollisionMap]")
{
    const auto cases = std::to_array<ReachCase_s>({
        // A straight wall is reached from the side it faces, and from either end unless a wall closes it.
        {LocShape::WALL_STRAIGHT, WEST, -1, 0, true},
        {LocShape::WALL_STRAIGHT, WEST, 1, 0, false},
        {LocShape::WALL_STRAIGHT, WEST, 0, 1, true},
        {LocShape::WALL_STRAIGHT, WEST, 0, -1, true},
        {LocShape::WALL_STRAIGHT, WEST, -1, 1, false},
        {LocShape::WALL_STRAIGHT, NORTH, 0, 1, true},
        {LocShape::WALL_STRAIGHT, NORTH, 0, -1, false},
        {LocShape::WALL_STRAIGHT, NORTH, -1, 0, true},
        {LocShape::WALL_STRAIGHT, NORTH, 1, 0, true},
        {LocShape::WALL_STRAIGHT, EAST, 1, 0, true},
        {LocShape::WALL_STRAIGHT, EAST, -1, 0, false},
        {LocShape::WALL_STRAIGHT, EAST, 0, 1, true},
        {LocShape::WALL_STRAIGHT, EAST, 0, -1, true},
        {LocShape::WALL_STRAIGHT, SOUTH, 0, -1, true},
        {LocShape::WALL_STRAIGHT, SOUTH, 0, 1, false},
        {LocShape::WALL_STRAIGHT, SOUTH, -1, 0, true},
        {LocShape::WALL_STRAIGHT, SOUTH, 1, 0, true},
        // An L wall is reached from both sides it faces, and from the other two unless walled.
        {LocShape::WALL_L, WEST, -1, 0, true},
        {LocShape::WALL_L, WEST, 0, 1, true},
        {LocShape::WALL_L, WEST, 1, 0, true},
        {LocShape::WALL_L, WEST, 0, -1, true},
        {LocShape::WALL_L, NORTH, 0, 1, true},
        {LocShape::WALL_L, NORTH, 1, 0, true},
        {LocShape::WALL_L, EAST, 1, 0, true},
        {LocShape::WALL_L, EAST, 0, -1, true},
        {LocShape::WALL_L, SOUTH, -1, 0, true},
        {LocShape::WALL_L, SOUTH, 0, -1, true},
        {LocShape::WALL_L, SOUTH, 1, 1, false},
        // A diagonal wall is reached from any side.
        {LocShape::WALL_DIAGONAL, WEST, 0, 1, true},
        {LocShape::WALL_DIAGONAL, WEST, 0, -1, true},
        {LocShape::WALL_DIAGONAL, WEST, -1, 0, true},
        {LocShape::WALL_DIAGONAL, WEST, 1, 0, true},
        {LocShape::WALL_DIAGONAL, WEST, 1, 1, false},
        // Corners are only reached from their own tile.
        {LocShape::WALL_DIAGONAL_CORNER, WEST, -1, 0, false},
        {LocShape::WALL_DIAGONAL_CORNER, WEST, 0, 0, true},
    });

    const auto map = CollisionMap{};
    for (const auto& reach : cases)
    {
        CAPTURE(reach.shape, reach.angle, reach.dx, reach.dz);
        CHECK(ReachesWall(map, reach) == reach.reaches);
    }

    SECTION("a wall on the standing tile closes the way round the end")
    {
        auto walled = CollisionMap{};
        walled.AddWall(X, Z + 1, LocShape::WALL_STRAIGHT, SOUTH, false);
        CHECK_FALSE(ReachesWall(walled, {LocShape::WALL_STRAIGHT, WEST, 0, 1, false}));
        CHECK(ReachesWall(walled, {LocShape::WALL_STRAIGHT, WEST, 0, -1, true}));

        walled.AddWall(X + 1, Z, LocShape::WALL_STRAIGHT, WEST, false);
        CHECK_FALSE(ReachesWall(walled, {LocShape::WALL_L, WEST, 1, 0, false}));
        CHECK_FALSE(ReachesWall(walled, {LocShape::WALL_DIAGONAL, WEST, 1, 0, false}));
    }
}

TEST_CASE("CollisionMap reaches wall decor as the webclient's testWDecor does", "[CollisionMap]")
{
    const auto cases = std::to_array<ReachCase_s>({
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, WEST, 1, 0, true},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, WEST, 0, -1, true},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, WEST, -1, 0, false},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, NORTH, -1, 0, true},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, NORTH, 0, -1, true},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, EAST, -1, 0, true},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, EAST, 0, 1, true},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, SOUTH, 1, 0, true},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, SOUTH, 0, 1, true},
        {LocShape::WALLDECOR_DIAGONAL_OFFSET, SOUTH, 0, -1, false},
        // The no-offset kind faces the opposite way.
        {LocShape::WALLDECOR_DIAGONAL_NOOFFSET, WEST, -1, 0, true},
        {LocShape::WALLDECOR_DIAGONAL_NOOFFSET, WEST, 0, 1, true},
        {LocShape::WALLDECOR_DIAGONAL_NOOFFSET, WEST, 1, 0, false},
        {LocShape::WALLDECOR_DIAGONAL_BOTH, WEST, 0, 1, true},
        {LocShape::WALLDECOR_DIAGONAL_BOTH, WEST, 0, -1, true},
        {LocShape::WALLDECOR_DIAGONAL_BOTH, WEST, -1, 0, true},
        {LocShape::WALLDECOR_DIAGONAL_BOTH, WEST, 1, 0, true},
        {LocShape::WALLDECOR_STRAIGHT_NOOFFSET, WEST, -1, 0, false},
        {LocShape::WALLDECOR_STRAIGHT_NOOFFSET, WEST, 0, 0, true},
    });

    const auto map = CollisionMap{};
    for (const auto& reach : cases)
    {
        CAPTURE(reach.shape, reach.angle, reach.dx, reach.dz);
        CHECK(ReachesWallDecor(map, reach) == reach.reaches);
    }
}

TEST_CASE("CollisionMap reaches areas as the webclient's testLoc does", "[CollisionMap]")
{
    auto map = CollisionMap{};
    const auto reaches = [&map](s32 dx, s32 dz, u8 forceApproach = 0)
    {
        return map.CanReachArea(X + dx, Z + dz, X, Z, 2, 3, forceApproach);
    };

    CHECK(reaches(0, 0));
    CHECK(reaches(1, 2));
    CHECK(reaches(-1, 0));
    CHECK(reaches(-1, 2));
    CHECK(reaches(2, 1));
    CHECK(reaches(0, -1));
    CHECK(reaches(1, 3));
    CHECK_FALSE(reaches(-1, -1));
    CHECK_FALSE(reaches(2, 3));
    CHECK_FALSE(reaches(-2, 0));

    SECTION("forceApproach forbids sides: 1 north, 2 east, 4 south, 8 west")
    {
        CHECK_FALSE(reaches(-1, 0, 0x8));
        CHECK_FALSE(reaches(2, 0, 0x2));
        CHECK_FALSE(reaches(0, -1, 0x4));
        CHECK_FALSE(reaches(0, 3, 0x1));
        CHECK(reaches(0, 3, 0x8));
    }

    SECTION("a wall on the standing tile's side facing the area closes it")
    {
        map.AddWall(X - 1, Z, LocShape::WALL_STRAIGHT, EAST, false);
        CHECK_FALSE(reaches(-1, 0));
        CHECK(reaches(-1, 1));
    }
}
