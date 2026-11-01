"""Ported from rs2b0t's test/api/ai/quests/regicidePockets.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.regicide.areas import RG_TILE
from rs2004.quests.defs.regicide.journal import RG_STAGE
from rs2004.quests.defs.regicide.pass_ import east_of_chasm, on_shelf
from rs2004.quests.defs.regicide.pockets import ARDOUGNE, FOREST_STAGE, GATE_STAGE, plan_route, pocket_at
from rs2004.quests.defs.regicide.seams import REGICIDE_POCKETS, REGICIDE_SEAMS

# Why: generated seam omissions compile cleanly but strand a live route.
def at(t):
    return (Record({'x': t.x, 'z': t.z, 'level': 0}))


def _fn1():
    def _fn2():
        _flat3 = []
        for seam in REGICIDE_SEAMS:
            _flat3.extend([side.pocket for side in seam.sides])
        named = set(_flat3)
        named = set([name for name in named if name != ARDOUGNE])
        baked = set([pocket.name for pocket in REGICIDE_POCKETS])
        expect([name for name in list(named) if not (name in baked)]).to_equal([])
    test('every pocket a seam names has spans baked for it', _fn2)

    def _fn4():
        degenerate = [seam for seam in REGICIDE_SEAMS if seam.sides[0].pocket == seam.sides[1].pocket]
        expect(degenerate).to_equal([])
    test('every seam joins two different pockets', _fn4)

    # Why: pitfalls and log balances are directional; using the far loc can stage the player inside the trap.
    def _fn5():
        loose = [seam for seam in REGICIDE_SEAMS if (seam.kind == 'pit' or seam.kind == 'log') and not seam.directed]
        expect(loose).to_equal([])
    test('every pitfall and log balance is marked one-way', _fn5)

    def _fn6():
        odd = [seam for seam in REGICIDE_SEAMS if seam.directed and seam.kind != 'pit' and seam.kind != 'log']
        expect(odd).to_equal([])
    test('nothing else is one-way', _fn6)

    def _fn7():
        wrong = [leg for leg in plan_route('isafdar-entry', 'elf-camp', RG_STAGE.SPOKEN_SCOUTS) if leg.seam.directed and leg.from_.stand is not leg.seam.sides[0].stand]
        expect(wrong).to_equal([])
    test('a one-way seam is never planned against its grain', _fn7)

    def _fn8():
        _flat9 = []
        for seam in REGICIDE_SEAMS:
            _flat9.extend([f'{seam.loc}@({seam.x},{seam.z}) -> {side.pocket}' for side in [side for side in seam.sides if side.pocket != ARDOUGNE and pocket_at(at(side.stand)) != side.pocket]])
        wrong = _flat9
        expect(wrong).to_equal([])
    test('every seam stand is inside the pocket it claims', _fn8)


describe('the Tirannwn seam table', _fn1)


def _fn10():
    def _fn11(_what, tile, pocket):
        expect(pocket_at(tile)).to_be(pocket)
    test_each([
        ['the Isafdar entry', RG_TILE.ISAFDAR_ENTRY, 'isafdar-entry'],
        ['the elf camp', RG_TILE.IORWERTH, 'elf-camp'],
        ['the loom', RG_TILE.LOOM, 'elf-camp'],
        ['the barrel spawn', RG_TILE.BARREL_SPAWN, 'elf-camp'],
        ['the pot spawn', RG_TILE.POT_SPAWN, 'elf-camp'],
        ['the old camp', RG_TILE.TRACKER, 'old-camp'],
        ['the tracks', RG_TILE.FOOTPRINTS, 'old-camp'],
        ['the coal-tar seep', RG_TILE.TAR, 'old-camp'],
        ['a sulphur formation', RG_TILE.SULPHUR, 'old-camp'],
        ['the guard ambush', RG_TILE.OLD_CAMP_WEST, 'old-camp-west'],
        ['the catapult', RG_TILE.CATAPULT, 'catapult'],
        ['the lazy guard', RG_TILE.LAZY_GUARD, 'catapult'],
        ['the camp entrance', RG_TILE.CAMP_ENTRANCE, 'catapult'],
        ["Tyras's camp", RG_TILE.TYRAS_CAMP, 'tyras-camp'],
        ['the camp furnace', RG_TILE.FURNACE, 'tyras-camp'],
        ['the limestone quarry', RG_TILE.QUARRY, 'quarry'],
    ])('%s is where the route table says it is', _fn11)

    def _fn12():
        expect(pocket_at(RG_TILE.ARDOUGNE_BANK)).to_be_undefined()
        expect(pocket_at(RG_TILE.ARANDAR_NORTH)).to_be_undefined()
    test("the mainland is nobody's pocket — the navigator owns it", _fn12)


describe('pocketAt', _fn10)


def _fn13():
    early = RG_STAGE.SPOKEN_SCOUTS
    late = RG_STAGE.SPOKEN_IORWERTH2

    def _fn14():
        route = plan_route('isafdar-entry', 'elf-camp', early)
        expect(route).not_.to_be_null()
        expect(all([leg.seam.kind != 'forest' for leg in route])).to_be(True)
    test('the early quest reaches the elf camp without a dense forest', _fn14)

    def _fn15():
        expect(plan_route('isafdar-entry', 'old-camp', early)).not_.to_be_null()
        expect(plan_route('elf-camp', 'old-camp', early)).not_.to_be_null()
    test('the early quest reaches the old camp and its tracker', _fn15)

    # Why: `_regicide_cross_over` answers "You can see no way to get past this" below stage 8, and the camp is behind four of them, a route that used one early would park the run at a crossing that refuses.
    def _fn16():
        expect(plan_route('elf-camp', 'tyras-camp', FOREST_STAGE - 1)).to_be_null()
        expect(plan_route('elf-camp', 'tyras-camp', FOREST_STAGE)).not_.to_be_null()
    test("Tyras's camp is unreachable until the tracker has explained the woodland", _fn16)

    def _fn17():
        expect(plan_route('elf-camp', 'catapult', late)).not_.to_be_null()
        expect(plan_route('catapult', 'elf-camp', late)).not_.to_be_null()
    test('the catapult is reachable once the forests open', _fn17)

    def _fn18():
        expect(plan_route('elf-camp', 'quarry', late)).not_.to_be_null()
    test('the quarry is reachable from the elf camp', _fn18)

    # Why: `arandar_gate` opens northbound at any stage and southbound only past `killed_tyras`, so the way out is free from the moment the bomb ingredients are gathered and the way back in is not.
    def _fn19():
        out = plan_route('elf-camp', ARDOUGNE, late)
        expect(out).not_.to_be_null()
        expect(any([leg.seam.kind == 'gate' for leg in out])).to_be(True)
    test('the palisade lets the quest out at any stage', _fn19)

    def _fn20():
        expect(plan_route(ARDOUGNE, 'elf-camp', GATE_STAGE - 1)).to_be_null()
        expect(plan_route(ARDOUGNE, 'elf-camp', GATE_STAGE)).not_.to_be_null()
    test('the palisade refuses to let the quest back in until the deed is reported', _fn20)

    def _fn21():
        expect(plan_route('elf-camp', 'elf-camp', late)).to_equal([])
    test('a route that starts where it ends is no legs at all', _fn21)


describe('planRoute', _fn13)


# Why: the chasm is derived, not eyeballed, flooding the collision pack from the cave landing (2494,9716) and from the bridge's west foot (2442,9716) gives two tile sets sharing no tile, and these cases pin the line between them. Tiles from both floods' extremes, plus the grid approach a bare x test misreads.
def _fn22():
    CASES = [
        ['the cave landing', Record({'x': 2494, 'z': 9716}), True],
        ["Koftik's lip by the bridge", Record({'x': 2449, 'z': 9716}), True],
        ['the guide-rope shooting stand', Record({'x': 2448, 'z': 9721}), True],
        ['the east side at its westmost', Record({'x': 2446, 'z': 9720}), True],
        ['the east side at its southmost', Record({'x': 2466, 'z': 9710}), True],
        ["the bridge's west foot", Record({'x': 2442, 'z': 9716}), False],
        ['the west bank lever', Record({'x': 2436, 'z': 9716}), False],
        ['the west side at its eastmost in the bridge band', Record({'x': 2442, 'z': 9717}), False],
        ['the rock swing, south of the bridge band', Record({'x': 2462, 'z': 9699}), False],
        ['the grid approach, which a bare x test reads as east', Record({'x': 2479, 'z': 9679}), False],
    ]

    def _fn23(_name, tile, east):
        expect(east_of_chasm(tile)).to_be(east)
    test_each(CASES)('%s', _fn23)

    def _fn24():
        expect(east_of_chasm(None)).to_be(False)
    test('an unknown tile is not assumed to be east of it', _fn24)


describe('the Underground Pass chasm', _fn22)


# Why: the shelf and the orb corridor are the two halves of the first cavern and they share no tile, but their bounding boxes overlap, so the split is the two bands the corridor cannot reach, and these cases pin both edges of it. A regenerated collision pack that moved either boundary would otherwise send the leg back down the well from the shelf, forever.
def _fn25():
    CASES = [
        ['the unicorn tunnel landing', Record({'x': 2371, 'z': 9666}), True],
        ['the blood well', Record({'x': 2373, 'z': 9718}), True],
        ['the paladins', Record({'x': 2424, 'z': 9719}), True],
        ['the shelf west edge', Record({'x': 2369, 'z': 9670}), True],
        ['the corridor well', Record({'x': 2416, 'z': 9674}), False],
        ['the corridor west edge', Record({'x': 2380, 'z': 9680}), False],
        ['the corridor north edge', Record({'x': 2440, 'z': 9698}), False],
    ]

    def _fn26(_what, tile, expected):
        expect(on_shelf(tile)).to_be(expected)
    test_each(CASES)('%s', _fn26)

    def _fn27():
        expect(on_shelf(None)).to_be(False)
    test('a missing tile is not the shelf', _fn27)


describe('the paladins shelf against the orb corridor', _fn25)

