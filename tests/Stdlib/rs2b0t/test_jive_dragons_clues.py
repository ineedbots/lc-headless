"""rs2b0t's test/scripts/JiveDragons/clue.test.ts and post-clue-bank.test.ts, and hardPreparation.test.ts's
JiveDragons cases (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect, with the facades patched as
rs2b0t's scheduler fixture spies on them. pocketpy calls a class's method over one set on an instance, so a task's
validate or a SolveClue's bank stop is spied on its class, and rs2b0t's mockRestore of one is left out. The cases that
plan the way out of the lair, the egress and nearest-bank ones, need the hunting framework's real walks and aren't
ported; the walk back after a trail is."""

from bots.jive_dragons import BankRun, GearEquip, JiveDragons, PanicBank, SetAttackStyle
from rs2004 import execution
from rs2004.catalogs import loadout as loadout_module
from rs2004.catalogs.tasks import sustain
from rs2004.clues import bank_access
from rs2004.clues import solve as solve_module
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.solve import SolveClue
from rs2004.hunting import Retreat, site_for

FALADOR = Tile(2946, 3369, 0)


class Held:
    def __init__(self, id, name, count=1, slot=0):
        self.id = id
        self.name = name
        self.count = count
        self.slot = slot
        self.noted = False

    def copy(self, count=None, slot=None):
        return Held(self.id, self.name, self.count if count is None else count, self.slot if slot is None else slot)


class Lair:
    """The scheduler fixture's world: the bot at the site's first safespot, with a pack, a bank and worn gear."""

    def __init__(self, site_id, style):
        self.site = site_for(site_id)
        self.style = style
        spot = self.site.safespots[0] if self.site.safespots else self.site.melee_anchor
        self.tile = spot
        self.pack = [Held(379, self.site.food or 'Lobster') for _ in range(10)]
        self.bank = []
        self.worn = ([Held(1540, 'Dragonfire shield', 1, 5)] if style == 'melee' else []) + ([Held(1333, 'Rune scimitar', 1, 3)] if style == 'melee' else [])
        self.open = False
        self.walks = []
        self.walk_ok = True
        self.solves = 0
        self.outcomes = ['yield']
        self.on_solve = None
        self.solve_args = []

    def install(self):
        w = self
        stub(sustain, hook=None)
        spy_on(game, 'tile', lambda: w.tile)
        spy_on(game, 'ingame', lambda: True)
        spy_on(game, 'scene_ready', lambda: True)
        spy_on(game, 'in_combat', lambda: False)
        spy_on(game, 'combat_mode', lambda: 1)
        spy_on(skills, 'effective', lambda name: 99)
        spy_on(skills, 'level', lambda name: 99)
        spy_on(skills, 'xp', lambda name: 0)
        spy_on(npcs, 'query', querying(lambda: []))
        spy_on(ground_items, 'query', querying(lambda: []))
        spy_on(event_signal, 'pending', lambda: False)
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'is_open', lambda: False)
        spy_on(prayer, 'known', lambda name: False)
        spy_on(quests, 'status', lambda name: 'complete' if name == 'Lost City' else 'unknown')
        spy_on(prayer, 'max', lambda: 0)
        spy_on(inventory, 'items', lambda: list(w.pack))
        spy_on(inventory, 'first', lambda name: ([i for i in w.pack if i.name == name] + [None])[0])
        spy_on(inventory, 'count', lambda name: sum([i.count for i in w.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', lambda id: sum([i.count for i in w.pack if i.id == id]))
        spy_on(inventory, 'contains', lambda name: any([i.name == name for i in w.pack]))
        spy_on(inventory, 'free', lambda: 28 - len(w.pack))
        spy_on(inventory, 'used', lambda: len(w.pack))
        spy_on(inventory, 'is_full', lambda: len(w.pack) >= 28)
        spy_on(equipment, 'items', lambda: list(w.worn))
        spy_on(equipment, 'contains', lambda name: any([i.name == name for i in w.worn]))
        spy_on(equipment, 'equip', lambda name: w.equip(name))
        spy_on(bank, 'is_open', lambda: w.open)
        spy_on(bank, 'ready', lambda: w.open)
        spy_on(bank, 'wait_ready', lambda timeout_ms=4000: instant_until(w.is_open))
        spy_on(bank, 'items', lambda: list(w.bank) if w.open else [])
        spy_on(bank, 'count', lambda name: sum([i.count for i in w.bank if i.name == name]))
        spy_on(bank, 'count_by_id', lambda id: sum([i.count for i in w.bank if i.id == id]))
        spy_on(bank, 'withdraw', lambda name, op='Withdraw 1': w.take(name, op))
        spy_on(bank, 'withdraw_x', lambda name, count: instant_until(lambda: False))
        spy_on(bank, 'deposit_all_matching', lambda matches: w.deposit(matches))
        spy_on(bank, 'close', lambda: w.close())
        spy_on(bank, 'open_nearest', lambda *a: w.open_bank())
        spy_on(bank, 'open_nearest_access', lambda *a: w.open_bank())
        spy_on(bank, 'open_npc_access', lambda *a: w.open_bank())
        patch(solve_module, 'nearest_bank', lambda tile, settings=None: {'name': 'Falador west', 'tile': {'x': FALADOR.x, 'z': FALADOR.z, 'level': 0}})
        patch(bank_access, 'nearest_bank', lambda tile, settings=None: None)
        patch(loadout_module, '_store_all', lambda: [])
        spy_on(traversal, 'walk_resilient', lambda tile, **opts: w.walk(tile, opts))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', instant_ticks)
        patch(ClueExecutor, 'solve_held_clue', w.solver())
        return self

    def solver(self):
        w = self

        def solve_held_clue(executor, log, needs_bank=None, ranged=None):
            w.solves += 1
            w.solve_args.append(ranged)
            if w.on_solve is not None:
                result = yield from w.on_solve()
                return result
            return w.outcomes.pop(0) if len(w.outcomes) > 1 else w.outcomes[0]

        return solve_held_clue

    def is_open(self):
        return self.open

    def walk(self, tile, opts):
        self.walks.append((tile, opts))
        if self.walk_ok:
            self.tile = tile
        return self.walk_ok
        yield

    def open_bank(self):
        self.open = True
        return True
        yield

    def close(self):
        self.open = False
        return True
        yield

    def take(self, name, op):
        source = None
        for i in self.bank:
            if i.name == name and i.count > 0:
                source = i
                break
        if source is None:
            return False
        count = min(source.count, 10 if op == 'Withdraw 10' else (5 if op == 'Withdraw 5' else 1), 28 - len(self.pack))
        source.count -= count
        self.pack.extend([source.copy(1) for _ in range(count)])
        return count > 0

    def deposit(self, matches):
        self.bank.extend([i for i in self.pack if matches(i.name or '', i.id)])
        self.pack = [i for i in self.pack if not matches(i.name or '', i.id)]
        return None
        yield

    def equip(self, name):
        found = [i for i in self.pack if i.name == name]
        if not found:
            return any([i.name == name for i in self.worn])
        nxt = found[0]
        slot = nxt.slot or 3
        self.pack = [i for i in self.pack if i is not nxt] + [i for i in self.worn if i.slot == slot]
        self.worn = [i for i in self.worn if i.slot != slot] + [nxt.copy(None, slot)]
        self.open = False
        return True
        yield

    def sharks(self):
        return len([i for i in self.pack if i.id == 385])


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
