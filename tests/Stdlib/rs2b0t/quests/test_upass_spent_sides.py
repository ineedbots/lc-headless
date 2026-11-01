"""Ported from rs2b0t's test/api/ai/quests/upassSpentSides.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.geometry import Tile
from rs2004.quests.defs.upass.spent import spend_from, spent_here, spent_state_here

# Why: spending both sides of a cage seals the destination pocket; only the origin side is spent.
CAGE = 'cage@2384,9655'
WELL_SIDE = Tile(2385, 9655, 0)
CELL_SIDE = Tile(2384, 9657, 0)


def pocket(*tiles):
    """Stands reachable from the current pocket."""
    return lambda t: any([p.x == t.x and p.z == t.z and p.level == t.level for p in tiles])


def _fn1():
    def _fn2():
        sides = {}
        spend_from(sides, CAGE, WELL_SIDE)
        expect(spent_here(sides, CAGE, pocket(WELL_SIDE))).to_be(True)
        expect(spent_here(sides, CAGE, pocket(CELL_SIDE))).to_be(False)
    test('is still open from the other side, so a cul-de-sac can be backed out of', _fn2)

    def _fn3():
        sides = {}
        spend_from(sides, CAGE, WELL_SIDE)
        spend_from(sides, CAGE, CELL_SIDE)
        expect(spent_here(sides, CAGE, pocket(WELL_SIDE))).to_be(True)
        expect(spent_here(sides, CAGE, pocket(CELL_SIDE))).to_be(True)
        # Why: a cage may join a third pocket that remains unused.
        expect(spent_here(sides, CAGE, pocket(Tile(2384, 9654, 0)))).to_be(False)
    test('closes behind a character who has backed out, so the dead end is not re-entered', _fn3)

    def _fn4():
        sides = {}
        spend_from(sides, CAGE, WELL_SIDE)
        spend_from(sides, CAGE, WELL_SIDE)
        expect(sides.get(CAGE)).to_have_length(1)
    test('records a side once, however many times it is tried from there', _fn4)

    def _fn5():
        expect(spent_here({}, CAGE, pocket(WELL_SIDE))).to_be(False)
    test('leaves a seam nobody has crossed alone', _fn5)

    # Why: distinguish fresh, item-use, and return sides because they rank differently.
    def _fn6():
        sides = {}
        expect(spent_state_here(sides, CAGE, pocket(WELL_SIDE))).to_be('fresh')
        spend_from(sides, CAGE, WELL_SIDE)
        expect(spent_state_here(sides, CAGE, pocket(WELL_SIDE))).to_be('here')
        expect(spent_state_here(sides, CAGE, pocket(CELL_SIDE))).to_be('elsewhere')
    test('reads as fresh, used from here, or used from the far side', _fn6)


describe('a seam spent from one side', _fn1)

