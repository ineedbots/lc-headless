"""Last-mile interactions wait for scenes and distinguish refusals from blocked routes."""

import rs2004.reach as reach
import rs2004.traversal as routes
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from coverage_world import PatchWorld


class ReachObject:
    def __init__(self, world, name='Chest', op='Search', x=101):
        self.world, self.name, self.op, self.x = world, name, op, x
        self.id, self.layer = 1, LAYER_WALL
        self.accept = True

    def actions(self):
        return [self.op]

    def tile(self):
        return Tile(self.x, 100)

    def distance(self):
        return self.tile().distance_to(self.world.position)

    def interact(self, op):
        self.world.actions.append((self.name, op))
        if self.accept:
            self.world.pending_object = self
        return self.accept


class ReachWorld(PatchWorld):
    def __init__(self):
        PatchWorld.__init__(self)
        self.position = Tile(100, 100)
        self.objects = [ReachObject(self)]
        self.people = [ReachObject(self, 'Guard', 'Talk-to')]
        self.actions, self.walks, self.messages = [], [], []
        self.pending_object = None
        self.walk_result, self.reachable = True, True
        self.expect, self.chat = False, False
        self.outcome = 'done'
        self.appear_at = None
        self.traversal = FakeModule(walk_resilient=self.walk, last_outcome='unreachable')

    def __enter__(self):
        PatchWorld.__enter__(self)
        self.patch(reach, '_core', FakeModule(is_reachable=lambda x, z: self.reachable,
            can_reach_entity=lambda x, z: self.reachable, can_step=lambda *args: False))
        self.patch(reach, 'local_tile', lambda: self.position)
        self.patch(reach, 'locs', FakeModule(query=lambda: self.query(self.objects)))
        self.patch(reach, 'npcs', FakeModule(query=lambda: self.query(self.people)))
        self.patch(reach, 'chat_dialog', FakeModule(is_open=lambda: self.chat, can_continue=lambda: self.chat))
        self.patch(reach, 'game_messages', FakeModule(mark=lambda: len(self.messages), saw_since=self.saw))
        self.patch(routes, 'traversal', self.traversal)
        return self

    def query(self, objects):
        def supply(ids, names, radius, layer):
            return [obj for obj in objects if (names is None or obj.name in names)
                    and (radius is None or obj.distance() <= radius)]
        return EntityQuery(supply, lambda obj: True)

    def saw(self, mark, needle):
        return any([needle.lower() in line.lower() for line in self.messages[mark:]])

    def walk(self, tile, **kwargs):
        self.walks.append(tile)
        yield execution.Ticks(1)
        return self.walk_result

    def advance(self):
        PatchWorld.advance(self)
        if self.appear_at is not None and self.now >= self.appear_at:
            self.objects = [ReachObject(self)]
            self.appear_at = None
        if self.pending_object is not None:
            obj = self.pending_object
            self.pending_object = None
            if obj.name == 'Door':
                obj.op = 'Close' if obj.op == 'Open' else 'Open'
                self.reachable = True
            elif self.outcome == 'done':
                self.expect, self.chat = True, True
            elif self.outcome == 'refused':
                self.messages.append('You need a key.')
            elif self.outcome == 'blocked':
                self.messages.append("I can't reach that!")

    def loc(self):
        return self.run(reach.reach.loc_op('Chest', 'Search', self.position, lambda: self.expect,
            expect_ms=500, refused='need a key', log=self.logs.append))


def test_reach_loc_waits_for_new_scene_and_confirms_interaction():
    with ReachWorld() as world:
        world.objects, world.appear_at = [], 1500
        assert world.loc() == 'done' and world.now >= 1500
        assert world.actions == [('Chest', 'Search')]


def test_reach_loc_refusal_unreachable_stand_and_missing_scene():
    for failure, expected in [('refused', 'retry'), ('walk', 'unreachable'), ('missing', 'unreachable')]:
        with ReachWorld() as world:
            world.outcome = failure
            if failure == 'missing':
                world.objects = []
            if failure in ['walk', 'missing']:
                world.walk_result = False
            assert world.loc() == expected


def test_reach_loc_unanswered_interaction_exhausts_retry_budget():
    with ReachWorld() as world:
        world.outcome = 'silent'
        assert world.loc() == 'retry'
        assert len(world.actions) == reach.REACH_DOOR_ATTEMPTS


def test_reach_npc_dialog_success_existing_chat_and_far_chat():
    with ReachWorld() as world:
        assert world.run(reach.reach.npc_dialog('Guard', world.position)) == 'done'
        before = len(world.actions)
        assert world.run(reach.reach.npc_dialog('Guard', world.position)) == 'done'
        world.people[0].x = 110
        assert world.run(reach.reach.npc_dialog('Guard', world.position)) == 'retry'
        assert len(world.actions) == before


def test_reach_npc_missing_or_unreachable_stand():
    for missing in [True, False]:
        with ReachWorld() as world:
            if missing:
                world.people = []
            world.walk_result = False
            assert world.run(reach.reach.npc_dialog('Guard', world.position)) == 'unreachable'


def test_reach_entity_already_satisfied_and_rejected_dispatch():
    with ReachWorld() as world:
        world.expect = True
        assert world.run(reach.reach.entity_op(lambda: None, 'Search', lambda: world.expect)) == 'done'
        world.expect = False
        assert world.run(reach.reach.entity_op(lambda: None, 'Search', lambda: world.expect)) == 'retry'
        assert world.waits[-1].count == 1


def test_reach_closes_swung_leaf_then_opens_blocking_door():
    with ReachWorld() as world:
        world.reachable = False
        door = ReachObject(world, 'Door', 'Close')
        world.objects = [door]
        assert world.run(reach._clear_blocking_door(Tile(102, 100), world.logs.append))
        assert world.actions == [('Door', 'Close')] and world.reachable
        door.op, door.x = 'Open', 103
        assert world.run(reach._open_blocking_door(Tile(110, 100), world.logs.append))
        assert world.actions[-1] == ('Door', 'Open') and world.walks == [door.tile()]


def test_reach_unapproachable_door_and_rejected_open_are_failure():
    with ReachWorld() as world:
        world.reachable = False
        world.objects = [ReachObject(world, 'Door', 'Open')]
        assert world.run(reach._open_blocking_door(Tile(110, 100), world.logs.append)) is False
        world.reachable = True
        world.objects[0].accept = False
        assert world.run(reach._open_blocking_door(Tile(110, 100), world.logs.append)) is False
        assert reach._can_reach(Tile(100, 100, 1)) is False
