#include "pch.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../LogCapture.hpp"
#include "ScriptTestRuntime.hpp"

#include "Core/ConfigFile.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
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

    // Python asserts check the values, so a failure's traceback names the line that failed.
    class BindingFixture
    {
    public:
        BindingFixture()
            : client{std::make_shared<const Config_s>(), FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{state, actions}
            , vm{ScriptTestRuntime::Get(), {}, capture.GetLogger()}
        {
            BuildState();
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
        GameState_s state = Fixtures::PlacedState();
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
            state.inventories[ScriptApi::INVENTORY] = Inventory_s{.com = ScriptApi::INVENTORY, .slots = {{.id = 995, .count = 250}, {}, {.id = 526, .count = 1}}};
            state.stats[3] = Stat_s{.xp = 1154, .level = 5, .baseLevel = 10};
            state.varps[173] = 1;
            state.interfaces.mainModal = 5292;
            state.interfaces.components[2458].text = "Click here to logout";
            state.social.friends = {{.name37 = Base37::Encode("zezima"), .name = "Zezima", .world = 2}};
            state.social.ignores = {Base37::Encode("spammer")};
        }
    };
}

TEST_CASE("Script bindings read the local player and the area", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
assert get_tick() == 50
assert get_x() == get_position()[0] and get_z() == get_position()[1] and get_level() == 0
assert get_pid() == 5 and get_name() == 'Bot' and get_combat_level() == 3
assert is_moving() and get_walk_destination() == (get_x() + 4, get_z() + 4)
assert is_running() and not in_combat()
assert get_local_player().name == 'Bot'
assert get_current_stat(HITPOINTS) == 5 and get_max_stat(HITPOINTS) == 10 and get_experience(3) == 1154
assert get_hp() == 5 and get_max_hp() == 10 and get_hp_percent() == 50
assert distance_to(get_x() + 3, get_z() - 7) == 7
assert distance(10, 10, 13, 6) == 4
assert in_radius_of(get_x() + 2, get_z() + 2, 2) and not in_radius_of(get_x() + 3, get_z(), 2)
assert in_rect(get_x(), get_z(), 1, 1) and not in_rect(get_x() + 1, get_z(), 5, 5)
assert at(get_x(), get_z()) and not at(get_x() + 1, get_z())
)python");
}

TEST_CASE("Script bindings return NPCs, players and things on the ground as objects", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
npcs = get_npcs()
assert len(npcs) == 2 and isinstance(npcs[0], Npc)
chicken = get_nearest_npc_by_id(41)
assert chicken.index == 7 and chicken.id == 41 and chicken.x == get_x() + 2 and chicken.level == 0
assert chicken.hp == 2 and chicken.max_hp == 3 and chicken.last_hit_tick == 49
assert chicken.target == ('player', 5)
assert chicken.in_combat() and not chicken.is_moving()
assert get_nearest_npc_by_id([41, 81], radius=2).index == 7
assert get_nearest_npc_by_id(41, in_combat=False) is None
assert get_nearest_npc_by_id(81).hp is None and get_nearest_npc_by_id(81).target is None
assert get_nearest_npc_by_id(999) is None
assert [n.index for n in get_npcs(ids=81)] == [8]
assert get_npc(8).id == 81 and get_npc(9) is None
assert 'Npc(index=7' in repr(chicken)

players = get_players()
assert len(players) == 1 and players[0].name == 'Zezima' and players[0].combat_level == 126
assert get_player_by_name('zezima').index == 20 and get_player_by_name('nobody') is None
assert get_players(radius=0) == []

bones = get_nearest_ground_item_by_id(526)
assert isinstance(bones, GroundItem) and bones.count == 1 and bones.x == get_x() + 3
assert get_ground_items(ids=[1, 2]) == []

door = get_loc_at(get_x() + 1, get_z())
assert door.id == 1530 and door.layer == LAYER_WALL and door.angle == 2
assert get_loc_at(get_x() + 1, get_z(), LAYER_GROUND) is None
)python");
}

TEST_CASE("Script bindings read inventories, interfaces, varps and social lists", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
items = get_inventory()
assert [(i.id, i.slot) for i in items] == [(995, 0), (526, 2)] and isinstance(items[0], Item)
assert items[0].com == INVENTORY and items[0].count == 250
assert get_inventory_count_by_id(995) == 250 and get_inventory_count_by_id([995, 526]) == 251
assert get_inventory_item_by_id(526).slot == 2 and get_inventory_item_by_id(1) is None
assert get_empty_slots() == INVENTORY_SIZE - 2 and not is_inventory_full()
assert get_equipment() == [] and get_inventory(BANK) == []

assert get_main_modal() == 5292 and get_side_modal() == -1 and get_chat_modal() == -1
assert is_interface_open(5292) and not is_interface_open(1)
assert get_component_text(2458) == 'Click here to logout' and get_component_text(1) is None
assert not is_count_dialog_open()
assert get_varp(173) == 1 and get_varp(1) == 0
assert get_friends() == [('Zezima', 2)] and get_ignores() == ['Spammer']
)python");
}

TEST_CASE("Script bindings check argument types and ranges", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};

    CHECK_THROWS_WITH(fixture.Run("get_npcs(ids='chicken')\n"), ContainsSubstring("TypeError") && ContainsSubstring("ids must be an int, a list of ints or None"));
    CHECK_THROWS_WITH(fixture.Run("get_nearest_npc_by_id(41, radius='far')\n"), ContainsSubstring("TypeError"));
    CHECK_THROWS_WITH(fixture.Run("attack_npc('chicken')\n"), ContainsSubstring("TypeError") && ContainsSubstring("npc must be a Npc or its index"));
    CHECK_THROWS_WITH(fixture.Run("interact_npc(7, 6)\n"), ContainsSubstring("ValueError") && ContainsSubstring("op must be from 1 to 5"));
    CHECK_THROWS_WITH(fixture.Run("get_current_stat(25)\n"), ContainsSubstring("ValueError"));
    CHECK_THROWS_WITH(fixture.Run("walk_to(1, 2, run=1)\n"), ContainsSubstring("TypeError") && ContainsSubstring("run must be True or False"));
    CHECK_THROWS_WITH(fixture.Run("walk_path([(1, 2), (3,)])\n"), ContainsSubstring("TypeError") && ContainsSubstring("(x, z) pairs"));
    CHECK_THROWS_WITH(fixture.Run("drop_item(get_nearest_ground_item_by_id(526))\n"), ContainsSubstring("TypeError") && ContainsSubstring("item must be an Item"));
}

TEST_CASE("Script bindings report actions on targets that are gone, and need a session to send", "[ScriptBindings]")
{
    auto fixture = BindingFixture{};
    fixture.Run(R"python(
assert attack_npc(99) is False and interact_player(99, 1) is False
gone = get_nearest_ground_item_by_id(526)
)python");

    fixture.state.groundItems.clear();
    fixture.Run("assert take_ground_item(gone) is False\n");
    CHECK_THROWS_WITH(fixture.Run("drop_item(get_inventory()[0])\n"), ContainsSubstring("RuntimeError") && ContainsSubstring("not in game"));
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
