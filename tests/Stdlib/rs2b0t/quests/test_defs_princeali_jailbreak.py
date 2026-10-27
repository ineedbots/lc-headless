"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/princeali-jailbreak.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.princeali.areas import PA_ITEM
from rs2004.quests.defs.princeali.journal import PRINCE_STAGE
from rs2004.quests.defs.princeali.jailbreak import decide_jailbreak, source_beers, source_ropes

def at(stage, inv_ids=None, bank_ids=None):
    if inv_ids is None:
        inv_ids = []
    if bank_ids is None:
        bank_ids = []
    return Fake(**{'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in inv_ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in bank_ids}, 'bank_known': True, 'stage': stage, 'progress': Fake(**{'stage': stage, 'flags': set()})})
I = PA_ITEM
S = PRINCE_STAGE

def _fn1():

    def _fn2():
        step = source_beers(at(S.SPOKEN_OSMAN))
        expect((step.kind if step is not None else None) == 'talk' and step.stop.npc).to_be('Bartender')
    test('three, one per conversation at the Rusty Anchor', _fn2)

    def _fn3():
        expect(source_beers(at(S.SPOKEN_OSMAN)).kind if source_beers(at(S.SPOKEN_OSMAN)) is not None else None).not_.to_be('buy')
    test('the bartender has no Trade op, so this is a talk and never a buy', _fn3)

    def _fn4():
        expect(source_beers(at(S.SPOKEN_OSMAN, [[I.BEER.id, 3]]))).to_be_null()
    test('null once three are held', _fn4)

    def _fn5():
        expect(source_beers(at(S.PREP_FINISHED))).not_.to_be_null()
    test('still wanted at stage 30 — Joe has not drunk them yet', _fn5)

    def _fn6():
        expect(source_beers(at(S.GUARD_DRUNK))).to_be_null()
        expect(source_beers(at(S.TIED_KELI))).to_be_null()
        expect(source_beers(at(S.SAVED))).to_be_null()
    test('never wanted from stage 40 on: the guard is already drunk', _fn6)

    def _fn7():
        expect(source_beers(at(S.SPOKEN_OSMAN, [], [[I.BEER.id, 3]])).kind if source_beers(at(S.SPOKEN_OSMAN, [], [[I.BEER.id, 3]])) is not None else None).to_be('withdraw')
    test('the bank is used before the bartender', _fn7)
describe('beers', _fn1)

def _fn8():

    def _fn9():
        expect(source_ropes(at(S.SPOKEN_OSMAN, [[I.ROPE.id, 1]]))).not_.to_be_null()
        expect(source_ropes(at(S.SPOKEN_OSMAN, [[I.ROPE.id, 2]]))).to_be_null()
    test('two before the tie: she respawns 100 ticks later, five tiles from the door', _fn9)

    def _fn10():
        step = source_ropes(at(S.SPOKEN_OSMAN))
        expect((step.kind if step is not None else None) == 'talk' and step.stop.npc).to_be('Ned')
    test('bought from Ned by dialogue, not from a shop', _fn10)

    def _fn11():
        expect(source_ropes(at(S.GUARD_DRUNK, [[I.ROPE.id, 1]]))).to_be_null()
        expect(source_ropes(at(S.TIED_KELI, [[I.ROPE.id, 1]]))).to_be_null()
        expect(source_ropes(at(S.TIED_KELI))).not_.to_be_null()
    test('one spare kept at 40 and 50, for the re-tie', _fn11)

    def _fn12():
        expect(source_ropes(at(S.SAVED))).to_be_null()
    test('none wanted once the prince is out', _fn12)
describe('ropes', _fn8)

def _fn13():

    def _fn14():
        step = decide_jailbreak(at(S.PREP_FINISHED, [[I.BEER.id, 3]]))
        expect(step.kind == 'talk' and step.stop.npc).to_be('Joe')
    test('talks to Joe', _fn14)
describe('stage 30 — the guard', _fn13)

def _fn15():
    kit = [[I.BLOND_WIG.id, 1], [I.PINK_SKIRT.id, 1], [I.PASTE.id, 1], [I.PRINCE_KEY.id, 1], [I.ROPE.id, 1]]

    def _fn16():
        step = decide_jailbreak(at(S.GUARD_DRUNK, kit))
        expect(step.kind == 'custom' and step.name).to_contain('Keli')
    test('40 -> the one-shot break-in', _fn16)

    def _fn17():
        step = decide_jailbreak(at(S.TIED_KELI, kit))
        expect(step.kind == 'custom' and step.name).to_contain('Keli')
    test('50 -> the same break-in, re-entrant', _fn17)

    def _fn18():
        step = decide_jailbreak(at(S.GUARD_DRUNK, [[I.PRINCE_KEY.id, 1], [I.ROPE.id, 1]]))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('Wig')
    test('an incomplete disguise waits with a reason rather than walking into the cell', _fn18)

    def _fn19():
        step = decide_jailbreak(at(S.GUARD_DRUNK, [[I.PLAIN_WIG.id, 1], [I.PINK_SKIRT.id, 1], [I.PASTE.id, 1], [I.PRINCE_KEY.id, 1], [I.ROPE.id, 1]]))
        expect(step.kind).to_be('wait')
    test('a plain wig does not pass for the disguise', _fn19)

    def _fn20():
        step = decide_jailbreak(at(S.TIED_KELI, [[I.BLOND_WIG.id, 1], [I.PINK_SKIRT.id, 1], [I.PASTE.id, 1], [I.ROPE.id, 1]]))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('Bronze key')
    test('no key waits rather than unlocking a door it cannot open', _fn20)

    def _fn21():
        step = decide_jailbreak(at(S.GUARD_DRUNK, [[I.BLOND_WIG.id, 1], [I.PINK_SKIRT.id, 1], [I.PASTE.id, 1], [I.PRINCE_KEY.id, 1]]))
        expect(step.kind).to_be('wait')
        expect(step.kind == 'wait' and step.reason).to_contain('Rope')
    test('no rope at 40 waits — the tie is impossible without one', _fn21)
describe('stages 40 and 50 — Keli and the cell', _fn15)
