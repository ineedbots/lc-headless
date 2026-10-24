"""rs2b0t's test/api/ai/clues: gnomePilot.test.ts, puzzleRoom.test.ts and walkToBank.test.ts (MIT, see
thirdparty/rs2b0t), on spec.py's describe, test and expect, with the facades patched as rs2b0t spies on them.
gnomePilot's collision-pack check reads rs2b0t's pack."""

from rs2004 import execution
from rs2004.clues import puzzle_box
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.steps import PILOT_APPROACH, PILOT_REFUGE
from rs2004.clues.solve import walk_to_bank
from rs2004.clues.travel import set_trail_teleports
from rs2004.quests.exec import primitives

SHARK = 385


def item(id, name='Item', count=1, noted=False):
    return Fake(id=id, name=name, count=count, noted=noted, actions=lambda: [], interact=lambda op: True)


class Glider:
    """The White Wolf Mountain glider's world: wolves fighting the bot until it shelters."""

    def __init__(self):
        self.here = Tile(2847, 3499, 0)
        self.combat = True
        self.pending = False
        self.walked = []
        self.retaliation = True
        self.hp = 60
        self.pack = [item(3570), item(3571)] + [item(SHARK, 'Shark') for _ in range(12)]
        self.npc_dialogs = 0
        self.dialog = False
        self.pilot = None

    def install(self):
        w = self
        spy_on(inventory, 'items', lambda: list(w.pack))
        spy_on(inventory, 'count_by_id', lambda id: sum([i.count for i in w.pack if i.id == id and not i.noted]))
        spy_on(inventory, 'first', lambda name: None)
        spy_on(inventory, 'is_full', lambda: len(w.pack) >= 28)
        spy_on(game, 'tile', lambda: w.here)
        spy_on(game, 'in_combat', lambda: w.combat)
        spy_on(game, 'auto_retaliate_on', lambda: w.retaliation)
        spy_on(game, 'set_auto_retaliate', lambda on: w.retaliate(on))
        spy_on(skills, 'effective', lambda name: w.hp)
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(chat_dialog, 'is_open', lambda: w.dialog)
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(reader, 'count_dialog_open', lambda: False)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: w.walk(dest))
        spy_on(reach, 'npc_dialog', lambda name, near, **kw: w.npc_dialog())
        spy_on(npcs, 'query', querying(lambda: [w.pilot] if w.pilot is not None else []))
        return self

    def retaliate(self, on):
        self.retaliation = on
        return True

    def walk(self, dest):
        self.walked.append(Tile(dest.x, dest.z, dest.level))
        self.here = self.walked[-1]
        self.combat = False
        return True
        yield

    def npc_dialog(self):
        self.npc_dialogs += 1
        self.pending = True
        return 'retry'
        yield


def solve():
    return run_wait(ClueExecutor().solve_held_clue(lambda m: None))


def walking(w, fn):
    """Patches the glider's walks to fn(dest), a function giving True or False."""
    def walk(dest, **opts):
        return fn(dest)
        yield
    spy_on(traversal, 'walk_resilient', walk)


def puzzle(w, fn):
    """Patches the puzzle box to fn(), giving True or False; gives the spy."""
    def solve_held(id, log):
        return fn()
        yield
    return spy_on(puzzle_box, 'solve_held', solve_held)


def shelters_first():
    w = Glider().install()
    at_puzzle = []
    fighting = [True]

    def solved():
        at_puzzle.append(w.here)
        fighting[0] = w.combat
        w.pending = True
        return False

    puzzle(w, solved)
    expect(solve()).to_be('yield')
    expect(len(at_puzzle)).to_be(1)
    expect(at_puzzle[0].equals(PILOT_REFUGE)).to_be(True)
    expect(fighting[0]).to_be(False)
    expect(w.retaliation).to_be(True)


def failed_retreat():
    w = Glider().install()
    walking(w, lambda dest: False)
    spy = puzzle(w, lambda: False)
    expect(solve()).to_be('yield')
    expect(spy.called()).to_be(False)
    expect(any([i.id == 3570 for i in w.pack])).to_be(True)
    expect(w.retaliation).to_be(True)


def event_in_retreat():
    w = Glider().install()

    def walk(dest):
        w.pending = True
        return False

    walking(w, walk)
    spy = puzzle(w, lambda: False)
    expect(solve()).to_be('yield')
    expect(spy.called()).to_be(False)
    expect(w.npc_dialogs).to_be(0)


def persistent_combat():
    w = Glider().install()

    def walk(dest):
        w.walked.append(Tile(dest.x, dest.z, dest.level))
        w.here = w.walked[-1]
        return True

    walking(w, walk)
    spy = puzzle(w, lambda: True)
    expect(solve()).to_be('yield')
    expect(spy.called()).to_be(False)
    expect(len(w.walked)).to_be(1)
    expect(w.walked[0].equals(PILOT_REFUGE)).to_be(True)


def unsafe_food():
    w = Glider().install()
    w.pack = [item(3570), item(3571), item(SHARK, 'Shark')]
    spy = puzzle(w, lambda: True)
    expect(solve()).to_be('supplies-needed')
    expect(spy.called()).to_be(False)
    expect(w.walked).to_equal([])


def retaliation_stays_off():
    w = Glider().install()
    w.retaliation = False

    def solved():
        w.pending = True
        return False

    puzzle(w, solved)
    solve()
    expect(w.retaliation).to_be(False)


def death_in_retreat():
    w = Glider().install()

    def walk(dest):
        w.hp = 0
        return False

    walking(w, walk)
    spy = puzzle(w, lambda: True)
    expect(solve()).to_be('dead')
    expect(spy.called()).to_be(False)


def handoff(dead):
    w = Glider().install()

    def interact(op):
        w.dialog = True
        return True

    w.pilot = Fake(index=1, id=170, name='Gnome pilot', tile=lambda: Tile(2847, 3499, 0), distance=lambda: 1, actions=lambda: ['Talk-to'], interact=interact)

    def solved():
        expect(w.here.equals(PILOT_REFUGE)).to_be(True)
        return True

    puzzle(w, solved)

    def talk_through(name, prefer, log, gap_ms=None):
        if dead:
            w.hp = 0
            w.combat = True
        else:
            w.pending = True
        return True
        yield

    talked = spy_on(primitives, 'talk_through', talk_through)
    expect(solve()).to_be('dead' if dead else 'yield')
    expect([[t.x, t.z] for t in w.walked]).to_equal([[PILOT_REFUGE.x, PILOT_REFUGE.z], [PILOT_APPROACH.x, PILOT_APPROACH.z]])
    expect(talked.calls[0][0:2]).to_equal(('Gnome pilot', []))


def new_aggro():
    w = Glider().install()
    puzzle(w, lambda: True)

    def walk(dest):
        w.walked.append(Tile(dest.x, dest.z, dest.level))
        w.here = w.walked[-1]
        w.combat = w.here.equals(PILOT_APPROACH)
        return True

    walking(w, walk)
    clicks = []
    w.pilot = Fake(index=1, id=170, name='Gnome pilot', tile=lambda: Tile(2847, 3499, 0), distance=lambda: 1, actions=lambda: ['Talk-to'],
                   interact=lambda op: clicks.append(op) or True)
    expect(solve()).to_be('yield')
    expect([[t.x, t.z] for t in w.walked]).to_equal([[PILOT_REFUGE.x, PILOT_REFUGE.z], [PILOT_APPROACH.x, PILOT_APPROACH.z], [PILOT_REFUGE.x, PILOT_REFUGE.z]])
    expect(clicks).to_equal([])


def noted_sharks():
    w = Glider().install()
    w.pack = [item(3570), item(386, 'Shark', 12, True)]
    expect(solve()).to_be('supplies-needed')
    expect(w.walked).to_equal([])


def death_in_puzzle():
    w = Glider().install()

    def solved():
        w.hp = 0
        return True

    puzzle(w, solved)
    expect(solve()).to_be('dead')
    expect(len(w.walked)).to_be(1)


describe('the gnome pilot', lambda: [
    test('leaves wolf combat before opening the pilot puzzle', shelters_first),
    test('a failed retreat preserves the clue without opening its puzzle', failed_retreat),
    test('an event during retreat prevents puzzle and dialogue input', event_in_retreat),
    test('persistent wolf combat keeps the puzzle closed and the clue retryable', persistent_combat),
    test('unsafe food reserves request a restock before the pilot approach', unsafe_food),
    test('retaliation stays off when it was already disabled', retaliation_stays_off),
    test('death during retreat stops the trail instead of retrying the pilot', death_in_retreat),
    test('pilot handoff stops correctly when the bot lives', lambda: handoff(False)),
    test('pilot handoff stops correctly on a death during dialogue', lambda: handoff(True)),
    test('new aggro on the pilot approach retreats without starting a conversation', new_aggro),
    test('noted Sharks do not count as food for the pilot trip', noted_sharks),
    test('death during a puzzle stops before returning to the pilot', death_in_puzzle),
])


# The puzzle room (puzzleRoom.test.ts)

class Room:
    def __init__(self):
        self.pack = [item(2799, 'Clue scroll (hard)')] + [item(SHARK, 'Shark') for _ in range(27)]
        self.pending = False
        self.npc_dialogs = 0

    def install(self):
        w = self
        spy_on(inventory, 'items', lambda: list(w.pack))
        spy_on(inventory, 'count_by_id', lambda id: len([i for i in w.pack if i.id == id]))
        spy_on(inventory, 'first', lambda name: None)
        spy_on(inventory, 'is_full', lambda: len(w.pack) >= 28)
        spy_on(reader, 'count_dialog_open', lambda: False)
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(game, 'tile', lambda: Tile(2957, 3511, 0))
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'is_open', lambda: False)
        patch(execution, 'delay_until', instant_until)
        spy_on(reach, 'npc_dialog', lambda name, near, **kw: w.npc_dialog())
        return self

    def npc_dialog(self):
        self.npc_dialogs += 1
        self.pending = True
        return 'retry'
        yield


def full_pack():
    w = Room().install()
    expect(solve()).to_be('supplies-needed')
    expect(w.npc_dialogs).to_be(0)
    expect(any([i.id == 2799 for i in w.pack])).to_be(True)


def free_slot():
    w = Room().install()
    w.pack.pop()
    expect(solve()).to_be('yield')
    expect(w.npc_dialogs).to_be(1)


def box_held():
    w = Room().install()
    w.pack[1] = item(2800)
    spy = puzzle(w, lambda: True)
    expect(solve()).to_be('yield')
    expect(spy.calls[0][0]).to_be(2800)
    expect(w.npc_dialogs).to_be(1)


describe('the puzzle room', lambda: [
    test('a full pack asks for bank preparation before requesting a puzzle box', full_pack),
    test('a free slot allows the puzzle conversation', free_slot),
    test('a box already held can be solved with a full pack', box_held),
])


# Bank walks (walkToBank.test.ts)

FALADOR = Tile(2946, 3369, 0)


def bank_walk_on_foot():
    set_trail_teleports(False)
    seen = []

    def walk(dest, **opts):
        seen.append(opts)
        return True
        yield

    spy_on(traversal, 'walk_resilient', walk)
    run_wait(walk_to_bank(FALADOR, lambda m: None))
    set_trail_teleports(True)
    expect(seen[0]['policy']['use_teleports']).to_be(False)


def bank_walk_options():
    set_trail_teleports(True)
    seen = []

    def walk(dest, **opts):
        seen.append(opts)
        return True
        yield

    spy_on(traversal, 'walk_resilient', walk)
    expect(run_wait(walk_to_bank(FALADOR, lambda m: None))).to_be(True)
    expect(seen[0]['use_teleport_catalog']).to_be(True)
    expect(seen[0]['policy']['use_teleports']).to_be(True)
    expect(seen[0]['radius']).to_be(3)


describe('walk_to_bank', lambda: [
    test('a bank walk routes through the teleport catalog like a trail leg', bank_walk_options),
    test('a bank walk stays on foot once the host turns teleports off', bank_walk_on_foot),
])
