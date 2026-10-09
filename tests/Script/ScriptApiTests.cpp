#include "pch.hpp"
#include "../Cache/TestCache.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../LogCapture.hpp"

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/State/Entity_s.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/State/Zone_s.hpp"
#include "Game/Tile_s.hpp"
#include "Script/ScriptApi.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    constexpr auto CHICKEN = u16{41};
    constexpr auto COW = u16{81};
    constexpr auto UNKNOWN_NPC = u16{900};
    constexpr auto BONES = 526;
    constexpr auto COINS = 995;
    constexpr auto DOOR = u16{1530};
    constexpr auto TREE = u16{1276};
    constexpr auto WALL = u8{0};
    constexpr auto CENTREPIECE = u8{10};

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

    // Chicken 10 is penned in by blocked tiles, a door and a tree stand nearby, and the server has
    // removed a second tree.
    std::shared_ptr<const GameCache_s> MakeCache()
    {
        auto cache = GameCache_s{};
        TestCache::AddNpc(cache, CHICKEN, "Chicken", {"", "Attack"});
        TestCache::AddNpc(cache, COW, "Cow", {"", "Attack"});
        TestCache::AddObj(cache, BONES, "Bones", {}, {"Bury"});
        TestCache::AddObj(cache, COINS, "Coins");
        TestCache::AddLoc(cache, DOOR, "Door", {"Open"});
        TestCache::AddLoc(cache, TREE, "Tree", {"Chop down"});

        auto pen = std::vector<Tile_s>{};
        for (auto dx = 2; dx <= 4; ++dx)
        {
            for (auto dz = -1; dz <= 1; ++dz)
            {
                if (dx != 3 || dz != 0)
                {
                    pen.push_back(Offset(dx, dz));
                }
            }
        }

        const auto locs = std::to_array<TestLoc_s>({
            {.id = DOOR, .tile = Offset(1, -2), .shape = WALL},
            {.id = TREE, .tile = Offset(-3, -3), .shape = CENTREPIECE},
            {.id = TREE, .tile = Offset(8, 8), .shape = CENTREPIECE},
        });

        TestCache::SetMap(cache, locs, pen);
        return std::make_shared<const GameCache_s>(std::move(cache));
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

    // A client that never logs in: queries read the fixture state and map, and actions only get as far
    // as checking their targets, since sending throws without a session.
    class ApiFixture
    {
    public:
        ApiFixture()
            : map{cache}
            , client{std::make_shared<const Config_s>(), cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{state, map, actions}
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

            state.locChanges = {{.tile = Offset(8, 8), .layer = LocLayer_e::Ground, .id = -1, .shape = CENTREPIECE}};
            state.playerOps[1] = PlayerOp_s{.text = "Follow"};
            ++state.sceneChangeCount;
            map.Update(state);
        }

        LogCapture capture;
        std::shared_ptr<const GameCache_s> cache = MakeCache();
        GameState_s state = Fixtures::PlacedState();
        WorldMap map;
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
    CHECK(api.CountItems({.ids = {BONES}}, ScriptApi::INVENTORY) == 2);
    CHECK(api.CountItems({.ids = {BONES, COINS}}, ScriptApi::INVENTORY) == 102);
    CHECK(api.CountItems({}, ScriptApi::INVENTORY) == 102);
    CHECK(api.FindItem({.ids = {BONES}}, ScriptApi::INVENTORY)->slot == 2);
    CHECK_FALSE(api.FindItem({.ids = {1}}, ScriptApi::INVENTORY).has_value());
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

TEST_CASE("ScriptApi finds NPCs and items by name", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    auto& api = fixture.api;
    fixture.state.npcs.push_back(MakeNpc(14, UNKNOWN_NPC, Offset(1, 0)));

    CHECK(GetIndices(api.GetNpcs({.names = {"chicken"}})) == std::vector<u16>{10, 12, 13});
    CHECK(GetIndices(api.GetNpcs({.names = {"Cow", "CHICKEN"}, .radius = 3})) == std::vector<u16>{10, 11, 12});
    CHECK(api.GetNpcs({.names = {""}}).empty());
    CHECK(api.GetNearestNpc({.names = {"Cow"}}, std::nullopt)->index == 11);
    CHECK(api.GetNearestGroundItem({.names = {"bones"}})->id == BONES);
    CHECK_FALSE(api.GetNearestGroundItem({.names = {"Logs"}}).has_value());
    CHECK(api.CountItems({.names = {"Bones"}}, ScriptApi::INVENTORY) == 2);
    CHECK(api.FindItem({.names = {"coins"}}, ScriptApi::INVENTORY)->slot == 0);
}

TEST_CASE("ScriptApi chooses options by their text", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    const auto& api = fixture.api;
    fixture.state.npcs.push_back(MakeNpc(14, UNKNOWN_NPC, Offset(1, 0)));

    CHECK(api.FindNpcOp(10, "attack") == std::optional<u8>{2});
    CHECK_FALSE(api.FindNpcOp(99, "Attack").has_value());
    CHECK_THROWS_WITH(api.FindNpcOp(10, "Pickpocket"), "Chicken (NPC 41) has no option 'Pickpocket'; its options are Attack (2)");
    CHECK_THROWS_WITH(api.FindNpcOp(14, "Attack"), ContainsSubstring("NPC 900 isn't in the cache"));
    CHECK(api.FindLocOp(DOOR, "OPEN") == 1);
    CHECK_THROWS_AS(api.FindLocOp(DOOR, "Close"), std::invalid_argument);
    CHECK(api.FindPlayerOp("follow") == 2);
    CHECK_THROWS_WITH(api.FindPlayerOp("Trade"), "a player has no option 'Trade'; its options are Follow (2)");

    SECTION("ground items offer Take, and inventory items Drop, where their type has no option")
    {
        CHECK(api.FindGroundItemOp(BONES, "take") == ScriptApi::OP_TAKE);
        CHECK(api.FindItemOp(BONES, "Bury") == 1);
        CHECK(api.FindItemOp(BONES, "drop") == ScriptApi::OP_DROP);
        CHECK_THROWS_WITH(api.FindItemOp(COINS, "Bury"), "Coins (item 995) has no option 'Bury'; its options are Drop (5)");
    }
}

TEST_CASE("ScriptApi sees the cache's scenery and the server's changes", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    const auto& api = fixture.api;

    const auto door = api.GetLocAt(Fixtures::HOME + 1, Fixtures::HOME - 2, std::nullopt);
    REQUIRE(door.has_value());
    CHECK(door->id == DOOR);
    CHECK(door->layer == LocLayer_e::Wall);
    CHECK_FALSE(door->changed);
    CHECK_FALSE(api.GetLocAt(Fixtures::HOME + 1, Fixtures::HOME - 2, LocLayer_e::Ground).has_value());

    const auto removed = api.GetLocAt(Fixtures::HOME + 8, Fixtures::HOME + 8, std::nullopt);
    REQUIRE(removed.has_value());
    CHECK(removed->id == -1);
    CHECK(removed->changed);

    const auto locs = api.GetLocs({}, std::nullopt);
    REQUIRE(locs.size() == 2);
    CHECK(locs[0].id == DOOR);
    CHECK(locs[1].id == TREE);
    CHECK(api.GetLocs({.ids = {TREE}, .radius = 2}, std::nullopt).empty());
    CHECK(api.GetLocs({}, LocLayer_e::Ground).size() == 1);
    CHECK(api.GetNearestLoc({.names = {"tree"}}, std::nullopt)->tile == Offset(-3, -3));
    CHECK_FALSE(api.GetNearestLoc({.names = {"Bank booth"}}, std::nullopt).has_value());
}

TEST_CASE("ScriptApi finds routes and skips what can't be reached", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    const auto& api = fixture.api;

    CHECK(api.IsReachable(Fixtures::HOME, Fixtures::HOME + 5));
    CHECK_FALSE(api.IsReachable(Fixtures::HOME + 3, Fixtures::HOME));
    CHECK(api.FindPath(Fixtures::HOME, Fixtures::HOME + 5) == std::vector<Tile_s>{Offset(0, 5)});
    CHECK_FALSE(api.FindPath(Fixtures::HOME + 3, Fixtures::HOME).has_value());

    CHECK(api.GetNearestNpc({.ids = {CHICKEN}}, std::nullopt)->index == 10);
    CHECK(api.GetNearestNpc({.ids = {CHICKEN}}, std::nullopt, true)->index == 12);
    CHECK(api.GetNearestLoc({.ids = {DOOR}}, std::nullopt, true)->id == DOOR);
    CHECK(api.GetNearestGroundItem({.ids = {BONES}}, true)->id == BONES);
}
