#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"

#include "Cache/GameCache_s.hpp"
#include "Config/Config_s.hpp"
#include "Config/Revision_e.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/State/Player_s.hpp"
#include "Game/State/Zone_s.hpp"
#include "Game/Tile_s.hpp"
#include "Script/Bindings/ScriptBindings.hpp"
#include "Script/Error/ScriptError.hpp"
#include "Script/ScriptContext.hpp"
#include "Script/ScriptVm.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    Tile_s Offset(s32 dx, s32 dz)
    {
        return {.x = Fixtures::HOME + dx, .z = Fixtures::HOME + dz, .level = 0};
    }

    std::shared_ptr<const GameCache_s> MakeCache(Revision_e revision, bool withInterfaces)
    {
        auto cache = GameCache_s{};
        cache.revision = revision;
        TestCache::SetComponents(cache);
        TestCache::AddNpc(cache, 41, "Chicken", {"", "Attack"}).combatLevel = 1;
        TestCache::AddNpc(cache, 81, "Cow", {"", "Attack"});
        TestCache::AddObj(cache, 526, "Bones", {}, {"Bury"});
        TestCache::AddObj(cache, 995, "Coins").stackable = true;
        TestCache::AddLoc(cache, 1530, "Door", {"Open"});
        TestCache::AddLoc(cache, 1276, "Tree", {"Chop down"});

        if (withInterfaces)
        {
            TestCache::SetChatInterfaces(cache);
            TestCache::SetTradeScreen(cache);
            TestCache::AddComponents(cache, {
                {.id = 700, .root = 700, .type = ComponentType_e::Layer, .width = 480, .height = 300,
                    .children = {{.id = 701, .x = 20, .y = 20}, {.id = 702, .x = 62, .y = 20}, {.id = 703, .x = 200, .y = 100}}},
                {.id = 701, .root = 700, .type = ComponentType_e::Inv, .width = 4, .height = 1, .marginX = 10,
                    .options = {"Make", "Make 5", "Make 10"}},
                {.id = 702, .root = 700, .type = ComponentType_e::Model, .width = 32, .height = 32},
                {.id = 703, .root = 700, .type = ComponentType_e::InvText, .width = 1, .height = 1},
            });
        }

        const auto locs = std::to_array<TestLoc_s>({{.id = 1276, .tile = Offset(-2, 3), .shape = 10}});
        TestCache::SetMap(cache, locs);
        return std::make_shared<const GameCache_s>(std::move(cache));
    }

    std::shared_ptr<const Config_s> MakeConfig(Revision_e revision)
    {
        auto config = Config_s{};
        config.login.revision = revision;
        return std::make_shared<const Config_s>(std::move(config));
    }

    // Python asserts check the values, so a failure's traceback names the line that failed.
    class BindingFixture
    {
    public:
        explicit BindingFixture(Revision_e revision = Revision_e::Rev289, bool withInterfaces = false, std::shared_ptr<const Config_s> config = {})
            : cache{MakeCache(revision, withInterfaces)}
            , map{cache}
            , client{config ? std::move(config) : MakeConfig(revision), cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
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

        void Login()
        {
            client.Login();
            const auto deadline = std::chrono::steady_clock::now() + 5s;
            while (client.GetState().messages.empty() && std::chrono::steady_clock::now() < deadline)
            {
                client.Pump(20ms);
            }
            REQUIRE(client.GetMap().IsLoaded());
        }

        LogCapture capture;
        std::shared_ptr<const GameCache_s> cache;
        GameState_s state = Fixtures::PlacedState();
        WorldMap map;
        GameClient client;
        GameActions actions;
        ScriptContext api;
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

TEST_CASE("Native reachability bindings distinguish nearby targets from unloaded tiles", "[ScriptBindings][BindingBoundaryCoverage]")
{
    auto fixture = BindingFixture{};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
here = game.tile()
assert _core.can_reach_entity(here.x, here.z + 1)
assert _core.can_reach_ground_item(here.x, here.z + 1)
assert not _core.can_reach_entity(0, 0)
assert not _core.can_reach_ground_item(0, 0)
)python"));
    for (const auto function : {"can_reach_entity", "can_reach_ground_item"})
    {
        CHECK_THROWS_WITH(fixture.Run(std::format("_core.{}(-1, 3200)", function)), ContainsSubstring("ValueError") && ContainsSubstring("x must be from"));
        CHECK_THROWS_WITH(fixture.Run(std::format("_core.{}(3200, 'north')", function)), ContainsSubstring("TypeError") && ContainsSubstring("z must be an int"));
        REQUIRE_NOTHROW(fixture.Run(std::format("assert _core.{}(game.tile().x, game.tile().z + 1)", function)));
    }
}

TEST_CASE("Native entity conversion retains identity when metadata has not arrived", "[ScriptBindings][BindingBoundaryCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.state.npcs[0].type = 65535;
    fixture.state.players[0].appearance.reset();
    REQUIRE_NOTHROW(fixture.Run(R"python(
unknown = npcs.all()[0]
assert unknown.index == 7 and unknown.id == 65535
assert unknown.name is None and unknown.level == 0 and unknown.size == 1
assert unknown.tile() == game.tile().translate(2, 0)
assert unknown.actions() == [] and unknown.health == 2
player = players.all()[0]
assert player.index == 20 and player.name is None and player.combat_level == 0
assert player.tile() == game.tile().translate(1, -1)
)python"));
    fixture.state.npcs[0].type = 41;
    fixture.state.players[0].appearance = Appearance_s{.name = "Returned", .combatLevel = 42};
    REQUIRE_NOTHROW(fixture.Run("assert npcs.all()[0].name == 'Chicken'\nassert players.all()[0].name == 'Returned'\nassert players.all()[0].combat_level == 42\n"));
}

TEST_CASE("Script bindings report the configured revision", "[ScriptBindings]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = BindingFixture{revision};
    fixture.Run(std::format("assert game.revision() == {}\n", static_cast<u16>(revision)));
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

TEST_CASE("Script bindings read the hint arrow, what you face and say, and the scene's collision", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.state.hintArrow = HintArrow_s{.kind = HintArrowKind_e::Tile, .tile = Offset(3, 2)};
    fixture.state.localPlayer.faceEntity = EntityRef_s{.type = EntityType_e::Npc, .index = 7};
    fixture.state.localPlayer.say = OverheadText_s{.text = "Hello", .tick = 48};
    fixture.Run(R"python(
here = game.tile()
assert reader.hint_tile() == here.translate(3, 2) and reader.hint_arrow().kind == 'tile'
assert game.facing() == ('npc', 7) and not facing_player(game.facing())
assert game.overhead_text() == 'Hello'
assert reachability.flags(here.translate(1, 0)) and reachability.flags(here.translate(0, -1)) == 0
assert reachability.flags(here.translate(500, 0)) is None
assert reachability.line_of_sight(here, here.translate(0, -3))
assert not reachability.line_of_sight(here, here.translate(-4, 6))
)python");

    // The text shows for 5 ticks.
    fixture.state.hintArrow = HintArrow_s{.kind = HintArrowKind_e::Npc, .index = 7};
    fixture.state.localPlayer.say = OverheadText_s{.text = "Hello", .tick = 45};
    fixture.Run(R"python(
arrow = reader.hint_arrow()
assert arrow.kind == 'npc' and arrow.index == 7 and reader.hint_tile() is None
assert game.overhead_text() is None
)python");

    fixture.state.hintArrow.reset();
    fixture.Run("assert reader.hint_arrow() is None and reader.hint_tile() is None\n");
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

TEST_CASE("Native query bindings accept tuple filters and preserve empty results", "[ScriptBindings][BindingCoverage]")
{
    auto fixture = BindingFixture{};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert [n.index for n in _core.get_npcs(ids=(41, 81))] == [7, 8]
assert [n.index for n in _core.get_npcs(names=('Cow', 'Chicken'))] == [7, 8]
assert [n.index for n in _core.get_npcs(ids=41, radius=2)] == [7]
assert _core.get_npcs(ids=(9999,), radius=0) == []
assert _core.get_npcs(names=['Missing']) == []
assert _core.get_inventory_count_by_id((995, 526)) == 251
assert _core.get_inventory_item_by_id((526,)).slot == 2
assert _core.get_inventory_item_by_id(9999) is None
assert _core.get_inventory_count_by_name(('Coins', 'Bones')) == 251
assert _core.get_inventory_item_by_name(('Missing', 'Bones')).id == 526
assert _core.get_inventory_item_by_name(['Missing']) is None
assert _core.get_inventory_count_by_id([], com=9999) == 0
)python"));
}

TEST_CASE("Native query bindings reject malformed filter sequences", "[ScriptBindings][BindingCoverage]")
{
    const auto [source, type, message] = GENERATE(
        std::tuple{"_core.get_npcs(ids=[41, 'Cow'])", "TypeError", "ids must be an int"},
        std::tuple{"_core.get_npcs(ids=(41, -1))", "ValueError", "ids must be from"},
        std::tuple{"_core.get_npcs(ids=2147483648)", "ValueError", "ids must be from"},
        std::tuple{"_core.get_npcs(names=[])", "ValueError", "names must have at least one name"},
        std::tuple{"_core.get_npcs(names=())", "ValueError", "names must have at least one name"},
        std::tuple{"_core.get_npcs(names=('Cow', 41))", "TypeError", "names must be a str"},
        std::tuple{"_core.get_npcs(radius=-1)", "ValueError", "radius must be from"},
        std::tuple{"_core.get_npcs(radius='near')", "TypeError", "radius must be an int"},
        std::tuple{"_core.get_locs(layer=4)", "ValueError", "layer must be from"},
        std::tuple{"_core.get_locs(layer='wall')", "TypeError", "layer must be an int"});
    CAPTURE(source);
    auto fixture = BindingFixture{};
    fixture.Run("import _core\n");
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring(type) && ContainsSubstring(message));
    // A rejected call must leave the VM usable for the next query.
    REQUIRE_NOTHROW(fixture.Run("assert len(_core.get_npcs(ids=41)) == 1\n"));
}

TEST_CASE("Native action bindings validate byte arrays for appearance changes", "[ScriptBindings][BindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.Run("import _core\n");
    const auto [source, type, message] = GENERATE(
        std::tuple{"_core.set_appearance(False, 7, [0]*5)", "TypeError", "kits must be a list of 7 numbers"},
        std::tuple{"_core.set_appearance(False, [0]*6, [0]*5)", "ValueError", "kits must hold 7 numbers"},
        std::tuple{"_core.set_appearance(False, (0,0,0,0,0,0,-1), [0]*5)", "ValueError", "kits must be from 0 to 255"},
        std::tuple{"_core.set_appearance(False, [0]*7, [0,0,0,0,256])", "ValueError", "colours must be from 0 to 255"},
        std::tuple{"_core.set_appearance(False, [0]*7, [0,0,0,0,'red'])", "TypeError", "colours must be an int"},
        std::tuple{"_core.set_appearance(1, [0]*7, [0]*5)", "TypeError", "female must be True or False"});
    CAPTURE(source);
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring(type) && ContainsSubstring(message));
    REQUIRE_NOTHROW(fixture.Run(R"python(
assert _core.set_appearance(False, [0]*7, [0]*5) is False
assert _core.set_appearance(True, (0,1,2,3,4,5,255), (0,1,2,3,255)) is False
)python"));
}

TEST_CASE("Native movement bindings reject malformed points and coordinates", "[ScriptBindings][BindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.Run("import _core\n");
    const auto [source, type, message] = GENERATE(
        std::tuple{"_core.walk_path(42)", "TypeError", "points must be a list of (x, z) points"},
        std::tuple{"_core.walk_path([1])", "TypeError", "points must hold (x, z) pairs"},
        std::tuple{"_core.walk_path([(1,2,3)])", "TypeError", "points must hold (x, z) pairs"},
        std::tuple{"_core.walk_path(([1,'north'],))", "TypeError", "points must be an int"},
        std::tuple{"_core.walk_to(-1, 0)", "ValueError", "x must be from"},
        std::tuple{"_core.walk_to(0, -1)", "ValueError", "z must be from"},
        std::tuple{"_core.answer_count(-1)", "ValueError", "value must be from"},
        std::tuple{"_core.click_text('Continue', root=65536)", "ValueError", "root must be from"});
    CAPTURE(source);
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring(type) && ContainsSubstring(message));
}

TEST_CASE("Native action bindings reject wrong target classes and ambiguous loc calls", "[ScriptBindings][BindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.Run("import _core\ndoor = locs.at(game.tile().translate(1, 0))\n");
    const auto [source, message] = GENERATE(
        std::pair{"_core.interact_npc(7, [])", "op must be an int or a str"},
        std::pair{"_core.interact_npc(7, 0)", "op must be from 1 to 5"},
        std::pair{"_core.interact_loc(door, 1, 2)", "interact_loc takes a Loc and an op"},
        std::pair{"_core.interact_loc(door, 1, op=2)", "interact_loc takes a Loc and an op"},
        std::pair{"_core.take_ground_item(inventory.first('Coins'))", "item must be a GroundItem"},
        std::pair{"_core.cast_on_item(1, door)", "item must be an InvItem"},
        std::pair{"_core.cast_on_player(1, door)", "player must be a Player or its index"});
    CAPTURE(source);
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring(message));
}

TEST_CASE("Native action bindings reject stale references across item and spell actions", "[ScriptBindings][BindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
import _core
item = inventory.first('Bones')
coins = inventory.first('Coins')
npc = npcs.query().first()
player = players.query().first()
ground = ground_items.query().first()
)python");
    fixture.state.inventories.clear();
    fixture.state.npcs.clear();
    fixture.state.players.clear();
    fixture.state.groundItems.clear();
    REQUIRE_NOTHROW(fixture.Run(R"python(
assert _core.item_op(item, 1) is False
assert _core.inv_button(item, 1) is False
assert _core.drop_item(item) is False
assert _core.use_item_on_npc(item, npc) is False
assert _core.use_item_on_player(item, player) is False
assert _core.use_item_on_loc(item, 1530, 3201, 3200) is False
assert _core.use_item_on_ground_item(item, ground) is False
assert _core.use_item_on_item(item, coins) is False
assert _core.cast_on_npc(1, npc) is False
assert _core.cast_on_player(1, player) is False
assert _core.cast_on_ground_item(1, ground) is False
assert _core.cast_on_item(1, item) is False
assert _core.talk_to_npc(npc) is False
assert _core.interact_player(player, 1) is False
assert _core.take_ground_item(ground) is False
)python"));
}

TEST_CASE("Native action bindings resolve named menus and report unavailable options", "[ScriptBindings][ActionBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    fixture.state.playerOps[0] = PlayerOp_s{.text = "Trade with"};
    fixture.state.inventories[701] = Inventory_s{.com = 701, .slots = {{.id = 526, .count = 1}}};
    fixture.Run(R"python(
import _core
npc = npcs.query().first()
player = players.query().first()
ground = ground_items.query().first()
item = inventory.first('Bones')
make_item = _core.get_inventory_item_by_id(526, com=701)
)python");
    const auto [source, target] = GENERATE(
        std::pair{"_core.interact_npc(npc, 'Dance')", "Chicken"},
        std::pair{"_core.interact_player(player, 'Dance')", "a player"},
        std::pair{"_core.interact_loc(1530, 3201, 3200, 'Dance')", "Door"},
        std::pair{"_core.interact_ground_item(ground, 'Dance')", "Bones"},
        std::pair{"_core.item_op(item, 'Dance')", "Bones"},
        std::pair{"_core.inv_button(make_item, 'Dance')", "701"});
    CAPTURE(source);
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring("ValueError") && ContainsSubstring(target) && ContainsSubstring("has no option 'Dance'"));
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_inventory_item_by_id(526).slot == 2\n"));
}

TEST_CASE("Native named NPC actions return false after the target disappears", "[ScriptBindings][ActionBindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.Run("import _core\nnpc = npcs.query().first()\n");
    fixture.state.npcs.clear();
    REQUIRE_NOTHROW(fixture.Run("assert _core.interact_npc(npc, 'Attack') is False\n"));
}

TEST_CASE("Native scenery bindings accept object and coordinate call forms", "[ScriptBindings][ActionBindingCoverage]")
{
    auto server = FakeGameServer{TestWorld::Send};
    auto fixture = BindingFixture{Revision_e::Rev289, false, std::make_shared<const Config_s>(server.MakeConfig())};
    fixture.Login();
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
door = locs.at(game.tile().translate(1, 0))
assert _core.interact_loc(door, 'open') is True
assert _core.interact_loc(door, op='Open') is True
assert _core.interact_loc(door, 1) is True
assert _core.interact_loc(1530, 3201, 3200, 'Open') is True
assert _core.interact_loc_via([(3200,3200),(3200,3201)], 1530, 3201, 3200, 'Open') is True
)python"));
    fixture.client.Flush();
    REQUIRE(server.WaitForPacket(ClientProt_e::OpLoc1, 5));
    const auto packets = server.GetPackets(ClientProt_e::OpLoc1);
    REQUIRE(packets.size() == 5);
    for (const auto& packet : packets)
    {
        auto payload = Packet{packet.payload};
        CHECK(payload.G2() == 3201);
        CHECK(payload.G2() == 3200);
        CHECK(payload.G2() == 1530);
        CHECK(payload.GetAvailable() == 0);
    }
}

TEST_CASE("Native scenery waypoint bindings validate paths and menu arguments", "[ScriptBindings][ActionBindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.Run("import _core\n");
    const auto [source, type, message] = GENERATE(
        std::tuple{"_core.interact_loc_via(7, 1530, 3201, 3200, 1)", "TypeError", "points must be a list"},
        std::tuple{"_core.interact_loc_via([(3200,)], 1530, 3201, 3200, 1)", "TypeError", "points must hold (x, z) pairs"},
        std::tuple{"_core.interact_loc_via([], -1, 3201, 3200, 1)", "ValueError", "id must be from"},
        std::tuple{"_core.interact_loc_via([], 1530, 3201, 3200, 'Dance')", "ValueError", "has no option 'Dance'"},
        std::tuple{"_core.interact_loc_via([], 1530, -1, 3200, 1)", "ValueError", "x must be from"});
    CAPTURE(source);
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring(type) && ContainsSubstring(message));
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_x() == 3200\n"));
}

TEST_CASE("Native spell and button bindings validate IDs before dispatch", "[ScriptBindings][ActionBindingCoverage]")
{
    auto server = FakeGameServer{TestWorld::Send};
    auto fixture = BindingFixture{Revision_e::Rev289, false, std::make_shared<const Config_s>(server.MakeConfig())};
    fixture.Login();
    fixture.Run("import _core\n");
    const auto [source, message] = GENERATE(
        std::pair{"_core.cast_on_loc(-1, 1530, 3201, 3200)", "spell must be from"},
        std::pair{"_core.cast_on_loc(1, 1530, 3201, -1)", "z must be from"},
        std::pair{"_core.click_button(65536)", "com must be from"},
        std::pair{"_core.set_run(1)", "run must be True or False"});
    CAPTURE(source);
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring(message));
    REQUIRE_NOTHROW(fixture.Run(R"python(
assert _core.cast_on_loc(1, 1530, 3201, 3200) is None
assert _core.click_button(2458) is None
assert _core.set_run(False) is None
assert _core.close_interfaces() is None
)python"));
    fixture.client.Flush();
    REQUIRE(server.WaitForPacket(ClientProt_e::CloseModal));
    const auto spells = server.GetPackets(ClientProt_e::OpLocT);
    REQUIRE(spells.size() == 1);
    auto spell = Packet{spells.front().payload};
    CHECK(spell.G2() == 3201);
    CHECK(spell.G2() == 3200);
    CHECK(spell.G2() == 1530);
    CHECK(spell.G2() == 1);
    CHECK(spell.GetAvailable() == 0);
    const auto buttons = server.GetPackets(ClientProt_e::IfButton);
    REQUIRE(buttons.size() == 2);
    auto click = Packet{buttons[0].payload};
    CHECK(click.G2() == 2458);
    auto run = Packet{buttons[1].payload};
    CHECK(run.G2() == TestCache::RUN_OFF_BUTTON);
}

TEST_CASE("Native inventory bindings distinguish unseen containers from empty ones", "[ScriptBindings][BindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.state.inventories.at(TestCache::INVENTORY).tick = 47;
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.has_inventory(INVENTORY)
assert _core.inventory_tick(INVENTORY) == 47
assert not _core.has_inventory(BANK)
assert _core.inventory_tick(BANK) == -1
assert _core.get_inventory(BANK) == []
)python"));
    fixture.state.inventories[TestCache::INVENTORY].slots.clear();
    REQUIRE_NOTHROW(fixture.Run(R"python(
assert _core.has_inventory(INVENTORY)
assert _core.get_inventory() == []
assert _core.get_inventory_count_by_name('Coins') == 0
assert _core.get_inventory_item_by_name('Coins') is None
)python"));
}

TEST_CASE("Native social bindings surface offline errors and leave queries usable", "[ScriptBindings][BindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.Run("import _core\n");
    const auto source = GENERATE("_core.say('Hello')", "_core.send_pm('Zezima', 'Hello')",
        "_core.command('test')", "_core.add_friend('Zezima')", "_core.remove_friend('Zezima')",
        "_core.add_ignore('Spammer')", "_core.remove_ignore('Spammer')");
    CAPTURE(source);
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring("RuntimeError") && ContainsSubstring("not in game"));
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_friends() == [('Zezima', 2)]\nassert _core.get_ignores() == ['Spammer']\n"));
}

TEST_CASE("Native component bindings expose cache fields and server overrides", "[ScriptBindings][InterfaceBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    fixture.state.interfaces.mainModal = TestCache::TRADE_SCREEN;
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
root = _core.get_component(300)
assert root.id == 300 and root.root == 300 and root.layer is None
assert root.type == 'layer' and root.button is None and root.visible
assert root.children == [301,302,303,304,306,307,308,309]
label = _core.get_component(302)
assert label.layer == 300 and label.type == 'text' and label.text == 'Accept'
assert label.colour == 0x00C000 and label.x == 239 and label.y == 181
assert label.width == 39 and label.height == 14 and label.options is None
assert label.item is None and label.varp is None and label.value is None
assert label.target_verb is None and label.target_name is None
button = _core.get_component(301)
assert button.button == 'ok' and button.button_text == 'Ok'
assert _core.get_component(9999) is None
)python"));
    fixture.state.interfaces.components[TestCache::TRADE_ACCEPT_LABEL].text = "Accepted";
    fixture.state.interfaces.components[TestCache::TRADE_ACCEPT_LABEL].colour = 0x123456;
    fixture.state.interfaces.components[TestCache::TRADE_ACCEPT_LABEL].position = ComponentPosition_s{.x = -10, .y = 20};
    REQUIRE_NOTHROW(fixture.Run(R"python(
label = _core.get_component(302)
assert label.text == 'Accepted' and label.colour == 0x123456
assert label.x == -10 and label.y == 20
)python"));
}

TEST_CASE("Native component filters honour hidden ancestors and selected roots", "[ScriptBindings][InterfaceBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    fixture.state.interfaces.mainModal = TestCache::TRADE_SCREEN;
    fixture.state.interfaces.sideModal = TestCache::TRADE_SIDE;
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert [c.id for c in _core.find_components(text='aCcEpT')] == [302]
assert [c.id for c in _core.find_components(button='close', root=300)] == [303]
assert _core.find_components(text='Accept', button='close') == []
assert _core.find_components(text='Accept', root=340) == []
assert _core.find_components(text='Waiting') == []
assert _core.get_component(304).hidden and not _core.get_component(305).visible
assert len(_core.get_interface(300)) == 10
assert _core.get_interface(9999) == []
)python"));
    fixture.state.interfaces.components[TestCache::TRADE_STATUS_LAYER].hidden = false;
    REQUIRE_NOTHROW(fixture.Run("assert [c.id for c in _core.find_components(text='Waiting')] == [305]\n"));
    fixture.state.interfaces.mainModal = -1;
    REQUIRE_NOTHROW(fixture.Run("assert _core.find_components(text='Accept', root=300) == []\n"));
}

TEST_CASE("Native interface roots deduplicate modals, overlays and tabs", "[ScriptBindings][InterfaceBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    auto& interfaces = fixture.state.interfaces;
    interfaces.mainModal = TestCache::TRADE_SCREEN;
    interfaces.sideModal = TestCache::TRADE_SIDE;
    interfaces.chatModal = TestCache::DIALOGUE;
    interfaces.overlay = TestCache::TRADE_SCREEN;
    interfaces.tabs[0] = TestCache::TRADE_SIDE;
    interfaces.tabs[14] = 700;
    interfaces.modalChanges = 17;
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.get_open_interfaces() == [300,340,310,700]
assert _core.get_tab_interface(0) == 340 and _core.get_tab_interface(14) == 700
assert _core.get_tab_interface(1) == -1 and _core.modal_changes() == 17
assert not _core.can_set_run() and not _core.is_appearance_screen_open()
)python"));
    const auto invalid = GENERATE(-1, 15);
    CHECK_THROWS_WITH(fixture.Run(std::format("_core.get_tab_interface({})", invalid)), ContainsSubstring("ValueError") && ContainsSubstring("tab must be from 0 to 14"));
}

TEST_CASE("Native dialogue bindings expose visible texts, choices and continue buttons", "[ScriptBindings][InterfaceBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    fixture.state.interfaces.chatModal = TestCache::DIALOGUE;
    fixture.state.interfaces.components[TestCache::DIALOGUE_TEXT].text = "@blu@Hello there.";
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.find_continue() == 312
assert _core.get_chat_texts() == ['Hello there.', 'Click here to continue']
assert _core.get_texts(310) == _core.get_chat_texts()
assert _core.get_chat_options() == []
)python"));
    fixture.state.interfaces.components[TestCache::DIALOGUE_CONTINUE].hidden = true;
    REQUIRE_NOTHROW(fixture.Run("assert _core.find_continue() is None\n"));
    fixture.state.interfaces.chatModal = TestCache::OPTIONS;
    fixture.state.interfaces.components[TestCache::OPTION_ONE].text = "Yes, please.";
    fixture.state.interfaces.components[TestCache::OPTION_TWO].text = "No, thanks.";
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_chat_options() == [(321,'Yes, please.'),(322,'No, thanks.')]\n"));
    fixture.state.interfaces.components[TestCache::OPTION_TWO].hidden = true;
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_chat_options() == [(321,'Yes, please.')]\n"));
    fixture.state.interfaces.chatModal = -1;
    REQUIRE_NOTHROW(fixture.Run("assert _core.find_continue() is None\nassert _core.get_chat_options() == []\nassert _core.get_chat_texts() == []\n"));
}

TEST_CASE("Native make bindings preserve product names and quantity button mappings", "[ScriptBindings][InterfaceBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    fixture.state.interfaces.mainModal = -1;
    fixture.state.interfaces.chatModal = TestCache::MAKE_MENU;
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
products = _core.get_make_products()
assert len(products) == 1
assert products[0][0] == 'Oak Long Bow' and products[0][1] == -1
assert products[0][2] == [(-1,331),(10,332),(5,333),(1,334)]
assert _core.get_chat_options() == []
)python"));
    fixture.state.interfaces.chatModal = -1;
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_make_products() == []\nassert _core.get_make_panel() == []\n"));
}

TEST_CASE("Native make panel bindings retain source item counts and overlaid product IDs", "[ScriptBindings][InterfaceBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    fixture.state.interfaces.mainModal = 700;
    fixture.state.inventories[701] = Inventory_s{.com = 701, .slots = {{.id = 995, .count = 250}, {.id = 526, .count = 3}, {}}};
    fixture.state.interfaces.components[702].model = ComponentModel_s{.kind = ComponentModelKind_e::Object, .id = 995};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
panel = _core.get_make_panel()
assert len(panel) == 2
assert isinstance(panel[0][0], InvItem)
assert (panel[0][0].com,panel[0][0].slot,panel[0][0].id,panel[0][0].count,panel[0][1]) == (701,0,995,250,995)
assert (panel[1][0].com,panel[1][0].slot,panel[1][0].id,panel[1][0].count,panel[1][1]) == (701,1,526,3,995)
assert _core.get_component(702).item == 995
inventories = _core.get_inventories(700)
assert inventories == [(701,'inv',20,['Make','Make 5','Make 10',None,None]),(703,'invtext',200,[None]*5)]
)python"));
    fixture.state.interfaces.components[701].hidden = true;
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_make_panel() == []\n"));
}

TEST_CASE("Native inventory component bindings preserve sparse operation slots", "[ScriptBindings][InterfaceBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    fixture.state.interfaces.mainModal = TestCache::TRADE_SCREEN;
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
offers = _core.get_inventories(300)
assert len(offers) == 2
assert offers[0][0:2] == (306,'inv') and offers[1][0:2] == (307,'inv')
assert offers[0][3] == ['Remove 1','Remove 5','Remove 10','Remove All','Remove X']
assert offers[1][3] == [None]*5
component = _core.get_component(306)
assert component.options == offers[0][3]
assert _core.get_inventories(9999) == []
)python"));
}

TEST_CASE("Native player menu bindings preserve absent options and server text", "[ScriptBindings][InterfaceBindingCoverage]")
{
    const auto revision = GENERATE(Revision_e::Rev274, Revision_e::Rev289);
    auto fixture = BindingFixture{revision};
    fixture.state.playerOps[0] = PlayerOp_s{.text = "Trade with"};
    fixture.state.playerOps[4] = PlayerOp_s{.text = "Follow", .deprioritised = true};
    REQUIRE_NOTHROW(fixture.Run("import _core\nassert _core.get_player_menu() == ['Trade with',None,None,None,'Follow']\n"));
    fixture.state.playerOps = {};
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_player_menu() == [None]*5\n"));
}

TEST_CASE("Native interface filters reject invalid optional arguments", "[ScriptBindings][InterfaceBindingCoverage]")
{
    auto fixture = BindingFixture{Revision_e::Rev289, true};
    fixture.Run("import _core\n");
    const auto [source, type, message] = GENERATE(
        std::tuple{"_core.find_components(text=1)", "TypeError", "text must be a str"},
        std::tuple{"_core.find_components(button=1)", "TypeError", "button must be a str"},
        std::tuple{"_core.find_components(root=-1)", "ValueError", "root must be from"});
    CHECK_THROWS_WITH(fixture.Run(source), ContainsSubstring(type) && ContainsSubstring(message));
}

TEST_CASE("Native player geometry bindings preserve radius and rectangle boundaries", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
x, z = _core.get_position()
assert (x,z) == (_core.get_x(),_core.get_z()) and _core.get_level() == 0
assert _core.distance_to(x+3,z-4) == 4
assert _core.distance(x,z,x+3,z-4) == 4
assert _core.in_radius_of(x+3,z-4,4) and not _core.in_radius_of(x+3,z-4,3)
assert _core.at(x,z) and not _core.at(x+1,z)
assert _core.in_rect(x,z,1,1)
assert not _core.in_rect(x-1,z,1,1) and not _core.in_rect(x,z-1,1,1)
assert not _core.in_rect(x,z,0,1) and not _core.in_rect(x,z,1,0)
)python"));
}

TEST_CASE("Native player bindings reflect missing appearance and changed session state", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.state.localPlayer.appearance.reset();
    fixture.state.members = true;
    fixture.state.runEnergy = 73;
    fixture.state.runWeight = -12;
    fixture.state.walkDestination.reset();
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.get_name() is None and _core.get_combat_level() == 0
assert _core.is_placed() and _core.is_members()
assert _core.get_run_energy() == 73 and _core.get_weight() == -12
assert _core.get_walk_destination() is None and not _core.is_moving()
assert _core.is_running()
)python"));
    fixture.state.placed = false;
    fixture.state.members = false;
    fixture.state.varps[173] = 0;
    REQUIRE_NOTHROW(fixture.Run("assert not _core.is_placed() and not _core.is_members() and not _core.is_running()\n"));
}

TEST_CASE("Native hitpoint bindings handle zero base health and boosted health", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.state.stats[3] = Stat_s{.xp = 100, .level = 0, .baseLevel = 0};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.get_hp() == 0 and _core.get_max_hp() == 0 and _core.get_hp_percent() == 0
assert _core.get_current_stat(3) == 0 and _core.get_max_stat(3) == 0 and _core.get_experience(3) == 100
)python"));
    fixture.state.stats[3] = Stat_s{.xp = 1154, .level = 12, .baseLevel = 10};
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_hp() == 12 and _core.get_max_hp() == 10 and _core.get_hp_percent() == 120\n"));
    CHECK_THROWS_WITH(fixture.Run("_core.get_max_stat(-1)"), ContainsSubstring("ValueError"));
    CHECK_THROWS_WITH(fixture.Run("_core.get_experience(25)"), ContainsSubstring("ValueError"));
}

TEST_CASE("Native damage bindings distinguish zero damage and inclusive tick windows", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    fixture.state.localPlayer.hits = {{.damage = 0, .tick = 50}, {.damage = 2, .tick = 46}};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.in_combat()
assert _core.took_damage() and _core.took_damage(4)
assert not _core.took_damage(3) and not _core.took_damage(0)
)python"));
    fixture.state.localPlayer.hits.clear();
    REQUIRE_NOTHROW(fixture.Run("assert not _core.in_combat() and not _core.took_damage()\n"));
    CHECK_THROWS_WITH(fixture.Run("_core.took_damage(-1)"), ContainsSubstring("ValueError"));
    CHECK_THROWS_WITH(fixture.Run("_core.took_damage(1001)"), ContainsSubstring("ValueError"));
    fixture.state.hintArrow = HintArrow_s{.kind = HintArrowKind_e::Player, .index = 20, .tile = Offset(1, 2), .height = 30};
    REQUIRE_NOTHROW(fixture.Run("assert _core.get_hint_arrow() == ('player',20,3201,3202,0,30)\n"));
}

TEST_CASE("Native nearest NPC bindings apply combat filters and return None for misses", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.get_npc(7).name == 'Chicken' and _core.get_npc(9999) is None
assert _core.get_nearest_npc_by_id((41,81), in_combat=True).index == 7
assert _core.get_nearest_npc_by_id((41,81), in_combat=False).index == 8
assert _core.get_nearest_npc_by_name(('Chicken','Cow'), in_combat=False).index == 8
assert _core.get_nearest_npc_by_name('Chicken', reachable=True).index == 7
assert _core.get_nearest_npc_by_id(9999) is None
assert _core.get_nearest_npc_by_name('Missing') is None
assert _core.get_nearest_npc_by_name('Cow', radius=4) is None
assert _core.get_player_by_name('ZEZIMA').index == 20
assert _core.get_player_by_name('Missing') is None
)python"));
    CHECK_THROWS_WITH(fixture.Run("_core.get_nearest_npc_by_id(in_combat=1)"), ContainsSubstring("TypeError") && ContainsSubstring("in_combat must be True or False"));
}

TEST_CASE("Native nearest scenery and ground item bindings preserve filter results", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.get_nearest_ground_item_by_id(526, reachable=True).id == 526
assert _core.get_nearest_ground_item_by_name('Bones').count == 1
assert _core.get_nearest_ground_item_by_id(995) is None
assert _core.get_nearest_ground_item_by_name('Missing') is None
assert _core.get_nearest_ground_item_by_name('Bones', radius=2) is None
assert _core.get_nearest_loc_by_id(1530, layer=0, reachable=True).id == 1530
assert _core.get_nearest_loc_by_name('Tree', layer=2).id == 1276
assert _core.get_nearest_loc_by_id(1276, layer=0) is None
assert _core.get_nearest_loc_by_name('Missing') is None
)python"));
}

TEST_CASE("Native cache lookup bindings expose named types and omit unnamed catalog entries", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.find_type_ids('item','bones') == [526]
assert _core.find_type_ids('npc','CHICKEN') == [41]
assert _core.find_type_ids('loc','tree') == [1276]
assert _core.find_type_ids('item','Missing') == []
assert _core.get_item_type(9999) is None and _core.get_loc_type(9999) is None
catalog = _core.get_item_catalog()
assert [entry[0] for entry in catalog] == [526,995]
assert catalog[0] == (526,'Bones',1,False,False,False,-1,False)
assert catalog[1][1] == 'Coins' and catalog[1][3] is True
)python"));
    CHECK_THROWS_WITH(fixture.Run("_core.find_type_ids('player','Zezima')"), ContainsSubstring("ValueError") && ContainsSubstring("kind must be 'item', 'npc' or 'loc'"));
}

TEST_CASE("Native map bindings distinguish cached scenery from live scene changes", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
x,z = _core.get_position()
assert _core.in_scene(x,z) and not _core.in_scene(x+500,z)
assert _core.square_locs((x-2)//64,(z+3)//64,0) == [((x-2)%64,(z+3)%64,1276,10,0)]
assert _core.square_locs((x-2)//64,(z+3)//64,1) == []
assert _core.square_locs(0,0,0) == []
)python"));
    CHECK_THROWS_WITH(fixture.Run("_core.square_locs(0,0,4)"), ContainsSubstring("ValueError") && ContainsSubstring("level must be from"));
}

TEST_CASE("Native navigation bindings report unavailable world navigation", "[ScriptBindings][WorldBindingCoverage]")
{
    auto fixture = BindingFixture{};
    REQUIRE_NOTHROW(fixture.Run(R"python(
import _core
assert _core.nav_data('edges') is None
assert _core.walk_tile(3200,3200,0) is None
assert _core.find_world_path('{"from":[3200,3200,0],"to":[3201,3201,0]}') is None
assert _core.can_step(3200,3200,3200,3201)
assert not _core.can_step(3200,3200,3200,3202)
)python"));
    CHECK_THROWS_WITH(fixture.Run("_core.find_world_path('{}')"), ContainsSubstring("ValueError") && ContainsSubstring("route request is malformed"));
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

TEST_CASE("Script bindings read game messages since a mark", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.state.messages.push_back({.sequence = 7, .type = MessageType_e::Game, .text = "Welcome to RuneScape."});
    fixture.state.messages.push_back({.sequence = 8, .type = MessageType_e::Public, .sender = "Zezima", .text = "I can't reach that!"});
    fixture.state.messages.push_back({.sequence = 9, .type = MessageType_e::Game, .text = "I can't reach that!"});
    fixture.state.messageCount = 9;
    fixture.Run(R"python(
assert game_messages.mark() == 9
assert [m.seq for m in game_messages.since(0)] == [7, 9]
assert game_messages.saw_since(7, CANT_REACH) and not game_messages.saw_since(9, CANT_REACH)
assert game_messages.first_since(0, lambda text: text.startswith('Welcome')).seq == 7
assert [m.text for m in game_messages.recent(1)] == ["I can't reach that!"]
)python");
}
