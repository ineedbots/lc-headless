# Ported from rs2b0t's test/api/acquisition/Tools.test.ts, woodcutting-axes.test.ts, ToolAcquire.test.ts,
# test/data/fishing-methods.test.ts and mining-rocks.test.ts (MIT, see third_party/rs2b0t).

from rs2004.catalogs.tools import AXES, PICKAXES, TINDERBOX, axe_req, best_axe, best_from_tiers, best_pickaxe
from rs2004.catalogs.tools import can_wield_tool, exact_tool, has_all_tools, missing_tool_labels, pickaxe_req
from rs2004.catalogs.tools import tinderbox_req, tool_attack_level, tool_keep_names, tool_kit_label, tool_restock_plan
from rs2004.catalogs.tools import tools_needing_equip, surplus_held_tool_names, best_held_tool_names
from rs2004.catalogs.tools import bank_has_better_gather_tool
from rs2004.catalogs.tool_acquire import AXE_BAR_FOR, BOB_VENDOR, BROKEN_AXE, GERRANT_VENDOR, HARRY_VENDOR
from rs2004.catalogs.tool_acquire import NURMOF_VENDOR, AcquireWorld, acquire_keep_names, best_affordable_shop_tier
from rs2004.catalogs.tool_acquire import best_owned_tier, best_smithable_axe, can_fund_plan, coins_to_withdraw
from rs2004.catalogs.tool_acquire import parse_tool_acquire_mode, pickaxe_shop_offers, plan_axe_acquire
from rs2004.catalogs.tool_acquire import plan_broken_tool_repair, buy_plans_cost, fishing_gear_shop_cart
from rs2004.catalogs.tool_acquire import plan_fishing_gear_acquire, plan_fishing_gear_buys, plan_gather_tool_acquire
from rs2004.catalogs.tool_acquire import plan_pickaxe_acquire, needs_tool_vendor_surface_hop
from rs2004.catalogs.mining import BROKEN_PICKAXE, GAS_ROCK_IDS, ROCK_OPTIONS, ROCK_TIER_ORDER, ROCK_TYPES
from rs2004.catalogs.mining import resolve_rock_ids, rock_tier_by_id
from rs2004.catalogs.fishing import ALL_FISHING_GEAR_NAMES, FISHING_METHODS, FISHING_METHOD_OPTIONS, WHIRLPOOL_IDS
from rs2004.catalogs.fishing import fishing_restock_plan, gear_keep_names, gear_label, has_fishing_gear
from rs2004.catalogs.fishing import missing_fishing_gear, resolve_fish_method, spot_matches_method
from rs2004.geometry import Tile


def holding(names):
    return lambda name: 1 if name in names else 0


def lvl(skill):
    if skill == 'mining' or skill == 'woodcutting':
        return 41
    return 40 if skill == 'attack' else 1


def test_tiers_are_best_first():
    for tiers in [PICKAXES, AXES]:
        for i in range(1, len(tiers)):
            assert tiers[i - 1].level >= tiers[i].level
    for tier in AXES:
        assert tier.level == 1


def test_the_best_tool_respects_the_skill_gate_and_axes_have_none():
    assert best_pickaxe(41, lambda n: n == 'Rune pickaxe') == 'Rune pickaxe'
    assert best_pickaxe(40, lambda n: n in ['Rune pickaxe', 'Adamant pickaxe']) == 'Adamant pickaxe'
    assert best_pickaxe(20, lambda n: n in ['Rune pickaxe', 'Adamant pickaxe', 'Mithril pickaxe', 'Steel pickaxe']) == 'Steel pickaxe'
    assert best_pickaxe(5, lambda n: n in ['Steel pickaxe', 'Iron pickaxe']) == 'Iron pickaxe'
    assert best_axe(20, lambda n: n in ['Rune axe', 'Steel axe', 'Bronze axe']) == 'Rune axe'
    assert best_axe(1, lambda n: n in ['Rune axe', 'Adamant axe']) == 'Rune axe'
    assert best_axe(99, lambda n: False) is None
    available = lambda n: n == 'Mithril pickaxe' or n == 'Bronze pickaxe'
    assert best_from_tiers(41, PICKAXES, available) == best_pickaxe(41, available)


def test_the_keep_list_names_every_tier_and_exact_tool():
    names = tool_keep_names([pickaxe_req(), tinderbox_req()])
    assert 'Rune pickaxe' in names and 'Bronze pickaxe' in names and TINDERBOX in names


def test_a_kit_is_whole_only_with_every_tool():
    reqs = [axe_req(), tinderbox_req()]
    none = lambda n: 0
    assert not has_all_tools(reqs, lvl, none)
    assert sorted(missing_tool_labels(reqs, lvl, none)) == sorted(['axe', TINDERBOX])
    held = holding(['Rune axe', TINDERBOX])
    assert has_all_tools(reqs, lvl, held)
    label = tool_kit_label(reqs, lvl, held)
    assert 'Rune axe' in label and TINDERBOX in label


def test_the_restock_plan_takes_the_best_banked_tier_and_missing_exact_tools():
    reqs = [pickaxe_req(), exact_tool(TINDERBOX)]
    plan = tool_restock_plan(reqs, lvl, lambda n: 0, holding(['Adamant pickaxe', 'Bronze pickaxe', TINDERBOX]))
    assert [p.name for p in plan] == ['Adamant pickaxe', TINDERBOX]
    assert plan[0].equip

    reqs = [axe_req(), tinderbox_req()]
    assert tool_restock_plan(reqs, lvl, holding(['Rune axe', TINDERBOX]), holding(['Rune axe', TINDERBOX])) == []

    plan = tool_restock_plan([axe_req(True), tinderbox_req()], lvl, holding(['Bronze axe']), holding(['Steel axe', 'Bronze axe', TINDERBOX]))
    assert [p.name for p in plan] == ['Steel axe', TINDERBOX]
    assert tool_restock_plan([axe_req(True)], lvl, holding(['Steel axe']), holding(['Steel axe', 'Bronze axe'])) == []
    assert bank_has_better_gather_tool([axe_req(True)], lvl, holding(['Bronze axe']), holding(['Steel axe']))
    assert not bank_has_better_gather_tool([axe_req(True)], lvl, holding(['Steel axe']), holding(['Bronze axe']))


def test_tools_are_wielded_only_when_marked_and_attack_allows():
    count = holding(['Rune axe', TINDERBOX])
    assert tools_needing_equip([axe_req(True), tinderbox_req()], lvl, count, lambda n: False) == ['Rune axe']
    assert tools_needing_equip([axe_req(True), tinderbox_req()], lvl, count, lambda n: n == 'Rune axe') == []
    assert tools_needing_equip([axe_req(False), tinderbox_req()], lvl, count, lambda n: False) == []
    rune = holding(['Rune pickaxe'])
    assert tools_needing_equip([pickaxe_req(True)], lambda s: 90 if s == 'mining' else 1, rune, lambda n: False) == []
    assert tools_needing_equip([pickaxe_req(True)], lambda s: 90 if s == 'mining' else 40, rune, lambda n: False) == ['Rune pickaxe']


def test_wielding_follows_the_metal_attack_gates():
    assert tool_attack_level('Rune pickaxe') == 40 and tool_attack_level('Adamant axe') == 30
    assert tool_attack_level('Steel pickaxe') == 5 and tool_attack_level('Bronze axe') == 1
    assert not can_wield_tool('Rune pickaxe', 39) and can_wield_tool('Rune pickaxe', 40)
    assert not can_wield_tool('Mithril axe', 19) and can_wield_tool('Mithril axe', 20)


def test_worse_tiers_held_beside_the_best_are_surplus():
    count = holding(['Steel axe', 'Bronze axe', TINDERBOX])
    assert surplus_held_tool_names([axe_req(), tinderbox_req()], lvl, count) == ['Bronze axe']
    assert best_held_tool_names([axe_req(), tinderbox_req()], lvl, count) == ['Steel axe', TINDERBOX]


def world(levels=None, held=None, bank=None):
    levels = levels or {}
    held = held or {}
    bank = bank or {}
    return AcquireWorld(lambda s: levels.get(s, 1), lambda n: held.get(n, 0), lambda n: held.get(n, 0),
                        lambda n: bank.get(n, 0), lambda n: False)


def test_the_acquire_setting_reads_buy_and_repair():
    assert parse_tool_acquire_mode('Off') == 'off'
    assert parse_tool_acquire_mode('Buy / repair') == 'on'
    assert parse_tool_acquire_mode('buy/repair') == 'on'
    assert parse_tool_acquire_mode(True) == 'on'
    assert parse_tool_acquire_mode(None) == 'off'


def test_a_missing_pickaxe_is_the_best_affordable_one():
    plan = plan_pickaxe_acquire(world({'mining': 41}, bank={'Coins': 5000}))
    assert plan.kind == 'buy' and plan.name == 'Adamant pickaxe' and plan.cost == 3200
    assert plan.vendor.keeper == NURMOF_VENDOR.keeper and plan.equip
    assert plan_pickaxe_acquire(world({'mining': 41}, bank={'Coins': 10})).name == 'Bronze pickaxe'
    assert plan_pickaxe_acquire(world({'mining': 41}, bank={'Coins': 0})) is None


def test_an_owned_pickaxe_is_upgraded_only_when_asked():
    w = world({'mining': 41}, held={'Bronze pickaxe': 1}, bank={'Coins': 50000})
    assert plan_pickaxe_acquire(w, False) is None
    plan = plan_pickaxe_acquire(w, True)
    assert plan.name == 'Rune pickaxe' and 'upgrade' in plan.reason


def test_a_broken_tool_is_repaired_before_anything_is_bought():
    plan = plan_pickaxe_acquire(world({'mining': 41}, held={BROKEN_PICKAXE: 1}, bank={'Coins': 50000}), True)
    assert plan.kind == 'repair' and plan.vendor.keeper == 'Nurmof' and plan.broken_name == BROKEN_PICKAXE
    plan = plan_broken_tool_repair(lambda n: n == BROKEN_AXE)
    assert plan.kind == 'repair' and plan.vendor.keeper == 'Bob'


def test_an_axe_is_bought_from_bob_or_smithed_whichever_is_better():
    plan = plan_axe_acquire(world({'woodcutting': 21, 'smithing': 1}, bank={'Coins': 500}))
    assert plan.kind == 'buy' and plan.name == 'Steel axe' and plan.vendor.keeper == BOB_VENDOR.keeper and plan.cost == 200
    plan = plan_axe_acquire(world({'woodcutting': 41, 'smithing': 51}, bank={'Mithril bar': 1, 'Hammer': 1}))
    assert plan.kind == 'smith' and plan.name == 'Mithril axe' and plan.bar == 'Mithril bar'
    plan = plan_axe_acquire(world({'woodcutting': 41, 'smithing': 51}, bank={'Mithril bar': 1, 'Hammer': 1, 'Coins': 500}))
    assert plan.kind == 'smith' and plan.name == 'Mithril axe'


def test_feathers_come_from_gerrant_even_beside_harry():
    method = resolve_fish_method('Fly fishing — trout/salmon')
    plan = plan_fishing_gear_acquire(method, world(held={'Fly fishing rod': 1}, bank={'Coins': 500}), Tile(2846, 3429, 0))
    assert plan.name.lower() == 'feather' and plan.vendor.keeper == GERRANT_VENDOR.keeper


def test_other_fishing_gear_comes_from_the_nearer_shop():
    plan = plan_fishing_gear_acquire(resolve_fish_method('Bait rod — sardine/herring'), world(held={'Fishing rod': 1}, bank={'Coins': 500}))
    assert plan.name.lower() == 'fishing bait' and plan.vendor.keeper == HARRY_VENDOR.keeper
    plan = plan_fishing_gear_acquire(resolve_fish_method('Lobster cage — lobster'), world(bank={'Coins': 100}), Tile(2846, 3429, 0))
    assert plan.name == 'Lobster pot' and plan.vendor.keeper == HARRY_VENDOR.keeper
    assert (plan.vendor.stand.x, plan.vendor.stand.z) == (2833, 3443)
    plan = plan_fishing_gear_acquire(resolve_fish_method('Small net — shrimp/anchovy'), world(bank={'Coins': 50}), Tile(3086, 3231, 0))
    assert plan.name == 'Small fishing net' and plan.vendor.keeper == GERRANT_VENDOR.keeper


def test_bait_is_bought_up_to_the_target():
    method = resolve_fish_method('Bait rod — sardine/herring')
    plan = plan_fishing_gear_acquire(method, world(held={'Fishing rod': 1, 'Fishing bait': 10}, bank={'Coins': 2000}), Tile(2846, 3429, 0), 50)
    assert plan.name == 'Fishing bait' and plan.qty == 40 and plan.cost == 120 and plan.vendor.keeper == HARRY_VENDOR.keeper
    assert plan_fishing_gear_acquire(method, world(held={'Fishing rod': 1, 'Fishing bait': 5}, bank={'Fishing bait': 200, 'Coins': 2000}), None, 100) is None


def test_a_fly_rod_and_feathers_are_one_cart():
    method = resolve_fish_method('Fly fishing — trout/salmon')
    buys = plan_fishing_gear_buys(method, world(bank={'Coins': 3000}), Tile(3013, 3224, 0), 50)
    assert [(b.name, b.qty, b.cost, b.vendor.keeper) for b in buys] == [('Fly fishing rod', 1, 5, 'Gerrant'), ('Feather', 50, 100, 'Gerrant')]
    assert buy_plans_cost(buys) == 105
    cart = fishing_gear_shop_cart(method, world(bank={'Coins': 3000}), Tile(3013, 3224, 0), 50)
    assert [p.name.lower() for p in cart] == ['fly fishing rod', 'feather']
    assert fishing_gear_shop_cart(method, world(bank={'Coins': 0}), None, 50) == []
    assert plan_fishing_gear_acquire(method, world(bank={'Coins': 3000}), None, 50).name == 'Fly fishing rod'


def test_shop_tiers_and_smithable_axes():
    assert best_owned_tier(41, PICKAXES, holding(['Steel pickaxe'])) == 'Steel pickaxe'
    assert best_affordable_shop_tier(41, PICKAXES, pickaxe_shop_offers(), 4000, 'Steel pickaxe').name == 'Adamant pickaxe'
    assert best_smithable_axe(41, 51, None, lambda b: 1 if b == 'Mithril bar' else 0, True)[0] == 'Mithril axe'
    assert best_smithable_axe(41, 51, None, lambda b: 1, False) is None
    assert best_smithable_axe(5, 1, None, lambda b: 1 if b == 'Bronze bar' else 0, True)[0] == 'Bronze axe'
    assert best_smithable_axe(5, 51, None, lambda b: 1 if b == 'Mithril bar' else 0, True)[0] == 'Mithril axe'
    assert best_smithable_axe(41, 50, None, lambda b: 1 if b == 'Mithril bar' else 0, True) is None


def test_funding_and_what_a_deposit_keeps():
    assert coins_to_withdraw(500, 100) == 400 and coins_to_withdraw(100, 200) == 0
    buy = plan_pickaxe_acquire(world({'mining': 1}, bank={'Coins': 10}))
    assert can_fund_plan(buy, 0, 10) and not can_fund_plan(buy, 0, 0)
    assert 'Coins' in acquire_keep_names(buy)
    assert BROKEN_PICKAXE in acquire_keep_names(plan_broken_tool_repair(lambda n: n == BROKEN_PICKAXE))
    smith = plan_axe_acquire(world({'woodcutting': 41, 'smithing': 86}, held={'Hammer': 1, 'Runite bar': 1}))
    assert smith.kind == 'smith' and smith.bar == 'Runite bar'
    keep = acquire_keep_names(smith)
    assert 'Coins' in keep and 'Runite bar' in keep and 'Hammer' in keep
    assert AXE_BAR_FOR['Rune axe'] == 'Runite bar'


def test_gathering_requirements_route_to_the_right_planner():
    assert plan_gather_tool_acquire([pickaxe_req()], world({'mining': 6}, bank={'Coins': 200})).name == 'Iron pickaxe'
    assert plan_gather_tool_acquire([axe_req()], world({'woodcutting': 1}, bank={'Coins': 20})).name == 'Bronze axe'


def test_nurmof_is_reached_through_the_trapdoor_from_above_ground():
    assert NURMOF_VENDOR.hop_from.x == 3019 and NURMOF_VENDOR.hop_loc == 'Trapdoor' and NURMOF_VENDOR.stand.z == 9844
    assert needs_tool_vendor_surface_hop(NURMOF_VENDOR, Tile(3013, 3355, 0))
    assert not needs_tool_vendor_surface_hop(NURMOF_VENDOR, Tile(3000, 9840, 0))
    assert not needs_tool_vendor_surface_hop(BOB_VENDOR, Tile(3013, 3355, 0))


def test_fishing_methods_tell_spots_apart_by_their_pair():
    small = resolve_fish_method('Small net — shrimp/anchovy')
    big = resolve_fish_method('Big net — mackerel/cod/bass')
    assert (small.op, small.pair, big.op, big.pair) == ('Net', 'Bait', 'Net', 'Harpoon')
    assert resolve_fish_method('Bait rod — sardine/herring').pair == 'Net'
    assert resolve_fish_method('Bait rod — pike').pair == 'Lure'
    tuna = resolve_fish_method('Harpoon — tuna/swordfish')
    shark = resolve_fish_method('Harpoon — sharks')
    assert spot_matches_method(['Cage', 'Harpoon'], tuna) and not spot_matches_method(['Net', 'Harpoon'], tuna)
    assert spot_matches_method(['Net', 'Harpoon'], shark) and not spot_matches_method(['Cage', 'Harpoon'], shark)
    lobster = resolve_fish_method('Lobster cage — lobster')
    assert spot_matches_method(['harpoon', 'cage'], lobster) and not spot_matches_method(['Cage'], lobster)
    oily = resolve_fish_method('Oily rod — lava eel')
    assert oily.pair == '' and [g.name for g in oily.gear] == ['Oily fishing rod', 'Fishing bait']
    assert spot_matches_method(['Bait'], oily) and spot_matches_method(['Net', 'Bait'], oily) and not spot_matches_method(['Net'], oily)
    assert resolve_fish_method('nonsense') is FISHING_METHODS[0]


def test_every_method_is_well_formed():
    ops = ['Net', 'Bait', 'Lure', 'Cage', 'Harpoon']
    for method in FISHING_METHODS:
        assert method.op in ops, method.name
        assert method.pair == '' or (method.pair in ops and method.pair != method.op), method.name
        assert len(method.gear) > 0
        for piece in method.gear:
            assert piece.min > 0 and piece.restock >= piece.min
    assert len(FISHING_METHOD_OPTIONS) == len(FISHING_METHODS)
    for name in ['Small fishing net', 'Harpoon', 'Fishing bait', 'Oily fishing rod']:
        assert name in ALL_FISHING_GEAR_NAMES
    for id in [403, 404, 405, 406]:
        assert id in WHIRLPOOL_IDS


def test_fishing_gear_helpers():
    rod = resolve_fish_method('Bait rod — sardine/herring')
    assert gear_keep_names(rod) == ['Fishing rod', 'Fishing bait']
    assert gear_label(rod) == 'Fishing rod + Fishing bait'
    assert not has_fishing_gear(rod, holding(['Fishing rod']))
    assert [g.name for g in missing_fishing_gear(rod, holding(['Fishing rod']))] == ['Fishing bait']
    assert has_fishing_gear(rod, lambda n: 1)
    assert fishing_restock_plan(rod, holding(['Fishing rod']), lambda n: 250 if n == 'Fishing bait' else 0) == [('Fishing bait', 100)]
    assert fishing_restock_plan(rod, lambda n: 100, lambda n: 50) == []


def test_rocks_are_two_ids_each_in_one_block_by_tier():
    all_ids = []
    for name in ROCK_OPTIONS:
        assert len(ROCK_TYPES[name]) == 2, name
        all_ids.extend(ROCK_TYPES[name])
    assert sorted(all_ids) == list(range(2090, 2110))
    assert ROCK_TIER_ORDER == ['Clay', 'Copper', 'Tin', 'Iron', 'Silver', 'Coal', 'Gold', 'Mithril', 'Adamantite', 'Runite']
    for id in all_ids:
        assert id not in GAS_ROCK_IDS
    assert rock_tier_by_id(2106) == 9 and rock_tier_by_id(2106) > rock_tier_by_id(2096) and rock_tier_by_id(2096) > rock_tier_by_id(2092)
    for name in ROCK_OPTIONS:
        assert rock_tier_by_id(ROCK_TYPES[name][1]) == rock_tier_by_id(ROCK_TYPES[name][0])
    assert rock_tier_by_id(450) == -1


def test_rock_names_resolve_without_regard_to_case():
    assert sorted(resolve_rock_ids(['iron', 'COAL'])) == [2092, 2093, 2096, 2097]
    assert resolve_rock_ids(['granite', '']) == [] and resolve_rock_ids([]) == []
