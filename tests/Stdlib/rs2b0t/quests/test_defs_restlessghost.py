"""rs2b0t's test/api/ai/quests/defs/restlessghost.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

from rs2004.quests.defs.restlessghost import decide
def snap(journal, inv=None, worn=None):
    if inv is None:
        inv = []
    if worn is None:
        worn = []
    return (QuestSnapshot().with_fields({
        'journal': journal,
        'inv': {_k: _v for _k, _v in [[n, 1] for n in inv]},
        'worn': set(worn),
        'no_progress': 0,
        'bank_coins': 0,
    }))


def _fn1():
    def _fn2():
        expect(decide(snap('complete')).kind).to_be('done')
        s = decide(snap('not_started'))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Father Aereck')
    test('ends and start', _fn2)

    def _fn3():
        s = decide(snap('in_progress'))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Father Urhney')
    test('no amulet anywhere -> Urhney (also the lost-amulet recovery)', _fn3)

    def _fn4():
        expect(decide(snap('in_progress', ['ghostspeak amulet'])).kind).to_be('equip')
    test('amulet in pack but not worn -> equip', _fn4)

    def _fn5():
        s = decide(snap('in_progress', [], ['ghostspeak amulet']))
        expect(s.kind == 'custom' and s.name).to_be('ghost + skull')
    test('amulet worn, no skull -> ghost+skull custom', _fn5)

    def _fn6():
        s = decide(snap('in_progress', ['skull'], ['ghostspeak amulet']))
        expect(s.kind == 'custom' and s.name).to_be('return skull')
    test('skull held -> return-to-coffin custom (works regardless of worn state)', _fn6)


describe('restlessghost decide', _fn1)
