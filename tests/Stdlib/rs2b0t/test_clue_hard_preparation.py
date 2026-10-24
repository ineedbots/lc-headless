"""rs2b0t's test/api/ai/clues/hardPreparation.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect, with the facades patched as rs2b0t spies on them. Its JiveDragons cases are with that bot's tests, in
test_jive_dragons_clues.py. rs2b0t's executor is one for the process; here each SolveClue owns one, so the case of a
new solver clearing an old session's death asks the new solver's executor. The walker's bank list is patched to the
Falador west bank, where rs2b0t's fixture stands."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.clues import bank_access
from rs2004.clues import solve as solve_module
from rs2004.clues.executor import ClueExecutor, ClueProgress
from rs2004.clues.plan import GuardianRangedLoadout
from rs2004.clues.solve import SolveClue

FALADOR = Tile(2946, 3369, 0)
REAL_SOLVE = ClueExecutor.solve_held_clue


class Held:
    def __init__(self, id, name, count=1, slot=0):
        self.id = id
        self.name = name
        self.count = count
        self.slot = slot
        self.noted = False

    def copy(self, id=None, count=None, slot=None):
        return Held(self.id if id is None else id, self.name, self.count if count is None else count, self.slot if slot is None else slot)

    def __repr__(self):
        return f'{self.name}#{self.id}x{self.count}@{self.slot}'


CLUE = Held(2723, 'Clue scroll (hard)')
BOW = Held(861, 'Magic shortbow')


def ranged():
    return GuardianRangedLoadout('Magic shortbow', 'Rune arrow', 500, 1)


class Host:
    def __init__(self, w, prepare=True, ranged_kit=False, hard_food=None):
        self.w = w
        self.statuses = []
        self.ranged_kit = ranged_kit
        self.initial_trips = 0
        self.prayer = False
        if hard_food is not None:
            self.hard_food_target = hard_food
        if prepare:
            self.prepare_initial_bank = self.prepare

    def prepare(self):
        self.initial_trips += 1
        return True
        yield

    def log(self, m):
        self.w.logs.append(m)

    def set_status(self, text):
        self.statuses.append(text)

    def is_food(self, name):
        return name == 'Lobster'

    def food_name(self):
        return 'Lobster'

    def food_withdraw(self):
        return 10

    def weapon_name(self):
        return 'Magic shortbow'

    def use_teleports(self):
        return False

    def restore_prayer(self):
        return self.prayer

    def ranged_loadout(self):
        return ranged() if self.ranged_kit else None


class Vault:
    """hardPreparation.test.ts's fixture: a pack, a bank and worn gear."""

    def __init__(self):
        self.pack = [CLUE.copy(), Held(952, 'Spade'), Held(2574, 'Sextant'), Held(2575, 'Watch'), Held(2576, 'Chart')]
        self.bank = [Held(1231, 'Dragon dagger(p)'), Held(2448, 'Superantipoison(4)'), Held(385, 'Shark', 30)]
        self.worn = [BOW.copy(slot=3)]
        self.open = False
        self.equips = []
        self.snapshot = None
        self.pending = False
        self.tile = FALADOR
        self.in_combat = False
        self.walk_ok = True
        self.walks = []
        self.opens = 0
        self.outcomes = ['yield']
        self.on_solve = None
        self.solves = 0
        self.on_equip = None
        self.on_unequip = None
        self.on_interact = None
        self.on_withdraw = None
        self.on_withdraw_x = None
        self.on_deposit = None
        self.on_close = None
        self.on_open = None
        self.eaten = []
        self.logs = []

    def install(self):
        w = self
        stub(sustain, hook=None)
        spy_on(inventory, 'items', lambda: [w.held(i) for i in w.pack])
        spy_on(inventory, 'first', lambda name: w.first(name))
        spy_on(inventory, 'count', lambda name: sum([i.count for i in w.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', lambda id: sum([i.count for i in w.pack if i.id == id]))
        spy_on(inventory, 'free', lambda: 28 - len(w.pack))
        spy_on(inventory, 'is_full', lambda: len(w.pack) >= 28)
        spy_on(equipment, 'items', lambda: list(w.worn))
        spy_on(equipment, 'contains', lambda name: any([i.name == name for i in w.worn]))
        spy_on(equipment, 'equip', lambda name: w.equip(name))
        spy_on(equipment, 'unequip', lambda name: w.unequip(name))
        spy_on(bank, 'is_open', lambda: w.open)
        spy_on(bank, 'ready', lambda: w.ready())
        spy_on(bank, 'wait_ready', lambda timeout_ms=4000: instant_until(w.ready))
        spy_on(bank, 'items', lambda: list(w.bank) if w.ready() else [])
        spy_on(bank, 'count', lambda name: sum([i.count for i in w.bank if i.name == name]))
        spy_on(bank, 'count_by_id', lambda id: sum([i.count for i in w.bank if i.id == id]))
        spy_on(bank, 'withdraw', lambda name, op='Withdraw 1': w.withdraw(name, op))
        spy_on(bank, 'withdraw_by_id', lambda id, op='Withdraw 1': w.withdraw_by_id(id))
        spy_on(bank, 'withdraw_x', lambda name, count: w.withdraw_x(name, count))
        spy_on(bank, 'deposit_all_matching', lambda matches: w.deposit(matches))
        spy_on(bank, 'close', lambda: w.close())
        spy_on(bank, 'open_nearest', lambda *a: w.open_bank())
        spy_on(bank, 'open_nearest_access', lambda *a: w.open_bank())
        spy_on(bank, 'open_npc_access', lambda *a: w.open_bank())
        patch(solve_module, 'nearest_bank', lambda tile, settings=None: w.nearest(tile))
        patch(bank_access, 'nearest_bank', lambda tile, settings=None: w.nearest(tile))
        spy_on(skills, 'level', lambda name: 60)
        spy_on(skills, 'effective', lambda name: 60)
        spy_on(quests, 'status', lambda name: 'complete' if name == 'Lost City' else 'unknown')
        spy_on(game, 'tile', lambda: w.tile)
        spy_on(game, 'in_combat', lambda: w.in_combat)
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(traversal, 'walk_resilient', lambda tile, **opts: w.walk(tile))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'is_open', lambda: False)
        spy_on(reader, 'count_dialog_open', lambda: False)
        spy_on(prayer, 'max', lambda: 0)
        spy_on(locs, 'query', querying(lambda: []))
        patch(ClueExecutor, 'solve_held_clue', w.solver())
        return self

    def solver(self):
        w = self

        def solve_held_clue(executor, log, needs_bank=None, ranged=None):
            w.solves += 1
            if w.on_solve is not None:
                result = yield from w.on_solve(executor, needs_bank, ranged)
                return result
            return w.outcomes.pop(0) if len(w.outcomes) > 1 else w.outcomes[0]

        return solve_held_clue

    def real_solver(self):
        """Puts the executor's own solve back, for the cases that run it."""
        patch(ClueExecutor, 'solve_held_clue', REAL_SOLVE)

    def nearest(self, tile):
        if tile is None:
            return None
        return {'name': 'Falador west', 'tile': {'x': FALADOR.x, 'z': FALADOR.z, 'level': 0}}

    def ready(self):
        return self.open and (self.snapshot is None or self.snapshot())

    def first(self, name):
        for i in self.pack:
            if i.name == name:
                return self.held(i)
        return None

    def held(self, i):
        w = self
        item = i

        def interact(op):
            if w.on_interact is not None:
                return w.on_interact(item, op)
            if op == 'Eat':
                w.eaten.append(item.id)
                w.pack = [p for p in w.pack if p is not item]
            return True

        return Fake(id=i.id, name=i.name, count=i.count, slot=i.slot, noted=False, actions=lambda: ['Wield', 'Eat', 'Drink'], interact=interact)

    def walk(self, tile):
        self.walks.append(tile)
        return self.walk_ok
        yield

    def walk_and_fire(self):
        self.pending = True
        return False
        yield

    def open_bank(self):
        self.opens += 1
        if self.on_open is not None:
            opened = self.on_open()
            if not opened:
                return False
        self.open = True
        return True
        yield

    def close(self):
        if self.on_close is not None:
            closed = self.on_close()
            if not closed:
                return False
        self.open = False
        return True
        yield

    def withdraw(self, name, op):
        if self.on_withdraw is not None:
            return self.on_withdraw(name, op)
        return self.take(name, op)

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
        self.pack.extend([source.copy(count=1) for _ in range(count)])
        return count > 0

    def withdraw_by_id(self, id):
        source = None
        for i in self.bank:
            if i.id == id and i.count > 0:
                source = i
                break
        if source is None or len(self.pack) >= 28:
            return False
        source.count -= 1
        self.pack.append(source.copy(count=1))
        return True

    def withdraw_x(self, name, count):
        if self.on_withdraw_x is not None:
            took = yield from self.on_withdraw_x(name, count)
            return took
        return False
        yield

    def deposit(self, matches):
        if self.on_deposit is not None:
            yield from self.on_deposit(matches)
            return None
        self.bank.extend([i for i in self.pack if matches(i.name or '', i.id)])
        self.pack = [i for i in self.pack if not matches(i.name or '', i.id)]
        return None
        yield

    def equip(self, name):
        self.equips.append(name)
        if self.on_equip is not None:
            on = yield from self.on_equip(name)
            return on
        return self.wear(name, None)

    def wear(self, name, slot_of):
        found = [i for i in self.pack if i.name == name]
        if not found:
            return any([i.name == name for i in self.worn])
        nxt = found[0]
        slot = slot_of(name) if slot_of is not None else (nxt.slot or 3)
        self.pack = [i for i in self.pack if i is not nxt] + [i for i in self.worn if i.slot == slot]
        self.worn = [i for i in self.worn if i.slot != slot] + [nxt.copy(slot=slot)]
        self.open = False
        return True

    def unequip(self, name):
        if self.on_unequip is not None:
            off = self.on_unequip(name)
            if not off:
                return False
        if self.open or len(self.pack) >= 28:
            return False
        self.pack.extend([i for i in self.worn if i.name == name])
        self.worn = [i for i in self.worn if i.name != name]
        return True
        yield

    def sharks(self):
        return len([i for i in self.pack if i.id == 385])

    def banked(self, id):
        return sum([i.count for i in self.bank if i.id == id])

    def worn_in(self, slot):
        for i in self.worn:
            if i.slot == slot:
                return i
        return None


def run(task):
    run_wait(task.execute())


def ranged_world(w):
    w.on_withdraw_x = None

    def withdraw_x(name, count):
        source = None
        for i in w.bank:
            if i.name == name and i.count > 0:
                source = i
                break
        if source is None:
            return False
        take = min(count, source.count)
        source.count -= take
        w.pack.append(source.copy(count=take))
        return True
        yield

    def wield(item, op):
        if item.id == 861 and op == 'Wield' and not w.open:
            w.pack = [i for i in w.pack if i is not item] + [i for i in w.worn if i.slot == 3]
            w.worn = [i for i in w.worn if i.slot != 3] + [item.copy(slot=3)]
            return True
        if item.id != 892 or op != 'Wield' or w.open:
            return False
        count = sum([i.count for i in w.worn if i.slot == 13 and i.id == 892]) + item.count
        w.worn = [i for i in w.worn if i.slot != 13] + [item.copy(count=count, slot=13)]
        w.pack = [i for i in w.pack if i is not item]
        return True

    w.on_withdraw_x = withdraw_x
    w.on_interact = wield
    return SolveClue(Host(w, True, True))


def ranged_arrows(count):
    w = Vault().install()
    if count:
        w.worn.append(Held(892, 'Rune arrow', count, 13))
    w.bank.append(Held(892, 'Rune arrow', 600))
    run(ranged_world(w))
    expect(w.solves).to_be(1)
    expect(w.worn_in(3).id).to_be(861)
    expect(w.worn_in(13).count).to_be(500)
    expect(w.banked(892)).to_be(100 + count)
    expect(w.banked(1231)).to_be(1)
    expect(any([i.id == 892 for i in w.pack])).to_be(False)


def strung_bow():
    w = Vault().install()
    w.worn = []
    w.bank.extend([Held(72, 'Magic shortbow'), BOW.copy(), Held(892, 'Rune arrow', 500)])
    run(ranged_world(w))
    expect(w.solves).to_be(1)
    expect(w.worn_in(3).id).to_be(861)
    expect(w.banked(72)).to_be(1)
    expect(w.banked(1231)).to_be(1)


def ranged_restock():
    w = Vault().install()
    w.bank.append(Held(892, 'Rune arrow', 1000))
    task = ranged_world(w)
    run(task)
    w.worn = [i for i in w.worn if i.slot != 13]
    w.outcomes = ['supplies-needed', 'yield']
    run(task)
    expect(w.solves).to_be(3)
    expect(w.worn_in(3).id).to_be(861)
    expect(w.worn_in(13).count).to_be(500)
    expect(w.banked(892)).to_be(0)
    expect(w.banked(1231)).to_be(1)
    expect(any([i.id == CLUE.id for i in w.pack])).to_be(True)


def ammo_arrives():
    w = Vault().install()
    task = ranged_world(w)
    run(task)
    expect(w.solves).to_be(0)
    expect(w.worn_in(3).id).to_be(861)
    expect(task.validate()).to_be(False)
    w.bank.append(Held(892, 'Rune arrow', 80))
    w.open = True
    expect(task.validate()).to_be(True)
    run(task)
    expect(w.worn_in(13).count).to_be(80)
    expect(w.solves).to_be(1)


def ranged_entrana():
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    w.worn.append(Held(892, 'Rune arrow', 500, 13))
    task = ranged_world(w)
    run(task)
    expect(w.worn).to_equal([])
    expect(any([i.id in [861, 892, 1231] for i in w.pack])).to_be(False)
    expect(w.solves).to_be(1)
    w.pack[0] = CLUE.copy()
    w.solves = 0
    w.outcomes = ['supplies-needed', 'yield']
    run(task)
    expect(w.worn_in(3).id).to_be(861)
    expect(w.worn_in(13).count).to_be(500)
    expect(w.banked(1231)).to_be(1)
    expect(w.solves).to_be(2)


describe('ranged hard preparation', lambda: [
    test('ranged clue preparation withdraws and equips arrows with 0 already worn', lambda: ranged_arrows(0)),
    test('ranged clue preparation withdraws and equips arrows with 50 already worn', lambda: ranged_arrows(50)),
    test('ranged preparation withdraws the strung bow even when an unstrung namesake comes first', strung_bow),
    test('a ranged guardian restock replenishes depleted arrows and keeps the bow', ranged_restock),
    test('ranged clue preparation resumes when missing ammunition arrives in the bank', ammo_arrives),
    test('ranged clue preparation banks bow and arrows for Entrana and restores them afterward', ranged_entrana),
])


def lacks(id):
    w = Vault().install()
    w.bank = [i for i in w.bank if i.id != id]
    task = SolveClue(Host(w))
    run(task)
    expect(w.solves).to_be(0)
    expect(any([i.id == CLUE.id for i in w.pack])).to_be(True)
    expect(task.validate()).to_be(False)


def fourteen_sharks():
    w = Vault().install()
    for i in w.bank:
        if i.id == 385:
            i.count = 14
    run(SolveClue(Host(w)))
    expect(w.solves).to_be(0)


def bank_only_kit():
    w = Vault().install()
    run(SolveClue(Host(w)))
    expect(w.solves).to_be(1)
    expect(w.worn[0].id).to_be(1231)
    expect(w.sharks()).to_be(15)
    expect(any([i.id == 2448 for i in w.pack])).to_be(True)
    expect(any([i.id == BOW.id for i in w.pack])).to_be(True)


def equip_fails():
    w = Vault().install()

    def refuse(name):
        return False
        yield

    w.on_equip = refuse
    run(SolveClue(Host(w)))
    expect(w.solves).to_be(0)


def unknown_bank():
    w = Vault().install()
    w.snapshot = lambda: False
    w.bank = []
    task = SolveClue(Host(w))
    run(task)
    expect(w.solves).to_be(0)
    expect(task.validate()).to_be(True)


def restoration_after_clue():
    w = Vault().install()
    task = SolveClue(Host(w))
    run(task)
    w.pack = [i for i in w.pack if i.id != CLUE.id]
    expect(task.validate()).to_be(True)
    run(task)
    expect(w.worn[0].id).to_be(BOW.id)
    expect(task.validate()).to_be(False)


def casket_only():
    w = Vault().install()
    w.pack = [Held(2724, 'Casket')]
    w.bank = []
    run(SolveClue(Host(w)))
    expect(w.solves).to_be(1)
    expect(w.opens).to_be(0)


def resumed_casket():
    w = Vault().install()
    w.pack[0] = Held(2724, 'Casket')
    task = SolveClue(Host(w))
    checks = []

    def solve(executor, needs_bank, ranged_kit):
        if w.solves == 1:
            checks.append(w.opens)
            w.pack[0] = CLUE.copy()
            return 'supplies-needed'
        checks.append((w.worn[0].id, w.sharks()))
        w.pack = [i for i in w.pack if i.id != CLUE.id]
        return 'done'
        yield

    w.on_solve = solve
    run(task)
    expect(w.solves).to_be(2)
    expect(checks).to_equal([0, (1231, 15)])
    expect(w.worn[0].id).to_be(BOW.id)
    expect(task.validate()).to_be(False)


def new_solver_clears_death():
    w = Vault().install()
    task = SolveClue(Host(w))
    task.note_death()
    w.real_solver()
    w.pending = True
    expect(run_wait(task.executor.solve_held_clue(lambda m: None))).to_be('dead')
    expect(task.validate()).to_be(False)
    fresh = SolveClue(Host(w))
    expect(run_wait(fresh.executor.solve_held_clue(lambda m: None))).to_be('yield')
    expect(task.validate()).to_be(False)


def preserves(rune_slots, stock, food, bank_bow):
    w = Vault().install()
    w.pack[0] = Held(3552, 'Clue scroll (hard)')
    w.pack.extend([Held(995, 'Coins', 1000), Held(1854, 'Shantay pass')])
    for i in w.bank:
        if i.id == 385:
            i.count = stock
    required = [i.id for i in w.pack] + [2448]
    runes = ['Air rune', 'Earth rune', 'Fire rune', 'Law rune', 'Water rune'][:rune_slots]

    def stock_teleports(kit):
        w.pack.extend([Held(550 + i, runes[i], 100) for i in range(len(runes))])
        return None
        yield

    spy_on(SolveClue, '_stock_teleports', stock_teleports)
    task = SolveClue(Host(w))
    run(task)
    expect(w.sharks()).to_be(food)
    expect(all([any([i.id == id for i in w.pack]) for id in required])).to_be(True)
    expect(all([any([i.name == name for i in w.pack]) for name in runes])).to_be(True)
    expect(any([i.id == BOW.id for i in w.pack])).to_be(not bank_bow)
    expect(any([i.id == BOW.id for i in w.bank])).to_be(bank_bow)
    expect(w.worn[0].id).to_be(1231)
    w.pack = [i for i in w.pack if i.id != 3552]
    run(task)
    expect(w.worn[0].id).to_be(BOW.id)


def entrana_strip():
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    task = SolveClue(Host(w))
    run(task)
    expect(w.worn).to_equal([])
    expect(any([i.id == 1231 for i in w.pack])).to_be(False)
    expect(w.solves).to_be(1)
    w.pack[0] = CLUE.copy()
    w.solves = 0
    w.outcomes = ['supplies-needed', 'yield']
    run(task)
    expect(w.worn[0].id).to_be(1231)
    expect(w.solves).to_be(2)


OUTFIT = [(861, 'Magic shortbow', 1, 3), (1127, 'Rune platebody', 1, 4), (1061, 'Leather boots', 1, 10), (1033, 'Zamorak robe', 1, 7),
          (1731, 'Amulet of power', 1, 2), (1635, 'Gold ring', 1, 12), (1007, 'Cape', 1, 1), (882, 'Bronze arrow', 100, 13)]


def outfit_slot(name):
    for id, n, count, slot in OUTFIT:
        if n == name:
            return slot
    return 3


def every_slot(extra):
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    w.pack.extend([Held(379, 'Lobster') for _ in range(extra)])
    w.worn = [Held(id, name, count, slot) for id, name, count, slot in OUTFIT]

    def equip(name):
        w.open = False
        return w.wear(name, outfit_slot)
        yield

    def withdraw_x(name, count):
        source = None
        for i in w.bank:
            if i.name == name and i.count >= count:
                source = i
                break
        if source is None or len(w.pack) >= 28:
            return False
        source.count -= count
        w.pack.append(source.copy(count=count))
        return True
        yield

    w.on_equip = equip
    w.on_withdraw_x = withdraw_x
    checks = []

    def solve(executor, needs_bank, ranged_kit):
        checks.append((w.worn == [], any([i.id == 3579 for i in w.pack]),
                       all([any([b.id == id and b.count >= count for b in w.bank]) for id, name, count, slot in OUTFIT]),
                       any([any([p.id == id for p in w.pack]) for id, name, count, slot in OUTFIT])))
        w.pack = [i for i in w.pack if i.id != 3579]
        return 'done'
        yield

    w.on_solve = solve
    task = SolveClue(Host(w))
    run(task)
    expect(checks).to_equal([(True, True, True, False)])
    expect(sorted([(i.name, i.count) for i in w.worn])).to_equal(sorted([(name, count) for id, name, count, slot in OUTFIT]))
    expect(task.validate()).to_be(False)


def deposits_fail():
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    w.pack.extend([Held(379, 'Lobster') for _ in range(23)])

    def keep(matches):
        return None
        yield

    w.on_deposit = keep
    task = SolveClue(Host(w))
    run(task)
    expect(len(w.pack)).to_be(28)
    expect(w.worn[0].id).to_be(BOW.id)
    expect(task.validate()).to_be(True)
    expect(w.solves).to_be(0)


def jewellery_only():
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    w.worn = [Held(1635, 'Gold ring', 1, 12)]
    w.walk_ok = False
    w.real_solver()
    spy_on(traversal, 'walk_resilient', lambda tile, **opts: w.walk_and_fire())
    expect(run_wait(ClueExecutor().solve_held_clue(lambda m: None))).to_be('supplies-needed')


def entrana_failure(failure):
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    once = {'used': False}

    def fail_once(*a):
        if once['used']:
            return True
        once['used'] = True
        return False

    def reopen_fails():
        if w.opens == 2 and not once['used']:
            once['used'] = True
            return False
        return True

    if failure == 'close':
        w.on_close = fail_once
    if failure == 'remove':
        w.on_unequip = fail_once
    if failure == 'reopen':
        w.on_open = reopen_fails
    task = SolveClue(Host(w))
    run(task)
    expect(task.validate()).to_be(True)
    expect(any([i.id == 3579 for i in w.pack])).to_be(True)
    expect(w.solves).to_be(0)
    run(task)
    expect(w.worn).to_equal([])
    expect(any([i.id == BOW.id for i in w.bank])).to_be(True)
    w.pack = [i for i in w.pack if i.id != 3579]
    run(task)
    expect(w.worn[0].id).to_be(BOW.id)


def outfit_before_fight(blocked):
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    w.worn = [Held(1305, 'Dragon longsword', 1, 3), Held(1127, 'Rune platebody', 1, 4), Held(1635, 'Gold ring', 1, 12)]
    task = SolveClue(Host(w))
    state = {'fought': False, 'checks': []}

    def refuse(name):
        return False
        yield

    def solve(executor, needs_bank, ranged_kit):
        if w.solves == 1:
            state['checks'].append(w.worn == [])
            w.pack[0] = CLUE.copy()
            state['checks'].append(needs_bank())
            if blocked:
                w.on_equip = refuse
            return 'supplies-needed'
        state['checks'].append(sorted([i.name for i in w.worn]))
        state['checks'].append(needs_bank())
        state['fought'] = True
        return 'yield'
        yield

    w.on_solve = solve
    run(task)
    expect(state['checks'][:2]).to_equal([True, True])
    if not blocked:
        expect(state['checks'][2:]).to_equal([['Dragon longsword', 'Gold ring', 'Rune platebody'], False])
    expect(state['fought']).to_be(not blocked)
    expect(task.validate()).to_be(True)


def partial_ammo():
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    w.worn.append(Held(882, 'Bronze arrow', 100, 13))
    task = SolveClue(Host(w))

    def withdraw_x(name, count):
        source = None
        for i in w.bank:
            if i.name == name and i.count > 0:
                source = i
                break
        if source is None:
            return False
        taken = min(count, 50, source.count)
        source.count -= taken
        held = [i for i in w.pack if i.id == source.id]
        if held:
            held[0].count += taken
        else:
            w.pack.append(source.copy(count=taken))
        return True
        yield

    def solve(executor, needs_bank, ranged_kit):
        w.pack = [i for i in w.pack if i.id != 3579]
        return 'done'
        yield

    w.on_withdraw_x = withdraw_x
    w.on_solve = solve
    run(task)
    expect(task.validate()).to_be(True)
    expect([i.count for i in w.pack if i.id == 882]).to_equal([50])
    run(task)
    expect([i.count for i in w.worn if i.id == 882]).to_equal([100])
    expect(task.validate()).to_be(False)


def stops_before_travel():
    w = Vault().install()
    w.real_solver()
    spy_on(traversal, 'walk_resilient', lambda tile, **opts: w.walk_and_fire())
    expect(run_wait(ClueExecutor().solve_held_clue(lambda m: None, lambda: True))).to_be('supplies-needed')
    expect(w.pending).to_be(False)


def failed_armour():
    w = Vault().install()
    w.pack[0] = CLUE.copy(id=3579)
    w.worn.append(Held(1127, 'Rune platebody', 1, 4))
    state = {'blocked': True}

    def equip(name):
        if name == 'Rune platebody' and state['blocked']:
            return False
        w.open = False
        return w.wear(name, None)
        yield

    def solve(executor, needs_bank, ranged_kit):
        w.pack = [i for i in w.pack if i.id != 3579]
        return 'done'
        yield

    w.on_equip = equip
    w.on_solve = solve
    task = SolveClue(Host(w))
    run(task)
    expect(task.validate()).to_be(True)
    expect(task.owns_equipment()).to_be(True)
    expect(any([i.id == 1127 for i in w.worn])).to_be(False)
    state['blocked'] = False
    run(task)
    expect(any([i.id == 1127 for i in w.worn])).to_be(True)
    expect(task.validate()).to_be(False)
    expect(task.owns_equipment()).to_be(False)


describe('hard kit preparation', lambda: [
    test('keeps the clue and suppresses retries when the READY bank lacks 1231', lambda: lacks(1231)),
    test('keeps the clue and suppresses retries when the READY bank lacks 2448', lambda: lacks(2448)),
    test('keeps the clue and suppresses retries when the READY bank lacks 385', lambda: lacks(385)),
    test('blocks fourteen Sharks', fourteen_sharks),
    test('stocks a bank-only kit and equips DDS before the executor', bank_only_kit),
    test('blocks an equip failure even when ownership and requirements pass', equip_fails),
    test('does not confuse an unknown bank with a confirmed shortage', unknown_bank),
    test('restoration remains runnable after the clue disappears', restoration_after_clue),
    test('casket-only execution needs no hard kit', casket_only),
    test('a resumed hard casket provisions the next guardian and restores the original weapon', resumed_casket),
    test('a new solver clears a previous session guardian death without retrying the failed session', new_solver_clears_death),
    test('preserves restoration and mandatory items when preparing 5 rune slots, 30 stocked', lambda: preserves(5, 30, 15, True)),
    test('preserves restoration and mandatory items when preparing 0 rune slots, 30 stocked', lambda: preserves(0, 30, 15, False)),
    test('preserves restoration and mandatory items when preparing 0 rune slots, 20 stocked', lambda: preserves(0, 20, 15, False)),
    test('preserves restoration and mandatory items when preparing 0 rune slots, 19 stocked', lambda: preserves(0, 19, 15, False)),
    test('allows an Entrana strip and equips again for a later guardian', entrana_strip),
    test('banks every equipment slot for Entrana with 0 extra inventory items', lambda: every_slot(0)),
    test('banks every equipment slot for Entrana with 23 extra inventory items', lambda: every_slot(23)),
    test('keeps a full Entrana pack and equipment when deposits fail', deposits_fail),
    test('an Entrana leg requests banking even when only allowed jewellery is equipped', jewellery_only),
    test('retries an Entrana close failure without losing the original equipment', lambda: entrana_failure('close')),
    test('retries an Entrana remove failure without losing the original equipment', lambda: entrana_failure('remove')),
    test('retries an Entrana reopen failure without losing the original equipment', lambda: entrana_failure('reopen')),
    test('restores the Entrana outfit before the next fight, with blocked equip=False', lambda: outfit_before_fight(False)),
    test('restores the Entrana outfit before the next fight, with blocked equip=True', lambda: outfit_before_fight(True)),
    test('keeps restoration pending after a partial ammunition withdrawal', partial_ammo),
    test('the executor stops before travel while the host has gear to restore', stops_before_travel),
    test('a completed Entrana clue retains ownership until a failed armour equip succeeds', failed_armour),
])


def one_restock():
    w = Vault().install()
    for i in w.bank:
        if i.id == 385:
            i.count = 20
    task = SolveClue(Host(w))
    run(task)
    w.pack = [i for i in w.pack if i.id != 385]
    w.outcomes = ['supplies-needed']
    run(task)
    expect(w.solves).to_be(2)
    expect(any([i.id == CLUE.id for i in w.pack])).to_be(True)
    expect(task.validate()).to_be(False)


def death_stops():
    w = Vault().install()
    task = SolveClue(Host(w))
    w.outcomes = ['dead']
    run(task)
    expect(task.validate()).to_be(False)
    run(task)
    expect(w.solves).to_be(1)
    task.retry()
    expect(task.validate()).to_be(True)


def eats_sharks():
    w = Vault().install()
    spy_on(skills, 'effective', lambda name: 25 if name == 'hitpoints' else 60)

    def solve(executor, needs_bank, ranged_kit):
        yield from sustain.run()
        return 'yield'

    def eat(item, op):
        if op == 'Eat':
            w.eaten.append(item.id)
            w.pack.remove(item)
        return True

    w.on_solve = solve
    w.on_interact = eat
    run(SolveClue(Host(w)))
    expect(w.eaten).to_equal([385])


def shortage_suppressed():
    w = Vault().install()
    w.bank = [i for i in w.bank if i.id != 1231]
    w.snapshot = lambda: w.open
    task = SolveClue(Host(w))
    run(task)
    expect(task.validate()).to_be(False)
    w.open = True
    expect(task.validate()).to_be(False)
    w.bank.append(Held(1231, 'Dragon dagger(p)'))
    expect(task.validate()).to_be(True)


def temporary_dds():
    w = Vault().install()
    task = SolveClue(Host(w))
    run(task)
    for i in w.pack:
        if i.id == CLUE.id:
            i.id = 3579

    def solve(executor, needs_bank, ranged_kit):
        if w.solves == 2:
            return 'supplies-needed'
        w.pack = [i for i in w.pack if i.id != 3579]
        return 'done'
        yield

    w.on_solve = solve
    run(task)
    expect(w.worn[0].id).to_be(BOW.id)
    expect(task.validate()).to_be(False)


def failed_retreat():
    w = Vault().install()
    task = SolveClue(Host(w))
    run(task)
    w.tile = None
    w.outcomes = ['guardian-lost']
    run(task)
    expect(task.validate()).to_be(True)
    w.tile = FALADOR
    run(task)
    expect(w.worn[0].id).to_be(BOW.id)
    expect(task.validate()).to_be(False)


def no_repeat_initial():
    w = Vault().install()
    host = Host(w)
    task = SolveClue(host)
    run(task)
    w.outcomes = ['supplies-needed']
    w.walk_ok = False
    run(task)
    run(task)
    expect(host.initial_trips).to_be(1)


def puzzle_room():
    w = Vault().install()
    w.pack[0] = Held(2799, 'Clue scroll (hard)')
    w.pack.extend([Held(995, 'Coins', 1000), Held(1854, 'Shantay pass')])
    names = ['Air rune', 'Earth rune', 'Fire rune', 'Law rune', 'Water rune']

    def stock_teleports(kit):
        w.pack.extend([Held(550 + i, names[i], 100) for i in range(5)])
        return None
        yield

    spy_on(SolveClue, '_stock_teleports', stock_teleports)
    run(SolveClue(Host(w)))
    expect(w.solves).to_be(1)
    expect(w.sharks()).to_be(15)
    expect(len(w.pack) < 28).to_be(True)
    expect(any([i.id == 2799 for i in w.pack])).to_be(True)


def held_puzzle_box():
    w = Vault().install()
    w.pack[0] = Held(2799, 'Clue scroll (hard)')
    w.pack.append(Held(2800, 'Puzzle box'))
    run(SolveClue(Host(w)))
    expect(w.solves).to_be(1)
    expect(any([i.id == 2800 for i in w.pack])).to_be(True)
    expect(any([i.id == 2800 for i in w.bank])).to_be(False)


def banked_puzzle_box():
    w = Vault().install()
    w.pack[0] = Held(2799, 'Clue scroll (hard)')
    w.bank.extend([Held(2795, 'Puzzle box'), Held(2800, 'Puzzle box')])
    run(SolveClue(Host(w)))
    expect(w.solves).to_be(1)
    expect(any([i.id == 2800 for i in w.pack])).to_be(True)
    expect(any([i.id == 2795 for i in w.pack])).to_be(False)


def reward_pickup():
    w = Vault().install()
    task = SolveClue(Host(w))

    def solve(executor, needs_bank, ranged_kit):
        if w.solves == 1:
            w.pack = [i for i in w.pack if i.id != CLUE.id]
            executor.current = ClueProgress(CLUE.id, 'hard clue', 'reward', 1, 1, 0, None, 0)
            return 'yield'
        executor.current = None
        return 'done'
        yield

    w.on_solve = solve
    run(task)
    expect(task.validate()).to_be(True)
    expect(task.owns_equipment()).to_be(True)
    expect(w.worn[0].id).to_be(1231)
    run(task)
    expect(w.solves).to_be(2)
    expect(w.worn[0].id).to_be(BOW.id)
    expect(task.validate()).to_be(False)


def normal_restore(id, name, outcome):
    w = Vault().install()
    w.pack[0] = Held(3599, 'Clue scroll (medium)')
    w.worn = [Held(id, name, 1, 3)]
    host = Host(w)
    task = SolveClue(host)

    def solve(executor, needs_bank, ranged_kit):
        w.bank.extend(w.worn)
        w.worn = []
        if outcome == 'done':
            w.pack = [Held(379, 'Lobster') for _ in range(28)]
        return outcome
        yield

    w.on_solve = solve
    run(task)
    expect([i.id for i in w.worn]).to_equal([id])
    expect(task.owns_equipment()).to_be(False)
    expect('clue solved' in host.statuses).to_be(outcome == 'done')


def unreclaimed():
    w = Vault().install()
    w.pack[0] = Held(3599, 'Clue scroll (medium)')
    w.worn = [Held(1333, 'Rune scimitar', 1, 3)]
    host = Host(w)
    task = SolveClue(host)

    def solve(executor, needs_bank, ranged_kit):
        w.bank.extend(w.worn)
        w.worn = []
        w.pack = []
        w.walk_ok = False
        return 'done'
        yield

    w.on_solve = solve
    run(task)
    expect(task.validate()).to_be(True)
    expect(task.owns_equipment()).to_be(True)
    expect(host.statuses).not_.to_contain('clue solved')
    w.walk_ok = True
    run(task)
    expect([i.id for i in w.worn]).to_equal([1333])
    expect(host.statuses).to_contain('clue solved')
    expect(task.validate()).to_be(False)


def current_weapon():
    w = Vault().install()
    task = SolveClue(Host(w))

    def solve(executor, needs_bank, ranged_kit):
        w.bank.extend(w.worn)
        w.worn = []
        w.pack = []
        return 'done'
        yield

    w.on_solve = solve
    seen = []
    for id, name in [(1333, 'Rune scimitar'), (1301, 'Adamant longsword'), (1333, 'Rune scimitar')]:
        w.pack = [Held(3599, 'Clue scroll (medium)')]
        w.worn = [Held(id, name, 1, 3)]
        run(task)
        seen.append([i.id for i in w.worn])
    expect(seen).to_equal([[1333], [1301], [1333]])


def restock_keeps_weapon():
    w = Vault().install()
    w.pack[0] = Held(3599, 'Clue scroll (medium)')
    w.worn = [Held(1333, 'Rune scimitar', 1, 3)]
    task = SolveClue(Host(w))
    run(task)
    w.pack.extend(w.worn + [Held(995, 'Coins'), Held(592, 'Ashes')])
    w.worn = []
    w.pack = [i for i in w.pack if i.name != 'Lobster']
    run(task)
    expect(any([i.id == 1333 for i in w.pack])).to_be(True)
    expect(any([i.id == 1333 for i in w.bank])).to_be(False)
    expect(any([i.id == 592 for i in w.bank])).to_be(True)
    expect(task.owns_equipment()).to_be(True)


def unarmed():
    w = Vault().install()
    w.pack[0] = Held(3599, 'Clue scroll (medium)')
    w.worn = []
    host = Host(w)
    task = SolveClue(host)

    def solve(executor, needs_bank, ranged_kit):
        w.pack = []
        return 'done'
        yield

    w.on_solve = solve
    run(task)
    expect(host.statuses).to_contain('clue solved')
    expect(task.validate()).to_be(False)
    expect(task.owns_equipment()).to_be(False)


def altar():
    w = Vault().install()
    w.tile = Tile(3222, 3218, 0)
    spy_on(prayer, 'max', lambda: 60)
    spy_on(prayer, 'full', lambda: False)
    spy_on(prayer, 'points', lambda: 10)
    spy_on(navigator, 'find_path', lambda start, to, **opts: Fake(ok=True, cost=25) if to.x == 3243 else Fake(ok=False, cost=0))
    host = Host(w)
    host.prayer = True
    run(SolveClue(host))
    expect(any([t.x == 3243 and t.z == 3205 for t in w.walks])).to_be(True)
    expect(w.solves).to_be(1)


def pass_stays_banked():
    w = Vault().install()
    w.bank.append(Held(1854, 'Shantay pass', 10))
    run(SolveClue(Host(w)))
    expect(any([i.id == 1854 for i in w.pack])).to_be(False)
    expect(w.banked(1854)).to_be(10)


def pass_deposited():
    w = Vault().install()
    w.pack.append(Held(1854, 'Shantay pass'))
    run(SolveClue(Host(w)))
    expect(any([i.id == 1854 for i in w.pack])).to_be(False)
    expect(w.banked(1854)).to_be(1)


def desert_pass():
    w = Vault().install()
    w.pack[0] = Held(3552, 'Clue scroll (hard)')
    w.bank.append(Held(1854, 'Shantay pass', 10))
    run(SolveClue(Host(w)))
    expect(len([i for i in w.pack if i.id == 1854])).to_be(1)
    expect(w.banked(1854)).to_be(9)


def kharazi_after_ordinary():
    w = Vault().install()
    spy_on(quests, 'status', lambda name: 'complete')
    w.bank.extend([Held(975, 'Machete'), Held(1351, 'Bronze axe')])
    task = SolveClue(Host(w))
    run(task)
    for i in w.pack:
        if i.id == CLUE.id:
            i.id = 3532
    checks = []

    def solve(executor, needs_bank, ranged_kit):
        if w.solves == 2:
            return 'supplies-needed'
        checks.append((any([i.name == 'Machete' for i in w.pack]), any([i.name == 'Bronze axe' for i in w.pack])))
        return 'yield'
        yield

    w.on_solve = solve
    run(task)
    expect(checks).to_equal([(True, True)])
    expect(any([i.id == 3532 for i in w.pack])).to_be(True)
    expect(task.validate()).to_be(True)


def jungle_tools_arrive():
    w = Vault().install()
    spy_on(quests, 'status', lambda name: 'complete')
    w.pack[0] = CLUE.copy(id=3532)
    task = SolveClue(Host(w))
    run(task)
    expect(w.solves).to_be(0)
    expect(task.validate()).to_be(False)
    expect(any([i.id == 3532 for i in w.pack])).to_be(True)
    w.bank.extend([Held(975, 'Machete'), Held(1351, 'Bronze axe')])
    w.open = True
    expect(task.validate()).to_be(True)
    run(task)
    expect(any([i.name == 'Machete' for i in w.pack])).to_be(True)
    expect(any([i.name == 'Bronze axe' for i in w.pack])).to_be(True)
    expect(w.solves).to_be(1)


def jungle_retry(interrupt):
    w = Vault().install()
    spy_on(quests, 'status', lambda name: 'complete')
    w.pack[0] = CLUE.copy(id=3532)
    w.bank.extend([Held(975, 'Machete'), Held(1351, 'Bronze axe')])
    state = {'failed': False}

    def withdraw(name, op):
        if name == 'Machete' and not state['failed']:
            state['failed'] = True
            w.pending = interrupt
            return False
        return w.take(name, op)

    w.on_withdraw = withdraw
    task = SolveClue(Host(w))
    run(task)
    expect(w.solves).to_be(0)
    w.pending = False
    expect(task.validate()).to_be(True)
    run(task)
    expect(any([i.name == 'Machete' for i in w.pack])).to_be(True)
    expect(any([i.name == 'Bronze axe' for i in w.pack])).to_be(True)
    expect(w.solves).to_be(1)


def reset_rebuild():
    w = Vault().install()
    task = SolveClue(Host(w, True, False, 12))
    w.outcomes = ['reset-needed', 'yield']
    run(task)
    remembered = list(task.stripped_gear)
    expect(remembered).to_contain('Magic shortbow')
    while len(w.pack) < 28:
        w.pack.append(Held(536, 'Dragon bones'))
    run(task)
    expect(w.solves).to_be(2)
    expect(any([i.id == 536 for i in w.pack])).to_be(False)
    expect(w.sharks()).to_be(12)
    expect(len([i for i in w.pack if i.id == 952])).to_be(1)
    expect(len(w.pack) < 28).to_be(True)
    expect(task.stripped_gear).to_equal(remembered)
    expect(w.worn[0].id).to_be(1231)
    expect(task.owns_equipment()).to_be(True)


def retains_until_retreat(outcome):
    w = Vault().install()
    task = SolveClue(Host(w))
    run(task)
    w.in_combat = True
    w.outcomes = [outcome]
    w.walk_ok = False
    run(task)
    run(task)
    expect(task.validate()).to_be(True)
    expect(task.owns_equipment()).to_be(True)
    expect(w.worn[0].id).to_be(1231)
    w.in_combat = False
    w.walk_ok = True
    w.outcomes = ['yield']
    run(task)
    expect(w.worn[0].id).to_be(BOW.id if outcome == 'abandon' else 1231)


def death_in_recovery():
    w = Vault().install()
    task = SolveClue(Host(w))
    w.outcomes = ['reset-needed']
    run(task)
    task.note_death()
    run(task)
    expect(task.recovery_pending).to_be(False)
    expect(task.death_blocked).to_be(True)
    expect(task.validate()).to_be(False)
    expect(w.worn[0].id).to_be(BOW.id)


def recovery_shortage():
    w = Vault().install()
    task = SolveClue(Host(w))
    w.outcomes = ['reset-needed', 'yield']
    run(task)
    w.pack = [i for i in w.pack if i.id != 385]
    w.bank = [i for i in w.bank if i.id != 385]
    run(task)
    expect(w.worn[0].id).to_be(BOW.id)
    expect(task.validate()).to_be(False)
    expect(task.owns_equipment()).to_be(False)
    expect(task.recovery_pending).to_be(True)
    expect(w.solves).to_be(1)
    w.open = True
    expect(task.validate()).to_be(False)
    w.bank.append(Held(385, 'Shark', 30))
    expect(task.validate()).to_be(True)
    run(task)
    expect(task.recovery_pending).to_be(False)
    expect(w.worn[0].id).to_be(1231)
    expect(w.sharks()).to_be(15)
    expect(w.solves).to_be(2)


describe('hard trail upkeep and recovery', lambda: [
    test('gives supply-needed one restock attempt and preserves the held clue', one_restock),
    test('death stops retries even if the kit is still present', death_stops),
    test('hard upkeep eats Sharks despite the host selecting Lobster', eats_sharks),
    test('a confirmed shortage stays suppressed across bank reopen until kit contents change', shortage_suppressed),
    test('does not mistake the temporary DDS for original gear after a mid-trail Entrana strip', temporary_dds),
    test('a failed retreat remains runnable rather than releasing the host into a live guardian', failed_retreat),
    test('a failed mid-trail bank trip does not repeat the caller initial-bank hook', no_repeat_initial),
    test('a puzzle clue leaves room for its box without reducing the guardian food supply', puzzle_room),
    test('bank preparation preserves a held puzzle box with its clue', held_puzzle_box),
    test('bank preparation retrieves the current clue puzzle box when it was banked earlier', banked_puzzle_box),
    test('reward pickup keeps ownership after the scroll disappears until collection finishes', reward_pickup),
    test('a normal trail restores its equipped weapon: Rune scimitar, done', lambda: normal_restore(1333, 'Rune scimitar', 'done')),
    test('a normal trail restores its equipped weapon: Adamant longsword, done', lambda: normal_restore(1301, 'Adamant longsword', 'done')),
    test('a normal trail restores its equipped weapon: Rune scimitar, abandon', lambda: normal_restore(1333, 'Rune scimitar', 'abandon')),
    test('an ordinary clue keeps restoration pending when the weapon cannot be reclaimed yet', unreclaimed),
    test('each ordinary trail remembers its current weapon rather than the previous trail or host fallback', current_weapon),
    test('a normal restock preserves the starting weapon in the pack ahead of a stale host weapon', restock_keeps_weapon),
    test('a normal trail started unarmed does not require an unavailable host weapon to finish', unarmed),
    test('clue prayer restoration walks to the reachable Lumbridge altar', altar),
    test('an unrelated hard clue leaves Shantay passes in the bank', pass_stays_banked),
    test('an unrelated clue deposits a pass left over from an earlier trip', pass_deposited),
    test('the desert dig packs a banked Shantay pass', desert_pass),
    test('a Kharazi leg banks for its tools after an earlier ordinary leg', kharazi_after_ordinary),
    test('missing jungle tools keep the clue and resume when the bank receives the tools', jungle_tools_arrive),
    test('retries a stocked jungle-tool withdrawal after interruption=False', lambda: jungle_retry(False)),
    test('retries a stocked jungle-tool withdrawal after interruption=True', lambda: jungle_retry(True)),
    test('bank reset rebuilds a full hard-clue pack with twelve Sharks and preserves the original outfit ledger', reset_rebuild),
    test('a abandon outcome retains combat gear until retreat succeeds', lambda: retains_until_retreat('abandon')),
    test('a reset-needed outcome retains combat gear until retreat succeeds', lambda: retains_until_retreat('reset-needed')),
    test('death during bank recovery releases the recovery flag and restores remembered gear', death_in_recovery),
    test('a recovery kit shortage restores the host outfit and resumes after supplies arrive', recovery_shortage),
])
