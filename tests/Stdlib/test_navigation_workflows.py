"""Navigation probes and door recovery with delayed scene and movement updates."""

import json
import rs2004.navigation as navigation
import rs2004.traversal as walking
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule


class Door:
    def __init__(self, world, x=105, name='Wooden door'):
        self.world = world
        self.x = x
        self.name = name
        self.open = False
        self.reachable = True

    def tile(self):
        return Tile(self.x, 100)

    def distance(self):
        return self.world.position.distance_to(self.tile())

    def actions(self):
        return ['Close'] if self.open else [None, 'Open']

    def interact(self, op):
        assert op == 'Open'
        self.world.clicks.append(self.x)
        if self.world.accept_click:
            self.world.pending_door = self
        return self.world.accept_click


class NavigationWorld:
    def __init__(self):
        self.position = Tile(100, 100)
        self.now = 0
        self.flags = 0
        self.reachable = True
        self.adjacent = True
        self.sighted = True
        self.accept_click = True
        self.door_responds = True
        self.walk_lands = True
        self.approach_lands = True
        self.destination_stalls = False
        self.door_disappears_on_approach = False
        self.pending_door = None
        self.pending_walk = None
        self.scene = [Door(self)]
        self.walks = []
        self.direct_walks = []
        self.clicks = []
        self.waits = []
        self.logs = []
        self.probes = []
        self.requests = []
        self.route = None

    def __enter__(self):
        self.saved = (navigation._core, navigation.game, navigation.local_tile,
                      navigation.locs, navigation.direct_navigator, execution._core, walking.traversal)
        navigation._core = self
        navigation.game = FakeModule(tile=lambda: self.position, tick=lambda: self.now // 500)
        navigation.local_tile = lambda: self.position
        navigation.locs = FakeModule(query=lambda: EntityQuery(self.entities, lambda loc: True))
        navigation.direct_navigator = FakeModule(walk=self.direct_walk)
        execution._core = self
        walking.traversal = FakeModule(walk_to=self.walk)
        return self

    def __exit__(self, *args):
        (navigation._core, navigation.game, navigation.local_tile, navigation.locs,
         navigation.direct_navigator, execution._core, walking.traversal) = self.saved

    def step_time(self):
        return self.now

    def is_reachable(self, x, z):
        self.probes.append(('reach', x, z))
        return self.reachable

    def can_reach_entity(self, x, z):
        self.probes.append(('adjacent', x, z))
        for door in self.scene:
            if door.x == x:
                return door.reachable
        return self.adjacent

    def scene_flags(self, x, z):
        return self.flags

    def can_step(self, ax, az, bx, bz):
        self.probes.append(('step', ax, az, bx, bz))
        return not (ax == 105 and bx == 106 and not self.scene[0].open)

    def line_of_sight(self, ax, az, bx, bz, size):
        self.probes.append(('sight', ax, az, bx, bz, size))
        return self.sighted

    def find_world_path(self, request):
        self.requests.append(json.loads(request))
        return json.dumps(self.route) if self.route is not None else None

    def entities(self, ids, names, radius, layer):
        return list(self.scene)

    def walk(self, dest, **kwargs):
        self.walks.append((dest, kwargs))
        kwargs['log']('walking')
        yield execution.Ticks(1)
        if dest.x == 110:
            if self.walk_lands and all([door.open for door in self.scene]):
                self.position = dest
            elif self.approach_lands and not self.destination_stalls:
                self.position = Tile(104, 100)
        elif self.approach_lands:
            self.position = Tile(dest.x - 1, dest.z)
            if self.door_disappears_on_approach:
                self.scene = []
        return self.position.equals(dest)

    def direct_walk(self, tile):
        self.direct_walks.append(tile)
        if self.walk_lands:
            self.pending_walk = tile
        return self.walk_lands

    def run(self, task):
        for guard in range(160):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            assert isinstance(wait, execution.Update) or isinstance(wait, execution.Ticks)
            self.waits.append(wait)
            self.now += 500
            if self.pending_door is not None and self.door_responds:
                self.pending_door.open = True
                self.pending_door = None
            if self.pending_walk is not None:
                self.position = self.pending_walk
                self.pending_walk = None
        assert False, 'navigation exceeded its simulated update budget'

    def opening(self, **options):
        return self.run(navigation.walk_opening(Tile(110, 100), 0, [' DOOR ', None, ''],
                                                log=self.logs.append, **options))


def test_reachability_rejects_unplaced_player_and_different_floor_without_core_calls():
    with NavigationWorld() as world:
        reach = navigation.reachability
        world.position = None
        assert not reach.can_reach(Tile(101, 100))
        assert not reach.walkable(Tile(101, 100))
        assert not reach.probeable(Tile(101, 100))
        world.position = Tile(100, 100, 1)
        assert not reach.can_reach(Tile(101, 100))
        assert not reach.walkable(Tile(101, 100))
        assert not reach.probeable(Tile(101, 100))
        assert world.probes == []


def test_exact_and_adjacent_reachability_use_distinct_core_probes():
    with NavigationWorld() as world:
        world.reachable = False
        assert not navigation.reachability.can_reach((101, 100, 0))
        assert navigation.reachability.can_reach((101, 100, 0), adjacent_ok=True)
        assert world.probes == [('reach', 101, 100), ('adjacent', 101, 100)]


def test_can_step_rejects_nonadjacent_tiles_and_other_floors():
    with NavigationWorld() as world:
        reach = navigation.reachability
        assert not reach.can_step((100, 100), (102, 100))
        assert not reach.can_step((100, 100), (100, 100))
        assert not reach.can_step((100, 100), (101, 100, 1))
        assert world.probes == []
        assert reach.can_step((100, 100), (101, 101))
        assert world.probes == [('step', 100, 100, 101, 101)]


def test_sight_probe_preserves_target_size_and_rejects_other_floor():
    with NavigationWorld() as world:
        reach = navigation.reachability
        assert not reach.line_of_sight((100, 100), (103, 100, 1), 3)
        assert world.probes == []
        world.sighted = False
        assert not reach.line_of_sight((100, 100), (103, 100), 3)
        assert world.probes == [('sight', 100, 100, 103, 100, 3)]


def test_walkability_distinguishes_unloaded_blocked_and_clear_tiles():
    with NavigationWorld() as world:
        reach = navigation.reachability
        for flags in [None, navigation.SQ_BLOCKED, 0]:
            world.flags = flags
            assert reach.walkable((101, 100)) == (flags == 0)
            assert reach.probeable((101, 100)) == (flags is not None)
            assert reach.flags((101, 100)) == flags


def test_arrival_probe_preserves_exact_and_adjacent_reachability():
    with NavigationWorld() as world:
        probe = navigation.reachability.arrival_probe()
        world.reachable = False
        assert not probe.can_reach(Tile(101, 100))
        assert probe.can_reach_adjacent(Tile(101, 100))
        assert probe.walkable(Tile(101, 100))
        assert probe.probeable(Tile(101, 100))


def test_route_request_preserves_policy_state_avoidance_and_search_limit():
    with NavigationWorld() as world:
        world.route = {'ok': True, 'cost': 8, 'expanded': 12,
                       'waypoints': [{'x': 100, 'z': 100, 'level': 0}, None,
                                     {'x': 110, 'z': 100, 'level': 0}]}
        state = {'members': True, 'items': {'Coins': 100}}
        route = navigation.navigator.find_path((100, 100), (110, 100), avoid_doors=[Tile(105, 100)],
                                                max_expansions=500, policy={'max_cost': 100},
                                                use_teleport_catalog=True, avoid_zones=['wild'], state=state)
        request = world.requests[0]
        assert request['from'] == [100, 100, 0] and request['to'] == [110, 100, 0]
        assert request['state'] == state and request['policy'] == {'max_cost': 100}
        assert request['avoid_doors'] == [[105, 100]] and request['avoid_zones'] == ['wild']
        assert request['max_expansions'] == 500 and request['use_teleport_catalog'] is True
        assert route.ok and route.cost == 8 and route.expanded == 12
        assert route.waypoints == [Tile(100, 100), Tile(110, 100)]
        assert '2 waypoints' in repr(route)


def test_missing_navigation_data_returns_explicit_failed_route():
    with NavigationWorld() as world:
        route = navigation.navigator.find_path((100, 100), (110, 100), state={})
        assert not route.ok and 'no walker data' in route.reason
        assert route.waypoints == [] and route.expanded == 0
        request = world.requests[0]
        assert request['avoid_doors'] == [] and request['avoid_zones'] == []
        assert request['policy'] == {} and request['use_teleport_catalog'] is False
        assert 'max_expansions' not in request


def test_route_search_failure_preserves_reason_without_inventing_waypoints():
    with NavigationWorld() as world:
        world.route = {'ok': False, 'reason': 'search limit reached', 'expanded': 500}
        route = navigation.navigator.find_path((100, 100), (110, 100), state={})
        assert not route.ok and route.reason == 'search limit reached'
        assert route.expanded == 500 and route.waypoints == []


def test_walk_opening_opens_blocking_door_then_reaches_destination():
    with NavigationWorld() as world:
        assert world.opening()
        assert world.position == Tile(110, 100)
        assert world.clicks == [105]
        assert len(world.walks) == 2


def test_walk_opening_already_arrived_does_not_walk_or_open_door():
    with NavigationWorld() as world:
        world.position = Tile(110, 100)
        assert world.opening()
        assert world.walks == [] and world.clicks == []


def test_walk_opening_stalled_without_obstacles_returns_failure():
    with NavigationWorld() as world:
        world.scene = []
        world.walk_lands = False
        assert world.opening() is False
        assert world.clicks == [] and len(world.walks) == 1


def test_walk_opening_ignores_unreachable_and_unrelated_scene_objects():
    for unreachable in [True, False]:
        with NavigationWorld() as world:
            world.scene[0].reachable = not unreachable
            if not unreachable:
                world.scene[0].name = 'Bank booth'
            assert world.opening() is False
            assert world.clicks == []


def test_walk_opening_bounds_retries_when_door_rejects_open_click():
    with NavigationWorld() as world:
        world.accept_click = False
        assert world.opening() is False
        assert len(world.clicks) == navigation.SEGMENTS
        assert not world.scene[0].open


def test_walk_opening_does_not_claim_arrival_when_door_never_changes():
    with NavigationWorld() as world:
        world.door_responds = False
        assert world.opening() is False
        assert len(world.clicks) == navigation.SEGMENTS
        assert world.now >= navigation.SEGMENTS * navigation.OPEN_WAIT_MS


def test_walk_opening_approaches_door_before_sending_open_click():
    with NavigationWorld() as world:
        world.destination_stalls = True
        # The failed destination walk leaves us five tiles from the door.
        assert world.opening()
        assert world.walks[1][0] == Tile(105, 100)
        assert world.walks[1][1]['radius'] == 1
        assert 'walking to Wooden door' in world.logs[1]


def test_door_disappearing_during_approach_is_not_clicked():
    with NavigationWorld() as world:
        world.destination_stalls = True
        world.door_disappears_on_approach = True
        assert world.opening()
        assert world.scene == []
        assert world.clicks == []


def test_step_through_waits_for_open_face_then_walks_across():
    with NavigationWorld() as world:
        assert world.opening(door_step_ticks=2)
        assert world.direct_walks == [Tile(106, 100)]
        assert any([isinstance(wait, execution.Ticks) and wait.count == 2 for wait in world.waits])
        assert any(['stepped through to 106,100 (crossed)' in line for line in world.logs])


def test_step_through_does_not_walk_when_no_collision_face_opens():
    with NavigationWorld() as world:
        world.position = Tile(104, 100)
        before = navigation.face_steps(Tile(105, 100))
        world.run(navigation._step_through(Tile(105, 100), before, 0, world.logs.append))
        assert world.direct_walks == []


def test_step_through_reports_when_movement_does_not_land():
    with NavigationWorld() as world:
        world.position = Tile(104, 100)
        before = navigation.face_steps(Tile(105, 100))
        world.scene[0].open = True
        world.walk_lands = False
        world.run(navigation._step_through(Tile(105, 100), before, 0, world.logs.append))
        assert world.direct_walks == [Tile(106, 100)]
        assert '(not crossed)' in world.logs[-1]
