# fixture: jive_dragons
import bots.jive_dragons as dragons
from rs2004.game import game
from rs2004.navigation import navigator

"""rs2b0t's test/scripts/JiveDragons/clue.test.ts and post-clue-bank.test.ts, and hardPreparation.test.ts's
JiveDragons cases (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect, with the facades patched as
rs2b0t's scheduler fixture spies on them. pocketpy calls a class's method over one set on an instance, so a task's
validate or a SolveClue's bank stop is spied on its class, and rs2b0t's mockRestore of one is left out. The cases that
plan the way out of the lair, the egress and nearest-bank ones, need the hunting framework's real walks and aren't
ported; the walk back after a trail is."""


def start(w, settings):
    values = {'site': 'taverley-blue', 'combat_style': w.style, 'ammo': 'Rune arrow', 'solve_clues': True, 'use_special': False}
    values.update(settings)
    bot = JiveDragons()
    bot.settings = SettingsBag(values)
    run_wait(bot.on_start())
    stub(sustain, hook=None)
    return bot


def task_of(bot, kind):
    for task in bot._tasks:
        if isinstance(task, kind):
            return task
    return None


def scenario(style='range', settings=None, site='taverley-blue'):
    w = Lair(site, style).install()
    chosen = {'site': site}
    chosen.update(settings or {})
    bot = start(w, chosen)
    return w, bot, task_of(bot, SolveClue)


def hard_clue():
    return Held(2723, 'Clue scroll (hard)')


def banked_first(*a):
    return True
    yield


def ready():
    return True
    yield


def clue_bank_after_egress(egress_ok):
    world, bot, clue = scenario('melee')
    here = Tile(2898, 9803, 0)
    bank = {'name': 'nearest reachable', 'tile': {'x': 2946, 'z': 3369, 'level': 0}}
    order = []

    def leave(host, site):
        order.append(('egress', site.key))
        return egress_ok
        yield

    def nearest(tile, nav):
        order.append(('nearest', tile))
        expect(nav).to_be(navigator)
        return bank

    def walk(tile, log):
        order.append(('walk', tile))
        return True
        yield

    spy_on(dragons, 'leave_lair', impl=leave)
    spy_on(dragons, 'nearest_bank_reachable', impl=nearest)
    spy_on(dragons, 'walk_to_bank', impl=walk)
    spy_on(game, 'tile', returns=here)
    expect(run_wait(bot.prepare_clue_bank())).to_be(egress_ok)
    if egress_ok:
        expect(order).to_equal([('egress', bot.site.key), ('nearest', here), ('walk', Tile(2946, 3369, 0))])
    else:
        expect(order).to_equal([('egress', bot.site.key)])


test_each([True, False])('clue preparation leaves the lair before routing to the nearest reachable bank: %s', clue_bank_after_egress)


# clue.test.ts

def restock_policy():
    w, bot, clue = scenario('melee')
    bot.clue_restock = True
    w.tile = Tile(3305, 3494, 0)
    w.walk_ok = False
    run_wait(task_of(bot, BankRun).execute())
    expect(len(w.walks)).to_be(1)
    expect(w.walks[0][1].get('policy', {}).get('use_teleports')).to_be(True)
    expect(bot.clue_restock).to_be(True)


def loot_pending():
    w, bot, clue = scenario()
    w.pack = [Held(3490, 'Clue scroll')]
    bot.loot_run = Fake(food=[])
    expect(clue.validate()).to_be(False)


def hands_off():
    w, bot, clue = scenario()
    w.pack = [Held(3490, 'Clue scroll')]
    expect(clue.validate()).to_be(True)
    tasks = bot._tasks
    expect(tasks.index(task_of(bot, GearEquip)) < tasks.index(clue)).to_be(True)
    expect(tasks.index(task_of(bot, PanicBank)) < tasks.index(clue)).to_be(True)
    expect(tasks.index(task_of(bot, Retreat)) < tasks.index(clue)).to_be(True)


def keeps_guardian_weapon():
    w, bot, clue = scenario('melee', {'weapon': 'Rune scimitar'})
    w.pack = [hard_clue(), Held(1333, 'Rune scimitar', 1, 1)]
    w.worn = [i for i in w.worn if i.slot != 3]

    def bank_first(*a):
        w.worn = [i for i in w.worn if i.slot != 3] + [Held(1231, 'Dragon dagger(p)', 1, 3)]
        return True
        yield

    spy_on(SolveClue, '_bank_first', bank_first)
    stub(clue.host, prepare_initial_bank=ready)
    run_wait(clue.execute())
    spy_on(game, 'combat_mode', lambda: -1)
    expect(task_of(bot, GearEquip).validate()).to_be(False)
    expect(task_of(bot, SetAttackStyle).validate()).to_be(False)
    run_wait(clue.execute())
    expect([i.name for i in w.worn if i.slot == 3]).to_equal(['Dragon dagger(p)'])
    expect(w.solves).to_be(2)


def low_hp_hard_pack():
    w, bot, clue = scenario('melee', {'weapon': 'Rune scimitar'})
    w.pack = [hard_clue(), Held(385, 'Shark')]
    stub(clue.host, prepare_initial_bank=ready)
    spy_on(SolveClue, '_bank_first', banked_first)
    run_wait(clue.execute())
    spy_on(skills, 'effective', lambda name: 10)
    expect(clue.owns_equipment()).to_be(True)
    expect(task_of(bot, PanicBank).validate()).to_be(False)
    expect(task_of(bot, BankRun).validate()).to_be(False)


def hard_restock():
    w, bot, clue = scenario('melee', {'weapon': 'Rune scimitar'})
    w.tile = Tile(2900, 9800, 0)
    w.pack = [hard_clue()]
    stub(clue.host, prepare_initial_bank=ready)
    spy_on(SolveClue, '_bank_first', banked_first)

    def solve():
        w.pack = [Held(379, 'Lobster')]
        return 'done'
        yield

    w.on_solve = solve
    run_wait(clue.execute())
    expect(clue.owns_equipment()).to_be(False)
    expect(task_of(bot, BankRun).validate()).to_be(True)
    w.walk_ok = False
    run_wait(task_of(bot, BankRun).execute())
    expect(bot.bank_trips).to_be(0)
    expect(task_of(bot, BankRun).validate()).to_be(True)


def casket_restock():
    w, bot, clue = scenario('melee', {'weapon': 'Rune scimitar'})
    w.pack = [Held(2714, 'Casket')]

    def solve():
        w.pack = [Held(379, 'Lobster')]
        return 'done'
        yield

    w.on_solve = solve
    expect(bot.clue_restock).to_be(False)
    run_wait(clue.execute())
    expect(bot.clue_restock).to_be(True)
    expect(bot.clues_solved).to_be(1)
    expect(task_of(bot, BankRun).validate()).to_be(True)


describe('JiveDragons clue hand-off', lambda: [
    test('post-clue restocking keeps the trail teleport policy for the trip back to the bank', restock_policy),
    test('does not hand off a clue while safe food return is pending', loot_pending),
    test('hands off after fight and loot finish without changing emergency or ammo priority', hands_off),
    test('a yielded melee hard clue keeps its guardian weapon through the host scheduler', keeps_guardian_weapon),
    test('low HP with a hard-clue Shark pack does not trigger dragon banking during a yielded trail', low_hp_hard_pack),
    test('finishing a hard clue requires a dragon restock even when food and weapons remain', hard_restock),
    test('finishing a casket-only trail requires post-clue restocking', casket_restock),
])


# hardPreparation.test.ts's JiveDragons cases

def hard_world(w):
    w.tile = FALADOR
    w.pack = [hard_clue(), Held(952, 'Spade'), Held(2574, 'Sextant'), Held(2575, 'Watch'), Held(2576, 'Chart')]
    w.bank = [Held(1231, 'Dragon dagger(p)'), Held(2448, 'Superantipoison(4)'), Held(385, 'Shark', 30)]


def twelve_sharks(stock):
    w, bot, clue = scenario('melee', {'food_withdraw': 20})
    hard_world(w)
    if stock == 30:
        w.pack.extend([Held(385, 'Shark') for _ in range(20)])
    for i in w.bank:
        if i.id == 385:
            i.count = stock
    stub(clue.host, prepare_initial_bank=ready)
    run_wait(clue.execute())
    expect(w.sharks()).to_be(12)
    expect(w.solves).to_be(1)


def restocks_twelve():
    w, bot, clue = scenario('melee', {'food_withdraw': 20})
    hard_world(w)
    stub(clue.host, prepare_initial_bank=ready)
    loads = []

    def solve():
        loads.append(w.sharks())
        if len(loads) == 1:
            w.pack = [i for i in w.pack if i.id != 385]
            return 'supplies-needed'
        return 'yield'
        yield

    w.on_solve = solve
    run_wait(clue.execute())
    expect(loads).to_equal([12, 12])


describe('JiveDragons hard clue preparation', lambda: [
    test('JiveDragons prepares exactly twelve Sharks with 12 banked', lambda: twelve_sharks(12)),
    test('JiveDragons prepares exactly twelve Sharks with 30 banked', lambda: twelve_sharks(30)),
    test('JiveDragons restocks a hard clue to twelve Sharks after supplies run low', restocks_twelve),
])
