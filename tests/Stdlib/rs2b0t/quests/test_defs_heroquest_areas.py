"""Ported from rs2b0t's test/api/ai/quests/defs/heroquest-areas.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.heroquest.areas import HERO_TILE, in_brimhaven_hq, in_deep_dungeon, in_garden, in_kitchen, in_mansion, in_side_room, in_store_corridor, in_treasure_room, in_velrak_cell, in_west_wing, in_yard, on_entrana

def at(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


# Why: every box is a flood of the collision pack, the Brimhaven mansion is six sealed pockets and a
# distance test calls the two sides of one wall the same place.
POCKETS = [
    Record({'name': 'kitchen', 'test': in_kitchen, 'seed': at(2789, 3191), 'size': 26}),
    Record({'name': 'garden', 'test': in_garden, 'seed': at(2784, 3194), 'size': 42}),
    Record({'name': 'yard', 'test': in_yard, 'seed': at(2781, 3196), 'size': 9}),
    Record({'name': 'sideroom', 'test': in_side_room, 'seed': at(2781, 3197), 'size': 5}),
    Record({'name': 'mansion', 'test': in_mansion, 'seed': at(2774, 3192), 'size': 82}),
    Record({'name': 'treasure', 'test': in_treasure_room, 'seed': at(2765, 3198), 'size': 17}),
    Record({'name': 'corridor', 'test': in_store_corridor, 'seed': at(2771, 3198), 'size': 8}),
]


def _seed_is_inside(pocket):
    def check():
        expect(pocket.test(pocket.seed)).to_be(True)
    return check


def _fn1():
    for pocket in POCKETS:
        test(f'the {pocket.name} seed is in the {pocket.name}', _seed_is_inside(pocket))

    def _fn3():
        for pocket in POCKETS:
            others = [p for p in POCKETS if p != pocket]
            for other in others:
                expect(other.test(pocket.seed)).to_be(False)
    test('no tile belongs to two pockets', _fn3)

    # Why: the two sides of `pete_sidedoor` are one tile apart and belong to different pockets.
    def _fn4():
        expect(in_yard(at(2781, 3196))).to_be(True)
        expect(in_side_room(at(2781, 3196))).to_be(False)
        expect(in_side_room(at(2781, 3197))).to_be(True)
        expect(in_yard(at(2781, 3197))).to_be(False)
    test('the side door separates the yard from the side room', _fn4)

    # Why: `snipable_wall` at (2780,3198) carries blockrange=no. The slit is the only line onto Grip.
    def _fn5():
        expect(in_side_room(HERO_TILE.ARROW_SLIT)).to_be(True)
        expect(in_mansion(HERO_TILE.GRIP_LURE)).to_be(True)
        expect(in_side_room(HERO_TILE.GRIP_LURE)).to_be(False)
    test('the arrow slit is in the side room and the lure tile is in the mansion', _fn5)

    def _fn6():
        expect(in_west_wing(at(2762, 3194))).to_be(True)
        expect(in_mansion(at(2762, 3194))).to_be(True)
        expect(in_treasure_room(at(2762, 3194))).to_be(False)
        expect(in_mansion(at(2765, 3198))).to_be(False)
    test('the west wing is inside what Garv seals, and the treasure room is not', _fn6)

    def _fn7():
        expect(in_mansion(HERO_TILE.CABINET_STAND)).to_be(True)
        expect(in_treasure_room(HERO_TILE.CHEST_STAND)).to_be(True)
        expect(in_west_wing(HERO_TILE.TREASURE_DOOR)).to_be(True)
        expect(in_treasure_room(HERO_TILE.TREASURE_DOOR_INNER)).to_be(True)
        expect(in_kitchen(HERO_TILE.KITCHEN_PANEL)).to_be(True)
        expect(in_garden(HERO_TILE.KITCHEN_PANEL_INNER)).to_be(True)
        expect(in_brimhaven_hq(HERO_TILE.GRUBOR_DOOR_INNER)).to_be(True)
        expect(in_brimhaven_hq(HERO_TILE.GRUBOR_DOOR)).to_be(False)
        expect(in_mansion(HERO_TILE.GARV_DOOR_INNER)).to_be(True)
        expect(in_mansion(HERO_TILE.GARV_DOOR)).to_be(False)
    test('each stand tile is in the pocket its loc lives in', _fn7)

    def _fn8():
        tile = HERO_TILE.RENDEZVOUS
        for pocket in POCKETS:
            expect(pocket.test(tile)).to_be(False)
        expect(in_brimhaven_hq(tile)).to_be(False)
    test('the rendezvous is on the street, outside every pocket', _fn8)

    def _fn9():
        for pocket in POCKETS:
            expect(pocket.test(None)).to_be(False)
        expect(on_entrana(None)).to_be(False)
    test('a null tile is nowhere', _fn9)

    def _fn10():
        expect(on_entrana(HERO_TILE.FIREBIRD)).to_be(True)
        expect(on_entrana(HERO_TILE.PORT_SARIM_MONK)).to_be(False)
    test('Entrana covers the firebird and not Port Sarim', _fn10)

    def _fn11():
        expect(in_mansion(at(2774, 3192, 1))).to_be(False)
        expect(in_kitchen(at(2789, 3191, 1))).to_be(False)
    test('a first-floor tile is never a ground-floor pocket', _fn11)


describe("hero's quest Brimhaven pockets", _fn1)


# Why: the deep dungeon and the rest of Taverley's interleave across x 2881-2923, so the predicate is a
# four-box cover of the flood rather than one rectangle over the pair.
def _fn12():
    def _fn13():
        expect(in_deep_dungeon(HERO_TILE.DEEP_GATE_INNER)).to_be(True)
        expect(in_deep_dungeon(HERO_TILE.DEEP_GATE)).to_be(False)
        expect(in_deep_dungeon(HERO_TILE.LAVA_FISH)).to_be(True)
    test('the deep gate separates the corridor from the lava eels', _fn13)

    def _fn14():
        expect(in_velrak_cell(HERO_TILE.JAIL_DOOR_INNER)).to_be(True)
        expect(in_velrak_cell(HERO_TILE.VELRAK)).to_be(True)
        expect(in_velrak_cell(HERO_TILE.JAIL_DOOR)).to_be(False)
        expect(in_velrak_cell(HERO_TILE.JAILER)).to_be(False)
    test('the cell door separates the jail from the corridor the Jailer patrols', _fn14)

    # Why: the chaos druid camp and the dungeon ladder are both in the main component; a predicate that
    # claimed either would strand the herb grind behind a gate it never crossed.
    def _fn15():
        expect(in_deep_dungeon(HERO_TILE.TAVERLEY_DUNGEON)).to_be(False)
        expect(in_deep_dungeon(HERO_TILE.CHAOS_DRUIDS)).to_be(False)
        expect(in_deep_dungeon(HERO_TILE.JAILER)).to_be(False)
        expect(in_deep_dungeon(HERO_TILE.VELRAK)).to_be(False)
    test('the ladder, the druids and the jail are all outside the deep dungeon', _fn15)

    def _fn16():
        expect(in_deep_dungeon(None)).to_be(False)
        expect(in_velrak_cell(None)).to_be(False)
        expect(in_deep_dungeon(at(2923, 9803, 1))).to_be(False)
        expect(in_velrak_cell(at(2931, 9689, 1))).to_be(False)
    test('a null tile and a first-floor tile are in neither', _fn16)


describe("hero's quest Taverley pockets", _fn12)
