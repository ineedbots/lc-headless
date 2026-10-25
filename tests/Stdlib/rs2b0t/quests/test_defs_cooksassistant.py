"""rs2b0t's test/api/ai/quests/defs/cooksassistant.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

from rs2004.quests.defs.cooksassistant import cooksassistant, decide, gather_flour, gather_milk
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
        expect(gather_flour(snap('in_progress')).kind).to_be('grab_ground')
        expect(gather_flour(snap('in_progress', [['pot', 1]])).kind).to_be('pick_loc')
        expect(gather_flour(snap('in_progress', [['pot', 1], ['grain', 1]])).kind).to_be('custom')
    test('flour: pot first, then grain, then the mill custom', _fn2)

    def _fn3():
        expect(gather_milk(snap('in_progress')).kind).to_be('grab_ground')
        s = gather_milk(snap('in_progress', [['bucket', 1]]))
        expect(s.kind == 'use_on' and s.target).to_be('Cow')
    test('milk: bucket first, then use it on a cow', _fn3)


describe('cooksassistant gathers', _fn1)


def _fn4():
    def _fn5():
        s = decide(snap('not_started'))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Cook')
        s2 = decide(snap('in_progress', [['egg', 1], ['bucket of milk', 1], ['pot of flour', 1]]))
        expect(s2.kind == 'talk' and s2.stop.npc).to_be('Cook')
    test('notStarted and full-handed both talk to the Cook', _fn5)

    def _fn6():
        s = decide(snap('in_progress', [['egg', 1], ['bucket of milk', 1]]))
        expect(s.kind).not_.to_be('talk')
    test('inProgress missing an ingredient self-heals through the gathers', _fn6)

    def _fn7():
        s = decide(snap('in_progress'))
        expect(s).to_match_object(Record({'kind': 'grab_ground', 'item': 'Egg', 'wait_if_missing': True}))
    test('the egg waits at the pen instead of treating arrival as a take', _fn7)


describe('cooksassistant decide', _fn4)


def _fn8():
    def _fn9():
        expect(cooksassistant.coin_float).to_be(0)
    test('spends nothing, so it carries no engine coin float', _fn9)


describe('cooksassistant module', _fn8)
