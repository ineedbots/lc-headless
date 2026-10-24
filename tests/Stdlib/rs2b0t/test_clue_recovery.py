"""rs2b0t's test/api/ai/clues: stuckRecovery.test.ts and legPreparation.test.ts (MIT, see thirdparty/rs2b0t), on
spec.py's describe, test and expect, with the facades patched as rs2b0t spies on them."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.clues import executor as executor_module
from rs2004.clues.executor import ClueExecutor


def clue_item(w, id, name=None, count=1):
    held = Fake(id=id)

    def interact(op):
        return w.interact(held, op)

    return Fake(id=id, name=name or ('Spade' if id == 952 else 'Clue scroll'), count=count, slot=0, noted=False,
                actions=lambda: ['Dig'], interact=interact)


class Stall:
    """A dig leg whose walk stalls behind an open interface until it's closed."""

    def __init__(self):
        self.blocked = True
        self.pending = False
        self.resets = 0
        self.walks = 0
        self.repaths = 0
        self.logs = []
        self.ids = [2713, 952]
        self.walk_result = None
        self.on_close = None
        self.on_interact = None
        self.quest = 'complete'

    def install(self):
        w = self
        spy_on(inventory, 'items', lambda: [clue_item(w, id) for id in w.ids])
        spy_on(inventory, 'first', lambda name: w.first(name))
        spy_on(inventory, 'count', lambda name: len([i for i in w.ids if (name == 'Spade') == (i == 952)]))
        spy_on(inventory, 'count_by_id', lambda id: len([i for i in w.ids if i == id]))
        spy_on(inventory, 'is_full', lambda: False)
        spy_on(equipment, 'items', lambda: [])
        spy_on(ground_items, 'query', querying(lambda: []))
        spy_on(reader, 'main_modal', lambda: 1 if w.blocked else -1)
        spy_on(reader, 'count_dialog_open', lambda: False)
        spy_on(game, 'tile', lambda: Tile(3000, 3000, 0))
        spy_on(game, 'in_combat', lambda: False)
        spy_on(quests, 'status', lambda name: w.quest)
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(sustain, 'run', lambda: instant_until(lambda: True))
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'is_open', lambda: False)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: w.walk())
        spy_on(traversal, 'request_repath', lambda why: w.repath())
        spy_on(modals, 'close', lambda: w.close())
        spy_on(settings_store, 'save', lambda *a: None)
        return self

    def first(self, name):
        for i in self.ids:
            if (name == 'Spade') == (i == 952):
                return clue_item(self, i)
        return None

    def walk(self):
        self.walks += 1
        return (not self.blocked) if self.walk_result is None else self.walk_result
        yield

    def repath(self):
        self.repaths += 1

    def close(self):
        self.resets += 1
        self.blocked = False
        if self.on_close is not None:
            self.on_close()
        return True
        yield

    def interact(self, held, op):
        if self.on_interact is not None:
            return self.on_interact(held, op)
        if held.id == 952:
            self.ids = [952]
        return True

    def log(self, m):
        self.logs.append(m)


def solve(w, executor):
    return run_wait(executor.solve_held_clue(w.log))


def one_reset():
    w = Stall().install()
    executor = ClueExecutor()
    expect(solve(w, executor)).to_be('reset-needed')
    expect(2713 in w.ids).to_be(True)
    expect(solve(w, executor)).to_be('done')
    expect(w.resets).to_be(1)
    expect(w.walks).to_be(5)
    expect(w.repaths).to_be(1)
    expect(w.ids).to_equal([952])
    expect(any(['resetting' in l for l in w.logs])).to_be(True)


def second_stall():
    w = Stall().install()
    w.walk_result = False
    executor = ClueExecutor()
    expect(solve(w, executor)).to_be('reset-needed')
    expect(solve(w, executor)).to_be('abandon')
    expect(w.resets).to_be(1)
    expect(w.walks).to_be(8)
    expect(2713 in w.ids).to_be(True)


def event_budget():
    w = Stall().install()

    def on_close():
        w.pending = True

    w.on_close = on_close
    executor = ClueExecutor()
    expect(solve(w, executor)).to_be('reset-needed')
    expect(solve(w, executor)).to_be('yield')
    w.pending = False
    w.blocked = True
    expect(solve(w, executor)).to_be('abandon')
    expect(w.resets).to_be(1)
    expect(w.walks).to_be(8)


def next_leg():
    w = Stall().install()

    def on_interact(held, op):
        if held.id != 952:
            return False
        if 2713 in w.ids:
            w.ids = [2716, 952]
            w.blocked = True
        else:
            w.ids = [952]
        return True

    w.on_interact = on_interact
    executor = ClueExecutor()
    expect(solve(w, executor)).to_be('reset-needed')
    expect(solve(w, executor)).to_be('reset-needed')
    expect(solve(w, executor)).to_be('done')
    expect(w.resets).to_be(2)
    expect(w.walks).to_be(10)


def quest_unmet():
    w = Stall().install()
    w.ids = [3564]
    w.quest = 'not_started'
    expect(solve(w, ClueExecutor())).to_be('abandon')
    expect(w.resets).to_be(0)
    expect(w.walks).to_be(0)


describe('stuck recovery', lambda: [
    test('a stalled clue closes the blocking interface and completes after one reset', one_reset),
    test('a second stalled attempt abandons instead of resetting forever', second_stall),
    test('an event yield does not renew the reset budget for the same clue', event_budget),
    test('the next clue leg receives its own reset allowance', next_leg),
    test('an unmet quest requirement does not trigger navigation recovery', quest_unmet),
])


# Leg preparation (legPreparation.test.ts)

class Legs:
    def __init__(self):
        self.pending = False
        self.pack = []
        self.digs = 0
        self.ids = [2713, 2716, 2719]

    def install(self):
        w = self
        spy_on(inventory, 'items', lambda: [w.item(i) for i in w.pack])
        spy_on(inventory, 'first', lambda name: w.first(name))
        spy_on(inventory, 'count', lambda name: sum([i.count for i in w.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', lambda id: sum([i.count for i in w.pack if i.id == id]))
        spy_on(inventory, 'is_full', lambda: False)
        spy_on(equipment, 'items', lambda: [Fake(id=1305, name='Dragon longsword', count=1, slot=3, noted=False)])
        spy_on(ground_items, 'query', querying(lambda: []))
        spy_on(skills, 'level', lambda name: 75)
        spy_on(skills, 'effective', lambda name: 75)
        spy_on(quests, 'status', lambda name: 'complete')
        spy_on(game, 'tile', lambda: Tile(2987, 3963, 0))
        spy_on(game, 'in_combat', lambda: False)
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'is_open', lambda: False)
        spy_on(reader, 'count_dialog_open', lambda: False)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: instant_until(lambda: True))
        return self

    def first(self, name):
        for i in self.pack:
            if i.name == name:
                return self.item(i)
        return None

    def item(self, i):
        w = self
        held = i

        def interact(op):
            if held.id != 952 or op != 'Dig':
                return False
            w.digs += 1
            w.pack = [Fake(id=w.ids[w.digs], name='Clue scroll', count=1)] if w.digs < len(w.ids) else []
            if w.digs == len(w.ids):
                w.pending = True
            return True

        return Fake(id=i.id, name=i.name, count=i.count, slot=0, noted=False, actions=lambda: ['Dig'], interact=interact)


def pack_of(*rows):
    return [Fake(id=r[0], name=r[1], count=r[2] if len(r) > 2 else 1) for r in rows]


def kharazi(id):
    w = Legs().install()
    w.pack = pack_of((id, 'Clue scroll'), (952, 'Spade'), (2574, 'Sextant'), (2575, 'Watch'), (2576, 'Chart'),
                     (2448, 'Superantipoison(4)'), (385, 'Shark', 15))
    expect(run_wait(ClueExecutor().solve_held_clue(lambda m: None))).to_be('supplies-needed')
    expect(any([i.id == id for i in w.pack])).to_be(True)


def later_leg():
    w = Legs().install()
    w.pack = pack_of((w.ids[0], 'Clue scroll'))

    def spade(log):
        w.pack.append(Fake(id=952, name='Spade', count=1))
        return True
        yield

    patch(executor_module, 'ensure_spade', spade)
    expect(run_wait(ClueExecutor().solve_held_clue(lambda m: None))).to_be('yield')
    expect(w.digs).to_be(3)


describe('leg preparation', lambda: [
    test('Kharazi clue 3532 requests a bank stop for tools instead of abandoning', lambda: kharazi(3532)),
    test('Kharazi clue 3534 requests a bank stop for tools instead of abandoning', lambda: kharazi(3534)),
    test('Kharazi clue 3536 requests a bank stop for tools instead of abandoning', lambda: kharazi(3536)),
    test('a later leg gets its own tool-acquisition attempts', later_leg),
])
