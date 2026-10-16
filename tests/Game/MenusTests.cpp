#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/QueryWorld.hpp"

#include "Game/Menu/MenuOp.hpp"
#include "Game/Menu/Menus.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    using W = QueryWorld;
}

TEST_CASE("Menus chooses options by their text", "[Menus]")
{
    auto world = QueryWorld{};
    const auto& state = world.state;
    const auto& cache = *world.cache;
    world.state.npcs.push_back(W::MakeNpc(14, W::UNKNOWN_NPC, W::Offset(1, 0)));

    CHECK(Menus::FindNpcOp(state, cache, 10, "attack") == std::optional<u8>{2});
    CHECK_FALSE(Menus::FindNpcOp(state, cache, 99, "Attack").has_value());
    CHECK_THROWS_WITH(Menus::FindNpcOp(state, cache, 10, "Pickpocket"), "Chicken (NPC 41) has no option 'Pickpocket'; its options are Attack (2)");
    CHECK_THROWS_WITH(Menus::FindNpcOp(state, cache, 14, "Attack"), ContainsSubstring("NPC 900 isn't in the cache"));
    CHECK(Menus::FindLocOp(cache, W::DOOR, "OPEN") == 1);
    CHECK_THROWS_AS(Menus::FindLocOp(cache, W::DOOR, "Close"), std::invalid_argument);
    CHECK(Menus::FindPlayerOp(state, "follow") == 2);
    CHECK_THROWS_WITH(Menus::FindPlayerOp(state, "Trade"), "a player has no option 'Trade'; its options are Follow (2)");

    SECTION("ground items offer Take, and inventory items Drop, where their type has no option")
    {
        CHECK(Menus::FindGroundItemOp(cache, W::BONES, "take") == MenuOp::TAKE);
        CHECK(Menus::FindItemOp(cache, W::BONES, "Bury") == 1);
        CHECK(Menus::FindItemOp(cache, W::BONES, "drop") == MenuOp::DROP);
        CHECK_THROWS_WITH(Menus::FindItemOp(cache, W::COINS, "Bury"), "Coins (item 995) has no option 'Bury'; its options are Drop (5)");
    }
}

TEST_CASE("Menus lists each kind of target's menu by slot", "[Menus]")
{
    const auto world = QueryWorld{};
    const auto& cache = *world.cache;

    CHECK(Menus::GetNpcMenu(cache, W::CHICKEN) == Menus::Menu{"", "Attack", "", "", ""});
    CHECK(Menus::GetLocMenu(cache, W::DOOR) == Menus::Menu{"Open", "", "", "", ""});
    CHECK(Menus::GetGroundItemMenu(cache, W::BONES) == Menus::Menu{"", "", "Take", "", ""});
    CHECK(Menus::GetItemMenu(cache, W::BONES) == Menus::Menu{"Bury", "", "", "", "Drop"});
    CHECK(Menus::GetPlayerMenu(world.state) == Menus::Menu{"", "Follow", "", "", ""});

    SECTION("a type the cache doesn't have has only the options the menu adds")
    {
        CHECK(Menus::GetNpcMenu(cache, W::UNKNOWN_NPC) == Menus::Menu{});
        CHECK(Menus::GetGroundItemMenu(cache, 1) == Menus::Menu{"", "", "Take", "", ""});
        CHECK(Menus::GetItemMenu(cache, 1) == Menus::Menu{"", "", "", "", "Drop"});
    }

    SECTION("a component the cache doesn't have has no inventory menu")
    {
        CHECK_FALSE(Menus::GetInventoryMenu(cache, TestCache::INVENTORY).has_value());
        CHECK_THROWS_WITH(Menus::FindInventoryOption(cache, TestCache::INVENTORY, "Withdraw 1"), std::format("component {} isn't an inventory", TestCache::INVENTORY));
    }
}
