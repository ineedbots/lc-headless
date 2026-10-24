"""rs2b0t's test/api/ai/clues: hard-tier.test.ts, guardianWait.test.ts and the anchor half of clue-audit.test.ts (MIT,
see thirdparty/rs2b0t), on spec.py's describe, test and expect. hard-tier's check that a gate names a quest the bot
can drive waits for the quest engine's list (phase 16); clue-audit's pack-gated audit and hardclueNavReach.test.ts
run rs2b0t's own audit tool over its baked pack."""

from rs2004.clues.data import CLUE_DB, CLUE_GATES, KILL_ANCHORS, PUZZLE_PIECE_SLOT
from rs2004.clues.guardian import sustain_until
from rs2004.clues.puzzle import PUZZLE_BLANK_SLOT

ROWS = list(CLUE_DB.values())
HARD = [r for r in ROWS if '_hard_' in r['obj']]
GUARDED = [r for r in HARD if r.get('guardian')]
PUZZLES = [r for r in HARD if r.get('puzzle')]
GUARDIANS = ['Saradomin Wizard', 'Zamorak Wizard']


def piece_sets():
    slots = list(PUZZLE_PIECE_SLOT.values())
    expect(len(slots)).to_be(72)
    for s in range(3):
        expect(sorted(slots[s * 24:s * 24 + 24])).to_equal(list(range(PUZZLE_BLANK_SLOT)))


def gates_named():
    for id, gate in CLUE_GATES.items():
        expect(id in CLUE_DB).to_be(True)
        expect(len(gate['reason'])).to_be_greater_than(10)


describe('hard tier in CLUE_DB', lambda: [
    test('all 64 hard clues from trail_hard.enum are present', lambda: [expect(len(HARD)).to_be(64), expect(len(ROWS)).to_be(186)]),
    test('the tiers share one table without colliding on an obj id', lambda: expect(len(set([r['id'] for r in ROWS]))).to_be(len(ROWS))),
    # A trail_casket param alone doesn't make a dig: riddle004 carries one but has no coord and is answered by Gerrant.
    test('every dig has a coord and every talk has an npc', lambda: [
        expect([r['id'] for r in ROWS if r['type'] == 'dig' and not r.get('coord')]).to_equal([]),
        expect([r['id'] for r in ROWS if r['type'] == 'talk' and not r.get('npc')]).to_equal([]),
        expect(CLUE_DB[2778]).to_match_object({'type': 'talk', 'npc': 'Gerrant'}),
    ]),
])

describe('dig guardians', lambda: [
    test('30 coordinate digs are guarded, by one of the two wizards', lambda: [
        expect(len(GUARDED)).to_be(30),
        expect(sorted(set([r['guardian'] for r in GUARDED]))).to_equal(GUARDIANS),
    ]),
    test('a guardian only ever sits on a sextant dig', lambda: [
        expect([r['id'] for r in GUARDED if r['type'] != 'dig']).to_equal([]),
        expect([r['id'] for r in GUARDED if r.get('needs_sextant') != True]).to_equal([]),
    ]),
    test('no easy or medium clue picked up a guardian', lambda: expect([r['id'] for r in ROWS if r.get('guardian') and '_hard_' not in r['obj']]).to_equal([])),
])

describe('puzzle boxes', lambda: [
    test('9 talk clues hand over a puzzle box, each with a resolved obj id', lambda: [
        expect(len(PUZZLES)).to_be(9),
        expect([r['id'] for r in PUZZLES if r['type'] != 'talk']).to_equal([]),
        expect([r['id'] for r in PUZZLES if type(r['puzzle']['id']) is not int or r['puzzle']['id'] <= 0]).to_equal([]),
    ]),
    test('the three piece sets cover every board slot exactly once', piece_sets),
])

describe('gated clues', lambda: [
    test('every gate names a real clue and gives a reason', gates_named),
])

KEY_FROM_IDS = sorted([id for id, row in CLUE_DB.items() if row.get('key_from')])


def anchors():
    expect(KEY_FROM_IDS).to_equal([2831, 2833, 2835, 2837, 2839, 3605, 3607])
    expect(sorted(KILL_ANCHORS.keys())).to_equal(KEY_FROM_IDS)
    for id in KEY_FROM_IDS:
        a = KILL_ANCHORS[id]
        expect(type(a.x) is int and type(a.z) is int and 0 <= a.level <= 3).to_be(True)


test('exactly the 7 key_from riddles carry a well-formed hunt anchor, none stale', anchors)


class Harness:
    """A fake clock and tick pump, so the wait runs without a client."""

    def __init__(self, ticks_to_satisfy, tick_ms=600):
        self.tick_ms = tick_ms
        self.at = 0
        self.ticks = 0
        self.pumps = 0
        self.ticks_to_satisfy = ticks_to_satisfy

    def now(self):
        return self.at

    def pump(self):
        self.pumps += 1
        yield from []

    def tick(self):
        self.ticks += 1
        self.at += self.tick_ms
        yield from []

    def cond(self):
        return self.ticks >= self.ticks_to_satisfy


def run(gen):
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        return stop.value


def pumps_every_tick():
    h = Harness(10)
    expect(run(sustain_until(h.cond, 180000, h))).to_be(True)
    # A tick-paced wait pumps once a tick; a single 180s park would pump once.
    expect(h.pumps).to_be_greater_than_or_equal(10)


def pumps_once_when_true():
    h = Harness(0)
    expect(run(sustain_until(h.cond, 10000, h))).to_be(True)
    expect(h.pumps).to_be(1)
    expect(h.ticks).to_be(0)


def gives_up():
    h = Harness(1000000)
    expect(run(sustain_until(h.cond, 3000, h))).to_be(False)
    expect(h.ticks).to_be_less_than_or_equal(5)
    expect(h.pumps).to_be_greater_than(1)


def zero_budget():
    h = Harness(1000000)
    expect(run(sustain_until(h.cond, 0, h))).to_be(False)
    expect(h.pumps).to_be(1)


describe('sustain_until', lambda: [
    test('pumps upkeep on every tick it waits: a long fight must still eat', pumps_every_tick),
    test('pumps at least once even when the condition is already true', pumps_once_when_true),
    test('gives up at the deadline and reports the condition', gives_up),
    test('a zero budget still pumps once rather than skipping upkeep entirely', zero_budget),
])
