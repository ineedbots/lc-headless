"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/knightssword-portrait.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.knightssword.portrait import best_approach, should_wait_out, vyvin_too_close
from rs2004.quests.defs.knightssword.areas import VYVIN_APPROACHES
CUPBOARD_STAND = Fake(**{'x': 2985, 'z': 3335, 'level': 2})
VYVIN_SPAWN = Fake(**{'x': 2983, 'z': 3335, 'level': 2})

def _fn1():

    def _fn2():
        for dx, dz in [[0, 1], [1, 0], [1, 1], [-1, -1], [0, -1], [-1, 0]]:
            beside = Fake(**{'x': CUPBOARD_STAND.x + dx, 'z': CUPBOARD_STAND.z + dz, 'level': 2})
            expect(vyvin_too_close(CUPBOARD_STAND, beside)).to_be(True)
    test('catches you from one tile away, in any direction', _fn2)

    def _fn3():
        expect(vyvin_too_close(CUPBOARD_STAND, CUPBOARD_STAND)).to_be(True)
    test('standing on the same tile counts as too close', _fn3)

    def _fn4():
        expect(vyvin_too_close(CUPBOARD_STAND, Fake(**{'x': 2986, 'z': 3337, 'level': 2}))).to_be(False)
        expect(vyvin_too_close(CUPBOARD_STAND, Fake(**{'x': 2984, 'z': 3339, 'level': 2}))).to_be(False)
    test('two tiles away is clear', _fn4)

    def _fn5():
        diagonal = Fake(**{'x': CUPBOARD_STAND.x + 1, 'z': CUPBOARD_STAND.z + 1, 'level': 2})
        expect(vyvin_too_close(CUPBOARD_STAND, diagonal)).to_be(True)
    test('the guard is a square, not a circle', _fn5)

    def _fn6():
        expect(vyvin_too_close(CUPBOARD_STAND, VYVIN_SPAWN)).to_be(False)
    test('his spawn tile is already clear of the stand', _fn6)

    def _fn7():
        expect(vyvin_too_close(CUPBOARD_STAND, None)).to_be(False)
        expect(vyvin_too_close(None, VYVIN_SPAWN)).to_be(False)
    test('an absent Vyvin never blocks', _fn7)
describe('Sir Vyvin proximity guard', _fn1)

def _fn8():
    adjacent = Fake(**{'x': CUPBOARD_STAND.x, 'z': CUPBOARD_STAND.z + 1, 'level': 2})

    def _fn9():
        expect(should_wait_out(0, CUPBOARD_STAND, adjacent)).to_be(True)
    test('waits out an adjacent Vyvin for a few passes', _fn9)

    def _fn10():
        forced = [should_wait_out(i, CUPBOARD_STAND, adjacent) for i in range(40)]
        expect(any([not wait for wait in forced])).to_be(True)
    test('but searches anyway once the skips run out', _fn10)

    def _fn11():
        expect(should_wait_out(0, CUPBOARD_STAND, VYVIN_SPAWN)).to_be(False)
    test('never waits when he is already clear', _fn11)
describe('the guard is a hint, not a gate', _fn8)

def _fn12():

    def at(x, z):
        return Fake(**{'x': x, 'z': z, 'level': 2})

    def _fn13():
        expect([f'{t.x},{t.z},{t.level}' for t in VYVIN_APPROACHES]).to_equal(['2985,3335,2', '2984,3335,2'])
    test('both legal approaches are south of the cupboard', _fn13)

    def _fn14():
        expect(best_approach(VYVIN_APPROACHES, at(2982, 3335))).to_match_object(Fake(**{'x': 2985, 'z': 3335}))
        expect(best_approach(VYVIN_APPROACHES, at(2987, 3335))).to_match_object(Fake(**{'x': 2984, 'z': 3335}))
    test('stands on the tile further from Sir Vyvin', _fn14)

    def _fn15():
        vyvin = at(2982, 3335)
        chosen = best_approach(VYVIN_APPROACHES, vyvin)
        expect(vyvin_too_close(chosen, vyvin)).to_be(False)
    test('picking the far tile actually clears the guard when he is off to one side', _fn15)

    def _fn16():
        vyvin = at(2984, 3334)
        for tile in VYVIN_APPROACHES:
            expect(vyvin_too_close(tile, vyvin)).to_be(True)
    test('directly south blocks both, which is what the retreat is for', _fn16)

    def _fn17():
        expect(best_approach(VYVIN_APPROACHES, None)).to_match_object(Fake(**{'x': 2985, 'z': 3335}))
    test('falls back to a stable tile when he is not in the scene', _fn17)
describe('picking the approach tile', _fn12)
