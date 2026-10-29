"""Milling waits for server messages before operating controls or changing floors."""

import rs2004.quests.defs.cooksassistant as cook
from rs2004 import execution
from rs2004.entities import EntityQuery
from helpers import FakeModule
from test_dialogue_workflows import DialogueWorld


class MillObject:
    def __init__(self, world, name, op):
        self.world = world
        self.name = name
        self.op = op
        self.dist = 1

    def distance(self):
        return self.dist

    def actions(self):
        return [self.op]

    def interact(self, op):
        assert op == self.op
        self.world.clicks.append((self.name, op, self.world.now))
        if self.name == 'Hopper controls':
            if self.world.accept_controls:
                self.world.queue('message', self.world.grind_message)
            return self.world.accept_controls
        if self.world.accept_bin:
            self.world.queue('flour', None)
        return self.world.accept_bin


class Grain:
    def __init__(self, world):
        self.world = world

    def use_on(self, target):
        assert target.name == 'Hopper'
        self.world.uses.append(target.name)
        if self.world.accept_grain:
            self.world.queue('grain', None, 500)
            self.world.queue('message', self.world.fill_message, self.world.fill_delay)
        return self.world.accept_grain


class MillWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.grain = Grain(self)
        self.has_flour = False
        self.scene = [MillObject(self, 'Hopper', 'Fill'), MillObject(self, 'Hopper controls', 'Operate')]
        self.bin = MillObject(self, 'Flour bin', 'Empty')
        self.messages = []
        self.scheduled = []
        self.uses = []
        self.walks = []
        self.walk_results = []
        self.accept_grain = True
        self.accept_controls = True
        self.accept_bin = True
        self.fill_message = 'You put the grain in the hopper.'
        self.grind_message = 'The grain slides down the chute.'
        self.fill_delay = 1500
        self.floor_loads = True
        self.floor_delay = 500
        self.flour_arrives = True

    def __enter__(self):
        DialogueWorld.__enter__(self)
        replacements = {
            'inventory': self,
            'locs': FakeModule(query=lambda: EntityQuery(self.locations, lambda obj: True)),
            'game_messages': FakeModule(mark=lambda: len(self.messages), saw_since=self.saw_since),
            'traversal': FakeModule(walk_resilient=self.walk),
        }
        self.mill_saved = {}
        for name, value in replacements.items():
            self.mill_saved[name] = getattr(cook, name)
            setattr(cook, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.mill_saved.items():
            setattr(cook, name, value)
        DialogueWorld.__exit__(self, *args)

    def first(self, name):
        assert name == 'Grain'
        return self.grain

    def contains(self, name):
        assert name == 'Pot of flour'
        return self.has_flour

    def locations(self, ids, names, radius, layer):
        return [obj for obj in self.scene if (names is None or obj.name in names)
                and (radius is None or obj.distance() <= radius)]

    def saw_since(self, mark, predicate):
        return any([predicate(text) for text in self.messages[mark:]])

    def queue(self, kind, value, delay=500):
        self.scheduled.append((self.now + delay, kind, value))

    def walk(self, tile, **kwargs):
        self.walks.append((tile, kwargs, self.now))
        result = self.walk_results.pop(0) if self.walk_results else True
        if result and tile == cook.MILL_BASE:
            self.scene = []
            if self.floor_loads:
                self.queue('scene', [self.bin], self.floor_delay)
        yield execution.Ticks(1)
        return result

    def advance(self):
        DialogueWorld.advance(self)
        ready = [entry for entry in self.scheduled if entry[0] <= self.now]
        self.scheduled = [entry for entry in self.scheduled if entry[0] > self.now]
        for at, kind, value in ready:
            if kind == 'message' and value is not None:
                self.messages.append(value)
            elif kind == 'grain':
                self.grain = None
            elif kind == 'flour' and self.flour_arrives:
                self.has_flour = True
            elif kind == 'scene':
                self.scene = value

    def fill(self):
        return self.run(cook._fill_hopper(self.logs.append))

    def grind(self):
        return self.run(cook._grind_hopper(self.logs.append))

    def mill(self):
        return self.run(cook.mill_flour(self.logs.append))


def test_cook_fill_waits_for_message_after_grain_leaves_inventory():
    with MillWorld() as world:
        task = cook._fill_hopper(world.logs.append)
        next(task)
        world.now = 500
        world.advance()
        assert world.grain is None
        assert isinstance(next(task), execution.Update)
        assert world.run(task)
        assert world.now == 1500 and world.uses == ['Hopper']


def test_cook_fill_accepts_already_loaded_hopper_message():
    with MillWorld() as world:
        world.fill_message = 'There is already grain in the hopper.'
        assert world.fill() and world.now == 1500


def test_cook_fill_without_grain_is_already_done():
    with MillWorld() as world:
        world.grain = None
        assert world.fill() and world.uses == [] and world.waits == []


def test_cook_fill_missing_hopper_reports_failure():
    with MillWorld() as world:
        world.scene = []
        assert world.fill() is False
        assert world.uses == [] and 'no Hopper' in world.logs[-1]


def test_cook_fill_ignores_hopper_outside_reach():
    with MillWorld() as world:
        world.scene[0].dist = 9
        assert world.fill() is False and world.uses == []


def test_cook_fill_rejected_use_does_not_wait():
    with MillWorld() as world:
        world.accept_grain = False
        assert world.fill() is False and world.waits == []


def test_cook_fill_silent_server_times_out_even_after_grain_removed():
    with MillWorld() as world:
        world.fill_message = None
        assert world.fill() is False
        assert world.grain is None and world.now == 20000


def test_cook_fill_ignores_old_confirmation_message():
    with MillWorld() as world:
        world.messages = [world.fill_message]
        world.fill_message = None
        assert world.fill() is False and world.now == 20000


def test_cook_grind_waits_for_ground_confirmation():
    with MillWorld() as world:
        assert world.grind() == 'ground'
        assert world.now == 500 and world.clicks[0][:2] == ('Hopper controls', 'Operate')


def test_cook_grind_recognizes_full_bin():
    with MillWorld() as world:
        world.grind_message = 'The flour bin downstairs is full, I should empty it.'
        assert world.grind() == 'bin_full'
        assert 'already full' in world.logs[-1]


def test_cook_grind_empty_hopper_is_failure():
    with MillWorld() as world:
        world.grind_message = 'You operate the empty hopper.'
        assert world.grind() == 'failed' and 'still empty' in world.logs[-1]


def test_cook_grind_missing_controls_is_failure():
    with MillWorld() as world:
        world.scene = [world.scene[0]]
        assert world.grind() == 'failed' and world.clicks == []


def test_cook_grind_controls_without_operate_action_are_ignored():
    with MillWorld() as world:
        world.scene[1].op = 'Inspect'
        assert world.grind() == 'failed' and world.clicks == []


def test_cook_grind_refused_operation_does_not_wait():
    with MillWorld() as world:
        world.accept_controls = False
        assert world.grind() == 'failed' and world.waits == []


def test_cook_grind_unrelated_message_does_not_confirm_operation():
    with MillWorld() as world:
        world.grind_message = 'Nothing interesting happens.'
        assert world.grind() == 'failed' and world.now == 20000
        assert 'never answered' in world.logs[-1]


def test_cook_mill_waits_for_fill_then_grind_then_flour():
    with MillWorld() as world:
        assert world.mill()
        assert world.has_flour and world.grain is None
        assert [entry[0] for entry in world.walks] == [cook.MILL_TOP, cook.MILL_BASE]
        assert world.clicks[0][2] >= world.fill_delay
        assert world.walks[1][2] > world.clicks[0][2]
        assert [entry[:2] for entry in world.clicks] == [('Hopper controls', 'Operate'), ('Flour bin', 'Empty')]


def test_cook_mill_full_bin_still_goes_down_to_collect_flour():
    with MillWorld() as world:
        world.grind_message = 'The flour bin downstairs is full, I should empty it.'
        assert world.mill() and world.has_flour
        assert len(world.walks) == 2


def test_cook_mill_failed_top_floor_walk_stops_before_interactions():
    with MillWorld() as world:
        world.walk_results = [False]
        assert world.mill() is False
        assert world.uses == [] and world.clicks == []


def test_cook_mill_waits_for_top_floor_scene_to_load():
    with MillWorld() as world:
        world.queue('scene', world.scene, 2000)
        world.scene = []
        assert world.mill()
        assert world.clicks[0][2] >= 3500


def test_cook_mill_missing_top_floor_scene_times_out():
    with MillWorld() as world:
        world.scene = []
        assert world.mill() is False and world.now == 6500
        assert 'top floor has not loaded' in world.logs[-1]


def test_cook_mill_fill_failure_does_not_pull_controls():
    with MillWorld() as world:
        world.accept_grain = False
        assert world.mill() is False and world.clicks == []
        assert len(world.walks) == 1


def test_cook_mill_grinding_failure_does_not_descend():
    with MillWorld() as world:
        world.grind_message = 'You operate the empty hopper.'
        assert world.mill() is False and len(world.walks) == 1


def test_cook_mill_failed_descent_does_not_empty_bin():
    with MillWorld() as world:
        world.walk_results = [True, False]
        assert world.mill() is False and len(world.clicks) == 1


def test_cook_mill_waits_for_ground_floor_scene_to_load():
    with MillWorld() as world:
        world.floor_delay = 2500
        assert world.mill()
        assert world.clicks[-1][2] >= world.walks[-1][2] + 2500


def test_cook_mill_missing_ground_floor_scene_times_out():
    with MillWorld() as world:
        world.floor_loads = False
        assert world.mill() is False
        assert 'ground floor has not loaded' in world.logs[-1]
        assert len(world.clicks) == 1


def test_cook_mill_bin_without_empty_action_is_failure():
    with MillWorld() as world:
        world.bin.op = 'Inspect'
        assert world.mill() is False and len(world.clicks) == 1


def test_cook_mill_rejected_bin_click_stops_without_collection_wait():
    with MillWorld() as world:
        world.accept_bin = False
        assert world.mill() is False and not world.has_flour
        assert world.now == world.clicks[-1][2]


def test_cook_mill_waits_for_flour_and_reports_collection_timeout():
    with MillWorld() as world:
        world.flour_arrives = False
        assert world.mill() is False and not world.has_flour
        assert world.now == world.clicks[-1][2] + 15000
