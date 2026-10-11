# Ported from rs2b0t's test/event/webwalk/followMath.test.ts and dangerZones.test.ts (MIT, see
# thirdparty/rs2b0t), less what needs its PathFinder, which the C++ tests cover.

from rs2004.walkgeom import PathTile, choose_cross_click, crossing_eligible, expand_waypoints
from rs2004.walkgeom import find_forward_recovery_index, is_arrived, locate_on_path, min_chebyshev_to_path
from rs2004.walkgeom import resolve_danger_zones, select_click_target, select_client_walk_target
from rs2004.walkgeom import should_approach_closed_barrier, stall_phase, starved_terminal_index
from rs2004.walkgeom import tile_in_danger_zones, INFINITY


def t(x, z, level=0):
    return PathTile(x, z, level)


def switchback():
    tiles = [t(x, 0) for x in range(0, 31)]
    tiles.append(t(30, 1))
    tiles.extend([t(x, 2) for x in range(30, -1, -1)])
    return tiles


def index_of(tiles, tile):
    for i in range(len(tiles)):
        if tiles[i] is tile:
            return i
    return -1


def test_locate_on_path_advances_to_the_furthest_tile_on_the_corridor():
    tiles = switchback()
    assert locate_on_path(tiles, t(12, 0), 10, 26, 3) == 15
    assert locate_on_path(tiles, t(12, 9), 10, 26, 3) == -1
    assert locate_on_path(tiles, t(12, 0, 1), 10, 26, 3) == -1


def test_locate_on_path_does_not_jump_across_a_transport_where_the_path_folds():
    folded = [t(0, 0), t(1, 0), t(2, 0), t(3, 0), t(3, 1), t(2, 1), t(1, 1), t(0, 1)]
    assert locate_on_path(folded, t(0, 0), 0, 20, 1) == 7
    assert locate_on_path(folded, t(0, 0), 0, 20, 1, 3) == 1


def test_select_click_target_goes_by_path_index_and_its_limits():
    tiles = switchback()
    last = len(tiles) - 1
    assert select_click_target(tiles, 15, 20, last, 0, lambda tile: True) == 35
    assert select_click_target(tiles, 15, 20, last, 0, lambda tile: index_of(tiles, tile) <= 30) == 30
    assert select_click_target(tiles, 15, 20, 25, 0, lambda tile: True) == 25
    assert select_click_target(tiles, 15, 20, last, 0, lambda tile: False) == -1
    assert select_click_target(tiles, 15, 20, last, 3, lambda tile: True) == -1


def test_select_client_walk_target_takes_the_furthest_walk_the_client_accepts():
    tiles = [t(0, 0), t(1, 0), t(2, 0), t(3, 0), t(4, 0), t(5, 0)]
    tried = []

    def try_walk(i):
        tried.append(i)
        return i == 3

    assert select_client_walk_target(tiles, 0, 20, 5, 0, lambda tile: True, try_walk) == 3
    assert tried == [5, 4, 3]
    assert select_client_walk_target(tiles, 0, 20, 5, 0, lambda tile: True, lambda i: False) == -1

    skipped = []

    def record(i):
        skipped.append(i)
        return False

    select_client_walk_target(tiles, 0, 20, 5, 0, lambda tile: tile.x != 5, record)
    assert 5 not in skipped and skipped[0] == 4


def test_a_starved_selection_falls_back_to_the_terminal():
    tiles = [t(2667, 3312), t(2668, 3312)]
    me = t(2667, 3312)
    path_idx = locate_on_path(tiles, me, 0, 26, 3)
    assert path_idx == 1
    assert select_click_target(tiles, path_idx, 20, len(tiles) - 1, 0, lambda tile: True) == -1
    assert starved_terminal_index(tiles, me, lambda tile: True) == 1

    swap = [t(2669, 3310), t(2670, 3310), t(2670, 3311), t(2670, 3312), t(2669, 3312), t(2668, 3312)]
    me = t(2669, 3310)
    assert locate_on_path(swap, me, 0, 26, 3) == 5
    assert starved_terminal_index(swap, me, lambda tile: True) == 5

    assert starved_terminal_index(tiles, t(2668, 3312), lambda tile: True) == -1
    assert starved_terminal_index(tiles, t(2667, 3312), lambda tile: False) == -1
    assert starved_terminal_index([t(2667, 3312), t(2668, 3312, 1)], t(2667, 3312), lambda tile: True) == -1
    assert starved_terminal_index([], t(2667, 3312), lambda tile: True) == -1


def test_a_crossing_is_taken_only_near_its_reachable_approach():
    approach = t(10, 10)
    far = t(10, 11, 1)
    assert crossing_eligible(t(8, 8), approach, far, 4, lambda tile: True)
    assert not crossing_eligible(t(20, 21), t(0, 0), t(20, 20), 4, lambda tile: True)
    assert not crossing_eligible(t(9, 10), approach, far, 4, lambda tile: False)
    assert not crossing_eligible(t(10, 9, 1), approach, far, 4, lambda tile: True)

    probed = []

    def probe(tile):
        probed.append(tile)
        return True

    assert not crossing_eligible(t(30, 30), approach, far, 4, probe)
    assert probed == []


def test_cross_clicks_and_closed_barriers():
    assert choose_cross_click(True, True) == 'step' and choose_cross_click(True, False) == 'step'
    assert choose_cross_click(False, True) == 'landing-click'
    assert choose_cross_click(False, False) == 'landing-scene'
    approach = t(3106, 3162)
    assert should_approach_closed_barrier(t(3106, 3161), approach, True)
    assert not should_approach_closed_barrier(t(3106, 3161), approach, False)


def test_min_chebyshev_to_path_keeps_to_one_level():
    assert min_chebyshev_to_path([t(0, 0), t(5, 0), t(10, 0)], t(6, 1), 0, 10) == 1
    assert min_chebyshev_to_path([t(0, 0, 1), t(5, 0, 1)], t(0, 0, 0), 0, 10) == INFINITY


class Probe:
    def __init__(self, reach=False, walkable=False, adjacent=False, probeable=True):
        self._reach = reach
        self._walkable = walkable
        self._adjacent = adjacent
        self._probeable = probeable

    def can_reach(self, tile):
        return self._reach

    def walkable(self, tile):
        return self._walkable

    def can_reach_adjacent(self, tile):
        return self._adjacent

    def probeable(self, tile):
        return self._probeable


def test_arrival_beside_something_you_cannot_stand_on():
    booth = t(10, 10)
    assert is_arrived(t(10, 10), booth, 0, Probe())
    assert not is_arrived(t(11, 10, 1), booth, 2, Probe(reach=True))
    assert not is_arrived(t(13, 10), booth, 2, Probe(reach=True))
    assert is_arrived(t(11, 10), booth, 2, Probe(reach=True))
    assert not is_arrived(t(11, 10), booth, 2, Probe(walkable=True))
    assert is_arrived(t(11, 10), booth, 2, Probe(adjacent=True))
    assert not is_arrived(t(11, 10), booth, 2, Probe())
    assert is_arrived(t(11, 10), booth, 2, Probe(probeable=False))


def test_stall_recovery_clicks_ahead_then_escalates():
    tiles = [t(x, 0) for x in range(0, 10)]
    assert find_forward_recovery_index(tiles, t(2, 0), 2, lambda tile: tile.x <= 6) == 6
    assert find_forward_recovery_index(tiles, t(2, 0), 2, lambda tile: False) == 5
    assert find_forward_recovery_index([], t(2, 0), 0, lambda tile: True) == -1
    assert stall_phase(0, 4, False) == 'recover'
    assert stall_phase(1, 4, True) == 'combat'
    assert stall_phase(1, -1, False) == 'escalate'


def test_waypoints_expand_to_every_tile_with_hops_kept_whole():
    hop = {'kind': 'stair', 'action': 'Climb-up', 'loc_name': 'Staircase'}
    tiles = expand_waypoints([t(0, 0), t(3, 3), t(3, 5), PathTile(3, 5, 1, hop)])
    assert [(p.x, p.z, p.level) for p in tiles] == [(0, 0, 0), (1, 1, 0), (2, 2, 0), (3, 3, 0), (3, 4, 0), (3, 5, 0), (3, 5, 1)]
    assert tiles[-1].transport is hop and tiles[1].transport is None


KNOWN = [
    {'id': 'white-wolf-mountain', 'label': 'White Wolf Mountain', 'rects': [{'min_x': 2828, 'max_x': 2878, 'min_z': 3468, 'max_z': 3538, 'level': None}]},
    {
        'id': 'draynor-jail-guards', 'label': 'Draynor jail guards', 'automatic': True,
        'avoid_at_or_below_combat': 50, 'allow_when_endpoint_inside': True,
        'rects': [
            {'min_x': 3096, 'max_x': 3122, 'min_z': 3224, 'max_z': 3250, 'level': 0},
            {'min_x': 3107, 'max_x': 3133, 'min_z': 3225, 'max_z': 3251, 'level': 0},
            {'min_x': 3108, 'max_x': 3134, 'min_z': 3236, 'max_z': 3262, 'level': 0},
            {'min_x': 3114, 'max_x': 3140, 'min_z': 3235, 'max_z': 3261, 'level': 0},
        ],
    },
]


def test_tiles_in_danger_zones():
    rect = {'min_x': 10, 'max_x': 20, 'min_z': 100, 'max_z': 110, 'level': None}
    assert tile_in_danger_zones(10, 100, 0, [rect]) and tile_in_danger_zones(20, 110, 2, [rect])
    assert not tile_in_danger_zones(9, 100, 0, [rect]) and not tile_in_danger_zones(15, 111, 0, [rect])
    ground = {'min_x': 10, 'max_x': 20, 'min_z': 100, 'max_z': 110, 'level': 0}
    assert tile_in_danger_zones(15, 105, 0, [ground]) and not tile_in_danger_zones(15, 105, 1, [ground])
    assert not tile_in_danger_zones(15, 105, 0, None) and not tile_in_danger_zones(15, 105, 0, [])
    jail = KNOWN[1]['rects']
    assert tile_in_danger_zones(3120, 3238, 0, jail) and tile_in_danger_zones(3121, 3249, 0, jail)


def test_resolving_danger_zones():
    custom = {'min_x': 1, 'max_x': 2, 'min_z': 3, 'max_z': 4, 'level': 0}
    rects = resolve_danger_zones(['white-wolf-mountain', custom, 'not-a-real-zone'], known=KNOWN)
    assert custom in rects and len(rects) >= 2
    assert resolve_danger_zones(['nope'], known=KNOWN) == []
    assert resolve_danger_zones(None, known=KNOWN) == []

    outside = t(3080, 3240)
    east = t(3150, 3240)
    assert len(resolve_danger_zones(None, True, 50, outside, east, KNOWN)) == 4
    assert resolve_danger_zones(None, True, 51, outside, east, KNOWN) == []

    inside = t(3120, 3238)
    assert resolve_danger_zones(None, True, 20, outside, inside, KNOWN) == []
    assert resolve_danger_zones(None, True, 20, inside, outside, KNOWN) == []

    strict = {'min_x': 10, 'max_x': 20, 'min_z': 100, 'max_z': 110, 'level': 0}
    assert resolve_danger_zones([strict], False, 20, None, t(15, 105), KNOWN) == [strict]


def test_white_wolf_mountain_covers_the_pass_and_not_the_banks():
    zones = resolve_danger_zones(['white-wolf-mountain'], known=KNOWN)
    assert tile_in_danger_zones(2850, 3495, 0, zones)
    assert not tile_in_danger_zones(2809, 3441, 0, zones)
    assert not tile_in_danger_zones(2895, 3435, 0, zones)
