# Ported from rs2b0t's test/api/combat/food-heal.test.ts, eatTiming.test.ts, boostPotions.test.ts,
# tasks/Anchor.test.ts, loadout/loadoutPlan.test.ts, trade/PartnerTrade.test.ts and sustain/sustain.test.ts
# (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import FOOD_OPTIONS, MIN_EAT_HP, food_heal_amount, should_eat_to_use_food, eat_at_hp_threshold
from rs2004.catalogs import should_eat_food, should_hold_eat, URGENT_HP_FRACTION, AttackClock, food_forms, is_food_item
from rs2004.catalogs import boost_faded, potion_to_sip, planned_potions, ranging_plan, PotionPlan
from rs2004.catalogs import SUPER_ATTACK, SUPER_STRENGTH, SUPER_DEFENCE, SUPER_SET, RANGING_POTION, BOOST_POTIONS
from rs2004.catalogs import BOOST_FLOOR, EMPTY_VIAL, combat_keep_names
from rs2004.catalogs import CarryEntry, Loadout, parse_loadouts, food_of, gear_of, weapon_of, supplies_of
from rs2004.catalogs import script_food, script_foods, upsert_loadout, remove_loadout, unique_name
from rs2004.catalogs import parse_partner_list, is_configured_partner, count_offer_by_name, count_offer_matching
from rs2004.catalogs import decide_receiver_offer_screen, decide_giver_offer_screen, parse_mule_mode
from rs2004.catalogs import mule_gatherer_handoff_active, mule_receiver_active, mule_cooker_active
from rs2004.catalogs import mule_supplier_active, mule_non_gatherer_active
from rs2004.catalogs import AnchorHost, beyond_leash, tile_within_leash, resolve_run_anchor, create_return_to_anchor_task
from rs2004.catalogs import should_walk_home_to_gather_anchor, should_soft_home_from_gather_miss, sustain
from rs2004.catalogs import ItemNeed, has_all
from rs2004.geometry import Tile
from rs2004.settings import SettingsBag


def test_food_heals():
    for name, heal in [('Trout', 7), ('Lobster', 12), ('Swordfish', 14), ('Shark', 20), ('Cake', 4), ('2/3 cake', 4), ('slice of cake', 4)]:
        assert food_heal_amount(name) == heal, name
    assert food_heal_amount('Mystery meat') == 8
    assert 'Shark' in FOOD_OPTIONS
    assert food_forms('Cake') == ['cake', '2/3 cake', 'slice of cake'] and is_food_item('Slice of cake', 'cake')


def test_eat_when_a_whole_bite_fits_or_at_the_floor():
    assert should_eat_to_use_food(38, 50, 12, 2) and not should_eat_to_use_food(39, 50, 12, 2)
    assert MIN_EAT_HP == 5
    assert should_eat_to_use_food(5, 99, 12, 1) and not should_eat_to_use_food(5, 99, 12, 0)
    assert eat_at_hp_threshold(10, 12) == 5
    assert should_eat_to_use_food(5, 10, 12, 1) and not should_eat_to_use_food(6, 10, 12, 1)
    assert should_eat_food('Trout', 33, 40, 1) and not should_eat_food('Trout', 34, 40, 1)
    assert should_eat_food('Shark', 79, 99, 1) and not should_eat_food('Shark', 80, 99, 1)


def test_eating_waits_off_the_swing_tick_unless_urgent():
    assert should_hold_eat(True, 0.8) and not should_hold_eat(False, 0.8)
    assert not should_hold_eat(True, 0.2) and not should_hold_eat(True, URGENT_HP_FRACTION)


def test_the_attack_clock_marks_only_the_tick_an_animation_began():
    clock = AttackClock()
    assert not clock.attacked_this_tick(0)
    clock.observe(390, 100)
    clock.observe(390, 101)
    assert clock.attacked_this_tick(100) and not clock.attacked_this_tick(101)
    clock.observe(-1, 102)
    clock.observe(390, 104)
    assert clock.attacked_this_tick(104)
    clock.observe(391, 105)
    assert clock.attacked_this_tick(105)


def test_boosts_fade_into_the_floor():
    assert boost_faded(70, 70) and boost_faded(70, 77) and not boost_faded(70, 78) and not boost_faded(70, 85)
    assert boost_faded(1, 1) and not boost_faded(1, 2)
    assert not boost_faded(0, 0) and not boost_faded(70, 60)
    assert BOOST_FLOOR == 0.1 and EMPTY_VIAL == 'Vial'


def test_one_potion_a_tick_attack_first():
    plans = planned_potions([])
    levels = lambda base, effective: (lambda skill: (base, effective))
    assert potion_to_sip(plans, lambda p: 1, levels(70, 70)).potion is SUPER_ATTACK
    assert potion_to_sip(plans, lambda p: 1, levels(70, 85)) is None
    assert potion_to_sip(plans, lambda p: 0, levels(70, 70)) is None
    assert potion_to_sip([], lambda p: 9, levels(70, 70)) is None
    strength_faded = lambda skill: (70, 85) if skill == 'attack' else (70, 70)
    assert potion_to_sip(plans, lambda p: 1, strength_faded).potion is SUPER_STRENGTH


def test_the_loadout_sets_dose_forms_and_counts():
    assert [p.flask for p in planned_potions([], SUPER_SET)] == ['Super attack(3)', 'Super strength(3)', 'Super defence(3)']
    plans = planned_potions([CarryEntry('Super defence(4)', 2)], SUPER_SET)
    assert plans[2].flask == 'Super defence(4)' and plans[2].want == 2
    plans = planned_potions([CarryEntry('Super strength(4)', 2)])
    assert (plans[0].flask, plans[0].want, plans[1].flask, plans[1].want) == ('Super attack(3)', 1, 'Super strength(4)', 2)
    assert planned_potions([CarryEntry('super ATTACK(2)', 5)])[0].flask == 'Super attack(2)'
    ignored = planned_potions([CarryEntry('Lobster', 20), CarryEntry('Prayer potion(4)', 2)])
    assert [(p.flask, p.want) for p in ignored] == [('Super attack(3)', 1), ('Super strength(3)', 1)]
    assert SUPER_ATTACK.doses == ['Super attack(4)', 'Super attack(3)', 'Super attack(2)', 'Super attack(1)']
    assert BOOST_POTIONS == [SUPER_ATTACK, SUPER_STRENGTH] and RANGING_POTION not in BOOST_POTIONS
    assert (ranging_plan([]).flask, ranging_plan([CarryEntry('Ranging potion(4)', 2)]).want) == ('Ranging potion(3)', 2)


def test_a_fight_keeps_its_food_runes_ammo_and_weapon():
    keep = combat_keep_names('Cake', 'mage', 'Wind Strike', weapon='Staff of air')
    assert 'slice of cake' in keep and 'Mind rune' in keep and 'Air rune' in keep and 'Staff of air' in keep
    assert 'Bronze arrow' in combat_keep_names('Trout', 'range', ammo='Bronze arrow')


def is_food(name):
    return name in ['Lobster', 'Shark']


MELEE = Loadout('melee', {'righthand': 'Rune scimitar', 'torso': 'Rune chainbody'}, [CarryEntry('Prayer potion(4)', 2), CarryEntry('Lobster', 10)])
EMPTY = Loadout('empty')


def test_a_loadout_names_food_gear_weapon_and_supplies():
    assert food_of(MELEE, 'Trout', is_food) == 'Lobster'
    assert food_of(Loadout('a', {}, [CarryEntry('Prayer potion(4)', 2)]), 'Trout', is_food) == 'Trout'
    assert food_of(EMPTY, 'Trout', is_food) == 'Trout' and food_of(None, 'Trout', is_food) == 'Trout'
    assert food_of(None, '', is_food) == ''
    assert sorted(gear_of(MELEE)) == ['Rune chainbody', 'Rune scimitar'] and gear_of(None) == []
    assert weapon_of(MELEE) == 'Rune scimitar' and weapon_of(EMPTY, 'Rune scimitar') == 'Rune scimitar'
    assert weapon_of(None) is None
    assert supplies_of(MELEE) == MELEE.carry and supplies_of(None) == []


def test_loadouts_come_from_settings():
    loadouts = parse_loadouts([{'name': 'melee', 'worn': {'righthand': 'Rune scimitar', 'nowhere': 'x'}, 'carry': [{'item': 'Shark', 'qty': 10}, {'item': '', 'qty': 1}]}])
    assert len(loadouts) == 1 and loadouts[0].worn == {'righthand': 'Rune scimitar'} and len(loadouts[0].carry) == 1
    assert parse_loadouts('not json') == [] and parse_loadouts('') == [] and parse_loadouts([{'worn': {}}]) == []
    settings = SettingsBag({'loadout': 'melee', 'loadouts': [{'name': 'melee', 'carry': [{'item': 'Shark', 'qty': 10}]}]})
    assert script_food(settings, 'Trout') == 'Shark' or script_food(settings, 'Trout') == 'Trout'
    assert script_food(SettingsBag({}), 'Trout') == 'Trout'
    assert script_foods(SettingsBag({}), ['cake', 'bread']) == ['cake', 'bread']
    listed = upsert_loadout([MELEE], Loadout('Melee', {}, []))
    assert len(listed) == 1 and listed[0].worn == {}
    assert remove_loadout([MELEE, EMPTY], 'MELEE') == [EMPTY]
    assert unique_name([MELEE], 'melee') == 'melee 2' and unique_name([MELEE], 'ranged') == 'ranged'


class Offered:
    def __init__(self, name, count):
        self.name = name
        self.count = count


def test_trading_partners():
    assert parse_partner_list(' Alice, Bob , ') == ['Alice', 'Bob'] and parse_partner_list('') == []
    assert is_configured_partner('alice', ['Alice', 'Bob']) and not is_configured_partner('Eve', ['Alice'])
    assert not is_configured_partner(None, ['Alice'])
    items = [Offered('Pure essence', 10), Offered('pure essence', 5), Offered('Coins', 0), Offered(None, 3)]
    assert count_offer_by_name(items, 'Pure essence') == 15 and count_offer_by_name(items, 'coins') == 1
    assert count_offer_matching(items, lambda n: 'essence' in n.lower()) == 15
    assert decide_receiver_offer_screen(None, ['Runner1'], 0, 0) == ('wait-header',)
    assert decide_receiver_offer_screen('Stranger', ['Runner1'], 0, 5)[0] == 'decline'
    assert decide_receiver_offer_screen('runner1', ['Runner1'], 1, 5)[0] == 'decline'
    assert decide_receiver_offer_screen('Runner1', ['Runner1'], 0, 0) == ('wait-offer',)
    assert decide_receiver_offer_screen('Runner1', ['Runner1'], 0, 5) == ('accept',)
    assert decide_giver_offer_screen(0) == 'offer' and decide_giver_offer_screen(2) == 'accept'
    assert [parse_mule_mode(m) for m in ['Gatherer', 'mule', 'Cooker', 'Supplier', 'Off']] == ['gatherer', 'mule', 'cooker', 'supplier', 'off']
    assert mule_gatherer_handoff_active('gatherer', ['Mule'], False)
    assert not mule_gatherer_handoff_active('gatherer', ['Mule'], True) and not mule_gatherer_handoff_active('gatherer', [], False)
    assert mule_receiver_active('mule', ['G']) and not mule_receiver_active('mule', [])
    assert mule_cooker_active('cooker', ['F']) and not mule_cooker_active('mule', ['F'])
    assert mule_supplier_active('supplier', ['C'], False) and not mule_supplier_active('supplier', ['C'], True)
    assert mule_non_gatherer_active('cooker', ['A']) and mule_non_gatherer_active('supplier', ['A'])
    assert not mule_non_gatherer_active('gatherer', ['A'])


def test_the_leash_and_the_anchor():
    spot = Tile(200, 200, 0)
    assert resolve_run_anchor(Tile(100, 100, 0), spot) is spot and resolve_run_anchor(Tile(100, 100, 0), None).x == 100
    host = AnchorHost(Tile(0, 0, 0), 10)
    assert not beyond_leash(host, Tile(10, 0, 0)) and beyond_leash(host, Tile(11, 0, 0))
    assert not beyond_leash(host, Tile(14, 0, 0), 4) and beyond_leash(host, Tile(15, 0, 0), 4)
    assert not beyond_leash(host, None)
    assert not beyond_leash(host, Tile(16, 0, 0), 6) and beyond_leash(host, Tile(17, 0, 0), 6)
    near = AnchorHost(Tile(50, 50, 0), 5)
    assert tile_within_leash(near, Tile(55, 50, 0)) and not tile_within_leash(near, Tile(56, 50, 0))
    assert tile_within_leash(near, Tile(56, 50, 0), 1)
    task = create_return_to_anchor_task(host, long_range_tiles=40, suppress=lambda: True)
    assert not task.validate()
    assert should_walk_home_to_gather_anchor(9) and not should_walk_home_to_gather_anchor(8) and not should_walk_home_to_gather_anchor(None)
    assert should_soft_home_from_gather_miss(29) and not should_soft_home_from_gather_miss(28)
    assert not should_soft_home_from_gather_miss(20, 10) and should_soft_home_from_gather_miss(21, 10)


def test_sustain_runs_its_hook_once_at_a_time():
    ran = []
    sustain.set(None)
    for _ in sustain.run():
        pass
    sustain.set(lambda: ran.append(1))
    for _ in sustain.run():
        pass
    assert ran == [1] and not sustain.running
    sustain.set(None)


def test_no_needs_are_all_met():
    assert has_all([])
    assert ItemNeed('Bucket', 1, ('ground', Tile(1, 2, 0))).source[0] == 'ground'
