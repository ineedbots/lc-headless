"""rs2b0t's test/api/ai/quests/defs/runemysteries.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

from rs2004.quests.defs.runemysteries import decide, WIZARD_HOPS
def snap(journal, items=None, no_progress=0):
    if items is None:
        items = []
    return (QuestSnapshot().with_fields({
        'journal': journal,
        'inv': {_k: _v for _k, _v in [[n, 1] for n in items]},
        'worn': set(),
        'no_progress': no_progress,
        'bank_coins': 0,
    }))


def npc_of(s):
    return ((s.stop.npc if s.kind == 'talk' else f'<{s.kind}>'))


def _fn1():
    def _fn2():
        expect(decide(snap('complete')).kind).to_be('done')
        expect(decide(snap('unknown')).kind).to_be('wait')
        expect(npc_of(decide(snap('not_started')))).to_be('Duke Horacio')
    test('journal drives the ends', _fn2)

    def _fn3():
        expect(npc_of(decide(snap('in_progress', ['air talisman'])))).to_be('Sedridor')
        expect(npc_of(decide(snap('in_progress', ['research package'])))).to_be('Aubury')
        expect(npc_of(decide(snap('in_progress', ['notes'])))).to_be('Sedridor')
        expect(npc_of(decide(snap('in_progress', ['research notes'])))).to_be('Aubury')
    test('held item drives the deliveries (exact full-name CI match)', _fn3)

    def _fn4():
        expect(npc_of(decide(snap('in_progress', ['air talisman', 'research package'])))).to_be('Aubury')
        expect(npc_of(decide(snap('in_progress', ['notes', 'air talisman'])))).to_be('Sedridor')
    test('research package outranks a leftover air talisman', _fn4)

    def _fn5():
        down = ([h for h in WIZARD_HOPS if h.op == 'Climb-down'] or [None])[0]
        expect((down.stand if down is not None else None).equals(Tile(3105, 3162, 0))).to_be(True)
        expect(((down.walk if down is not None else None).equals if (down.walk if down is not None else None) is not None else None)(Tile(3108, 3162, 0))).to_be(True)
    test('climb-down long-walks the hall east of the inner door', _fn5)

    def _fn6():
        expect(npc_of(decide(snap('in_progress', [], 0)))).to_be('Aubury')
        expect(npc_of(decide(snap('in_progress', [], 1)))).to_be('Sedridor')
        expect(npc_of(decide(snap('in_progress', [], 2)))).to_be('Duke Horacio')
        expect(npc_of(decide(snap('in_progress', [], 3)))).to_be('Aubury')
    test('inProgress empty-handed rotates the RECOVER probe Aubury -> Sedridor -> Duke via noProgress', _fn6)


describe('runemysteries decide', _fn1)
