"""Ported from rs2b0t's test/api/ai/quests/upassCageDoors.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.geometry import Tile
from rs2004.quests.defs.upass.doors import MUD_CAGE, MUD_CELL, door_across, door_stands, mud_cell_door

# Why: `~open_and_close_door2` chooses direction from the player's position on the door's axis, so stand on the door tile.
def _fn1():
    def _fn2():
        expect(door_across(Tile(2381, 9655, 0))).to_equal(Tile(2381, 9654, 0))
        expect(door_across(Tile(2393, 9655, 0))).to_equal(Tile(2393, 9654, 0))
    test('names the tile its edge runs against, south for the z 9655 row', _fn2)

    def _fn3():
        expect(door_across(Tile(2381, 9656, 0))).to_equal(Tile(2381, 9657, 0))
        expect(door_across(Tile(2393, 9656, 0))).to_equal(Tile(2393, 9657, 0))
    test('and north for the z 9656 row', _fn3)

    def _fn4():
        expect(door_across(Tile(2380, 9619, 0))).to_equal(Tile(2381, 9619, 0))
        expect(door_across(Tile(2404, 9620, 0))).to_equal(Tile(2403, 9620, 0))
    test('runs east-west where the map angles it that way', _fn4)

    def _fn5():
        expect(door_stands(Tile(2393, 9655, 0))).to_equal([Tile(2393, 9655, 0), Tile(2393, 9654, 0)])
    test('offers its own tile first and the tile across it second, and nothing else', _fn5)

    def _fn6():
        expect(door_across(Tile(2393, 9650, 0))).to_be_null()
        expect(door_stands(Tile(2393, 9650, 0))).to_equal([])
    test('offers nothing for a tile that carries no door, so the ring search keeps it', _fn6)


describe('a railing door', _fn1)


def _fn7():
    def _fn8():
        expect(MUD_CAGE).to_equal(Tile(2393, 9655, 0))
        expect(door_across(MUD_CAGE)).to_equal(Tile(2393, 9654, 0))
    test('is the south door at (2393,9655)', _fn8)

    def _fn9():
        expect(mud_cell_door(MUD_CAGE)).to_equal([MUD_CELL])
    test('carries the mud cell as its landing', _fn9)

    def _fn10():
        expect(mud_cell_door(Tile(2393, 9656, 0))).to_equal([])
    test('and the north door above it does not — it opens on a dead end', _fn10)

    def _fn11():
        for x in [2381, 2384, 2387, 2390]:
            expect(mud_cell_door(Tile(x, 9655, 0))).to_equal([])
    test('nor does any other cage in the row', _fn11)


describe('the cage that leads to the mud', _fn7)

