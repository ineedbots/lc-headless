"""rs2b0t's test/scripts/JiveKBD: logic.test.ts, settings.test.ts and sites.test.ts (MIT, see thirdparty/rs2b0t), on
spec.py's describe, test and expect. The escape teleport's catalog check is in nav/, beside the walker's data, and
sites.test.ts's pack-gated derivation needs rs2b0t's own tools."""

from rs2004.catalogs import drop_db
from bots.jivekbd.logic import ANTIPOISON_DOSES, DOSE_MARGIN_TICKS, IMMUNE_TICKS, POISONED, dose_due, dose_to_drink
from bots.jivekbd.sites import KBD_LAIR, KBD_ROUTE, KBD_SITES, SITE_OPTIONS, site_for
from bots.jive_kbd import SETTINGS, site_tile


def poisoned(text):
    return POISONED in text.lower()


HELD = {'Superantipoison(4)': 1, 'Superantipoison(2)': 1}

describe('POISONED', lambda: [
    test('matches the poisoning line whatever the case', lambda: [
        expect(poisoned('You have been poisoned!')).to_be(True),
        expect(poisoned('you have been poisoned!')).to_be(True),
    ]),
    test('ignores the cure and the shield lines', lambda: [
        expect(poisoned('You drink some of your antipoison potion.')).to_be(False),
        expect(poisoned("Your shield absorbs most of the dragon's toxic breath!")).to_be(False),
    ]),
])

describe('dose_due', lambda: [
    test('owed when nothing has been drunk', lambda: expect(dose_due(None, 1000)).to_be(True)),
    test('not owed inside the immunity window less the margin', lambda: expect(dose_due(1000, 1000 + IMMUNE_TICKS - DOSE_MARGIN_TICKS - 1)).to_be(False)),
    test('owed once the margin is reached', lambda: expect(dose_due(1000, 1000 + IMMUNE_TICKS - DOSE_MARGIN_TICKS)).to_be(True)),
])

describe('dose_to_drink', lambda: [
    test('drinks the smallest flask held first', lambda: expect(dose_to_drink(lambda n: HELD.get(n, 0))).to_be('Superantipoison(2)')),
    test('null with no dose in the pack', lambda: expect(dose_to_drink(lambda n: 0)).to_be_null()),
])

LOOT = SETTINGS['loot']

describe('JiveKBD loot defaults', lambda: [
    test('the options are the King Black Dragon table and every row starts ticked', lambda: [
        expect(LOOT.options).to_equal(drop_db()['King black dragon']),
        expect(LOOT.default).to_equal(LOOT.options),
        expect(LOOT.options).to_contain('Dragon bones'),
        expect(LOOT.options).to_contain('Dragon med helm'),
        expect(LOOT.options).to_contain('Rune longsword'),
    ]),
])

describe('JiveKBD is mage only', lambda: [
    test('a staff and a spell are offered, nothing for range or melee', lambda: [
        expect(SETTINGS['staff'].default).to_be('Staff of fire'),
        expect(SETTINGS['spell'].default).to_be('Fire Strike'),
    ] + [expect(key in SETTINGS).to_be(False) for key in ['combat_style', 'bow', 'ammo', 'range_style', 'ammo_withdraw', 'melee_style', 'weapon',
                                                          'use_special', 'use_potions', 'bury_bones', 'solve_clues', 'leave_via']]),
    test('one antipoison flask a trip by default, never none', lambda: [
        expect(SETTINGS['doses_withdraw'].default).to_be(1),
        expect(SETTINGS['doses_withdraw'].min).to_be(1),
    ]),
])

ELSEWHERE = Tile(3200, 3200, 0)


def alcove_defaults():
    expect(SETTINGS['safespot1'].default).to_equal(KBD_LAIR.safespots[0])
    expect(SETTINGS['safespot2'].default).to_equal(KBD_LAIR.safespots[1])
    expect(SETTINGS['bank_tile'].default).to_equal(KBD_LAIR.bank)
    expect(SETTINGS['site'].default).to_be('kbd-lair')
    expect(site_tile(SettingsBag({'safespot1': SETTINGS['safespot1'].default}), 'safespot1', ELSEWHERE)).to_be(ELSEWHERE)


describe('JiveKBD site tiles', lambda: [
    test('the schema default is the alcove, so an untouched setting hands the tile back to the site', alcove_defaults),
    test('a tile moved off the default is the one that applies', lambda: expect(
        site_tile(SettingsBag({'safespot1': Tile(2714, 9830, 0)}), 'safespot1', ELSEWHERE).equals(Tile(2714, 9830, 0))).to_be(True)),
])


def every_option_resolves():
    expect(SITE_OPTIONS).to_equal(['kbd-lair'])
    for key in SITE_OPTIONS:
        expect(site_for(key).key).to_be(key)
    expect(site_for('nope').key).to_be('kbd-lair')
    expect(KBD_SITES['kbd-lair'] is KBD_LAIR).to_be(True)


def inside(x, z, level=0):
    return KBD_LAIR.in_area(Tile(x, z, level))


describe('KBD_SITES', lambda: [
    test('the lair is the only entry and every option resolves', every_option_resolves),
    test('the target is the client display name, lower-case black', lambda: expect(KBD_LAIR.target).to_be('King black dragon')),
    test('the safespots are the two alcove tiles south of the arrival, the lever tile first', lambda: [
        expect([[t.x, t.z, t.level] for t in KBD_LAIR.safespots]).to_equal([[2717, 9801, 0], [2716, 9801, 0]]),
        expect([KBD_LAIR.melee_anchor.x, KBD_LAIR.melee_anchor.z]).to_equal([2714, 9829]),
    ]),
    test('no gate, no key, no approach, and the dragon breathes at the tile', lambda: [
        expect(KBD_LAIR.gate).to_be_null(),
        expect(KBD_LAIR.key_item).to_be_null(),
        expect(KBD_LAIR.approach).to_equal([]),
        expect(KBD_LAIR.ranged_threat).to_be(True),
    ]),
    test('banks at Edgeville and escapes by the Varrock teleport', lambda: [
        expect([KBD_LAIR.bank.x, KBD_LAIR.bank.z]).to_equal([3094, 3493]),
        expect(KBD_LAIR.walk_out.equals(KBD_LAIR.bank)).to_be(True),
        expect(KBD_LAIR.escape_teleport_id).to_be('varrock'),
    ]),
    test('in_area is the 42_153 square on level 0 and nothing else', lambda: [
        expect(inside(2717, 9802)).to_be(True),
        expect(inside(2688, 9792)).to_be(True),
        expect(inside(2751, 9855)).to_be(True),
        expect(inside(2687, 9802)).to_be(False),
        expect(inside(2752, 9802)).to_be(False),
        expect(inside(2717, 9791)).to_be(False),
        expect(inside(2717, 9856)).to_be(False),
        expect(inside(2717, 9802, 1)).to_be(False),
        expect(inside(3067, 10254)).to_be(False),
        expect(KBD_LAIR.in_area(None)).to_be(False),
    ]),
])


def stop(s):
    return [s.tile.x, s.tile.z, s.loc_id, s.op, s.radius]


def on_level_zero():
    route = KBD_ROUTE
    tiles = [route.ladder.tile, route.dungeon_arrival, route.lever.tile, route.lair_arrival, route.out_lever.tile, route.dungeon_return,
             route.up_ladder.tile, route.surface] + KBD_LAIR.safespots + [KBD_LAIR.bank]
    expect(len([t for t in tiles if t.level != 0])).to_be(0)


describe('KBD_ROUTE', lambda: [
    test('the ladder is the Lava Maze one, climbed from beside it', lambda: [
        expect(stop(KBD_ROUTE.ladder)).to_equal([3017, 3849, 1765, 'Climb-down', 1]),
        expect([KBD_ROUTE.dungeon_arrival.x, KBD_ROUTE.dungeon_arrival.z]).to_equal([3069, 10255]),
    ]),
    test('both levers are pulled from their own tile, a straight wall decoration being legal from underfoot alone', lambda: [
        expect(stop(KBD_ROUTE.lever)).to_equal([3067, 10253, 1816, 'Pull', 0]),
        expect(stop(KBD_ROUTE.out_lever)).to_equal([2717, 9801, 1817, 'Pull', 0]),
    ]),
    test('each teleport lands on the tile north of the other lever, and the out-lever sits on the first safespot', lambda: [
        expect([KBD_ROUTE.lair_arrival.x, KBD_ROUTE.lair_arrival.z]).to_equal([2717, 9802]),
        expect([KBD_ROUTE.dungeon_return.x, KBD_ROUTE.dungeon_return.z]).to_equal([3067, 10254]),
        expect(KBD_ROUTE.out_lever.tile.equals(KBD_LAIR.safespots[0])).to_be(True),
    ]),
    test('the ladder up stands beside the dungeon arrival and lands on the surface', lambda: [
        expect(stop(KBD_ROUTE.up_ladder)).to_equal([3069, 10256, 1766, 'Climb-up', 1]),
        expect(KBD_ROUTE.up_ladder.tile.distance_to(KBD_ROUTE.dungeon_arrival)).to_be(1),
        expect([KBD_ROUTE.surface.x, KBD_ROUTE.surface.z]).to_equal([3016, 3849]),
    ]),
    test('in_dungeon is the 47_160 square and excludes the lair and the surface', lambda: [
        expect(KBD_ROUTE.in_dungeon(KBD_ROUTE.dungeon_arrival)).to_be(True),
        expect(KBD_ROUTE.in_dungeon(KBD_ROUTE.lever.tile)).to_be(True),
        expect(KBD_ROUTE.in_dungeon(Tile(3008, 10240, 0))).to_be(True),
        expect(KBD_ROUTE.in_dungeon(Tile(3071, 10303, 0))).to_be(True),
        expect(KBD_ROUTE.in_dungeon(KBD_ROUTE.lair_arrival)).to_be(False),
        expect(KBD_ROUTE.in_dungeon(KBD_ROUTE.ladder.tile)).to_be(False),
        expect(KBD_ROUTE.in_dungeon(None)).to_be(False),
        expect(KBD_LAIR.in_area(KBD_ROUTE.dungeon_arrival)).to_be(False),
    ]),
    test('every tile sits on level 0', on_level_zero),
])
