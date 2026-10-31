"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/merlinscrystal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.merlinscrystal import bread_plan
from rs2004.quests.engine.types import QuestSnapshot

def snap(coins):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {_k: _v for _k, _v in ([['coins', coins]] if coins > 0 else [])},
        'worn': set(),
        'no_progress': 0,
        'bank_coins': 0,
    })


def _fn1():
    def _fn2():
        step = bread_plan(snap(100), 40, 0)
        expect(step.kind).to_be('buy')
        expect((step).item).to_be('Bread')
        expect((step).shop.npc).to_be('Wydin')
    test('buys Bread from Wydin when funded', _fn2)

    def _fn3():
        step = bread_plan(snap(0), 1, 0)
        expect(step.kind).to_be('wait')
    test('parks when broke (buyOrWait), never loops a bare buy', _fn3)


describe('breadPlan: Wydin buy (baker stall has no bread in rev 274)', _fn1)
