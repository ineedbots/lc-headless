"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/treegnome-areas.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.treegnome.areas import TG_ITEM, TG_TILE, in_chest_floor, in_khazard_hall, in_ladder_room, in_stronghold

def at(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


def _fn1():
    def _fn2():
        expect(in_khazard_hall(TG_TILE.HALL_LANDING)).to_be(True)
        expect(in_ladder_room(TG_TILE.HALL_LANDING)).to_be(False)
    test('the crumbled-wall landing is the east hall', _fn2)

    def _fn3():
        expect(in_ladder_room(TG_TILE.LADDER_STAND)).to_be(True)
        expect(in_khazard_hall(TG_TILE.LADDER_STAND)).to_be(False)
    test('the ladder stand is the west room', _fn3)

    # Why: the two rooms share x and z ranges, so a single box would answer for the wrong side of the inner door.
    def _fn4():
        expect(in_ladder_room(at(2506, 3255))).to_be(True)
        expect(in_khazard_hall(at(2506, 3255))).to_be(False)
        expect(in_khazard_hall(at(2507, 3255))).to_be(True)
        expect(in_ladder_room(at(2507, 3255))).to_be(False)
    test('the rows that overlap in z still separate the two rooms', _fn4)

    def _fn5():
        expect(in_chest_floor(TG_TILE.CHEST_STAND)).to_be(True)
        expect(in_chest_floor(at(2506, 3258))).to_be(False)
    test('the chest floor is level 1 only', _fn5)

    def _fn6():
        expect(in_stronghold(TG_TILE.OUTSIDE_FRONT_DOOR)).to_be(False)
        expect(in_stronghold(TG_TILE.WALL_STAND)).to_be(False)
    test('the tile the front door drops you on is outside', _fn6)

    def _fn7():
        expect(in_stronghold(TG_TILE.MONTAI)).to_be(False)
        expect(in_stronghold(TG_TILE.BOLREN)).to_be(False)
        expect(in_stronghold(None)).to_be(False)
    test('the battlefield and the village are outside', _fn7)


describe('Khazard stronghold rooms', _fn1)


def _fn8():
    # Why: `orb_of_protection` and `orbs_of_protection` share a display name, and only the plural finishes the quest.
    def _fn9():
        expect(TG_ITEM.ORB.name).to_be(TG_ITEM.ORBS.name)
        expect(TG_ITEM.ORB.id).not_.to_be(TG_ITEM.ORBS.id)
    test('the one orb and the two orbs differ by id alone', _fn9)


describe('Tree Gnome Village items', _fn8)
