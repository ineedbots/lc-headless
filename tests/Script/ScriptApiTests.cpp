#include "pch.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../LogCapture.hpp"

#include "Core/ConfigFile.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/State/Entity_s.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/State/Zone_s.hpp"
#include "Game/Tile_s.hpp"
#include "Script/ScriptApi.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto CHICKEN = u16{41};
    constexpr auto COW = u16{81};
    constexpr auto BONES = 526;
    constexpr auto COINS = 995;

    Tile_s Offset(s32 dx, s32 dz, s32 level = 0)
    {
        return {.x = Fixtures::HOME + dx, .z = Fixtures::HOME + dz, .level = level};
    }

    Npc_s MakeNpc(u16 index, u16 type, const Tile_s& tile)
    {
        auto npc = Npc_s{};
        npc.index = index;
        npc.type = type;
        npc.tile = tile;
        return npc;
    }

    std::vector<u16> GetIndices(const std::vector<Npc_s>& npcs)
    {
        auto indices = std::vector<u16>{};
        for (const auto& npc : npcs)
        {
            indices.push_back(npc.index);
        }

        return indices;
    }

    // A client that never logs in: queries read the fixture state, and actions only get as far as
    // checking their targets, since sending throws without a session.
    class ApiFixture
    {
    public:
        ApiFixture()
            : client{std::make_shared<const Config_s>(), FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{state, actions}
        {
            state.tick = 100;
            state.npcs = {
                MakeNpc(10, CHICKEN, Offset(3, 0)),
                MakeNpc(11, COW, Offset(1, 1)),
                MakeNpc(12, CHICKEN, Offset(-3, 2)),
                MakeNpc(13, CHICKEN, Offset(6, 0)),
            };

            state.groundItems = {
                {.tile = Offset(2, 2), .id = BONES, .count = 1},
                {.tile = Offset(0, 1), .id = COINS, .count = 25},
            };

            state.inventories[ScriptApi::INVENTORY] = Inventory_s{
                .com = ScriptApi::INVENTORY,
                .slots = {{.id = COINS, .count = 100}, {}, {.id = BONES, .count = 1}, {.id = BONES, .count = 1}},
            };
        }

        LogCapture capture;
        GameState_s state = Fixtures::PlacedState();
        GameClient client;
        GameActions actions;
        ScriptApi api;
    };
}

TEST_CASE("ScriptApi finds NPCs by id and radius", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    const auto& api = fixture.api;

    CHECK(GetIndices(api.GetNpcs({})) == std::vector<u16>{10, 11, 12, 13});
    CHECK(GetIndices(api.GetNpcs({.ids = {CHICKEN}})) == std::vector<u16>{10, 12, 13});
    CHECK(GetIndices(api.GetNpcs({.ids = {CHICKEN}, .radius = 3})) == std::vector<u16>{10, 12});
    CHECK(GetIndices(api.GetNpcs({.ids = {CHICKEN, COW}, .radius = 1})) == std::vector<u16>{11});
    CHECK(api.GetNpcs({.ids = {9999}}).empty());

    SECTION("the nearest is by tiles in either direction, and ties go to the first in server order")
    {
        REQUIRE(api.GetNearestNpc({.ids = {CHICKEN}}, std::nullopt).has_value());
        CHECK(api.GetNearestNpc({.ids = {CHICKEN}}, std::nullopt)->index == 10);
        CHECK(api.GetNearestNpc({}, std::nullopt)->index == 11);
        CHECK_FALSE(api.GetNearestNpc({.ids = {CHICKEN}, .radius = 2}, std::nullopt).has_value());
    }

    SECTION("a radius only counts NPCs on the local player's level")
    {
        fixture.state.npcs.push_back(MakeNpc(14, CHICKEN, Offset(0, 0, 1)));
        CHECK(GetIndices(api.GetNpcs({.ids = {CHICKEN}, .radius = 0})).empty());
        CHECK(GetIndices(api.GetNpcs({.ids = {CHICKEN}})).back() == 14);
    }

    SECTION("in combat means hit within the last few ticks")
    {
        fixture.state.npcs[0].hits.push_back({.damage = 1, .health = 2, .maxHealth = 3, .tick = 100 - ScriptApi::COMBAT_TICKS});
        fixture.state.npcs[2].hits.push_back({.damage = 1, .tick = 100 - ScriptApi::COMBAT_TICKS - 1});
        CHECK(ScriptApi::InCombat(fixture.state.npcs[0], fixture.state.tick));
        CHECK_FALSE(ScriptApi::InCombat(fixture.state.npcs[2], fixture.state.tick));
        CHECK(api.GetNearestNpc({.ids = {CHICKEN}}, false)->index == 12);
        CHECK(api.GetNearestNpc({.ids = {CHICKEN}}, true)->index == 10);
    }
}

TEST_CASE("ScriptApi reads ground items and inventories", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    const auto& api = fixture.api;

    CHECK(api.GetNearestGroundItem({})->id == COINS);
    CHECK(api.GetNearestGroundItem({.ids = {BONES}})->tile == Offset(2, 2));
    CHECK_FALSE(api.GetNearestGroundItem({.ids = {BONES}, .radius = 1}).has_value());

    const auto items = api.GetInventory(ScriptApi::INVENTORY);
    REQUIRE(items.size() == 3);
    CHECK(items[1].slot == 2);
    CHECK(api.CountItems(std::vector<s32>{BONES}, ScriptApi::INVENTORY) == 2);
    CHECK(api.CountItems(std::vector<s32>{BONES, COINS}, ScriptApi::INVENTORY) == 102);
    CHECK(api.CountItems({}, ScriptApi::INVENTORY) == 102);
    CHECK(api.FindItem(std::vector<s32>{BONES}, ScriptApi::INVENTORY)->slot == 2);
    CHECK_FALSE(api.FindItem(std::vector<s32>{1}, ScriptApi::INVENTORY).has_value());
    CHECK(api.GetEmptySlots() == ScriptApi::INVENTORY_SIZE - 3);
    CHECK(api.GetInventory(ScriptApi::EQUIPMENT).empty());
}

TEST_CASE("ScriptApi reads stats, modals and run mode", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    auto& state = fixture.state;
    const auto& api = fixture.api;

    state.stats[3] = Stat_s{.xp = 1154, .level = 7, .baseLevel = 10};
    CHECK(api.GetStat(3).level == 7);
    CHECK_THROWS_AS(api.GetStat(-1), std::invalid_argument);
    CHECK_THROWS_AS(api.GetStat(static_cast<s32>(GameState_s::STAT_COUNT)), std::invalid_argument);

    state.interfaces.mainModal = 5292;
    CHECK(api.IsInterfaceOpen(5292));
    CHECK_FALSE(api.IsInterfaceOpen(-1));

    CHECK_FALSE(api.IsRunning());
    state.varps[ScriptApi::RUN_VARP] = 1;
    CHECK(api.IsRunning());
}

TEST_CASE("ScriptApi actions report targets that are gone", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    auto& api = fixture.api;
    const auto bones = InventoryItem_s{.com = ScriptApi::INVENTORY, .slot = 2, .id = BONES, .count = 1};

    CHECK_FALSE(api.InteractNpc(99, ScriptApi::OP_ATTACK));
    CHECK_FALSE(api.InteractPlayer(99, 1));
    CHECK_FALSE(api.InteractGroundItem(BONES, Fixtures::HOME, Fixtures::HOME, ScriptApi::OP_TAKE));
    CHECK_FALSE(api.ItemOp({.com = ScriptApi::INVENTORY, .slot = 1, .id = BONES}, ScriptApi::OP_DROP));
    CHECK_FALSE(api.ItemOp({.com = ScriptApi::INVENTORY, .slot = 40, .id = BONES}, ScriptApi::OP_DROP));
    CHECK_FALSE(api.UseItemOnNpc(bones, 99));

    // The targets exist, so these get as far as sending, which needs a session.
    CHECK_THROWS_AS(api.InteractGroundItem(BONES, Fixtures::HOME + 2, Fixtures::HOME + 2, ScriptApi::OP_TAKE), std::runtime_error);
    CHECK_THROWS_AS(api.ItemOp(bones, ScriptApi::OP_DROP), std::runtime_error);
}

TEST_CASE("ScriptApi keeps the strongest stop request until it's taken", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    auto& api = fixture.api;

    CHECK(api.TakeStopRequest() == StopRequest_e::None);
    api.RequestStop(StopRequest_e::Account);
    api.RequestStop(StopRequest_e::Script);
    CHECK(api.TakeStopRequest() == StopRequest_e::Account);
    CHECK(api.TakeStopRequest() == StopRequest_e::None);
}
