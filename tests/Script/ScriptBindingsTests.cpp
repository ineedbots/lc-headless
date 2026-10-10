#include "pch.hpp"
#include "../Cache/TestCache.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../LogCapture.hpp"
#include "ScriptTestRuntime.hpp"

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/State/Player_s.hpp"
#include "Game/State/Zone_s.hpp"
#include "Game/Tile_s.hpp"
#include "Script/ScriptApi.hpp"
#include "Script/ScriptBindings.hpp"
#include "Script/ScriptError.hpp"
#include "Script/ScriptVm.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    Tile_s Offset(s32 dx, s32 dz)
    {
        return {.x = Fixtures::HOME + dx, .z = Fixtures::HOME + dz, .level = 0};
    }

    std::shared_ptr<const GameCache_s> MakeCache()
    {
        auto cache = GameCache_s{};
        TestCache::SetComponents(cache);
        TestCache::AddNpc(cache, 41, "Chicken", {"", "Attack"}).combatLevel = 1;
        TestCache::AddNpc(cache, 81, "Cow", {"", "Attack"});
        TestCache::AddObj(cache, 526, "Bones", {}, {"Bury"});
        TestCache::AddObj(cache, 995, "Coins").stackable = true;
        TestCache::AddLoc(cache, 1530, "Door", {"Open"});
        TestCache::AddLoc(cache, 1276, "Tree", {"Chop down"});
        const auto locs = std::to_array<TestLoc_s>({{.id = 1276, .tile = Offset(-2, 3), .shape = 10}});
        TestCache::SetMap(cache, locs);
        return std::make_shared<const GameCache_s>(std::move(cache));
    }

    // Python asserts check the values, so a failure's traceback names the line that failed.
    class BindingFixture
    {
    public:
        BindingFixture()
            : map{cache}
            , client{std::make_shared<const Config_s>(), cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{state, map, actions}
            , vm{ScriptTestRuntime::Get(), {}, capture.GetLogger()}
        {
            BuildState();
            map.Update(state);
            ScriptBindings::Bind(vm, api);
        }

        ~BindingFixture()
        {
            ScriptBindings::Unbind(vm);
        }

        BindingFixture(const BindingFixture&) = delete;
        BindingFixture& operator=(const BindingFixture&) = delete;

        void Run(std::string_view source)
        {
            vm.RunSource(source, "test.py");
        }

        LogCapture capture;
        std::shared_ptr<const GameCache_s> cache = MakeCache();
        GameState_s state = Fixtures::PlacedState();
        WorldMap map;
        GameClient client;
        GameActions actions;
        ScriptApi api;
        ScriptVm vm;

    private:
        void BuildState()
        {
            state.tick = 50;
            state.localPlayer.appearance = Appearance_s{.name37 = Base37::Encode("bot"), .name = "Bot", .combatLevel = 3};
            state.walkDestination = Offset(4, 4);

            auto chicken = Npc_s{};
            chicken.index = 7;
            chicken.type = 41;
            chicken.tile = Offset(2, 0);
            chicken.hits.push_back({.damage = 1, .health = 2, .maxHealth = 3, .tick = 49});
            chicken.faceEntity = EntityRef_s{.type = EntityType_e::Player, .index = Fixtures::PID};
            auto cow = Npc_s{};
            cow.index = 8;
            cow.type = 81;
            cow.tile = Offset(-5, 0);
            state.npcs = {chicken, cow};

            auto other = Player_s{};
            other.index = 20;
            other.tile = Offset(1, -1);
            other.appearance = Appearance_s{.name37 = Base37::Encode("zezima"), .name = "Zezima", .combatLevel = 126};
            state.players = {other};

            state.groundItems = {{.tile = Offset(3, 3), .id = 526, .count = 1}};
            state.locChanges = {{.tile = Offset(1, 0), .layer = LocLayer_e::Wall, .id = 1530, .shape = 0, .angle = 2}};
            ++state.sceneChangeCount;
            state.inventories[TestCache::INVENTORY] = Inventory_s{.com = TestCache::INVENTORY, .slots = {{.id = 995, .count = 250}, {}, {.id = 526, .count = 1}}};
            state.stats[3] = Stat_s{.xp = 1154, .level = 5, .baseLevel = 10};
            state.varps[173] = 1;
            state.interfaces.mainModal = 5292;
            state.interfaces.components[2458].text = "Click here to logout";
            state.social.friends = {{.name37 = Base37::Encode("zezima"), .name = "Zezima", .world = 2}};
            state.social.ignores = {Base37::Encode("spammer")};
        }
    };
}

TEST_CASE("Script bindings read you and the game", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
assert game.tick() == 50 and game.ingame()
here = game.tile()
assert here.level == 0 and here == Tile(here.x, here.z)
assert reader.pid() == 5 and game.my_name() == 'Bot' and game.combat_level() == 3
assert game.moving() and direct_navigator.destination() == here.translate(4, 4)
assert game.run_enabled() and not game.in_combat()
assert players.local().name == 'Bot'
assert skills.effective('hitpoints') == 5 and skills.level('Hitpoints') == 10 and skills.xp('hitpoints') == 1154
assert skills.hp_fraction() == 0.5
assert skills.index('runecraft') == 20 and skills.index('sailing') == -1
)python");

    CHECK_THROWS_WITH(fixture.Run("skills.level('sailing')\n"), ContainsSubstring("ValueError") && ContainsSubstring("'sailing' is not a skill"));
}

TEST_CASE("Script bindings find NPCs, players, scenery and ground items with queries", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
here = game.tile()
everyone = npcs.all()
assert len(everyone) == 2 and isinstance(everyone[0], Npc)

chicken = npcs.query().id(41).nearest()
assert chicken.index == 7 and chicken.id == 41 and chicken.name == 'Chicken' and chicken.level == 1 and chicken.size == 1
assert chicken.tile() == here.translate(2, 0) and chicken.distance() == 2
assert chicken.health == 2 and chicken.max_health == 3 and chicken.in_combat and not chicken.moving
assert chicken.target == ('player', 5) and chicken.targets_me() and not chicken.targets_another_player()
assert chicken.actions() == ['Attack'] and chicken.valid()
assert 'Npc(index=7' in repr(chicken)

cow = npcs.query().name('cow').first()
assert cow.index == 8 and cow.health == 0 and cow.target is None and cow.level == 0
assert npcs.query().id(41, 81).within(2).nearest().index == 7
assert npcs.query().name(['Goblin', 'Cow']).count() == 1
assert npcs.query().name('Goblin').nearest() is None and not npcs.query().name('Goblin').exists()
assert npcs.query().action('ATTACK').count() == 2
assert npcs.query().where(lambda npc: not npc.in_combat).first().index == 8
assert npcs.query().within_of(here.translate(-5, 0), 1).first().index == 8
assert npcs.query().inside(Area.rectangular(here, here.translate(3, 3))).first().index == 7
assert npcs.query().inside({'minX': here.x - 6, 'maxX': here.x - 4, 'minZ': here.z, 'maxZ': here.z}).first().index == 8
assert npcs.query().nearest_prefer_local(1).index == 7
assert [npc.index for npc in npcs.nearest(2)] == [7, 8]

zezima = players.query().name('zezima').first()
assert zezima.index == 20 and zezima.combat_level == 126 and players.all()[0].name == 'Zezima'
assert players.query().within(0).first() is None

bones = ground_items.query().name('bones').nearest()
assert isinstance(bones, GroundItem) and bones.count == 1 and bones.tile() == here.translate(3, 3)
assert bones.actions() == ['Take'] and bones.valid()
assert ground_items.query().id(1, 2).results() == []

door = locs.at(here.translate(1, 0))
assert door.id == 1530 and door.name == 'Door' and door.layer == LAYER_WALL and door.angle == 2 and door.changed
assert door.actions() == ['Open'] and door.valid()
assert locs.at(here.translate(1, 0), LAYER_GROUND) is None
tree = locs.query().name('tree').nearest()
assert tree.id == 1276 and not tree.changed and tree.tile() == here.translate(-2, 3) and tree.layer == LAYER_GROUND
assert locs.at(here.translate(-2, 3)).id == 1276
assert [loc.id for loc in locs.query().results()] == [1530, 1276]
assert locs.query().id(1276).layer(LAYER_WALL).results() == [] and locs.query().within(1).first().id == 1530
assert locs.query().id(1530).reachable().first().id == 1530

assert direct_navigator.reachable(here.translate(0, 1))
assert direct_navigator.path(here.translate(0, 3)) == [here.translate(0, 3)]
assert direct_navigator.path(here.translate(500, 0)) is None
)python");
}

TEST_CASE("Script bindings read items, types, interfaces, varps and social lists", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
items = inventory.items()
assert [(item.id, item.slot) for item in items] == [(995, 0), (526, 2)] and isinstance(items[0], InvItem)
assert items[0].com == INVENTORY and items[0].count == 250 and items[0].name == 'Coins' and not items[0].noted
assert items[0].actions() == ['Drop'] and items[1].actions() == ['Bury', 'Drop']
assert inventory.first('BONES').slot == 2 and inventory.first('logs') is None
assert inventory.contains('coins') and inventory.count('Coins') == 250 and inventory.count_by_id(526) == 1
assert inventory.used() == 2 and inventory.free() == INVENTORY_SIZE - 2 and not inventory.is_full()
assert equipment.items() == [] and not equipment.contains('Bronze sword') and reader.inventory(BANK) == []

npc_type = reader.npc_type(41)
assert isinstance(npc_type, NpcType) and npc_type.name == 'Chicken' and npc_type.ops == [None, 'Attack', None, None, None]
assert npc_type.examine is None and npc_type.size == 1 and npc_type.combat_level == 1
assert reader.npc_type(5000) is None
bones = reader.item_type(526)
assert isinstance(bones, ItemType) and bones.inventory_ops[0] == 'Bury' and bones.ops == [None] * 5
assert not bones.stackable and not bones.members and bones.value == 1 and bones.note_of is None
assert reader.item_type(995).stackable
tree = reader.loc_type(1276)
assert isinstance(tree, LocType) and tree.ops[0] == 'Chop down' and tree.blocks_walk and tree.blocks_projectiles

assert reader.main_modal() == 5292 and reader.side_modal() == -1 and reader.chat_modal() == -1
assert reader.interface_open(5292) and not reader.interface_open(1)
assert reader.component_text(2458) == 'Click here to logout' and reader.component_text(1) is None
assert not reader.count_dialog_open()
assert reader.varp(173) == 1 and reader.varp(1) == 0
assert friends.list() == [('Zezima', 2)] and ignores.list() == ['Spammer']
)python");
}

TEST_CASE("Script bindings choose options by their text, as rs2b0t's interact does", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
here = game.tile()
chicken = npcs.query().id(41).first()
door = locs.at(here.translate(1, 0))
bones = ground_items.query().first()
assert chicken.interact('Pickpocket') is False and door.interact('Close') is False and bones.interact('Eat') is False
assert inventory.first('Coins').interact('Bury') is False
)python");

    // These have the option, so they get as far as sending, which needs a session.
    CHECK_THROWS_WITH(fixture.Run("door.interact('open')\n"), ContainsSubstring("RuntimeError") && ContainsSubstring("not in game"));
    CHECK_THROWS_WITH(fixture.Run("inventory.first('Bones').interact('Bury')\n"), ContainsSubstring("RuntimeError") && ContainsSubstring("not in game"));
    CHECK_THROWS_WITH(fixture.Run("bones.interact('Take')\n"), ContainsSubstring("RuntimeError") && ContainsSubstring("not in game"));
    CHECK_THROWS_WITH(fixture.Run("inventory.first('Bones').use_on(inventory.first('Coins'))\n"), ContainsSubstring("RuntimeError") && ContainsSubstring("not in game"));
}

TEST_CASE("Script bindings check argument types and ranges", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run("import _core\n");

    CHECK_THROWS_WITH(fixture.Run("_core.get_npcs(ids='chicken')\n"), ContainsSubstring("TypeError") && ContainsSubstring("ids must be an int, a list of ints or None"));
    CHECK_THROWS_WITH(fixture.Run("_core.get_npcs(names=41)\n"), ContainsSubstring("TypeError") && ContainsSubstring("names must be a str or a list of str"));
    CHECK_THROWS_WITH(fixture.Run("_core.attack_npc('chicken')\n"), ContainsSubstring("TypeError") && ContainsSubstring("npc must be a Npc or its index"));
    CHECK_THROWS_WITH(fixture.Run("_core.interact_npc(7, 6)\n"), ContainsSubstring("ValueError") && ContainsSubstring("op must be from 1 to 5"));
    CHECK_THROWS_WITH(fixture.Run("_core.get_current_stat(25)\n"), ContainsSubstring("ValueError"));
    CHECK_THROWS_WITH(fixture.Run("_core.walk_to(1, 2, run=1)\n"), ContainsSubstring("TypeError") && ContainsSubstring("run must be True or False"));
    CHECK_THROWS_WITH(fixture.Run("direct_navigator.walk_path([(1, 2), (3,)])\n"), ContainsSubstring("TypeError") && ContainsSubstring("(x, z) pairs"));
    CHECK_THROWS_WITH(fixture.Run("_core.drop_item(ground_items.query().first())\n"), ContainsSubstring("TypeError") && ContainsSubstring("item must be an InvItem"));
    CHECK_THROWS_WITH(fixture.Run("inventory.first('Coins').use_on(5)\n"), ContainsSubstring("TypeError") && ContainsSubstring("not int"));
}

TEST_CASE("Script bindings report actions on targets that are gone", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run("chicken = npcs.query().id(41).first()\nbones = ground_items.query().first()\n");

    fixture.state.npcs.clear();
    fixture.state.groundItems.clear();
    fixture.Run(R"python(
assert not chicken.valid() and chicken.interact('Attack') is False
assert not bones.valid() and bones.interact('Take') is False
)python");
}

TEST_CASE("Script bindings expose the account's settings", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    ScriptBindings::SetSettings(fixture.vm, R"json({"npc_ids": [41, 1017], "loot": true, "area": {"x": 3230}, "name": "chickens"})json");
    fixture.Run(R"python(
assert settings.npc_ids == [41, 1017] and settings.loot is True and settings.area['x'] == 3230
assert settings.name == 'chickens'
assert settings.get('missing', 5) == 5 and 'loot' in settings and 'missing' not in settings
)python");

    CHECK_THROWS_WITH(fixture.Run("settings.missing\n"), ContainsSubstring("AttributeError"));
}
