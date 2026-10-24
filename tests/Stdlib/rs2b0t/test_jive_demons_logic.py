"""rs2b0t's test/scripts/JiveDemons: logic.test.ts, settings.test.ts and sites.test.ts (MIT, see thirdparty/rs2b0t),
on spec.py's describe, test and expect. paint.test.ts tests the paint, which isn't headless, and sites.test.ts's
pack-gated derivation needs rs2b0t's own tools. The escape teleport's catalog check is in nav/, beside the
walker's data."""

from rs2004.catalogs import Record, drop_db
from rs2004.hunting import LOOT_GUARD, TAVERLEY_BLUE, guarded
from bots.jivedemons.sites import DEMON_SITES, SITE_OPTIONS, TAVERLEY_BLACK_DEMON, site_for
from bots.jive_demons import SETTINGS, site_tile


def body(x, z, size):
    return Record({'tile': {'x': x, 'z': z}, 'size': size})


def spot(x, z):
    return Record({'x': x, 'z': z})


DEMON = body(2860, 9781, 3)
FAR = body(2870, 9776, 3)

describe('guarded', lambda: [
    test("a drop at a demon's feet is guarded", lambda: expect(guarded(spot(2862, 9784), [DEMON])).to_be(True)),
    test('the guard reaches the hunt range plus a tile, measured to the body, inclusive', lambda: [
        expect(LOOT_GUARD).to_be(4),
        expect(guarded(spot(2856, 9786), [DEMON])).to_be(True),
        expect(guarded(spot(2856, 9787), [DEMON])).to_be(False),
    ]),
    test('with no demon in the scene nothing is guarded', lambda: expect(guarded(spot(2862, 9784), [])).to_be(False)),
    test('any one demon in range guards the drop', lambda: [
        expect(guarded(spot(2856, 9787), [FAR, DEMON])).to_be(False),
        expect(guarded(spot(2856, 9786), [FAR, DEMON])).to_be(True),
    ]),
])

LOOT = SETTINGS['loot']

describe('JiveDemons loot defaults', lambda: [
    test('the options are the black demon table', lambda: [
        expect(LOOT.options).to_equal(drop_db()['Black Demon']),
        expect(LOOT.options).to_contain('Rune chainbody'),
        expect(LOOT.options).to_contain('Blood rune'),
    ]),
    test('Ashes are offered but start unticked, since nothing pays for a slot of them', lambda: [
        expect(LOOT.options).to_contain('Ashes'),
        expect(LOOT.default).not_.to_contain('Ashes'),
    ]),
    test('Coins start ticked, since the pile is the most common drop and the walk to it is two tiles', lambda: [
        expect(LOOT.default).to_contain('Coins'),
        expect(LOOT.default).to_contain('Rune med helm'),
    ]),
])

describe('JiveDemons styles', lambda: [
    test('range and mage are the only styles, range by default', lambda: [
        expect(SETTINGS['combat_style'].options).to_equal(['range', 'mage']),
        expect(SETTINGS['combat_style'].default).to_be('range'),
    ]),
    test('nothing melee, nothing to bury and no clue trail is offered', lambda: [
        expect(key in SETTINGS).to_be(False) for key in ['melee_style', 'weapon', 'use_special', 'use_potions', 'melee_tile', 'bury_bones', 'solve_clues']
    ]),
    test('the teleport and the gate walk are the only ways out, the teleport by default', lambda: [
        expect(SETTINGS['leave_via'].options).to_equal(['teleport', 'walk']),
        expect(SETTINGS['leave_via'].default).to_be('teleport'),
    ]),
])

ELSEWHERE = Tile(3200, 3200, 0)


def untouched_hands_back():
    expect(SETTINGS['safespot1'].default).to_equal(TAVERLEY_BLACK_DEMON.safespots[0])
    expect(SETTINGS['site'].default).to_be('taverley-black-demon')
    bag = SettingsBag({'safespot1': SETTINGS['safespot1'].default})
    expect(site_tile(bag, 'safespot1', ELSEWHERE)).to_be(ELSEWHERE)


def moved_applies():
    moved = Tile(2858, 9787, 0)
    expect(site_tile(SettingsBag({'safespot1': moved}), 'safespot1', ELSEWHERE).equals(moved)).to_be(True)


describe('JiveDemons site tiles', lambda: [
    test('the schema default is the Taverley pocket, so an untouched setting hands the tile back to the site', untouched_hands_back),
    test('a tile moved off the default is the one that applies', moved_applies),
    test('a site carrying more safespots than the panel has keys for keeps its own', lambda: expect(site_tile(SettingsBag({}), None, ELSEWHERE)).to_be(ELSEWHERE)),
    test('the bank stand reads the same way', lambda: expect(site_tile(SettingsBag({'bank_tile': Tile(3013, 3355, 0)}), 'bank_tile', ELSEWHERE).equals(Tile(3013, 3355, 0))).to_be(True)),
])


def every_option_resolves():
    expect(SITE_OPTIONS).to_equal(['taverley-black-demon'])
    for key in SITE_OPTIONS:
        expect(site_for(key).key).to_be(key)


def tiles():
    s = DEMON_SITES['taverley-black-demon']
    expect([[t.x, t.z] for t in s.safespots]).to_equal([[2856, 9786], [2857, 9786], [2855, 9786]])
    expect([s.melee_anchor.x, s.melee_anchor.z]).to_equal([2859, 9786])
    expect(len([t for t in s.safespots if t.level != 0])).to_be(0)


def same_gate():
    s = TAVERLEY_BLACK_DEMON
    expect(s.gate).to_equal(TAVERLEY_BLUE.gate)
    expect(s.key_item).to_equal(TAVERLEY_BLUE.key_item)
    expect(s.bank.equals(TAVERLEY_BLUE.bank)).to_be(True)
    expect(s.walk_out.equals(TAVERLEY_BLUE.walk_out)).to_be(True)
    expect(s.escape_teleport_id).to_be(TAVERLEY_BLUE.escape_teleport_id)


def inside(x, z, level=0):
    return TAVERLEY_BLACK_DEMON.in_area(Tile(x, z, level))


describe('DEMON_SITES', lambda: [
    test('Taverley black is the only entry and every option resolves', every_option_resolves),
    test('an unknown key falls back to Taverley rather than throwing', lambda: expect(site_for('nope').key).to_be('taverley-black-demon')),
    test('the target is the client display name, capital D and all', lambda: expect(TAVERLEY_BLACK_DEMON.target).to_be('Black Demon')),
    test('the tiles are the probe tile the run was given and the two derived beside it', tiles),
    test('the approach runs down the passage and along the corridor before the pocket', lambda: expect(
        [[t.x, t.z] for t in DEMON_SITES['taverley-black-demon'].approach]).to_equal([[2893, 9790], [2893, 9771], [2875, 9774]])),
    test('demons drop ashes, so there is nothing to bury', lambda: expect(TAVERLEY_BLACK_DEMON.bones).to_be('')),
    test('the demons sit behind the same gate, key, bank and escape as the blue dragons', same_gate),
    test('in_area holds the blue lair, the passage, the corridor and the pocket', lambda: [
        expect(inside(2923, 9803)).to_be(True),
        expect(inside(2901, 9809)).to_be(True),
        expect(inside(2893, 9782)).to_be(True),
        expect(inside(2883, 9769)).to_be(True),
        expect(inside(2856, 9786)).to_be(True),
        expect(inside(2854, 9776)).to_be(True),
    ]),
    test('in_area rejects the entrance corridor, the far side of the gate and the surface', lambda: [
        expect(inside(2884, 9798)).to_be(False),
        expect(inside(2881, 9796)).to_be(False),
        expect(inside(2887, 9810)).to_be(False),
        expect(inside(2924, 9803)).to_be(False),
        expect(inside(2856, 3786)).to_be(False),
        expect(inside(2856, 9786, 1)).to_be(False),
        expect(TAVERLEY_BLACK_DEMON.in_area(None)).to_be(False),
    ]),
    test('the pocket box is pinned from both sides on every edge', lambda: [
        expect(inside(2850, 9776)).to_be(True),
        expect(inside(2849, 9776)).to_be(False),
        expect(inside(2880, 9790)).to_be(True),
        expect(inside(2881, 9790)).to_be(False),
        expect(inside(2860, 9762)).to_be(True),
        expect(inside(2860, 9761)).to_be(False),
        expect(inside(2870, 9797)).to_be(True),
        expect(inside(2870, 9798)).to_be(False),
    ]),
    test('the corridor box bridges the pocket to the passage without touching the ladder side', lambda: [
        expect(inside(2885, 9770)).to_be(True),
        expect(inside(2885, 9776)).to_be(False),
        expect(inside(2885, 9762)).to_be(True),
        expect(inside(2885, 9761)).to_be(False),
    ]),
])
