"""rs2b0t's test/api/ai/clues/trailUpkeep.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect, with the facades patched as rs2b0t stubs them. rs2b0t swaps a SolveClue's bankFirst on the instance; pocketpy
calls the class's method over one set on an instance, so it's spied on the class here."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.clues.data import CLUE_DB
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.solve import SolveClue

LOBSTER = 'Lobster'
MAX_HP = 70
HELD_CLUE = list(CLUE_DB.keys())[0]


class Pack:
    def __init__(self):
        self.hp = MAX_HP
        self.eaten = 0
        self.dropped = 0
        self.reject_drop = False
        self.operations = []
        self.inv = [Fake(id=id, name=LOBSTER) for id in [1, 2, 3]]
        self.logs = []
        self.incoming = 0
        self.confirmations = []
        self.budgets = []

    def install(self):
        w = self
        stub(sustain, hook=None)
        spy_on(inventory, 'items', lambda: [w.item(i) for i in w.inv])
        spy_on(equipment, 'items', lambda: [])
        spy_on(skills, 'level', lambda name: MAX_HP if name == 'hitpoints' else 70)
        spy_on(skills, 'effective', lambda name: w.hp if name == 'hitpoints' else 70)
        spy_on(game, 'in_combat', lambda: False)
        spy_on(event_signal, 'pending', lambda: False)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', lambda cond, ticks: w.confirm(cond, ticks))
        patch(execution, 'delay_ticks', instant_ticks)
        return self

    def confirm(self, cond, ticks):
        ok = cond()
        self.confirmations.append(ok)
        self.budgets.append(ticks)
        return ok
        yield

    def item(self, i):
        w = self
        held = i

        def interact(op):
            w.operations.append(op)
            if op == 'Drop':
                if w.reject_drop or held.id != 2959:
                    return False
                w.dropped += 1
                w.inv = [x for x in w.inv if x is not held]
                return True
            w.eaten += 1
            w.inv = [x for x in w.inv if x is not held]
            w.hp = max(0, min(MAX_HP, w.hp + 12) - w.incoming)
            return True

        return Fake(id=i.id, name=i.name, count=1, slot=0, noted=False, actions=lambda: ['Drop'] if held.id == 2959 else ['Eat'], interact=interact)


class Host:
    def __init__(self, w):
        self.w = w

    def log(self, m):
        self.w.logs.append(m)

    def set_status(self, text):
        pass

    def is_food(self, name):
        return name == LOBSTER

    def food_name(self):
        return LOBSTER

    def food_withdraw(self):
        return 8


def solving(trail):
    """Stands trail(w) in for the executor: a Wait the trail runs in place of solving."""
    spy_on(ClueExecutor, 'solve_held_clue', lambda *a: trail())


def mid_trail():
    w = Pack().install()
    seen = []

    def trail():
        w.hp = 30
        yield from sustain.run()
        seen.append(w.eaten)
        return 'done'

    solving(trail)
    run_wait(SolveClue(Host(w)).execute())
    expect(seen).to_equal([1])
    expect(w.hp).to_be(42)
    expect(any(['eating Lobster' in l for l in w.logs])).to_be(True)


def cancelled_bite():
    w = Pack().install()
    w.incoming = 20

    def trail():
        w.hp = 44
        yield from sustain.run()
        yield from sustain.run()
        yield from sustain.run()
        return 'done'

    solving(trail)
    run_wait(SolveClue(Host(w)).execute())
    expect(w.eaten).to_be(3)
    expect(w.confirmations).to_equal([True, True, True])
    expect(all([t <= 2 for t in w.budgets])).to_be(True)


def dry_spell():
    w = Pack().install()
    banks = []

    def abandon():
        return 'abandon'
        yield

    def bank_first(*a):
        banks.append(len(w.inv))
        return True
        yield

    solving(abandon)
    spy_on(SolveClue, '_bank_first', bank_first)
    clue = Fake(id=HELD_CLUE, name='Clue scroll')
    task = SolveClue(Host(w))
    task.banked_this_solve = True
    w.inv = [clue]
    run_wait(task.execute())
    expect(len(banks)).to_be(1)
    task.banked_this_solve = True
    run_wait(task.execute())
    expect(len(banks)).to_be(1)
    w.inv = [clue, Fake(id=1, name=LOBSTER)]
    task.banked_this_solve = True
    run_wait(task.execute())
    w.inv = [clue]
    task.banked_this_solve = True
    run_wait(task.execute())
    expect(len(banks)).to_be(2)


def full_health():
    w = Pack().install()

    def trail():
        yield from sustain.run()
        return 'done'

    solving(trail)
    run_wait(SolveClue(Host(w)).execute())
    expect(w.eaten).to_be(0)


def host_hook_back():
    w = Pack().install()

    def host_hook():
        return None
        yield

    stub(sustain, hook=host_hook)
    during = []

    def trail():
        during.append(sustain.hook)
        return 'abandon'
        yield

    solving(trail)
    run_wait(SolveClue(Host(w)).execute())
    expect(during[0]).not_.to_be(host_hook)
    expect(sustain.hook).to_be(host_hook)


def empty_pack():
    w = Pack().install()
    w.inv = []

    def trail():
        w.hp = 5
        yield from sustain.run()
        return 'done'

    solving(trail)
    run_wait(SolveClue(Host(w)).execute())
    expect(w.eaten).to_be(0)


describe('trail upkeep', lambda: [
    test('a host with no hook of its own still eats while the trail runs', mid_trail),
    test('a bite that damage cancels out still confirms, so the next pump can eat', cancelled_bite),
    test('an empty pack sends the bot back to the bank, once per dry spell', dry_spell),
    test('full health eats nothing', full_health),
    test("the host's own hook is put back when the trail ends", host_hook_back),
    test('an empty pack eats nothing rather than throwing', empty_pack),
])


def rotten_dropped():
    w = Pack().install()
    gone = []

    def trail():
        w.inv.append(Fake(id=952, name='Spade'))
        for _ in range(2):
            w.inv.append(Fake(id=2959, name='Rotten food'))
            yield from sustain.run()
            gone.append(not any([i.id == 2959 for i in w.inv]))
        return 'yield'

    solving(trail)
    run_wait(SolveClue(Host(w)).execute())
    expect(gone).to_equal([True, True])
    expect(w.dropped).to_be(2)
    expect(w.eaten).to_be(0)
    expect([i.id for i in w.inv]).to_equal([1, 2, 3, 952])


def rotten_retried():
    w = Pack().install()
    seen = []

    def trail():
        w.hp = 30
        w.inv.append(Fake(id=2959, name='Rotten food'))
        w.reject_drop = True
        yield from sustain.run()
        seen.append((w.operations[0], w.hp, any([i.id == 2959 for i in w.inv])))
        w.reject_drop = False
        yield from sustain.run()
        seen.append(any([i.id == 2959 for i in w.inv]))
        return 'yield'

    solving(trail)
    run_wait(SolveClue(Host(w)).execute())
    expect(seen).to_equal([('Eat', 42, True), False])
    expect(w.dropped).to_be(1)
    expect(len([op for op in w.operations if op == 'Drop'])).to_be(2)


describe('rotten food', lambda: [
    test('trail upkeep drops newly rotten food at full health and leaves supplies alone', rotten_dropped),
    test('a rejected rotten-food drop retries on later upkeep after healing', rotten_retried),
])
