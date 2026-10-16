#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"

#include "Cache/GameCache_s.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("GameCache_s finds names by id", "[GameCache]")
{
    auto cache = GameCache_s{};
    TestCache::AddNpc(cache, 41, "Chicken");
    TestCache::AddObj(cache, 526, "Bones");
    TestCache::AddLoc(cache, 1276, "Tree");

    CHECK(cache.FindNpcName(41) == "Chicken");
    CHECK(cache.FindObjName(526) == "Bones");
    CHECK(cache.FindLocName(1276) == "Tree");
    CHECK(cache.FindNpcName(-1).empty());
    CHECK(cache.FindObjName(99999).empty());
}

TEST_CASE("GameCache_s finds ids by name, in any case", "[GameCache]")
{
    auto cache = GameCache_s{};
    TestCache::AddNpc(cache, 41, "Chicken");
    TestCache::AddNpc(cache, 1017, "chicken");
    TestCache::AddNpc(cache, 81, "Cow");
    TestCache::AddLoc(cache, 1276, "Tree");
    TestCache::AddObj(cache, 526, "Bones");

    CHECK(cache.FindNpcIds("CHICKEN") == std::vector<s32>{41, 1017});
    CHECK(cache.FindLocIds("tree") == std::vector<s32>{1276});
    CHECK(cache.FindObjIds("Bones") == std::vector<s32>{526});
    CHECK(cache.FindNpcIds("Goblin").empty());
    CHECK(cache.FindNpcIds("").empty());
}
