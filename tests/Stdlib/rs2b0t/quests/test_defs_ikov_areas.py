"""Ported from rs2b0t's test/api/ai/quests/defs/ikov-areas.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.ikov.areas import ICE_CHESTS, IKOV_TILE, in_chamber_of_fear, in_dark_room, in_guardian_temple, in_ice_cavern, in_temple, in_trap_pit, on_winelda_ledge, past_south_gate, west_of_bridge

REGIONS = [
    ['dark room', in_dark_room],
    ['west of the bridge', west_of_bridge],
    ['trap pit', in_trap_pit],
    ["Winelda's ledge", on_winelda_ledge],
    ["guardians' temple", in_guardian_temple],
]
INSIDE = [
    ['dark room', IKOV_TILE.DARK_LANDING],
    ['west of the bridge', IKOV_TILE.BRIDGE_WEST],
    ['trap pit', Record({'x': 2682, 'z': 9854})],
    ["Winelda's ledge", IKOV_TILE.WINELDA],
    ["guardians' temple", IKOV_TILE.GUARDIANS],
]


def _fn1():
    # Why: `escapePocket` picks its climb off these, so two that overlap send the bot up the wrong ladder.
    def _fn2():
        for name, tile in INSIDE:
            matched = [label for label, _2 in [(_1, inside) for _1, inside in REGIONS if inside(tile)]]
            expect([name, matched]).to_equal([name, [name]])
    test('each pocket tile matches its own region and no other', _fn2)

    def _fn5():
        matched = [label for label, _2 in [(_1, inside) for _1, inside in REGIONS if inside(IKOV_TILE.ENTRANCE)]]
        expect(matched).to_equal([])
    test('the entrance corridor is in none of the pockets', _fn5)

    def _fn8():
        expect(in_chamber_of_fear(IKOV_TILE.TRAP_LEVER)).to_be(True)
        expect(in_chamber_of_fear(IKOV_TILE.BRIDGE_EAST)).to_be(True)
        expect(in_chamber_of_fear(IKOV_TILE.ENTRANCE)).to_be(False)
    test('the chamber of fear holds the trap lever and the east bank of the bridge', _fn8)

    def _fn9():
        for _item10 in ICE_CHESTS:
            loc = _item10.loc
            stand = _item10.stand
            expect(in_ice_cavern(loc)).to_be(True)
            expect(in_ice_cavern(stand)).to_be(True)
            expect(in_chamber_of_fear(loc)).to_be(False)
    test('every ice chest is inside the ice cavern and none is in the chamber of fear', _fn9)

    # Why: `forceapproach=north` rotates with each placement, and the wrong side drops the Open with no refusal at all.
    def _fn11():
        for _item12 in ICE_CHESTS:
            loc = _item12.loc
            stand = _item12.stand
            expect(abs(loc.x - stand.x) + abs(loc.z - stand.z)).to_be(1)
    test('every chest stand is one tile off its chest', _fn11)

    def _fn13():
        expect(in_ice_cavern(IKOV_TILE.SOUTH_GATE_NORTH)).to_be(False)
        expect(in_ice_cavern(IKOV_TILE.SOUTH_GATE_SOUTH)).to_be(True)
    test('the ice cavern excludes the corridor the south gate opens from', _fn13)

    # Why: `inIceCavern` is the half-plane south and east of the temple, and the boots room sits inside it, a leg that treats "in the cavern" as "past the gate" reads the dark room as an unlocked gate.
    def _fn14():
        expect(in_ice_cavern(IKOV_TILE.BOOTS_SPAWN)).to_be(True)
        expect(in_dark_room(IKOV_TILE.BOOTS_SPAWN)).to_be(True)
    test('the boots room is inside the ice cavern half-plane', _fn14)

    def _fn15():
        expect(past_south_gate(IKOV_TILE.BOOTS_SPAWN)).to_be(False)
        expect(past_south_gate(IKOV_TILE.SOUTH_GATE_NORTH)).to_be(False)
        expect(past_south_gate(IKOV_TILE.SOUTH_GATE_SOUTH)).to_be(True)
        for _item16 in ICE_CHESTS:
            stand = _item16.stand
            expect(past_south_gate(stand)).to_be(True)
    test('past the south gate excludes the boots room and the corridor alike', _fn15)

    # Why: the far side wraps around the Fire Warrior's room, so the temple box has to stop at the corridor the wall opens into.
    def _fn17():
        expect(in_guardian_temple(IKOV_TILE.SECRET_WALL_INSIDE)).to_be(True)
        expect(in_guardian_temple(IKOV_TILE.SECRET_WALL)).to_be(False)
        expect(in_guardian_temple(IKOV_TILE.MCGRUBOR_LADDER)).to_be(False)
        expect(in_guardian_temple(Record({'x': 2637, 'z': 9893}))).to_be(False)
        expect(in_guardian_temple(Record({'x': 2657, 'z': 9895}))).to_be(False)
    test('the guardian temple box excludes the far side that shares its rows', _fn17)

    def _fn18():
        expect(in_temple(IKOV_TILE.ENTRANCE)).to_be(True)
        expect(in_temple(IKOV_TILE.GUARDIANS)).to_be(True)
        expect(in_temple(IKOV_TILE.DARK_LANDING)).to_be(True)
        expect(in_temple(IKOV_TILE.TEMPLE_LADDER)).to_be(False)
        expect(in_temple(IKOV_TILE.LUCIEN_HUT)).to_be(False)
    test('every temple tile reads as inside the temple, and the surface does not', _fn18)


describe('Temple of Ikov regions', _fn1)


def surface_is_not_past_the_gate():
    expect(past_south_gate(Record({'x': 2721, 'z': 3493, 'level': 0}))).to_be(False)
    expect(past_south_gate(Record({'x': 2661, 'z': 9800, 'level': 0}))).to_be(True)


test("the surface is not past the south gate, though it's south of the half-plane", surface_is_not_past_the_gate)
