"""Ported from rs2b0t's test/api/ai/quests/upassRailingsRun.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.geometry import Tile
from rs2004.quests.defs.upass.areas import UP_LOC
from rs2004.quests.defs.upass.railings import TO_RAILINGS

# Why: this fixed four-crossing route keeps searches from selecting seams in other pockets.
def _fn1():
    def _fn2():
        expect([f'{s.op} {s.loc}' for s in TO_RAILINGS]).to_equal([
        f'Pick-lock {UP_LOC.RAILINGS_LOCKED}',
        f'Dig {UP_LOC.MUD_DIG}',
        f'Cross {UP_LOC.LEDGE}',
        f'Pick-lock {UP_LOC.RAILINGS_HARD}',
        f'Pick-lock {UP_LOC.RAILINGS_HARD}',
        f'Squeeze-through {UP_LOC.PIPE_AREA2}',
    ])
    test('starts in the corridor, because that is where the well drops the character', _fn2)

    def _fn3():
        expect((TO_RAILINGS[1].item.name if TO_RAILINGS[1].item is not None else None)).to_be('Spade')
        expect(TO_RAILINGS[1].stand).to_equal(Tile(2393, 9651, 0))
        expect(TO_RAILINGS[1].lands).to_equal(Tile(2392, 9646, 0))
    test('digs the mud with a spade rather than an op the client cannot send', _fn3)

    def _fn4():
        ledge = TO_RAILINGS[2]
        expect(ledge.stand).to_equal(Tile(2375, 9644, 0))
        expect(ledge.at).to_equal(Tile(2374, 9644, 0))
        expect(ledge.lands).to_equal(Tile(2374, 9638, 0))
    test('crosses the ledge from (2375,9644) on the loc at (2374,9644)', _fn4)

    def _fn5():
        for step in TO_RAILINGS:
            expect(step.at.level).to_be(0)
            # Why: a wall railing is used from its OWN tile, so `at` equals the stand there; the ledge and
            # the pipe are used from beside them. Either way the loc is named rather than searched for.
            expect(step.at.distance_to(step.stand)).to_be_less_than_or_equal(2)
    test('names the loc tile for every crossing, so a row of them cannot be picked by nearest', _fn5)

    def _fn6():
        pipe = TO_RAILINGS[5]
        expect(pipe.stand).to_equal(Tile(2419, 9605, 0))
        expect(pipe.at).to_equal(Tile(2417, 9605, 0))
        expect(pipe.lands).to_equal(Tile(2412, 9605, 0))
        expect(pipe.via).to_equal([Tile(2420, 9617, 0)])
    test('squeezes the pipe at (2417,9605) from (2419,9605) into (2412,9605)', _fn6)

    def _fn7():
        expect(TO_RAILINGS[3].stand).to_equal(Tile(2380, 9619, 0))
        expect(TO_RAILINGS[3].lands).to_equal(Tile(2381, 9619, 0))
        expect(TO_RAILINGS[4].stand).to_equal(Tile(2403, 9620, 0))
        expect(TO_RAILINGS[4].at).to_equal(Tile(2404, 9620, 0))
    test('picks the railings from the tiles the map angles them to', _fn7)


describe('the run from the cage corridor down to the loose railings', _fn1)

