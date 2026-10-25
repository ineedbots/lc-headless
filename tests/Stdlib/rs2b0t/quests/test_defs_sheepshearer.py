"""rs2b0t's test/api/ai/quests/defs/sheepshearer.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

from rs2004.quests.defs.sheepshearer import decide, gather_balls, sheepshearer
def snap(journal, items=None):
    if items is None:
        items = []
    return (QuestSnapshot().with_fields({
        'journal': journal,
        'inv': {_k: _v for _k, _v in items},
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 0,
    }))


def _fn1():
    def _fn2():
        expect(gather_balls(snap('in_progress'), 20).kind).to_be('grab_ground')
    test('no shears and short of wool -> grab the free shears spawn', _fn2)

    def _fn3():
        s = gather_balls(snap('in_progress', [['shears', 1], ['wool', 3]]), 20)
        expect(s.kind).to_be('custom')
    test('shears held, short of wool -> shear (custom)', _fn3)

    def _fn4():
        s = gather_balls(snap('in_progress', [['shears', 1], ['wool', 20]]), 20)
        expect(s.kind == 'custom' and s.name).to_be('spin wool at Falador')
    test('enough wool -> spin the batch (custom, Falador wheel)', _fn4)


describe('sheepshearer gatherBalls', _fn1)


def _fn5():
    def _fn6():
        s = decide(snap('not_started'))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Fred the Farmer')
        s2 = decide(snap('in_progress', [['ball of wool', 20]]))
        expect(s2.kind == 'talk' and s2.stop.npc).to_be('Fred the Farmer')
        expect(decide(snap('complete')).kind).to_be('done')
    test('notStarted -> Fred; balls held -> Fred (hand-in); complete -> done', _fn6)

    def _fn7():
        expect(decide(snap('in_progress')).kind).not_.to_be('talk')
    test('inProgress with no balls -> re-gather (partial hand-in / lost wool recovery)', _fn7)


describe('sheepshearer decide', _fn5)


def _fn8():
    def _fn9():
        expect(sheepshearer.coin_float).to_be(0)
    test('spends nothing, so it carries no engine coin float', _fn9)


describe('sheepshearer module', _fn8)
