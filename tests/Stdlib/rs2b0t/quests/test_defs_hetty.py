"""rs2b0t's test/api/ai/quests/defs/hetty.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

from rs2004.quests.defs.hetty import decide, gather_onion, gather_rats_tail, gather_eye_of_newt, gather_burnt_meat, hetty
def snap(journal, items=None, bank_coins=0):
    if items is None:
        items = []
    return (QuestSnapshot().with_fields({
        'journal': journal,
        'inv': {_k: _v for _k, _v in items},
        'worn': set(),
        'no_progress': 0,
        'bank_coins': bank_coins,
    }))


TAIL = "rat's tail"
ALL_FOUR = [[TAIL, 1], ['onion', 1], ['eye of newt', 1], ['burnt meat', 1]]


def _fn1():
    def _fn2():
        expect(decide(snap('complete')).kind).to_be('done')
        expect(decide(snap('unknown')).kind).to_be('wait')
    test('complete -> done, unknown -> wait', _fn2)

    def _fn3():
        s = decide(snap('not_started'))
        expect(s.kind == 'talk' and s.stop.npc).to_be('Hetty')
        expect(s.kind == 'talk' and s.stop.prefer).to_equal(['I am in search of a quest.', 'Yes help me become one with my darker side.'])
    test('notStarted talks to Hetty with the start dialogue options', _fn3)

    def _fn4():
        s = decide(snap('in_progress', ALL_FOUR))
        expect(s.kind).to_be('custom')
        expect('drink' in str(s.kind == 'custom' and s.name).lower()).to_be(True)
    test('holding all four ingredients hands in and drinks (one custom step)', _fn4)


describe('hetty decide — quest states', _fn1)


def _fn5():
    def _fn6():
        s = decide(snap('in_progress'))
        expect('rat' in str(s.kind == 'custom' and s.name).lower()).to_be(True)
    test('nothing held -> the quest-gated rat tail first', _fn6)

    def _fn7():
        s = decide(snap('in_progress', [[TAIL, 1]]))
        expect(s.kind == 'pick_loc' and s.item).to_be('Onion')
    test('tail held -> onion next', _fn7)

    def _fn8():
        s = decide(snap('in_progress', [[TAIL, 1], ['onion', 1]], 50))
        expect(s.kind == 'buy' and s.shop.npc).to_be('Betty')
        expect(s.kind == 'buy' and s.item).to_be('Eye of newt')
    test('tail+onion held, funded -> buy the eye of newt from Betty', _fn8)

    def _fn9():
        s = decide(snap('in_progress', [[TAIL, 1], ['onion', 1], ['eye of newt', 1]], 50))
        expect(s.kind == 'buy' and s.shop.npc).to_be('Wydin')
        expect(s.kind == 'buy' and s.item).to_be('Raw beef')
    test('tail+onion+eye held, funded -> burnt meat buys raw beef from Wydin', _fn9)


describe('hetty decide — gather routing (record-item order, self-heal any gap)', _fn5)


def _fn10():
    def _fn11():
        expect(decide(snap('in_progress', [[TAIL, 1]])).kind).to_be('pick_loc')
        s = decide(snap('in_progress', ALL_FOUR))
        expect('drink' in str(s.kind == 'custom' and s.name).lower()).to_be(True)
    test("holding Rat's tail is enough to leave the kill and to hand in", _fn11)

    def _fn12():
        s = decide(snap('in_progress', [['rats tail', 1]]))
        expect('rat' in str(s.kind == 'custom' and s.name).lower()).to_be(True)
        fake_four = decide(snap('in_progress', [['rats tail', 1], ['onion', 1], ['eye of newt', 1], ['burnt meat', 1]]))
        expect('rat' in str(fake_four.kind == 'custom' and fake_four.name).lower()).to_be(True)
    test("the pre-289 'rats tail' spelling is not the packed item", _fn12)


describe('hetty decide — rev 289 display name', _fn10)


def _fn13():
    def _fn14():
        for g in [gather_onion, gather_rats_tail, gather_eye_of_newt, gather_burnt_meat]:
            s = g(snap('not_started'))
            expect(s.kind == 'talk' and s.stop.npc).to_be('Hetty')
    test('every gather starts the quest first when notStarted (the rat tail is quest-gated)', _fn14)

    def _fn15():
        expect(gather_onion(snap('in_progress')).kind).to_be('pick_loc')
        expect(gather_rats_tail(snap('in_progress')).kind).to_be('custom')
    test('onion picks from the field; rat tail is a custom kill', _fn15)

    def _fn16():
        expect(gather_eye_of_newt(snap('in_progress', [], 50)).kind).to_be('buy')
        broke = gather_eye_of_newt(snap('in_progress'))
        expect('gp for Eye of newt' in str(broke.kind == 'wait' and broke.reason)).to_be(True)
    test('eye of newt: buy when funded, park when broke', _fn16)

    def _fn17():
        expect(gather_burnt_meat(snap('in_progress', [], 50)).kind).to_be('buy')
        expect(gather_burnt_meat(snap('in_progress', [['raw beef', 2]])).kind).to_be('custom')
        expect(gather_burnt_meat(snap('in_progress', [['cooked meat', 1]])).kind).to_be('custom')
        broke = gather_burnt_meat(snap('in_progress'))
        expect('gp for Raw beef' in str(broke.kind == 'wait' and broke.reason)).to_be(True)
    test('burnt meat: raw meat first (buy), then the burn custom once meat is held', _fn17)


describe('hetty gathers — startedOr gate + shape', _fn13)


def _fn18():
    def _fn19():
        expect(hetty.record.id).to_be('hetty')
        expect(hetty.record.name).to_be("Witch's Potion")
        expect(any([i.name == "Rat's tail" for i in hetty.record.items])).to_be(True)
        expect(hetty.grind).to_contain('Rat')
        expect(sorted(list((hetty.gather if hetty.gather is not None else Record({})).keys()))).to_equal(['burnt meat', 'eye of newt', 'onion', TAIL])
    test('binds the existing record, banks at Draynor, grinds the Rat, gathers all four', _fn19)


describe('hetty module wiring', _fn18)
