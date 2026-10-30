"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/scorpcatcher-cages.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.scorpcatcher.areas import CAGE_ID, EVERY_SCORPION, cage_with, caught_in

def _fn1():
    def _fn2():
        expect(list(caught_in(CAGE_ID.EMPTY))).to_equal([])
    test('the empty cage holds nothing', _fn2)

    def _fn3():
        expect(list(caught_in(CAGE_ID.A))).to_equal(['a'])
        expect(list(caught_in(CAGE_ID.B))).to_equal(['b'])
        expect(list(caught_in(CAGE_ID.C))).to_equal(['c'])
    test('each single-scorpion cage names its own scorpion', _fn3)

    def _fn4():
        expect(sorted(list(caught_in(CAGE_ID.AB)))).to_equal(['a', 'b'])
        expect(sorted(list(caught_in(CAGE_ID.AC)))).to_equal(['a', 'c'])
        expect(sorted(list(caught_in(CAGE_ID.BC)))).to_equal(['b', 'c'])
    test('each pair cage names both of its scorpions', _fn4)

    def _fn5():
        expect(sorted(list(caught_in(CAGE_ID.FULL)))).to_equal(['a', 'b', 'c'])
    test('the full cage names all three', _fn5)

    def _fn6():
        expect(list(caught_in(995))).to_equal([])
    test('an id that is not a cage holds nothing', _fn6)

    # Why: the cage id is the only client-visible record of which scorpions are in it, so every combination has to round-trip or a resumed run re-catches one it already has.
    def _fn7():
        combos = [[], ['a'], ['b'], ['c'], ['a', 'b'], ['a', 'c'], ['b', 'c'], ['a', 'b', 'c']]
        for combo in combos:
            id = cage_with(set(combo))
            expect(id).not_.to_be_undefined()
            expect(sorted(list(caught_in(id)))).to_equal(sorted(list(combo)))
    test('every combination of scorpions round-trips through an id', _fn7)

    def _fn8():
        expect(sorted(list(EVERY_SCORPION))).to_equal(['a', 'b', 'c'])
    test('the three scorpions are catchable in a fixed order', _fn8)


describe('cage ids', _fn1)
