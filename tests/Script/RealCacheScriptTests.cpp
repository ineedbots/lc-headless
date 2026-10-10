#include "pch.hpp"
#include "../Cache/RealCache.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../LogCapture.hpp"
#include "ScriptTestRuntime.hpp"

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/State/GameState_s.hpp"
#include "Script/ScriptApi.hpp"
#include "Script/ScriptBindings.hpp"
#include "Script/ScriptVm.hpp"

#include <catch2/catch_test_macros.hpp>

// The standard library's rules for finding things in the side tabs, run against the 289 cache's interfaces.
namespace
{
    constexpr auto COMBAT_UNARMED = s32{5855};
    constexpr auto COMBAT_STABSWORD = s32{2276};
    constexpr auto STABSWORD_SPECIAL_BAR = u16{7562};
    constexpr auto COMBAT_STAFF = s32{328};
    constexpr auto STAFF_SPELLS = s32{1829};
    constexpr auto QUEST_LIST = s32{638};
    constexpr auto PRAYER = s32{5608};
    constexpr auto MAGIC = s32{1151};
    constexpr auto CONTROLS_TAB = std::size_t{11};

    class RealCacheFixture
    {
    public:
        RealCacheFixture()
            : cache{RealCache::RequireShared()}
            , map{cache}
            , client{std::make_shared<const Config_s>(), cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{state, map, actions}
            , vm{ScriptTestRuntime::Get(), {}, capture.GetLogger()}
        {
            auto& tabs = state.interfaces.tabs;
            tabs[0] = COMBAT_UNARMED;
            tabs[2] = QUEST_LIST;
            tabs[5] = PRAYER;
            tabs[6] = MAGIC;
            for (const auto& [id, component] : cache->components)
            {
                if (component.text == "Auto Retaliate" || component.text == "Auto retaliate")
                {
                    tabs[CONTROLS_TAB] = component.root;
                }
            }

            ScriptBindings::Bind(vm, api);
        }

        ~RealCacheFixture()
        {
            ScriptBindings::Unbind(vm);
        }

        RealCacheFixture(const RealCacheFixture&) = delete;
        RealCacheFixture& operator=(const RealCacheFixture&) = delete;

        LogCapture capture;
        std::shared_ptr<const GameCache_s> cache;
        GameState_s state = Fixtures::PlacedState();
        WorldMap map;
        GameClient client;
        GameActions actions;
        ScriptApi api;
        ScriptVm vm;
    };
}

TEST_CASE("The stdlib finds the real cache's combat styles, prayers, spells and quests", "[RealCache]")
{
    auto fixture = RealCacheFixture{};
    fixture.vm.RunSource(R"python(
assert game.combat_styles() == [(0, '(Accurate)'), (1, '(Aggressive)'), (2, '(Defensive)')], game.combat_styles()
assert game.combat_style_mode('strength') == 1
# Unarmed has no controlled style, so it trains defence instead.
resolution = game.combat_style_resolution('controlled')
assert resolution.effective == 'defence' and resolution.mode == 2

from rs2004.tabs import _select_button, spell_button, teleport_button
assert _select_button(172, 0) is not None and _select_button(172, 1) is not None

toggles = [c for c in interfaces.root(interfaces.tab(5)) if c.button == 'toggle']
assert len(toggles) == len(PRAYER_NAMES)
assert len(set([c.varp for c in toggles])) == len(PRAYER_NAMES)
assert prayer.known('Protect from Melee') and prayer._button('thick skin').id == toggles[0].id

assert spell_button('wind strike') != -1 and spell_button('Superheat item') != -1
assert spell_button('Kamehameha') == -1
assert teleport_button('Varrock') != -1 and teleport_button('Cast @gre@Lumbridge teleport') != -1

all_quests = quests.all()
assert len(all_quests) > 10
assert quests.status("Cook's Assistant") == 'not_started', all_quests
assert special.bar_component() == -1
)python", "real_cache.py");
}

TEST_CASE("The stdlib finds the real cache's special attack bar and autocast spells", "[RealCache]")
{
    auto fixture = RealCacheFixture{};
    auto& tabs = fixture.state.interfaces.tabs;
    tabs[0] = COMBAT_STABSWORD;
    fixture.vm.RunSource(R"python(
assert special.bar_component() == -1
assert not autocast.staff_tab_attached()
)python", "hidden_special.py");

    // The bar's layer starts hidden; the server shows it when a weapon with a special is wielded.
    const auto layer = *fixture.cache->FindComponent(STABSWORD_SPECIAL_BAR)->parent;
    fixture.state.interfaces.components[layer].hidden = false;
    fixture.vm.RunSource(R"python(
assert special.bar_component() == 7562
)python", "special.py");

    tabs[0] = COMBAT_STAFF;
    fixture.vm.RunSource(R"python(
assert autocast.staff_tab_attached()
from rs2004.tabs import _select_button_reading
assert _select_button_reading(108) is not None
)python", "staff.py");

    tabs[0] = STAFF_SPELLS;
    fixture.vm.RunSource(R"python(
choices = [c.id for c in interfaces.root(interfaces.tab(0)) if c.button == 'ok']
assert choices[:len(AUTOCAST_SPELLS)] == list(range(1830, 1830 + len(AUTOCAST_SPELLS))), choices
)python", "spells.py");
}

TEST_CASE("The maze random event's route from each spawn ends at the shrine", "[RealCache]")
{
    auto fixture = RealCacheFixture{};
    fixture.vm.RunSource(R"python(
from rs2004.random_solvers import maze_graph, solve_maze_route, MAZE_SHRINE_DOOR
graph = maze_graph()
assert len(graph.walls) > 100 and len(graph.doors) > 10, (len(graph.walls), len(graph.doors))
for spawn in [(2891, 4597), (2933, 4597), (2933, 4555), (2891, 4555)]:
    route = solve_maze_route(graph, spawn)
    assert len(route) > 0, spawn
    assert route[-1] == MAZE_SHRINE_DOOR, (spawn, route)
    # The old goal accepted the tile south of the shrine's corner, through a wall.
    assert (2911, 4574) not in route, (spawn, route)
)python", "maze.py");
}

// Every item, NPC and loc the catalogs name is in the 289 cache, so a table entry that names something the
// cache lacks fails here rather than in a script.
TEST_CASE("The catalogs name only items, NPCs and locs the real cache has", "[RealCache]")
{
    auto fixture = RealCacheFixture{};
    fixture.vm.RunSource(R"python(
from rs2004.catalogs import tools, tool_acquire, fishing, mining, gathering, tables

items = set()
for tier in tools.PICKAXES + tools.AXES:
    items.add(tier.name)
for name in [tools.TINDERBOX, tools.HAMMER, tools.KNIFE, tools.CHISEL, tools.NEEDLE, tool_acquire.COINS, mining.BROKEN_PICKAXE]:
    items.add(name)
for name in fishing.ALL_FISHING_GEAR_NAMES + list(tool_acquire.AXE_BAR_FOR.values()) + list(tables.LOG_LEVELS.keys()):
    items.add(name)
for herb in tables.HERBS:
    items.add(herb.name)
for route in tables.RUNES.values():
    items.add(route.rune)
    items.add(route.talisman)
items.add(gathering.SHILO_WATER_VENDOR.item)

npcs = set()
for vendor in [tool_acquire.BOB_VENDOR, tool_acquire.NURMOF_VENDOR, tool_acquire.GERRANT_VENDOR, tool_acquire.HARRY_VENDOR]:
    npcs.add(vendor.keeper)
for name in tables.PICKPOCKET_TARGET_NAMES + tables.ARDOUGNE_PICKPOCKET_TARGETS:
    npcs.add(name)
for loc in gathering.FISHING_LOCATIONS:
    if loc.bait_vendor is not None:
        npcs.add(loc.bait_vendor.keeper)
        items.add(loc.bait_vendor.item)
npcs.add(gathering.SHILO_WATER_VENDOR.keeper)

loc_names = set([tool_acquire.NURMOF_VENDOR.hop_loc, 'Range'])
for loc in gathering.FISHING_LOCATIONS + gathering.MINING_LOCATIONS + gathering.WOODCUTTING_LOCATIONS:
    if loc.booth_name is not None:
        loc_names.add(loc.booth_name)
    if loc.range_name is not None:
        loc_names.add(loc.range_name)
for surface in tables.COOKING_SURFACE_LOCS:
    loc_names.add(surface.name)

missing = [('item', n) for n in items if not reader.item_ids(n)]
missing += [('npc', n) for n in npcs if not reader.npc_ids(n)]
missing += [('loc', n) for n in loc_names if not reader.loc_ids(n)]
assert missing == [], sorted(missing)
assert reader.item_ids('logs') == reader.item_ids('Logs') and len(reader.item_ids('Logs')) > 0

from rs2004.catalogs import Loadout, CarryEntry, food_of
assert food_of(Loadout('melee', {}, [CarryEntry('Prayer potion(4)', 2), CarryEntry('Lobster', 10)]), 'Trout') == 'Lobster'
)python", "catalog_names.py");
}
