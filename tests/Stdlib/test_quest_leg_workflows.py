"""Quest conversations and containers verify delayed scene and modal changes."""

import rs2004.quests.exec.legs as legs
import rs2004.quests.exec.prompts as prompts
from rs2004 import execution
from rs2004.geometry import Tile
from helpers import FakeModule
from test_quest_prompt_workflows import PromptWorld, Door


class LegWorld(PromptWorld):
    def __init__(self):
        PromptWorld.__init__(self)
        self.position = Tile(3000, 3000)
        self.stop = FakeModule(npc='Curator', anchor=Tile(3000, 3000), leash=2)
        self.talk_status = 'done'
        self.talk_pages = []
        self.talks = []
        self.open_on_attempt = 1
        self.goal_at = None

    def __enter__(self):
        PromptWorld.__enter__(self)
        replacements = {
            'game': FakeModule(tile=lambda: self.position),
            'traversal': prompts.traversal,
            'reach': FakeModule(npc_dialog=self.npc_dialog),
            'locs': prompts.locs,
            '_now_ms': self.step_time,
        }
        self.leg_saved = {}
        for name, value in replacements.items():
            self.leg_saved[name] = getattr(legs, name)
            setattr(legs, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.leg_saved.items():
            setattr(legs, name, value)
        PromptWorld.__exit__(self, *args)

    def npc_dialog(self, name, anchor, **kwargs):
        self.talks.append((name, anchor))
        yield execution.Ticks(1)
        self.pages = list(self.talk_pages)
        return self.talk_status

    def loc_op(self, name, op, near, expect, **kwargs):
        self.loc_requests.append((name, op, near, kwargs))
        yield execution.Ticks(1)
        if len(self.loc_requests) == self.open_on_attempt:
            self.locations = [Door(self, id=124, name='Chest')]
        return 'done' if expect() else 'unavailable'

    def goal(self):
        return self.goal_at is not None and self.now >= self.goal_at

    def talk(self):
        return self.run(legs.walk_and_talk(self.stop, ['Yes'], self.logs.append))

    def until(self, ms=5000):
        return self.run(legs.talk_until(self.stop, ['Yes'], self.goal, self.logs.append, ms=ms))

    def container(self):
        return self.run(legs.open_container('Chest', 123, 124, self.stop.anchor, self.logs.append))


def test_open_container_already_open_skips_interaction():
    with LegWorld() as world:
        world.locations = [Door(world, id=124)]
        assert world.container()
        assert world.loc_requests == [] and world.waits == []


def test_open_container_waits_for_scene_change_and_passes_exact_ids():
    with LegWorld() as world:
        assert world.container()
        request = world.loc_requests[0]
        assert request[:3] == ('Chest', 'Open', world.stop.anchor)
        assert request[3]['id'] == 123 and request[3]['within'] == 6
        assert world.waits[-1].count == 2


def test_open_container_retries_before_reporting_success():
    with LegWorld() as world:
        world.open_on_attempt = 3
        assert world.container()
        assert len(world.loc_requests) == 3
        assert not any(['never became' in line for line in world.logs])


def test_open_container_failure_is_bounded_and_logs_both_ids():
    with LegWorld() as world:
        world.open_on_attempt = None
        assert world.container() is False
        assert len(world.loc_requests) == 3
        assert world.logs[-1] == 'the shut chest (123) never became 124'


def test_open_container_ignores_open_twin_outside_search_radius():
    with LegWorld() as world:
        world.locations = [Door(world, id=124, distance=7)]
        world.open_on_attempt = None
        assert world.container() is False
        assert len(world.loc_requests) == 3


def test_walk_and_talk_nearby_starts_dialogue_without_walking():
    with LegWorld() as world:
        world.talk_pages = [('continue', ['Welcome']), ('options', ['No', 'Yes, please'])]
        assert world.talk()
        assert world.walks == []
        assert world.talks == [('Curator', world.stop.anchor)]
        assert world.clicks == ['continue', 111]


def test_walk_and_talk_walks_when_far_unplaced_or_on_another_floor():
    for position in [None, Tile(3100, 3100), Tile(3000, 3000, 1)]:
        with LegWorld() as world:
            world.position = position
            assert world.talk()
            assert len(world.walks) == 1
            assert world.walks[0][1]['radius'] == 2
            assert len(world.talks) == 1


def test_walk_and_talk_includes_leash_boundary():
    with LegWorld() as world:
        world.position = Tile(3002, 3000)
        assert world.talk()
        assert world.walks == []


def test_walk_and_talk_reports_failed_dialogue_without_answering():
    for status in ['missing', 'timeout', 'refused']:
        with LegWorld() as world:
            world.talk_status = status
            world.talk_pages = [('continue', ['Unrelated'])]
            assert world.talk() is False
            assert status in world.logs[-1] and 'Curator' in world.logs[-1]
            assert world.clicks == []


def test_walk_and_talk_preserves_unmatched_options():
    with LegWorld() as world:
        world.talk_pages = [('options', ['Leave', 'No thanks'])]
        assert world.talk() is False
        assert world.clicks == [] and world.kind() == 'options'


def test_talk_and_close_dismisses_signoff_message():
    with LegWorld() as world:
        world.talk_pages = [('continue', ['Farewell']), ('main', ['Quest complete'])]
        assert world.run(legs.talk_and_close(world.stop, [], world.logs.append))
        assert world.clicks == ['continue', 'close'] and not world.pages


def test_talk_and_close_cleans_up_even_when_opening_dialogue_failed():
    with LegWorld() as world:
        world.talk_status = 'timeout'
        world.talk_pages = [('main', ['Blocked'])]
        assert world.run(legs.talk_and_close(world.stop, [], world.logs.append)) is False
        assert world.clicks == ['close']


def test_talk_and_close_without_message_does_not_close_interfaces():
    with LegWorld() as world:
        assert world.run(legs.talk_and_close(world.stop, [], world.logs.append))
        assert world.clicks == []


def test_talk_until_existing_goal_does_not_start_conversation():
    with LegWorld() as world:
        world.goal_at = 0
        assert world.until()
        assert world.talks == [] and world.waits == []


def test_talk_until_drives_chat_after_intermediate_message_box():
    with LegWorld() as world:
        world.talk_pages = [('main', ['A message']), ('continue', ['More']), ('options', ['Yes'])]
        world.goal_at = 4000
        assert world.until(ms=10000)
        assert world.clicks == ['close', 'continue', 110]
        assert world.logs == []


def test_talk_until_waits_across_gap_for_delayed_goal():
    with LegWorld() as world:
        world.goal_at = 2000
        assert world.until()
        assert world.now == 2000 and world.clicks == []


def test_talk_until_timeout_logs_missing_result():
    with LegWorld() as world:
        assert world.until(ms=2000) is False
        assert world.now == 2500
        assert world.logs[-1] == 'Curator conversation ended without the expected result'


def test_talk_until_closes_final_message_after_goal_lands():
    with LegWorld() as world:
        world.talk_pages = [('main', ['Reward'])]
        world.goal_at = 500
        assert world.until()
        assert world.clicks == ['close'] and not world.pages


def test_talk_until_zero_budget_still_cleans_up_message():
    with LegWorld() as world:
        world.talk_pages = [('main', ['No reward'])]
        assert world.until(ms=0) is False
        assert world.clicks == ['close']
