"""The teleport halves of rs2b0t's site tests, test/scripts/JiveDemons/sites.test.ts and its dragon and King Black
Dragon kin (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect: every site's escape is a teleport
the walker's catalog knows, with the runes and level to cast it."""

from rs2004.hunting import DRAGON_SITES, escape_runes_for
from rs2004.routeplan import teleport_by_id
from bots.jivedemons.sites import TAVERLEY_BLACK_DEMON
from bots.jivekbd.sites import KBD_LAIR


def every_escape_known():
    for site in list(DRAGON_SITES.values()) + [TAVERLEY_BLACK_DEMON, KBD_LAIR]:
        expect(teleport_by_id(site.escape_teleport_id)).not_.to_be_null()
        spell = escape_runes_for(site.escape_teleport_id)
        expect(len(spell.runes)).to_be_greater_than(0)
        expect(spell.level).to_be_greater_than(0)


describe('the sites\' escape teleports', lambda: [
    test('the demons leave by the same catalog teleport as the blue dragons', lambda: expect(teleport_by_id(TAVERLEY_BLACK_DEMON.escape_teleport_id)).not_.to_be_null()),
    test('every site escapes by a catalog teleport with runes and a level', every_escape_known),
    test('the Falador teleport costs a law, a water and three airs at 37', lambda: [
        expect(escape_runes_for('falador').runes).to_equal([('Water rune', 1), ('Air rune', 3), ('Law rune', 1)]),
        expect(escape_runes_for('falador').level).to_be(37),
    ]),
])
