"""Firemaking's lane finder and thieving's rules, with rs2b0t's test/scripts/GatheringBot/FiremakingLogic.test.ts
and test/scripts/ArdyFighter ThievingBotLogic and CakeStallLogic tests ported."""

from rs2004.catalogs import BURN_WEST, FIRE_SPOTS, NoLightTiles, burn_lane_want, expand_local_fire_plot, find_burn_lane
from rs2004.catalogs import firemaking_level_for_logs, local_fire_plot, logs_for_tree, nearest_fire_spot, parse_burn_mode
from rs2004.catalogs import run_west, should_burn_full_load, tile_key
from rs2004.catalogs.record import Record
from rs2004.catalogs.thieving import CAKE_ITEMS, RESET_AFTER_REFUSALS, STALL_TILE, STAND, STAND_ALT, STUN_COMBAT_TICKS
from rs2004.catalogs.thieving import THIEVER_BANKING_OPTIONS, auto_food_banking, can_steal_now, classify_steal, count_food
from rs2004.catalogs.thieving import food_matches, next_withdraw_chunk, safe_to_steal, should_reset, should_restock_food


def anywhere(*_):
    return True


def strip(x0, x1, z0, z1):
    return Record({'bank': Tile(0, 0, 0), 'x0': x0, 'x1': x1, 'z0': z0, 'z1': z1})


def test_burn_modes_logs_and_levels_are_read_by_name():
    assert parse_burn_mode('Off') == 'off'
    assert parse_burn_mode('Chop then burn') == 'chop-then-burn'
    assert logs_for_tree('Tree') == 'Logs'
    assert logs_for_tree('Oak') == 'Oak logs'
    assert logs_for_tree('Willow') == 'Willow logs'
    assert logs_for_tree('Yew') == 'Yew logs'
    assert logs_for_tree('Magic tree') == 'Magic logs'
    assert firemaking_level_for_logs('Logs') == 1
    assert firemaking_level_for_logs('Yew logs') == 60


def test_a_lane_wants_the_logs_held_from_1_to_27():
    assert burn_lane_want(0) == 1
    assert burn_lane_want(5) == 5
    assert burn_lane_want(27) == 27
    assert burn_lane_want(28) == 27
    assert burn_lane_want(99) == 27


def test_a_west_run_stops_at_a_fire_or_its_cap():
    plot = FIRE_SPOTS['Varrock East']
    start = Tile(3260, 3429, 0)
    assert run_west(start, plot, set(), anywhere, anywhere, 5) == 5
    assert run_west(start, plot, {tile_key(Tile(3258, 3429))}, anywhere, anywhere, 10) == 2


def test_the_lane_finder_prefers_the_longer_west_run():
    found = find_burn_lane(strip(10, 14, 5, 5), Tile(12, 5, 0), {tile_key(Tile(11, 5))}, 10, anywhere, anywhere, [BURN_WEST])
    assert found is not None
    assert found.run >= 3
    assert found.start.x == 14
    assert found.dir == BURN_WEST


def test_the_lane_finder_prefers_a_full_load_west_lane_over_a_nearer_partial_one():
    # z 5 is free from x 11 to 14, a run of 4 and near you; z 6 from 11 to 15, a full load of 5 and further off.
    occupied = {tile_key(Tile(10, 5)), tile_key(Tile(15, 5)), tile_key(Tile(10, 6))}
    found = find_burn_lane(strip(10, 15, 5, 6), Tile(14, 5, 0), occupied, 5, anywhere, anywhere)
    assert found.dir == BURN_WEST
    assert found.run == 5
    assert (found.start.x, found.start.z) == (15, 6)


def test_with_no_west_lane_the_lane_finder_takes_a_single_free_tile():
    occupied = {tile_key(Tile(10, 5)), tile_key(Tile(12, 5))}
    found = find_burn_lane(strip(10, 12, 5, 5), Tile(11, 5, 0), occupied, 10, anywhere, anywhere)
    assert found.start.x == 11
    assert found.run == 1


def test_fire_spots_and_plots():
    assert nearest_fire_spot(Tile(3090, 3245, 0))[0] == 'Draynor'
    assert not should_burn_full_load('off', True, 28, True)
    assert should_burn_full_load('chop-then-burn', True, 28, True)
    assert not should_burn_full_load('chop-then-burn', True, 28, False)
    plot = local_fire_plot(Tile(100, 200, 0), 5)
    assert (plot.bank.x, plot.bank.z, plot.x0, plot.x1, plot.z0, plot.z1) == (100, 200, 95, 105, 195, 205)


def test_a_local_plot_grows_until_its_cap():
    plot = local_fire_plot(Tile(50, 50, 0), 4)
    grown = expand_local_fire_plot(plot, 4, 24)
    assert grown.x1 - grown.x0 > plot.x1 - plot.x0
    for _ in range(20):
        grown = expand_local_fire_plot(plot, 4, 8)
        if grown is None:
            assert (plot.x1 - plot.x0) // 2 >= 8
            break
        plot = grown


def test_refused_tiles_are_remembered_and_kept_out_of_lanes():
    refused = NoLightTiles()
    assert not refused.has(Tile(3253, 3428))
    refused.add(Tile(3253, 3428))
    assert refused.has(Tile(3253, 3428))
    assert not refused.has(Tile(3254, 3428))
    assert refused.size == 1
    refused = NoLightTiles()
    refused.add(Tile(10, 20))
    occupied = refused.merge(['1,2'])
    assert '1,2' in occupied and '10,20' in occupied
    plot = local_fire_plot(Tile(100, 100, 0), 2)
    first = find_burn_lane(plot, Tile(100, 100, 0), set(), 1, anywhere, anywhere)
    refused = NoLightTiles()
    refused.add(first.start)
    second = find_burn_lane(plot, Tile(100, 100, 0), refused.merge([]), 1, anywhere, anywhere)
    assert tile_key(second.start) != tile_key(first.start)


def test_thiever_banking_is_opt_in_and_food_is_matched_by_part():
    assert THIEVER_BANKING_OPTIONS == ['None', 'Auto']
    assert auto_food_banking('Auto')
    assert not auto_food_banking(' none ')
    assert food_matches('2/3 cake', 'cake')
    assert not food_matches('Lobster', 'CAKE')
    assert not food_matches('Cake', '')
    pack = [Record({'name': 'Cake', 'count': 1}), Record({'name': 'Slice of cake', 'count': 2}), Record({'name': 'Coins', 'count': 50})]
    assert count_food(pack, 'cake') == 3


def test_food_is_restocked_at_the_floor_or_with_a_full_pack():
    assert should_restock_food(True, 1, 1, False)
    assert not should_restock_food(True, 2, 1, False)
    assert should_restock_food(True, 10, 1, True)
    assert not should_restock_food(False, 0, 1, True)


def test_low_health_without_food_stops_a_steal_unless_suicide_thieving():
    assert not safe_to_steal(0.49, 0.5, 0)
    assert safe_to_steal(0.49, 0.5, 1)
    assert safe_to_steal(0.5, 0.5, 0)
    assert not can_steal_now(0, 4, 5, False)
    assert can_steal_now(1, 4, 5, False)
    assert can_steal_now(0, 6, 5, False)
    assert can_steal_now(0, 4, 5, True)
    assert can_steal_now(0, 1, 5, True)


def test_withdrawals_go_by_1_5_10_then_x():
    assert next_withdraw_chunk(0) is None
    assert next_withdraw_chunk(-1) is None
    assert next_withdraw_chunk(1) == ('op', 'Withdraw-1')
    assert next_withdraw_chunk(4) == ('op', 'Withdraw-1')
    assert next_withdraw_chunk(5) == ('op', 'Withdraw-5')
    assert next_withdraw_chunk(9) == ('op', 'Withdraw-5')
    assert next_withdraw_chunk(10) == ('op', 'Withdraw-10')
    assert next_withdraw_chunk(11) == ('x', 11)
    assert next_withdraw_chunk(22) == ('x', 22)
    # The full 9-tick movement lock; retrying at 8 only turns the character.
    assert STUN_COMBAT_TICKS == 9


def test_a_steal_is_resolved_by_what_came_of_it():
    assert classify_steal(True, False, False, True) == 'success'
    # A cake is a success even when a fight happens to start.
    assert classify_steal(True, True, False, True) == 'success'
    assert classify_steal(False, True, False, True) == 'caught'
    assert classify_steal(False, False, True, True) == 'lockout'
    # The Baker refuses overhead only.
    assert classify_steal(False, False, False, True) == 'refused'
    assert classify_steal(False, False, False, False) == 'timeout'


def test_refusals_swap_stands_at_the_threshold():
    assert not should_reset(RESET_AFTER_REFUSALS - 1)
    assert should_reset(RESET_AFTER_REFUSALS)
    assert should_reset(RESET_AFTER_REFUSALS + 1)
    assert max(abs(STAND.x - STALL_TILE.x), abs(STAND.z - STALL_TILE.z)) <= 2
    assert max(abs(STAND_ALT.x - STALL_TILE.x), abs(STAND_ALT.z - STALL_TILE.z)) <= 2
    assert STAND != STAND_ALT
    assert 'cake' in CAKE_ITEMS
