"""Upstream quest acquisition: staff budgets, Caleb's fish and Watchtower's dragon hunt."""

import rs2004.quests.strike as strike
import rs2004.quests.defs.familycrest.fish as fish
import rs2004.quests.defs.watchtower.bones as bones
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.items import inventory, equipment
from rs2004.bank import bank, banking
from rs2004 import execution


def result(value):
    return value
    yield


def snap(**fields):
    state = QuestSnapshot(bank_known=True, bank={}, inv_ids={}, bank_ids={}, magic=13, attack=40, free_slots=20, bank_coins=10000)
    for key, value in fields.items():
        setattr(state, key, value)
    return state


def staff_sources():
    state = snap()
    expect(strike.prepare_strike_staff(state).items).to_equal([{'name': 'Coins', 'qty': 2000}])
    state.inv = {'coins': 2000}
    expect(strike.prepare_strike_staff(state).kind).to_be('custom')
    state.bank = {'staff of fire': 1}
    expect(strike.prepare_strike_staff(state).items[0]['name']).to_be('Staff of fire')
    state.inv['staff of fire'] = 1
    expect(strike.prepare_strike_staff(state).kind).to_be('equip')
    state.inv = {}
    state.worn.add('staff of fire')
    expect(strike.prepare_strike_staff(state)).to_be(None)
    state.worn.clear()
    state.inv = {'fire rune': 450}
    expect(strike.prepare_strike_staff(state)).to_be(None)
    state.inv = {}
    state.bank_known = False
    expect(strike.prepare_strike_staff(state).kind).to_be('scan_bank')
    state.bank_known = True
    state.bank = {}
    state.bank_coins = 0
    expect(strike.prepare_strike_staff(state)).to_be(None)
    state.bank = {'staff of water': 1}
    state.free_slots = 0
    state.inv = {'junk': 28}
    expect(strike.prepare_strike_staff(state).kind).to_be('deposit')
    state.inv = {'coins': 2000}
    expect(strike.prepare_strike_staff(state).kind).to_be('wait')
    state.magic = 0
    expect(strike.prepare_strike_staff(state)).to_be(None)


test('Strike staff provisioning respects held, worn, banked, funded and full inventories', staff_sources)


def staff_budget():
    state = snap(inv={'mind rune': 600}, worn=set(['staff of air']), bank={})
    expect(strike.prepare_strikes(state)).to_be(None)
    expect(strike.strike_spell(13, lambda name: 10 if name == 'Mind rune' else 0, ['Staff of air'])).to_be('Wind Strike')
    state.inv = {'mind rune': 1}
    expect(strike.prepare_strikes(state).qty).to_be(599)
    state.worn = set(['staff of fire'])
    state.inv = {'mind rune': 150, 'air rune': 300}
    expect(strike.prepare_strikes(state)).to_be(None)


test('a weaker staff-supplied Strike gets an equivalent damage budget', staff_budget)


def staff_shop(mode):
    def run():
        behavior = mode
        scene = Scene(strike.ZAFF)
        spy_on(strike.shop, 'open', impl=lambda *args: result(behavior != 'closed'))
        spy_on(strike.shop, 'stock', returns=[Fake(name='Staff of fire', count=1)] if behavior != 'empty' else [])
        spy_on(strike.shop, 'buy', impl=lambda *args: result(1 if behavior == 'bought' else 0))
        closed = spy_on(strike.shop, 'close', impl=instant_ticks)
        if mode == 'walk':
            scene.walk_ok = False
        expect(run_wait(strike.buy_strike_staff(['Staff of fire'], scene.log))).to_be(mode == 'bought')
        expect(len(closed.calls)).to_be(0 if mode in ['closed', 'walk'] else 1)
    return run


for mode in ['bought', 'closed', 'empty', 'refused', 'walk']:
    test('Zaff staff purchase: ' + mode, staff_shop(mode))


def fish_sources():
    swordfish = fish.FISH[0]
    state = snap()
    missing = [swordfish]
    expect(fish.source_caleb_fish(state, missing, 1, 1).kind).to_be('wait')
    state.bank_ids = {swordfish.raw: 1}
    expect(fish.source_caleb_fish(state, missing, 1, 1).kind).to_be('withdraw')
    state.bank_ids = {}
    state.inv_ids = {swordfish.raw: 1}
    expect(fish.source_caleb_fish(state, missing, 1, 45).name).to_be('cook Swordfish for Caleb')
    state.inv_ids = {}
    state.free_slots = 1
    expect(fish.source_caleb_fish(state, missing, 50, 45).kind).to_be('deposit')
    state.free_slots = 20
    expect(fish.source_caleb_fish(state, missing, 50, 45).item).to_be('Harpoon')
    state.bank = {'harpoon': 1}
    expect(fish.source_caleb_fish(state, missing, 50, 45).items[0]['name']).to_be('Harpoon')
    state.inv = {'harpoon': 1}
    expect(fish.source_caleb_fish(state, missing, 50, 45).name).to_be('catch Swordfish for Caleb')
    state.inv = {'fly fishing rod': 1}
    step = fish.source_caleb_fish(state, [fish.FISH[3]], 50, 45)
    expect(step.item).to_be('Feather')
    state.bank = {'feather': 7}
    expect(fish.source_caleb_fish(state, [fish.FISH[3]], 50, 45).items[0]['qty']).to_be(7)
    state.inv['feather'] = 7
    spy_on(fish.skills, 'level', returns=50)
    expect(fish.source_caleb_fish(state, [fish.FISH[3]]).kind).to_be('custom')


test('Caleb sources usable raw fish, tools and feathers before catching and cooking', fish_sources)


def catch_and_cook():
    scene = Scene(fish.SHORE)
    chosen = fish.FISH[0]
    expect(run_wait(fish.catch_fish(chosen, scene.log))).to_be(False)
    scene.npc('Fishing spot', ['Harpoon', 'Cage'], effect=lambda op: scene.item(chosen.raw, 'Raw swordfish'))
    expect(run_wait(fish.catch_fish(chosen, scene.log))).to_be(True)
    raw = scene.pack[0]
    raw._fields['use_on'] = lambda other: (scene.pack.clear(), True)[1]
    scene.loc('Range')
    expect(run_wait(fish.cook_fish(chosen, scene.log))).to_be(True)
    expect(run_wait(fish.cook_fish(chosen, scene.log))).to_be(False)
    scene.walk_ok = False
    expect(run_wait(fish.catch_fish(chosen, scene.log))).to_be(False)
    expect(run_wait(fish.cook_fish(chosen, scene.log))).to_be(False)


test('Caleb requires a matching fishing spot and confirms the raw fish was cooked', catch_and_cook)


def dragon_host_contract():
    scene = Scene()
    scene.stats['attack'] = 40
    scene.stats['hitpoints'] = 50
    host = bones.dragon_host('Lobster', scene.log)
    host.pick_weapon(['Rune 2h sword', 'Rune scimitar'])
    expect(host.weapon_name()).to_be('Rune scimitar')
    expect(host.style()).to_be('melee')
    expect(host.food_name()).to_be('Lobster')
    expect(host.food_withdraw()).to_be(12)
    expect(host.ammo_name()).to_be('')
    expect(host.spell_name()).to_be('')
    expect(host.leave_by_walk()).to_be(True)
    expect(host.keep_extra()).to_equal(['Dragon bones'])
    expect(host.bone_name()).to_be('Dragon bones')
    expect(host.bury_bones()).to_be(False)
    expect(host.died).to_be(False)
    expect(host.retreat_hp()).to_be(0.5)
    expect(host.panic_hp()).to_be(0.35)
    host.set_safespot_index(2)
    expect(host.safespot_index()).to_be(2)
    host.count_bank_trip()
    host.count_burial()
    host.count_kill()
    host.set_status('test')
    host.park_for('reason')
    host.vlog('trace')
    expect(run_wait(host.eat_once())).to_be(False)
    scene.stats['hitpoints'] = 20
    scene.item(379, 'Lobster', effect=lambda op: scene.pack.clear())
    spy_on(bones.skills, 'level', returns=50)
    expect(host.need_eat()).to_be(True)
    expect(run_wait(host.eat_once())).to_be(True)
    host.pick_weapon([])
    expect(host.weapon_name()).to_be('')
    expect(bones.in_dragon_lair(Tile(2930, 9685, 0))).to_be(True)
    expect(bones.in_dragon_lair(None)).to_be(False)


test('Watchtower dragon host supplies the combat interface and keeps one-handed weapons', dragon_host_contract)


def bridge_equipment():
    import rs2004.quests.defs.ikov as ikov
    scene = Scene()
    scene.wear('Rune platebody')
    scene.wear('Boots of lightness')
    spy_on(ikov.equipment, 'unequip', impl=lambda name: result(False))
    expect(run_wait(ikov.remove_bridge_equipment(scene.log))).to_be(False)
    spy_on(ikov.equipment, 'unequip', impl=lambda name: result(True))
    expect(run_wait(ikov.remove_bridge_equipment(scene.log))).to_be(True)
    state = snap(worn=set(['rune platebody']))
    expect(ikov.bridge_trim_step(state).kind).to_be('custom')
    state.inv_ids = {ikov.IKOV_OBJ.YEW_SHORTBOW: 1, 379: 8}
    state.inv = {'lobster': 8}
    state.worn = set()
    expect(ikov.war_kit_step(state)).to_be(None)
    state.bank = {'ice arrows': 100}
    expect(ikov.war_kit_step(state).items[0]['qty']).to_be(min(100, ikov.ARROWS_WANTED))


test('Ikov removes bridge weight safely and recovers banked arrows before chest runs', bridge_equipment)


def goblin_gear_and_bank():
    import rs2004.quests.defs.goblindiplomacy as gd
    scene = Scene()
    state = snap(inv={'coins': 500}, attack=40, worn_ids=set(), inv_ids={}, bank_ids={})
    weapon = Fake(id=1333, name='Rune scimitar')
    spy_on(gd, 'wieldable', returns=[weapon])
    state.bank = {'goblin mail': 3}
    expect(gd.goblin_mail_gather_step(state, 2).items[0]['qty']).to_be(2)
    state.bank = {}
    state.inv_ids = {1333: 1}
    expect(gd.goblin_mail_gather_step(state).kind).to_be('equip')
    state.inv_ids = {}
    state.bank_ids = {1333: 1}
    expect(gd.goblin_mail_gather_step(state).items[0]['id']).to_be(1333)
    state.bank_ids = {}
    state.worn_ids = set([1333])
    expect(gd.goblin_mail_gather_step(state).name).to_be('farm goblin mail')


test('Goblin Diplomacy retrieves banked mail and arms the gatherer before combat', goblin_gear_and_bank)


def goblin_offense(mode):
    def run():
        import rs2004.quests.defs.goblindiplomacy as gd
        scene = Scene()
        target = Fake(index=7, health=0 if mode == 'kill' else 30, max_health=30)
        spy_on(gd.npcs, 'all', returns=[target])
        patch(gd, 'goblin_mail_target_index', 7)
        spy_on(gd, '_farm_goblin_mail_tick', impl=lambda log: result(True))
        clock = [0]
        def now():
            clock[0] += 5000
            return clock[0]
        spy_on(gd._core, 'step_time', impl=now)
        expect(run_wait(gd.farm_goblin_mail(scene.log))).to_be(mode == 'kill')
        if mode == 'stall':
            expect(gd.goblin_mail_rejected_target_index).to_be(7)
            expect(scene.logged('no damage or XP')).to_be(True)
    return run


for mode in ['kill', 'stall']:
    test('Goblin Diplomacy confirms offensive progress: ' + mode, goblin_offense(mode))
