#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/QueryWorld.hpp"

#include "Game/Query/InventoryItem_s.hpp"
#include "Game/Query/InventoryQuery.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using W = QueryWorld;
}

TEST_CASE("InventoryQuery reads inventories", "[InventoryQuery]")
{
    const auto world = QueryWorld{};
    const auto query = InventoryQuery{world.state, *world.cache};

    const auto items = query.GetInventory(TestCache::INVENTORY);
    REQUIRE(items.size() == 3);
    CHECK(items[1].slot == 2);
    CHECK(query.CountItems({.ids = {W::BONES}}, TestCache::INVENTORY) == 2);
    CHECK(query.CountItems({.ids = {W::BONES, W::COINS}}, TestCache::INVENTORY) == 102);
    CHECK(query.CountItems({}, TestCache::INVENTORY) == 102);
    CHECK(query.FindItem({.ids = {W::BONES}}, TestCache::INVENTORY)->slot == 2);
    CHECK_FALSE(query.FindItem({.ids = {1}}, TestCache::INVENTORY).has_value());
    CHECK(query.GetEmptySlots() == TestCache::INVENTORY_SIZE - 3);
    CHECK(query.GetInventory(TestCache::EQUIPMENT).empty());
}

TEST_CASE("InventoryQuery finds items by name", "[InventoryQuery]")
{
    const auto world = QueryWorld{};
    const auto query = InventoryQuery{world.state, *world.cache};

    CHECK(query.CountItems({.names = {"Bones"}}, TestCache::INVENTORY) == 2);
    CHECK(query.FindItem({.names = {"coins"}}, TestCache::INVENTORY)->slot == 0);
    CHECK_FALSE(query.FindItem({.names = {"Logs"}}, TestCache::INVENTORY).has_value());
}

TEST_CASE("InventoryQuery knows whether an item is still in its slot", "[InventoryQuery]")
{
    const auto world = QueryWorld{};
    const auto query = InventoryQuery{world.state, *world.cache};

    CHECK(query.HasItem({.com = TestCache::INVENTORY, .slot = 2, .id = W::BONES}));
    CHECK_FALSE(query.HasItem({.com = TestCache::INVENTORY, .slot = 1, .id = W::BONES}));
    CHECK_FALSE(query.HasItem({.com = TestCache::INVENTORY, .slot = 40, .id = W::BONES}));
    CHECK_FALSE(query.HasItem({.com = TestCache::EQUIPMENT, .slot = 0, .id = W::BONES}));
}
