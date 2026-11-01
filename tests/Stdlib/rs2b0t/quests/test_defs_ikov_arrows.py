"""Ported from rs2b0t's test/api/ai/quests/defs/ikov-arrows.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.ikov.fight import arrow_action

def _fn1():
    def _fn2():
        expect(arrow_action(20, 0, True)).to_be('shoot')
        expect(arrow_action(1, 0, False)).to_be('shoot')
    test('a nocked quiver shoots', _fn2)

    # Why: the bug this replaced. A sweep puts the recovered arrows in the pack, and a count that
    # Why: added the pack to the quiver read that as armed, every Attack after it answered
    # Why: "There is no ammo left in your quiver" for the rest of the 900-tick guard.
    def _fn3():
        expect(arrow_action(0, 12, True)).to_be('nock')
        expect(arrow_action(0, 1, False)).to_be('nock')
    test('an empty quiver over a full pack nocks rather than shooting', _fn3)

    def _fn4():
        expect(arrow_action(0, 0, True)).to_be('sweep')
    test('an empty quiver and an empty pack sweeps the floor first', _fn4)

    # Why: 80% of every shot is recoverable, but a sweep that found nothing will find nothing again, a second one is the fight ending, not another circuit.
    def _fn5():
        expect(arrow_action(0, 0, False)).to_be('spent')
    test('a sweep that already ran is the end of the fight', _fn5)


describe('Temple of Ikov arrow supply', _fn1)
