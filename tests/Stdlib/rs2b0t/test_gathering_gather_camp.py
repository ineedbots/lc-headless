"""rs2b0t's test/scripts/GatheringBot/GatherCamp.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import DEFAULT_CHASE_RADIUS, HOME_ARRIVE_RADIUS, Record, resolve_camp_radius, should_soft_home_from_gather_miss, should_walk_home_to_gather_anchor
from bots.gathering.camp import NAMED_CAMP_LEASH_FLOOR, effective_gather_leash, gather_hunt_radius, gather_spot_range_origin, is_auto_location, resource_within_camp, spot_avoided, spot_within_gather_range, sweep_stop_for


def _fn1():
    far = [Record({'x': 2855, 'z': 2977, 'level': 0})]

    def _fn2():
        expect(spot_avoided(Record({'x': 2855, 'z': 2977, 'level': 0}), far)).to_be(True)
        expect(spot_avoided(Record({'x': 2855, 'z': 2973, 'level': 0}), far)).to_be(False)
        expect(spot_avoided(Record({'x': 2855, 'z': 2977, 'level': 1}), far)).to_be(False)
        expect(spot_avoided(Record({'x': 2855, 'z': 2977, 'level': 0}), [])).to_be(False)
    test('refuses only the exact avoided tile and plane', _fn2)
    sweep = [Record({'x': 2862, 'z': 2971, 'level': 0}), Record({'x': 2822, 'z': 2968, 'level': 0})]

    def _fn3():
        expect(sweep_stop_for(sweep, 0, None)).to_equal(Record({'stop': sweep[0], 'index': 0}))
        expect(sweep_stop_for(sweep, 0, Record({'x': 2841, 'z': 2970, 'level': 0}))).to_equal(Record({'stop': sweep[0], 'index': 0}))
        expect(sweep_stop_for(sweep, 0, Record({'x': 2863, 'z': 2972, 'level': 0}))).to_equal(Record({'stop': sweep[1], 'index': 1}))
        expect(sweep_stop_for(sweep, 1, Record({'x': 2822, 'z': 2968, 'level': 0}))).to_equal(Record({'stop': sweep[0], 'index': 0}))
        expect(sweep_stop_for(sweep, 0, Record({'x': 2862, 'z': 2971, 'level': 1}))).to_equal(Record({'stop': sweep[0], 'index': 0}))
    test('holds the current stop until arrival, then wraps', _fn3)

    def _fn4():
        expect(sweep_stop_for(sweep, 3, None)).to_equal(Record({'stop': sweep[1], 'index': 1}))
        expect(sweep_stop_for([], 4, None)).to_equal(Record({'stop': None, 'index': 0}))
    test('normalizes the index and holds the pin for camps without a sweep', _fn4)


describe('Shilo spot selection', _fn1)


def _fn5():
    def _fn6():
        expect(resource_within_camp(64, NAMED_CAMP_LEASH_FLOOR)).to_be(True)
        expect(resource_within_camp(65, NAMED_CAMP_LEASH_FLOOR)).to_be(False)
        expect(resource_within_camp(72, 80)).to_be(True)
    test('resourceWithinCamp inclusive Chebyshev', _fn6)

    def _fn7():
        expect(effective_gather_leash(12, 'Use Closest')).to_be(12)
        expect(effective_gather_leash(12, 'Use Start Position')).to_be(12)
        expect(effective_gather_leash(12, 'Use Custom Position')).to_be(12)
        expect(effective_gather_leash(12, 'Auto')).to_be(12)
        expect(effective_gather_leash(10, 'Catherby')).to_be(NAMED_CAMP_LEASH_FLOOR)
        expect(is_auto_location(' auto ')).to_be(True)
        expect(is_auto_location('Use Closest')).to_be(True)
        expect(is_auto_location('Use Start Position')).to_be(True)
        expect(is_auto_location('Use Custom Position')).to_be(True)
        expect(is_auto_location('Dwarven Mine')).to_be(False)
    test('effectiveGatherLeash freeform vs named floor', _fn7)

    def _fn8():
        expect(gather_hunt_radius(28)).to_be(52)
        expect(gather_hunt_radius(18)).to_be(48)
    test('gatherHuntRadius freeform pad', _fn8)

    def _fn9():
        expect(gather_spot_range_origin(True, True)).to_be('player')
        expect(gather_spot_range_origin(False, True, True)).to_be('player')
        expect(gather_spot_range_origin(False, True, False)).to_be('anchor')
        expect(spot_within_gather_range(40, 40)).to_be(True)
    test('gatherSpotRangeOrigin named + freeform fish use player', _fn9)

    def _fn10():
        expect(resolve_camp_radius(None)).to_be(64)
        expect(DEFAULT_CHASE_RADIUS).to_be(40)
    test('resolveCampRadius default', _fn10)


describe('GatherCamp membership', _fn5)


def _fn11():
    def _fn12():
        bank_dist = Tile(2845, 3431, 0).distance_to(Tile(2809, 3441, 0))
        expect(bank_dist).to_be(36)
        expect(should_walk_home_to_gather_anchor(bank_dist)).to_be(True)
        expect(should_walk_home_to_gather_anchor(HOME_ARRIVE_RADIUS)).to_be(False)
        expect(should_soft_home_from_gather_miss(36)).to_be(True)
        expect(should_soft_home_from_gather_miss(12)).to_be(False)
    test('Catherby bank needs walk (not full membership home)', _fn12)


describe('Anchor soft-home', _fn11)


def _fn13():
    # Why: the four Shilo tiles whose only stand is across the water, derived by tools/nav/shilo-fishing-stands.ts.
    FAR = [
        Record({'x': 2850, 'z': 2976, 'level': 0}),
        Record({'x': 2855, 'z': 2977, 'level': 0}),
        Record({'x': 2860, 'z': 2976, 'level': 0}),
        Record({'x': 2869, 'z': 2977, 'level': 0}),
    ]

    def _fn14():
        expect(spot_avoided(Record({'x': 2855, 'z': 2977, 'level': 0}), FAR)).to_be(True)
    test('a spot on a far-bank tile is refused however close it looks', _fn14)

    def _fn15():
        expect(spot_avoided(Record({'x': 2855, 'z': 2973, 'level': 0}), FAR)).to_be(False)
        expect(spot_avoided(Record({'x': 2856, 'z': 2977, 'level': 0}), FAR)).to_be(False)
    test('the village-bank tile one step from it is still fished', _fn15)

    def _fn16():
        expect(spot_avoided(Record({'x': 2850, 'z': 2976, 'level': 1}), FAR)).to_be(False)
    test('the same tile on another plane is a different tile', _fn16)

    def _fn17():
        expect(spot_avoided(Record({'x': 2850, 'z': 2976, 'level': 0}), [])).to_be(False)
    test('a camp with no list refuses nothing', _fn17)


describe('avoided spots', _fn13)


def _fn18():
    SWEEP = [
        Record({'x': 2862, 'z': 2971, 'level': 0}),
        Record({'x': 2856, 'z': 2972, 'level': 0}),
        Record({'x': 2841, 'z': 2970, 'level': 0}),
        Record({'x': 2836, 'z': 2970, 'level': 0}),
        Record({'x': 2822, 'z': 2968, 'level': 0}),
    ]

    def _fn19():
        expect(sweep_stop_for([], 0, Record({'x': 2841, 'z': 2970, 'level': 0}))).to_equal(Record({'stop': None, 'index': 0}))
    test('a camp with no sweep holds its pin', _fn19)

    def _fn20():
        expect(sweep_stop_for(SWEEP, 0, Record({'x': 2841, 'z': 2970, 'level': 0}))).to_equal(Record({'stop': SWEEP[0], 'index': 0}))
    test('heads for the current stop while it is still away from it', _fn20)

    # Why: arriving with nothing in view is what says the stop is spent; measuring off anything else leaves the bot walking to the tile it stands on.
    def _fn21():
        expect(sweep_stop_for(SWEEP, 0, Record({'x': 2862, 'z': 2971, 'level': 0}))).to_equal(Record({'stop': SWEEP[1], 'index': 1}))
        expect(sweep_stop_for(SWEEP, 0, Record({'x': 2863, 'z': 2972, 'level': 0}))).to_equal(Record({'stop': SWEEP[1], 'index': 1}))
    test('advances once it is standing on the stop, and counts a neighbouring tile as arrived', _fn21)

    def _fn22():
        expect(sweep_stop_for(SWEEP, 4, Record({'x': 2822, 'z': 2968, 'level': 0}))).to_equal(Record({'stop': SWEEP[0], 'index': 0}))
    test('wraps at the west end rather than turning, so a spot behind the bot is reached on the way round', _fn22)

    def _fn23():
        expect(sweep_stop_for(SWEEP, 7, None)).to_equal(Record({'stop': SWEEP[2], 'index': 2}))
        expect(sweep_stop_for(SWEEP, 0, None)).to_equal(Record({'stop': SWEEP[0], 'index': 0}))
    test('an index past the end and a missing player tile both resolve rather than throwing', _fn23)

    def _fn24():
        expect(sweep_stop_for(SWEEP, 0, Record({'x': 2862, 'z': 2971, 'level': 1}))).to_equal(Record({'stop': SWEEP[0], 'index': 0}))
    test('a stop underfoot on another plane is not arrival', _fn24)


describe('the sweep', _fn18)
