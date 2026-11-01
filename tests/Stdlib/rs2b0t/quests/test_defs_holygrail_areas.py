"""Ported from rs2b0t's test/api/ai/quests/defs/holygrail-areas.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.holygrail.areas import GRAIL_TILE, east_of_titan, in_blighted_realm, in_castle_upstairs, in_fisher_realm, in_renewed_realm

def at(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


def _fn1():
    def _fn2():
        expect(in_blighted_realm(GRAIL_TILE.REALM_ARRIVAL)).to_be(True)
        expect(in_renewed_realm(GRAIL_TILE.REALM_ARRIVAL)).to_be(False)
        expect(in_renewed_realm(GRAIL_TILE.RENEWED_ARRIVAL)).to_be(True)
        expect(in_blighted_realm(GRAIL_TILE.RENEWED_ARRIVAL)).to_be(False)
        expect(in_fisher_realm(GRAIL_TILE.GRAIL_STAND)).to_be(True)
    test('the two realms are distinct and both count as the Fisher realm', _fn2)

    def _fn3():
        expect(in_fisher_realm(GRAIL_TILE.SIX_HEADS)).to_be(False)
        expect(in_fisher_realm(GRAIL_TILE.GOBLIN_SACKS)).to_be(False)
        expect(in_fisher_realm(None)).to_be(False)
    test('mainland tiles are in neither realm', _fn3)

    def _fn4():
        expect(east_of_titan(GRAIL_TILE.REALM_ARRIVAL)).to_be(True)
        expect(east_of_titan(GRAIL_TILE.TITAN_STAND)).to_be(True)
        expect(east_of_titan(GRAIL_TILE.TITAN_WEST)).to_be(False)
    test('the whistle landing is on the titan side and his west tile is not', _fn4)

    # Every pair is a row of the baked collision pack: the pocket's westmost tile
    # and the outside component's eastmost tile on the same z.
    def _fn5(z, pocket_west, outside_east):
        expect(east_of_titan(at(pocket_west, z))).to_be(True)
        expect(east_of_titan(at(outside_east, z))).to_be(False)
    test_each([
        [4709, 2805, 2796],
        [4710, 2801, 2792],
        [4711, 2799, 2791],
        [4712, 2797, 2790],
        [4713, 2794, 2790],
        [4716, 2793, 2789],
        [4722, 2792, 2790],
        [4725, 2792, 2788],
        [4728, 2790, 2784],
        [4731, 2789, 2783],
    ])('z %i splits the pocket at x %i from the far side at x %i', _fn5)

    def _fn6():
        expect(east_of_titan(GRAIL_TILE.BELL_SPAWN)).to_be(False)
        expect(east_of_titan(GRAIL_TILE.CASTLE_LANDING)).to_be(False)
        expect(in_castle_upstairs(GRAIL_TILE.FISHER_KING)).to_be(True)
        expect(in_castle_upstairs(GRAIL_TILE.CASTLE_LANDING)).to_be(False)
        expect(in_castle_upstairs(GRAIL_TILE.GRAIL_STAND)).to_be(False)
    test('the castle side and the ground outside it are never confused by level', _fn6)

    def _fn7():
        expect(east_of_titan(at(GRAIL_TILE.REALM_ARRIVAL.x, GRAIL_TILE.REALM_ARRIVAL.z, 1))).to_be(False)
    test('upper floors of the arrival pocket are not the titan side', _fn7)


describe('Holy Grail areas', _fn1)
