"""rs2b0t's test/scripts/RockCrab: ammoLogic.test.ts, rockcrab-spots.test.ts and the RockCrab half of
RockCrabRangeLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect. The other grind
bots' ranged settings are in test_ranged_settings.py."""

from rs2004.catalogs import BOWS, DARTS, RANGED_WEAPONS, ROCK_CRAB_RANGED_WEAPONS, range_loadout_of, range_supply_empty, rock_crab_range_loadout
from bots.rock_crab import DEFAULT_SPOTS, ROCKS_SPAWNS, SETTINGS, Stack, spawns_within, sweep_plan


describe('sweep_plan', lambda: [
    test('ignores stacks below min_stack, keeps the rest nearest-first', lambda: expect(sweep_plan(
        [Stack('far-big', 9, 8), Stack('near-big', 5, 1), Stack('near-tiny', 1, 0)], 3, 12, False)).to_equal(['near-big', 'far-big'])),
    test('min_stack 1 collects everything in range', lambda: expect(sweep_plan([Stack('a', 1, 4)], 1, 12, False)).to_equal(['a'])),
    test('out-of-range stacks are never swept, even forced', lambda: expect(sweep_plan([Stack('a', 50, 13)], 1, 12, True)).to_equal([])),
    test('force takes sub-min_stack stacks (quiver empty / leaving field)', lambda: expect(sweep_plan([Stack('a', 1, 2)], 5, 12, True)).to_equal(['a'])),
])


def every_spot_touches():
    for spot in DEFAULT_SPOTS:
        touch = spawns_within(spot, 2)
        expect(touch).to_be_greater_than_or_equal(2)
        expect(touch).to_be_less_than_or_equal(3)


def pairwise_apart():
    for i in range(len(DEFAULT_SPOTS)):
        for j in range(i + 1, len(DEFAULT_SPOTS)):
            expect(DEFAULT_SPOTS[i].distance_to(DEFAULT_SPOTS[j])).to_be_greater_than(4)


def in_the_field():
    for t in DEFAULT_SPOTS + ROCKS_SPAWNS:
        expect(t.level).to_be(0)
        expect(t.x).to_be_greater_than_or_equal(2690)
        expect(t.x).to_be_less_than_or_equal(2723)
        expect(t.z).to_be_greater_than_or_equal(3710)
        expect(t.z).to_be_less_than_or_equal(3733)


def first_spot():
    expect(len(DEFAULT_SPOTS)).to_be_greater_than_or_equal(3)
    expect(len(DEFAULT_SPOTS)).to_be_less_than_or_equal(5)
    expect(DEFAULT_SPOTS[0].x).to_be(2704)
    expect(DEFAULT_SPOTS[0].z).to_be(3726)


describe('DEFAULT_SPOTS', lambda: [
    test('provides 3-5 preset spots, loc1 = the user-verified (2704,3726)', first_spot),
    test('every spot touches 2-3 spawns with its 3x3 square', every_spot_touches),
    test('the top two spots wake 2 crabs from standing still (huntrange 1)', lambda: [
        expect(spawns_within(DEFAULT_SPOTS[0], 1)).to_be(2),
        expect(spawns_within(DEFAULT_SPOTS[1], 1)).to_be(2),
    ]),
    test('no spot stands on a spawn tile', lambda: [expect(len([s for s in ROCKS_SPAWNS if s.equals(spot)])).to_be(0) for spot in DEFAULT_SPOTS]),
    test('spots are pairwise > 4 apart (one per cluster, switching hits fresh crabs)', pairwise_apart),
    test('all spots and spawns share the field level (0) and bounding box', in_the_field),
])


def loadout(weapon, projectile, thrown):
    return {'weapon': weapon, 'projectile': projectile, 'thrown': thrown}


def each_dart():
    for dart in DARTS:
        expect(range_loadout_of(dart, 'Rune arrow')).to_equal(loadout(dart, dart, True))
        # The deprecated RockCrab alias stays wired.
        expect(rock_crab_range_loadout(dart, 'Rune arrow')).to_equal(loadout(dart, dart, True))


describe('shared ranged loadouts (RockCrab)', lambda: [
    test('offers every bow and standard dart as a ranged weapon', lambda: [
        expect(RANGED_WEAPONS).to_equal(BOWS + DARTS),
        expect(ROCK_CRAB_RANGED_WEAPONS).to_equal(RANGED_WEAPONS),
        expect(DARTS).to_equal(['Bronze dart', 'Iron dart', 'Steel dart', 'Black dart', 'Mithril dart', 'Adamant dart', 'Rune dart']),
    ]),
    test('wires the bow setting to the ranged weapon control', lambda: [
        expect(SETTINGS['bow'].label).to_be('Ranged weapon'),
        expect(SETTINGS['bow'].options).to_equal(RANGED_WEAPONS + ['Other']),
        expect(SETTINGS['ammo'].label).to_be('Bow ammo'),
        expect('ignored when the ranged weapon is a dart' in SETTINGS['ammo'].help).to_be(True),
    ]),
    test('each dart is its own weapon-slot projectile', each_dart),
    test('recognizes persisted dart names case-insensitively', lambda: expect(range_loadout_of('  rUnE DaRt ', 'Bronze arrow')).to_equal(
        loadout('Rune dart', 'Rune dart', True))),
    test('bows retain their separate quiver ammo', lambda: expect(range_loadout_of('Maple shortbow', 'Adamant arrow')).to_equal(
        loadout('Maple shortbow', 'Adamant arrow', False))),
    test('only reports depletion when no projectile remains anywhere', lambda: [
        expect(range_supply_empty(0, 0, 0)).to_be(True),
        expect(range_supply_empty(1, 0, 0)).to_be(False),
        expect(range_supply_empty(0, 1, 0)).to_be(False),
        expect(range_supply_empty(0, 0, 1)).to_be(False),
    ]),
])
