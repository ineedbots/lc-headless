"""rs2b0t's test/api/ai/clues/initialBank.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect. It reads the walker's bank list, so it runs with the real cache. rs2b0t reaches into a SolveClue's private
fields; here they're plain attributes."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.solve import SolveClue


def held(id, name, slot=0):
    return Fake(id=id, name=name, count=1, slot=slot, noted=False)


CLUE = held(3490, 'Clue scroll (easy)')


def upkeep():
    return None
    yield


class Host:
    def __init__(self, w, food='', prepare=None):
        self.w = w
        self.food = food
        if prepare is not None:
            self.prepare_initial_bank = prepare

    def log(self, m):
        pass

    def set_status(self, text):
        pass

    def is_food(self, name):
        return name == 'Lobster'

    def food_name(self):
        return self.food

    def food_withdraw(self):
        return 20

    def use_teleports(self):
        return False

    def restore_prayer(self):
        return False


class Banking:
    def __init__(self):
        self.pack = [CLUE, held(536, 'Dragon bones', 1)]
        self.here = Tile(2900, 9800, 0)
        self.events = []
        self.open = False
        self.reject_open = False
        self.reject_deposit = False
        self.snapshot_ready = True
        self.outcomes = ['yield']
        self.solves = 0
        self.known_tile = True

    def install(self):
        w = self
        stub(sustain, hook=upkeep)
        spy_on(inventory, 'items', lambda: list(w.pack))
        spy_on(inventory, 'first', lambda name: w.first(name))
        spy_on(inventory, 'count', lambda name: len([i for i in w.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', lambda id: len([i for i in w.pack if i.id == id]))
        spy_on(inventory, 'free', lambda: 28 - len(w.pack))
        spy_on(inventory, 'is_full', lambda: len(w.pack) >= 28)
        spy_on(equipment, 'items', lambda: [])
        spy_on(equipment, 'contains', lambda name: False)
        spy_on(game, 'tile', lambda: w.here if w.known_tile else None)
        spy_on(game, 'in_combat', lambda: False)
        spy_on(event_signal, 'pending', lambda: False)
        patch(execution, 'delay_until', instant_until)
        spy_on(traversal, 'walk_resilient', lambda tile, **opts: w.walk(tile))
        spy_on(bank, 'open_nearest', lambda *a: w.open_bank())
        spy_on(bank, 'open_nearest_access', lambda *a: w.open_bank())
        spy_on(bank, 'open_npc_access', lambda *a: w.open_bank())
        spy_on(bank, 'is_open', lambda: w.open)
        spy_on(bank, 'ready', lambda: w.open and w.snapshot_ready)
        spy_on(bank, 'wait_ready', lambda timeout_ms=4000: w.wait_ready())
        spy_on(bank, 'items', lambda: [])
        spy_on(bank, 'count', lambda name: 0)
        spy_on(bank, 'count_by_id', lambda id: 0)
        spy_on(bank, 'deposit_all_matching', lambda matches: w.deposit(matches))
        spy_on(bank, 'withdraw', lambda name, op='Withdraw 1': False)
        spy_on(bank, 'withdraw_x', lambda name, count: instant_until(lambda: False))
        spy_on(bank, 'close', lambda: w.close())
        spy_on(ClueExecutor, 'solve_held_clue', lambda *a: w.solve())
        return self

    def first(self, name):
        for i in self.pack:
            if i.name == name:
                return i
        return None

    def walk(self, tile):
        self.here = Tile(tile.x, tile.z, tile.level)
        self.events.append(f'walk:{self.here.x},{self.here.z}')
        return True
        yield

    def open_bank(self):
        self.events.append(f'open:{self.here.x},{self.here.z}')
        self.open = not self.reject_open
        return self.open
        yield

    def deposit(self, matches):
        self.events.append('deposit')
        if not self.reject_deposit:
            self.pack = [i for i in self.pack if not matches(i.name or '', i.id)]
        return None
        yield

    def wait_ready(self):
        return self.open and self.snapshot_ready
        yield

    def close(self):
        self.open = False
        return True
        yield

    def solve(self):
        self.events.append('solve')
        self.solves += 1
        return self.outcomes[min(self.solves, len(self.outcomes)) - 1]
        yield


def caller_bank(w):
    def prepare():
        expect(sustain.hook).to_be(upkeep)
        w.events.append('exit')
        w.here = Tile(2946, 3369, 0)
        return True
        yield

    return prepare


def keeps_clue():
    w = Banking().install()
    task = SolveClue(Host(w, '', caller_bank(w)))
    run_wait(task.execute())
    expect(w.events).to_equal(['exit', 'open:2946,3369', 'deposit', 'solve'])
    expect(w.pack).to_equal([CLUE])
    expect(task.banked_this_solve).to_be(True)
    expect(sustain.hook).to_be(upkeep)


def preparation_fails():
    w = Banking().install()
    w.known_tile = False

    def refuse():
        return False
        yield

    task = SolveClue(Host(w, '', refuse))
    run_wait(task.execute())
    expect(w.events).to_equal([])
    expect(task.banked_this_solve).to_be(False)
    expect(w.pack[0]).to_be(CLUE)
    expect(sustain.hook).to_be(upkeep)


def step_fails(failure):
    w = Banking().install()
    w.reject_open = failure == 'open'
    w.reject_deposit = failure == 'deposit'
    task = SolveClue(Host(w, '', caller_bank(w)))
    run_wait(task.execute())
    expect(w.events).not_.to_contain('solve')
    expect(task.banked_this_solve).to_be(False)
    expect(w.pack[0]).to_be(CLUE)


def generic_caller():
    w = Banking().install()
    run_wait(SolveClue(Host(w)).execute())
    expect(w.events).to_equal(['walk:3094,3493', 'open:3094,3493', 'deposit', 'solve'])


def no_known_bank():
    w = Banking().install()
    w.known_tile = False
    run_wait(SolveClue(Host(w)).execute())
    expect(w.events).to_equal(['solve'])


def mid_trail_restock():
    w = Banking().install()
    task = SolveClue(Host(w, 'Lobster', caller_bank(w)))
    task.banked_this_solve = True
    run_wait(task.execute())
    expect(w.events).to_equal(['walk:3094,3493', 'open:3094,3493', 'deposit', 'solve'])


def booth_opens(succeeds):
    w = Banking().install()

    def booth(*a):
        expect(w.here.equals(Tile(2946, 3369, 0))).to_be(True)
        w.open = succeeds
        return True
        yield

    spy_on(bank, 'open_nearest', booth)
    spy_on(bank, 'open_nearest_access', booth)
    spy_on(bank, 'open_npc_access', booth)
    task = SolveClue(Host(w, '', caller_bank(w)))
    run_wait(task.execute())
    expect('solve' in w.events).to_be(succeeds)
    expect(task.banked_this_solve).to_be(succeeds)
    expect(w.pack[0]).to_be(CLUE)


def entrana_gear():
    w = Banking().install()
    w.outcomes = ['abandon']
    task = SolveClue(Host(w, '', caller_bank(w)))
    task.banked_this_solve = True
    task.stripped_gear = ['Rune platebody']
    run_wait(task.execute())
    expect(w.events).to_equal(['solve', 'walk:3094,3493', 'open:3094,3493'])


def snapshot_not_ready():
    w = Banking().install()
    w.snapshot_ready = False
    task = SolveClue(Host(w, '', caller_bank(w)))
    run_wait(task.execute())
    expect(w.events).to_equal(['exit', 'open:2946,3369'])
    expect(task.banked_this_solve).to_be(False)
    expect(w.pack[0]).to_be(CLUE)


def stuck_rebuild():
    w = Banking().install()
    task = SolveClue(Host(w, '', caller_bank(w)))
    task.banked_this_solve = True
    w.here = Tile(3250, 3420, 0)
    w.pack = [CLUE] + [held(952, 'Spade', slot + 1) for slot in range(27)]
    w.outcomes = ['reset-needed', 'yield']
    run_wait(task.execute())
    expect(w.events).to_equal(['solve'])
    expect(task.owns_equipment()).to_be(True)
    run_wait(task.execute())
    expect(w.events).to_equal(['solve', 'walk:3253,3420', 'open:3253,3420', 'deposit', 'solve'])
    expect(w.pack).to_equal([CLUE])
    expect(task.banked_this_solve).to_be(True)


def failed_reset_deposit():
    w = Banking().install()
    task = SolveClue(Host(w, '', caller_bank(w)))
    task.banked_this_solve = True
    w.outcomes = ['reset-needed', 'yield']
    run_wait(task.execute())
    w.reject_deposit = True
    run_wait(task.execute())
    expect(w.solves).to_be(1)
    expect(task.owns_equipment()).to_be(True)
    w.reject_deposit = False
    run_wait(task.execute())
    expect(w.solves).to_be(2)
    expect(w.pack).to_equal([CLUE])


def riddle_key():
    w = Banking().install()
    task = SolveClue(Host(w))
    task.banked_this_solve = True
    riddle = held(2831, 'Clue scroll (medium)')
    key = held(2832, 'Key', 1)
    w.pack = [riddle, key, held(536, 'Dragon bones', 2)]
    w.outcomes = ['reset-needed', 'yield']
    run_wait(task.execute())
    run_wait(task.execute())
    expect(w.pack).to_equal([riddle, key])
    expect(w.solves).to_be(2)


describe('the initial bank', lambda: [
    test('keeps the clue and deposits loot before solving at the caller bank', keeps_clue),
    test('blocks solving and banking when initial preparation fails even without a known tile', preparation_fails),
    test('blocks solving and keeps the clue when open fails', lambda: step_fails('open')),
    test('blocks solving and keeps the clue when deposit fails', lambda: step_fails('deposit')),
    test('keeps the default nearest-bank route for a generic caller', generic_caller),
    test('keeps the legacy no-known-bank behavior for a generic caller', no_known_bank),
    test('uses the default bank for a mid-trail restock without repeating caller preparation', mid_trail_restock),
    test('requires an actual open bank after the booth interaction succeeds', lambda: booth_opens(True)),
    test('requires an actual open bank after the booth interaction fails', lambda: booth_opens(False)),
    test('restores Entrana gear at the default bank without caller preparation', entrana_gear),
    test('blocks the initial handoff when the bank opens without a ready snapshot', snapshot_not_ready),
    test('a stuck clue rebuilds its pack at the nearest bank without repeating the host trip', stuck_rebuild),
    test('a failed reset deposit blocks the fresh attempt until the pack is rebuilt', failed_reset_deposit),
    test('reset keeps an earned riddle key so the server does not refuse another drop', riddle_key),
])
