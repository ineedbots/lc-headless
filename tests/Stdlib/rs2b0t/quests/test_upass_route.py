"""Ported from rs2b0t's test/api/ai/quests/upassRoute.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.geometry import Tile
from rs2004.quests.defs.upass.cross import chain_from
from rs2004.quests.defs.upass.route import UPASS_AREAS, UPASS_CROSSINGS

# Why: straight-line ranking crosses walls; each pocket has one valid exit action.
MUD_POCKET = '94725ac'
RAILINGS = '9592589'
LEDGE_SOUTH = '9422597'


def _fn1():
    def _fn2():
        named = set([a.area for a in UPASS_AREAS])
        for edge in UPASS_CROSSINGS:
            expect((edge.from_ in named)).to_be(True)
            expect((edge.to in named)).to_be(True)
    test('names every area a crossing touches', _fn2)

    def _fn3():
        for area in UPASS_AREAS:
            expect(area.anchor.level).to_be(0)
            expect(area.anchor.x).to_be_greater_than(2300)
    test('gives every area an anchor tile to identify it by', _fn3)

    def _fn4():
        for edge in UPASS_CROSSINGS:
            expect(edge.from_).not_.to_be(edge.to)
    test('never has a crossing that starts and ends in the same area', _fn4)


describe('the route table', _fn1)


def _fn5():
    def _fn6():
        first = chain_from(MUD_POCKET, RAILINGS)
        expect((first.loc if first is not None else None)).to_be(3238)
        expect((first.op if first is not None else None)).to_be('Cross')
        expect((first.stand if first is not None else None)).to_equal(Tile(2375, 9644, 0))
        expect((first.lands if first is not None else None)).to_equal(Tile(2374, 9638, 0))
    test('takes the northernmost ledge, from the tile beside it', _fn6)

    def _fn7():
        expect([e for e in UPASS_CROSSINGS if e.from_ == MUD_POCKET]).to_have_length(1)
    test('and the ledge is the only way out of it', _fn7)

    def _fn8():
        ledges = [e for e in UPASS_CROSSINGS if e.loc == 3238]
        expect(sorted([f'{e.from_}:{e.stand.z}' for e in ledges])).to_equal(['94725a6:9639', '94725ac:9644'])
    test('offers the other ledge loc only from the pocket that can reach it', _fn8)


describe('leaving the mud pocket', _fn5)


def _fn9():
    def _fn10():
        first = chain_from(LEDGE_SOUTH, RAILINGS)
        expect(first).not_.to_be_null()
        expect(chain_from(RAILINGS, RAILINGS)).to_be_null()
    test('the way to the railings runs through the pipe, not the cages', _fn10)

    def _fn11():
        pipe = ([e for e in UPASS_CROSSINGS if e.loc == 3237 and e.to == RAILINGS] or [None])[0]
        expect((pipe.stand if pipe is not None else None)).to_equal(Tile(2419, 9605, 0))
        expect((pipe.lands if pipe is not None else None)).to_equal(Tile(2412, 9605, 0))
    test('the pipe into the railings is used from the tile east of it', _fn11)


describe('past the ledge', _fn9)


def _fn12():
    def _fn13():
        cage = ([e for e in UPASS_CROSSINGS if e.loc == 3266 and e.stand.x == 2393 and e.stand.z == 9655] or [None])[0]
        expect((cage.op if cage is not None else None)).to_be('Pick-lock')
        expect((cage.lands if cage is not None else None)).to_equal(Tile(2393, 9654, 0))
    test('opens the mud cell from the door tile itself', _fn13)


describe('the cage corridor', _fn12)

