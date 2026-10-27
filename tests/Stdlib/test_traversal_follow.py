"""Route execution against a deterministic client boundary, without replacing the follower itself."""

import json
import rs2004.traversal as walker
from rs2004 import execution


class WalkWorld:
    def __init__(self):
        self.here = Tile(3200, 3200)
        self.now = 0
        self.ticks = 0
        self.requests = []
        self.clicks = []
        self.waits = []
        self.logs = []
        self.messages = []
        self.rejected = []
        self.blocked = []
        self.move = True
        self.pending = None
        self.on_wait = None
        self.terminal = None
        self.retaliate = True
        self.fighting = False
        self.retaliation_changes = []

    def __enter__(self):
        self.saved = []
        for owner, name, value in [
            (walker, '_core', self), (execution, '_core', self),
            (walker, 'game', self), (walker, 'game_messages', self),
            (walker, 'local_tile', lambda: self.here),
            (walker, 'world_state', lambda: {'items': {}, 'worn': {}, 'quests': {}}),
            (walker, 'bank_locations', lambda: []),
            (walker, 'gate_item_candidates', lambda: {}),
        ]:
            self.saved.append((owner, name, getattr(owner, name)))
            setattr(owner, name, value)
        return self

    def __exit__(self, *args):
        self.saved.reverse()
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def tick(self):
        return self.ticks

    def step_time(self):
        return self.now

    def get_level(self):
        return self.here.level

    def combat_level(self):
        return 50

    def in_combat(self):
        return self.fighting

    def auto_retaliate_on(self):
        return self.retaliate

    def set_auto_retaliate(self, enabled):
        self.retaliate = enabled
        self.retaliation_changes.append(enabled)
        return True

    def in_scene(self, x, z):
        return True

    def is_reachable(self, x, z):
        return (x, z) not in self.blocked

    def walk_tile(self, x, z, level):
        return [1 if self.is_reachable(x, z) else 0, 0]

    def can_reach_entity(self, x, z):
        return True

    def mark(self):
        return len(self.messages)

    def saw_since(self, mark, text):
        return any([text.lower() in message.lower() for message in self.messages[mark:]])

    def walk_to(self, x, z, run):
        self.clicks.append((x, z, run))
        if (x, z) in self.rejected or not self.is_reachable(x, z):
            return False
        self.pending = Tile(x, z, self.here.level)
        return True

    def find_world_path(self, text):
        request = json.loads(text)
        self.requests.append(request)
        start = request['from']
        end = self.terminal or request['to']
        points = [{'x': start[0], 'z': start[1], 'level': start[2]}]
        if start[0] != end[0] and start[1] != end[1]:
            points.append({'x': start[0], 'z': end[1], 'level': start[2]})
        points.append({'x': end[0], 'z': end[1], 'level': end[2]})
        return json.dumps({'ok': True, 'cost': 10, 'expanded': 4, 'waypoints': points})

    def run(self, task):
        for guard in range(100):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            self.waits.append(wait)
            assert isinstance(wait, execution.Ticks), 'route execution should wait for server ticks'
            self.ticks += wait.count
            self.now += 600 * wait.count
            if self.move and self.pending is not None:
                self.here = self.pending
                self.pending = None
            if self.on_wait is not None:
                self.on_wait()
        assert False, 'the walker did not finish within the simulated tick budget'


def test_walk_to_follows_a_planned_route_with_custom_follow_settings():
    with WalkWorld() as world:
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=10000,
                                      use_teleport_catalog=False,
                                      path_follow={'stall_ticks': 3, 'deviation_chebyshev': 5}))
        assert walk.last_outcome == 'arrived'
        assert world.clicks == [(3210, 3200, False)]
        assert world.requests[0]['to'] == [3210, 3200, 0]
        assert world.requests[0]['policy']['use_teleports'] is False
        assert len(world.waits) == 1


def test_a_rejected_walk_click_falls_back_to_a_nearer_reachable_tile():
    with WalkWorld() as world:
        world.rejected = [(3210, 3200)]
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=1, timeout_ms=10000))
        assert world.clicks == [(3210, 3200, False), (3209, 3200, False)]
        assert walk.last_outcome == 'arrived'


def test_a_server_cant_reach_message_replans_instead_of_repeating_the_old_click():
    with WalkWorld() as world:
        world.move = False

        def rejected():
            world.messages.append("I can't reach that!")
            world.move = True
            world.on_wait = None

        world.on_wait = rejected
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=10000, log=world.logs.append))
        assert len(world.requests) == 2
        assert len(world.clicks) == 2
        assert any(["can't reach" in message for message in world.logs])


def test_a_repath_request_interrupts_the_current_route_and_is_consumed_once():
    with WalkWorld() as world:
        world.move = False
        walk = walker._Traversal()

        def interrupt():
            walk.request_repath('the scene changed')
            world.move = True
            world.on_wait = None

        world.on_wait = interrupt
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=10000, log=world.logs.append))
        assert len(world.requests) == 2
        assert world.logs.count('repath requested') == 1


def test_being_moved_off_the_corridor_requests_a_route_from_the_new_position():
    with WalkWorld() as world:
        def displaced():
            world.here = Tile(3200, 3250)
            world.on_wait = None

        world.on_wait = displaced
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=20000, log=world.logs.append))
        assert len(world.requests) == 2
        assert world.requests[1]['from'] == [3200, 3250, 0]
        assert any(['off the route' in message for message in world.logs])


def test_a_walk_that_never_moves_stops_at_its_deadline():
    with WalkWorld() as world:
        world.move = False
        walk = walker._Traversal()
        assert not world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=4000,
                                          path_follow={'stall_ticks': 1000}))
        assert walk.last_outcome == 'failed'
        assert len(world.requests) == 1
        assert world.now >= 4000
        assert len(world.clicks) == 1


def test_a_stalled_walk_retries_a_forward_tile_before_replanning():
    with WalkWorld() as world:
        world.move = False

        def let_recovery_move():
            world.move = True
            world.on_wait = None

        world.on_wait = let_recovery_move
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=10000,
                                      path_follow={'stall_ticks': 2}, log=world.logs.append))
        assert len(world.requests) == 1
        assert len(world.clicks) == 2
        assert any(['stalled' in message for message in world.logs])


def test_a_walk_restores_auto_retaliation_after_escaping_a_combat_stall():
    with WalkWorld() as world:
        world.move = False
        world.fighting = True

        def let_escape_move():
            if not world.retaliate:
                world.move = True

        world.on_wait = let_escape_move
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=10000,
                                      path_follow={'stall_ticks': 2}))
        assert world.retaliation_changes == [False, True]
        assert world.retaliate is True
        assert len(world.requests) == 1


def test_a_combat_walk_preserves_an_existing_auto_retaliation_preference():
    with WalkWorld() as world:
        world.move = False
        world.fighting = True
        world.retaliate = False

        def let_escape_move():
            if world.ticks >= 6:
                world.move = True

        world.on_wait = let_escape_move
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=10000,
                                      path_follow={'stall_ticks': 2}))
        assert world.retaliation_changes == []
        assert world.retaliate is False


def test_an_impassable_adjacent_destination_finishes_as_blocked_after_settling():
    with WalkWorld() as world:
        world.blocked = [(3201, 3200)]
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3201, 3200), radius=0, timeout_ms=10000))
        assert walk.last_outcome == 'blocked'
        assert world.clicks == []
        assert len(world.waits) == walker.CANDIDATE_SETTLE_TRIES


def test_a_route_ending_short_of_the_destination_reports_closest():
    with WalkWorld() as world:
        world.terminal = [3200, 3200, 0]
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3210, 3200), radius=0, timeout_ms=10000))
        assert walk.last_outcome == 'closest'
        assert world.clicks == [] and world.waits == []
