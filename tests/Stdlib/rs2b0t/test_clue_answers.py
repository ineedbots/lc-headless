"""rs2b0t's test/api/ai/clues: clue-trace.test.ts, data/challengeAnswers.test.ts and data/clueGates.test.ts (MIT,
see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.clues.data import CHALLENGE_ANSWERS, CLUE_GATES, challenge_answer, clue_gate
from rs2004.clues.plan import ClueTrace, push_trace_ring, read_trace_ring


class Clock:
    def __init__(self):
        self.now = 1000

    def __call__(self):
        return self.now

    def tick(self):
        self.now += 250


def make_trace(cap=200):
    clock = Clock()
    return ClueTrace(cap, clock, lambda: '3210,3225,0'), clock


def collects():
    trace, clock = make_trace()
    trace.begin(2697, 'easy simple021')
    trace.note('solving trail_clue_easy_simple021 (talk Ned)')
    clock.tick()
    trace.note('step done')
    lines = trace.lines()
    expect(len(lines)).to_be(2)
    expect(lines[0]).to_equal({'t': 1000, 'pos': '3210,3225,0', 'm': 'solving trail_clue_easy_simple021 (talk Ned)'})
    expect(lines[1]['t']).to_be(1250)


def resets():
    trace, _ = make_trace()
    trace.begin(2697, 'easy simple021')
    trace.note('old line')
    trace.begin(2681, 'easy simple005')
    expect(len(trace.lines())).to_be(0)
    expect(trace.dump('abandon', 0)['clue_id']).to_be(2681)


def caps():
    trace, _ = make_trace(3)
    trace.begin(1, 'x')
    for i in range(5):
        trace.note(f'line {i}')
    lines = trace.lines()
    expect(len(lines)).to_be(3)
    expect(lines[0]['m']).to_be('line 2')
    expect(lines[2]['m']).to_be('line 4')


def dumps():
    trace, clock = make_trace()
    trace.begin(2697, 'easy simple021')
    trace.note('solving')
    clock.tick()
    dump = trace.dump('no progress after 4 attempts', 2)
    expect(dump).to_match_object({'clue_id': 2697, 'name': 'easy simple021', 'reason': 'no progress after 4 attempts', 'legs': 2, 'started_at': 1000,
                                  'ended_at': 1250})
    expect(len(dump['lines'])).to_be(1)


class MemStorage:
    def __init__(self):
        self.backing = {}

    def get_item(self, key):
        return self.backing.get(key)

    def set_item(self, key, value):
        self.backing[key] = value


def dump_of(id):
    return {'clue_id': id, 'name': f'clue {id}', 'reason': 'r', 'started_at': 0, 'ended_at': 1, 'legs': 1, 'lines': []}


def ring_caps():
    storage = MemStorage()
    for i in range(1, 8):
        push_trace_ring(storage, 'k', dump_of(i), 5)
    ring = read_trace_ring(storage, 'k')
    expect(len(ring)).to_be(5)
    expect(ring[0]['clue_id']).to_be(7)
    expect(ring[4]['clue_id']).to_be(3)


def ring_corrupt():
    storage = MemStorage()
    expect(read_trace_ring(storage, 'k')).to_equal([])
    storage.set_item('k', 'not json')
    expect(read_trace_ring(storage, 'k')).to_equal([])


describe('ClueTrace', lambda: [
    test('collects lines with timestamp and position', collects),
    test('begin resets the previous solve', resets),
    test('caps the line count by evicting the oldest', caps),
    test('dump carries clue identity, reason, leg count and timing', dumps),
])

describe('trace ring persistence', lambda: [
    test('pushes newest first and caps the ring', ring_caps),
    test('reads empty on missing or corrupt data', ring_corrupt),
])


def answer_rows():
    for c in CHALLENGE_ANSWERS:
        expect(c['clue']).to_start_with('trail_clue_medium_anagram')
        expect(type(c['answer'])).to_be(int)
        expect(c['answer']).to_be_greater_than(0)


describe('challenge_answer', lambda: [
    test('zoo animals: anagram003 (Zoo keeper)', lambda: expect(challenge_answer(2845)).to_be(40)),
    test('19 to the power of 3: anagram001 (Hazelmere)', lambda: expect(challenge_answer(2841)).to_be(6859)),
    test('Lumbridge cannons: anagram002 (Cook)', lambda: expect(challenge_answer(2843)).to_be(9)),
    test('16 kebabs shared: anagram006 (Kebab seller)', lambda: expect(challenge_answer(2849)).to_be(5)),
    test('3x + y: anagram007 (Oracle)', lambda: expect(challenge_answer(2851)).to_be(48)),
    test('57 x 89 + 23: anagram008 (Gnome ball referee)', lambda: expect(challenge_answer(2853)).to_be(5096)),
    test('a non-challenge clue id gives None (leave the dialog alone)', lambda: [expect(challenge_answer(2847)).to_be_null(), expect(challenge_answer(0)).to_be_null()]),
])

describe('CHALLENGE_ANSWERS table', lambda: [
    test('covers the six challenge clues with unique ids', lambda: [
        expect(CHALLENGE_ANSWERS).to_have_length(6),
        expect(len(set([c['id'] for c in CHALLENGE_ANSWERS]))).to_be(6),
    ]),
    test('every row is a medium anagram clue with a positive integer answer', answer_rows),
])

TIRANNWN = [3560, 3562, 3564]


def always(status):
    return lambda quest: status


def asks_its_quest():
    asked = []

    def status(name):
        asked.append(name)
        return 'complete'

    for id in CLUE_GATES.keys():
        clue_gate(id, status)
    expect(len(asked)).to_be(len(CLUE_GATES))
    expect(asked).to_equal([g['quest'] for g in CLUE_GATES.values()])


describe('clue_gate', lambda: [
    test('an ungated clue is open whatever the journal says', lambda: expect(clue_gate(2677, always('not_started'))).to_be_null()),
    test('a Tirannwn clue is open once Regicide reads complete', lambda: [expect(clue_gate(id, always('complete'))).to_be_null() for id in TIRANNWN]),
    test('a Tirannwn clue is blocked while Regicide is unfinished', lambda: [
        [expect(clue_gate(id, always('not_started'))).to_contain('Regicide') for id in TIRANNWN],
        [expect(clue_gate(id, always('in_progress'))).to_contain('Regicide') for id in TIRANNWN],
    ]),
    # Why: unknown is the quest tab not loaded yet, not a finished quest, so it mustn't open the gate.
    test('an unloaded quest tab keeps the gate shut', lambda: expect(clue_gate(3564, always('unknown'))).to_contain('Regicide')),
    test('the block names the quest and the observed status',
         lambda: expect(clue_gate(3564, always('in_progress'))).to_be('Lord Iorwerth is in the elf camp (Regicide reads in_progress)')),
    test('every gate asks about the quest it names', asks_its_quest),
])
