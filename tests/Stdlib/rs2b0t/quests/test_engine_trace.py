"""rs2b0t's test/api/ai/quests/engine/trace.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""


from rs2004.catalogs.record import Record
from rs2004.quests.engine.trace import HEARTBEAT_ATTEMPTS, HEARTBEAT_MS, StepTracker, format_duration, format_tile, inv_delta

def _fn1():
    def _fn2():
        expect(format_duration(320)).to_be('320ms')
        expect(format_duration(20300)).to_be('20.3s')
        expect(format_duration(185000)).to_be('3m05s')
    test('sub-second in ms, then seconds, then minutes', _fn2)


describe('formatDuration', _fn1)


def _fn3():
    def _fn4():
        expect(format_tile(Record({'x': 3042, 'z': 9760, 'level': 0}))).to_be('(3042,9760)')
        expect(format_tile(Record({'x': 2509, 'z': 3640, 'level': 2}))).to_be('(2509,3640,L2)')
        expect(format_tile(None)).to_be('(no tile)')
    test('omits the level on the ground floor and names it above', _fn4)


describe('formatTile', _fn3)


def _fn5():
    def _fn6():
        before = {_k: _v for _k, _v in [['coal', 3], ['iron ore', 4], ['coins', 20000]]}
        after = {_k: _v for _k, _v in [['coal', 4], ['iron ore', 4], ['coins', 20000]]}
        expect(inv_delta(before, after)).to_be('coal 3→4')
    test('reports only what moved', _fn6)

    def _fn7():
        expect(inv_delta({}, {_k: _v for _k, _v in [['steel bar', 4]]})).to_be('steel bar 0→4')
        expect(inv_delta({_k: _v for _k, _v in [['coal', 8]]}, {})).to_be('coal 8→0')
    test('names an item that appeared or vanished', _fn7)

    def _fn8():
        same = {_k: _v for _k, _v in [['coal', 3]]}
        expect(inv_delta(same, {k: same[k] for k in same})).to_be('no inventory change')
    test('a step that moved nothing says so — that is the diagnosis', _fn8)


describe('invDelta', _fn5)


def _fn9():
    def _fn10():
        t = StepTracker()
        expect(t.open('horror|smith 8 nails', 0)).to_be(1)
        expect(t.open('horror|smith 8 nails', 600)).to_be(2)
        expect(t.open('horror|smith 8 nails', 1200)).to_be(3)
        expect(t.open('horror|walk to the lighthouse', 1800)).to_be(1)
    test('counts attempts on a repeated step and resets on a new one', _fn10)

    def _fn11():
        t = StepTracker()
        t.open('a', 1000)
        t.open('a', 61000)
        expect(t.elapsed(61000)).to_be(60000)
    test('elapsed measures the whole run of the step, not the last attempt', _fn11)

    def _fn12():
        t = StepTracker()
        t.open('a', 0)
        expect(t.beat(0)).to_be(False)
    test('never beats on the first attempt', _fn12)

    def _fn13():
        t = StepTracker()
        for i in range(1, HEARTBEAT_ATTEMPTS):
            t.open('a', i)
            expect(t.beat(i)).to_be(False)
        t.open('a', HEARTBEAT_ATTEMPTS)
        expect(t.beat(HEARTBEAT_ATTEMPTS)).to_be(True)
    test('beats on the attempt count even when the ticks are fast', _fn13)

    def _fn14():
        t = StepTracker()
        t.open('a', 0)
        t.open('a', HEARTBEAT_MS + 1)
        expect(t.beat(HEARTBEAT_MS + 1)).to_be(True)
    test('beats on elapsed time even when one attempt blocks for minutes', _fn14)

    def _fn15():
        t = StepTracker()
        t.open('a', 0)
        t.open('a', 1)
        t.reset()
        expect(t.open('a', 2)).to_be(1)
    test('reset clears the count so a resumed quest starts fresh', _fn15)


describe('StepTracker', _fn9)
