"""Ported from rs2b0t's test/api/ai/quests/upassStandSide.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.geometry import Tile
from rs2004.quests.defs.upass.stand import by_side_that_lands, crossing_landing

# Why: rank by the fixed seam landing, not by mirroring a distant approach tile.
ROCKSLIDE = Tile(2467, 9723, 0)
KOFTIK = Tile(2449, 9716, 0)
CAVE_EXIT = Tile(2495, 9716, 0)


def sides(at, dest, me, *tiles):
    return [f'{t.x},{t.z}' for t in sorted(list(tiles), key=by_side_that_lands(at, dest, me))]


def _fn1():
    def _fn2():
        expect(crossing_landing(ROCKSLIDE, Tile(2468, 9723, 0))).to_equal(Tile(2466, 9723, 0))
        expect(crossing_landing(ROCKSLIDE, Tile(2471, 9723, 0))).to_equal(Tile(2466, 9723, 0))
        expect(crossing_landing(ROCKSLIDE, Tile(2466, 9723, 0))).to_equal(Tile(2468, 9723, 0))
        expect(crossing_landing(ROCKSLIDE, Tile(2467, 9720, 0))).to_equal(Tile(2467, 9724, 0))
    test('is one tile past the seam, however far out the stand is', _fn2)


describe('where a crossing from a stand lands', _fn1)


def _fn3():
    def _fn4():
        expect(sides(ROCKSLIDE, KOFTIK, CAVE_EXIT, Tile(2466, 9723, 0), Tile(2468, 9723, 0))).to_equal(['2468,9723', '2466,9723'])
    test('takes the side whose crossing lands toward the destination', _fn4)

    def _fn5():
        expect(sides(ROCKSLIDE, KOFTIK, CAVE_EXIT, Tile(2471, 9723, 0), Tile(2470, 9723, 0), Tile(2469, 9723, 0), Tile(2468, 9723, 0))).to_equal(['2468,9723', '2469,9723', '2470,9723', '2471,9723'])
    test('takes the cardinal neighbour over a tile four out that lands on the same square', _fn5)

    def _fn6():
        expect(sides(ROCKSLIDE, KOFTIK, CAVE_EXIT, Tile(2466, 9723, 0), Tile(2471, 9723, 0))).to_equal(['2471,9723', '2466,9723'])
    test('still prefers the side that lands forward over a nearer side that does not', _fn6)

    def _fn7():
        at = Tile(2380, 9619, 0)
        expect(sides(at, Tile(2380, 9619, 0), Tile(2384, 9619, 0), Tile(2381, 9619, 0), Tile(2380, 9620, 0))).to_equal(['2381,9619', '2380,9620'])
    test('breaks a tie on how far the stand is from the character', _fn7)


describe('ranking the tiles a seam can be used from', _fn3)

