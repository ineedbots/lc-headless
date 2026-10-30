"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/fightarena-areas.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.fightarena.areas import FA_TILE, pocket_of

def at(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


def _fn1():
    def _fn2():
        expect(pocket_of(FA_TILE.YANILLE_BANK)).to_be('outside')
        expect(pocket_of(FA_TILE.LADY_SERVIL)).to_be('outside')
        expect(pocket_of(FA_TILE.BARMAN)).to_be('outside')
        expect(pocket_of(FA_TILE.CHEST_STAND)).to_be('outside')
        expect(pocket_of(FA_TILE.DOOR1_OUTSIDE)).to_be('outside')
    test('the mainland stands are outside every pocket', _fn2)

    def _fn3():
        expect(pocket_of(FA_TILE.DOOR1_INSIDE)).to_be('building')
        expect(pocket_of(FA_TILE.DRUNK_GUARD)).to_be('building')
        expect(pocket_of(FA_TILE.DOOR2_OUTSIDE)).to_be('building')
        expect(pocket_of(FA_TILE.JEREMY_DOOR_STAND)).to_be('building')
        expect(pocket_of(at(2609, 3149))).to_be('building')
    test('the guard corridor, the drunk guard and the arena door stand are the building', _fn3)

    def _fn4():
        expect(pocket_of(FA_TILE.ARENA_CENTRE)).to_be('arena')
        expect(pocket_of(FA_TILE.DOOR2_INSIDE)).to_be('arena')
        expect(pocket_of(at(2583, 3160))).to_be('arena')
        expect(pocket_of(at(2606, 3170))).to_be('arena')
    test('the arena floor is its own pocket', _fn4)

    def _fn5():
        expect(pocket_of(at(2616, 3168))).to_be('jeremyCell')
        expect(pocket_of(at(2614, 3166))).to_be('jeremyCell')
        expect(pocket_of(at(2600, 3142))).to_be('prisonCell')
        expect(pocket_of(at(2598, 3142))).to_be('prisonCell')
    test('both cells win over the building rect they sit inside', _fn5)

    def _fn6():
        expect(pocket_of(at(2617, 3168))).to_be('building')
        expect(pocket_of(at(2602, 3142))).to_be('building')
    test('the corridor tile beside each cell is still the building', _fn6)

    def _fn7():
        expect(pocket_of(None)).to_be('outside')
        expect(pocket_of(None)).to_be('outside')
        expect(pocket_of(at(2600, 3160, 3))).to_be('outside')
    test('an unknown or upper-level tile is outside', _fn7)


describe('pocketOf', _fn1)
