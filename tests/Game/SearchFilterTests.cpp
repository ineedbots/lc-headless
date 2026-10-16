#include "pch.hpp"

#include "Game/Query/SearchFilter_s.hpp"
#include "Game/Tile_s.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("SearchFilter_s matches by id and name", "[SearchFilter]")
{
    CHECK(SearchFilter_s{}.MatchesType(41, "Chicken"));
    CHECK(SearchFilter_s{}.MatchesType(41, ""));
    CHECK(SearchFilter_s{.ids = {41, 81}}.MatchesType(81, "Cow"));
    CHECK_FALSE(SearchFilter_s{.ids = {41}}.MatchesType(81, "Cow"));
    CHECK(SearchFilter_s{.names = {"cow", "chicken"}}.MatchesType(41, "CHICKEN"));
    CHECK_FALSE(SearchFilter_s{.names = {"Cow"}}.MatchesType(41, "Chicken"));
    CHECK_FALSE(SearchFilter_s{.names = {""}}.MatchesType(41, ""));
    CHECK_FALSE(SearchFilter_s{.ids = {41}, .names = {"Cow"}}.MatchesType(41, "Chicken"));
}

TEST_CASE("SearchFilter_s counts its radius on the centre's level", "[SearchFilter]")
{
    const auto centre = Tile_s{.x = 3200, .z = 3200};

    CHECK(SearchFilter_s{}.MatchesTile(centre, {.x = 9000, .z = 9000, .level = 3}));
    CHECK(SearchFilter_s{.radius = 2}.MatchesTile(centre, {.x = 3202, .z = 3198}));
    CHECK_FALSE(SearchFilter_s{.radius = 2}.MatchesTile(centre, {.x = 3203, .z = 3200}));
    CHECK_FALSE(SearchFilter_s{.radius = 2}.MatchesTile(centre, {.x = 3200, .z = 3200, .level = 1}));
    CHECK_FALSE(SearchFilter_s{.ids = {1}, .radius = 2}.Matches(centre, centre, 2, "Rock"));
    CHECK(SearchFilter_s{.ids = {1}, .radius = 2}.Matches(centre, centre, 1, "Rock"));
}
