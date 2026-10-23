"""rs2b0t's test/scripts/GatheringBot/FiremakingLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import BURN_WEST, FIRE_SPOTS, NoLightTiles, Record, burn_lane_want, expand_local_fire_plot, find_burn_lane, firemaking_level_for_logs, local_fire_plot, logs_for_tree, nearest_fire_spot, parse_burn_mode, run_west, should_burn_full_load, tile_key


def _fn1():
    def _fn2():
        expect(parse_burn_mode('Off')).to_be('off')
        expect(parse_burn_mode('Chop then burn')).to_be('chop-then-burn')
    test('parseBurnMode', _fn2)

    def _fn3():
        expect(logs_for_tree('Tree')).to_be('Logs')
        expect(logs_for_tree('Oak')).to_be('Oak logs')
        expect(logs_for_tree('Willow')).to_be('Willow logs')
        expect(logs_for_tree('Yew')).to_be('Yew logs')
        expect(logs_for_tree('Magic tree')).to_be('Magic logs')
    test('logsForTree maps scenery names', _fn3)

    def _fn4():
        expect(firemaking_level_for_logs('Logs')).to_be(1)
        expect(firemaking_level_for_logs('Yew logs')).to_be(60)
    test('firemakingLevelForLogs', _fn4)

    def _fn5():
        expect(burn_lane_want(0)).to_be(1)
        expect(burn_lane_want(5)).to_be(5)
        expect(burn_lane_want(27)).to_be(27)
        expect(burn_lane_want(28)).to_be(27)
        expect(burn_lane_want(99)).to_be(27)
    test('burnLaneWant caps at 27', _fn5)

    def _fn6():
        plot = FIRE_SPOTS.get('Varrock East')
        from_ = Record({'x': 3260, 'z': 3429, 'level': 0})
        expect(run_west(from_, plot, set(), lambda *_args: True, lambda *_args: True, 5)).to_be(5)
        blocked = set([tile_key(Record({'x': 3258, 'z': 3429}))])
        expect(run_west(from_, plot, blocked, lambda *_args: True, lambda *_args: True, 10)).to_be(2)
    test('runWest stops on occupied / cap', _fn6)

    def _fn7():
        # Single-row strip: west-only so start.x is deterministic.
        plot = Record({'bank': Tile(0, 0, 0), 'x0': 10, 'x1': 14, 'z0': 5, 'z1': 5})
        here = Record({'x': 12, 'z': 5, 'level': 0})
        occ = set([tile_key(Record({'x': 11, 'z': 5}))])
        found = find_burn_lane(plot, here, occ, 10, lambda *_args: True, lambda *_args: True, [BURN_WEST])
        expect(found).not_.to_be_null()
        expect(found.run).to_be_greater_than_or_equal(3)
        expect(found.start.x).to_be(14)
        expect(found.dir).to_equal(BURN_WEST)
    test('findBurnLane prefers longer west runs', _fn7)

    def _fn8():
        # z=5: free x=11..14 → max west run 4 (partial for want=5), closer to the player.
        # z=6: free x=11..15 → max west run 5 (full load), farther.
        plot = Record({'bank': Tile(0, 0, 0), 'x0': 10, 'x1': 15, 'z0': 5, 'z1': 6})
        here = Record({'x': 14, 'z': 5, 'level': 0})
        occ = set([
        tile_key(Record({'x': 10, 'z': 5})),
        tile_key(Record({'x': 15, 'z': 5})),
        tile_key(Record({'x': 10, 'z': 6})),
    ])
        found = find_burn_lane(plot, here, occ, 5, lambda *_args: True, lambda *_args: True)
        expect(found).not_.to_be_null()
        expect(found.dir).to_equal(BURN_WEST)
        expect(found.run).to_be(5)
        expect(found.start.z).to_be(6)
        expect(found.start.x).to_be(15)
    test('findBurnLane prefers a full-load west lane over a longer partial elsewhere', _fn8)

    def _fn9():
        # Only one free tile; west neighbor is occupied so multi-light west fails.
        plot = Record({'bank': Tile(0, 0, 0), 'x0': 10, 'x1': 12, 'z0': 5, 'z1': 5})
        here = Record({'x': 11, 'z': 5, 'level': 0})
        occ = set([tile_key(Record({'x': 10, 'z': 5})), tile_key(Record({'x': 12, 'z': 5}))])
        found = find_burn_lane(plot, here, occ, 10, lambda *_args: True, lambda *_args: True)
        expect(found).not_.to_be_null()
        expect(found.start.x).to_be(11)
        expect(found.run).to_be(1)
    test('findBurnLane falls back to a single free tile when no west lane exists', _fn9)

    def _fn10():
        # Here the spot comes back as (name, plot).
        expect(nearest_fire_spot(Tile(3090, 3245, 0))[0]).to_be('Draynor')
    test('nearestFireSpot picks closest bank', _fn10)

    def _fn11():
        expect(should_burn_full_load('off', True, 28, True)).to_be(False)
        expect(should_burn_full_load('chop-then-burn', True, 28, True)).to_be(True)
        expect(should_burn_full_load('chop-then-burn', True, 28, False)).to_be(False)
    test('shouldBurnFullLoad gates', _fn11)

    def _fn12():
        plot = local_fire_plot(Record({'x': 100, 'z': 200, 'level': 0}), 5)
        expect(plot.bank.x).to_be(100)
        expect(plot.bank.z).to_be(200)
        expect(plot.x0).to_be(95)
        expect(plot.x1).to_be(105)
        expect(plot.z0).to_be(195)
        expect(plot.z1).to_be(205)
    test('localFirePlot boxes origin', _fn12)

    def _fn13():
        plot = local_fire_plot(Record({'x': 50, 'z': 50, 'level': 0}), 4)
        next_ = expand_local_fire_plot(plot, 4, 24)
        expect(next_).not_.to_be_null()
        expect(next_.x1 - next_.x0).to_be_greater_than(plot.x1 - plot.x0)
        i = 0
        while i < 20 and plot:
            n = expand_local_fire_plot(plot, 4, 8)
            if not n:
                expect(((plot.x1 - plot.x0) // 2)).to_be_greater_than_or_equal(8)
                break
            plot = n
            i += 1
    test('expandLocalFirePlot grows until max', _fn13)


describe('FiremakingLogic', _fn1)


def _fn14():
    def _fn15():
        refused = NoLightTiles()
        expect(refused.has(Record({'x': 3253, 'z': 3428}))).to_be(False)
        refused.add(Record({'x': 3253, 'z': 3428}))
        expect(refused.has(Record({'x': 3253, 'z': 3428}))).to_be(True)
        expect(refused.has(Record({'x': 3254, 'z': 3428}))).to_be(False)
        expect(refused.size).to_be(1)
    test('remembers a refused tile by coordinate', _fn15)

    def _fn16():
        refused = NoLightTiles()
        refused.add(Record({'x': 10, 'z': 20}))
        occupied = refused.merge(['1,2'])
        expect(('1,2' in occupied)).to_be(True)
        expect(('10,20' in occupied)).to_be(True)
    test('folds refused tiles into the occupied set', _fn16)

    def _fn17():
        plot = local_fire_plot(Record({'x': 100, 'z': 100, 'level': 0}), 2)

        def walkable(*_args):
            return True

        def can_step(*_args):
            return True
        first = find_burn_lane(plot, Record({'x': 100, 'z': 100, 'level': 0}), set(), 1, walkable, can_step)
        refused = NoLightTiles()
        refused.add(first.start)
        second = find_burn_lane(plot, Record({'x': 100, 'z': 100, 'level': 0}), refused.merge([]), 1, walkable, can_step)
        expect(tile_key(second.start)).not_.to_be(tile_key(first.start))
    test('keeps findBurnLane off a tile the game already refused', _fn17)


describe('NoLightTiles', _fn14)
