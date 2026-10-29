"""Quest prompts drive real dialogue pages and verify door crossings after server updates."""

import rs2004.quests.exec.prompts as prompts
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_dialogue_workflows import DialogueWorld


class Door:
    def __init__(self, world, id=123, name='Door', distance=1):
        self.world = world
        self.id = id
        self.name = name
        self.dist = distance

    def actions(self):
        return ['Open']

    def distance(self):
        return self.dist

    def interact(self, op):
        self.world.door_clicks.append((self.id, op))
        return self.world.answer_door()


class PromptWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.far = False
        self.can_walk = True
        self.door_accepts = True
        self.outcome = 'cross'
        self.cross_pending = False
        self.walks = []
        self.door_clicks = []
        self.key_uses = []
        self.messages = []
        self.pack = []
        self.locations = [Door(self)]
        self.sustain_calls = 0
        self.prayer_calls = 0
        self.loc_status = 'done'
        self.prompt_pages = []
        self.loc_requests = []

    def __enter__(self):
        DialogueWorld.__enter__(self)
        replacements = {
            '_core': self,
            'sustain': FakeModule(run=self.sustain_run),
            'prayer_upkeep': self.prayer_run,
            'inventory': FakeModule(items=lambda: self.pack),
            'locs': FakeModule(query=lambda: EntityQuery(self.entities, lambda loc: True)),
            'traversal': FakeModule(walk_resilient=self.walk),
            'reach': FakeModule(loc_op=self.loc_op),
            'game_messages': FakeModule(mark=lambda: len(self.messages), since=lambda mark: self.messages[mark:]),
        }
        self.prompt_saved = {}
        for name, value in replacements.items():
            self.prompt_saved[name] = getattr(prompts, name)
            setattr(prompts, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.prompt_saved.items():
            setattr(prompts, name, value)
        DialogueWorld.__exit__(self, *args)

    def sustain_run(self):
        self.sustain_calls += 1
        yield from execution.delay_ticks(0)

    def prayer_run(self):
        self.prayer_calls += 1
        yield from execution.delay_ticks(0)

    def entities(self, ids, names, radius, layer):
        return [loc for loc in self.locations if (ids is None or loc.id in ids)
                and (names is None or loc.name in names) and (radius is None or loc.distance() <= radius)]

    def walk(self, tile, **kwargs):
        self.walks.append((tile, kwargs))
        yield execution.Ticks(1)
        return self.can_walk

    def answer_door(self):
        if not self.door_accepts:
            return False
        if self.outcome == 'cross':
            self.cross_pending = True
        elif self.outcome == 'refusal':
            self.messages.append('The door is locked.')
        elif self.outcome == 'dialogue':
            self.pages = [('continue', ['A challenge']), ('options', ['Leave', 'Yes, enter']), ('cross', [])]
        return True

    def loc_op(self, name, op, near, expect, **kwargs):
        self.loc_requests.append((name, op, near, kwargs))
        yield execution.Ticks(1)
        self.pages = list(self.prompt_pages)
        if self.loc_status == 'done':
            assert expect() or not self.pages
        return self.loc_status

    def use_key(self, loc):
        self.key_uses.append(loc.id)
        return self.answer_door()

    def advance(self):
        DialogueWorld.advance(self)
        if self.cross_pending or self.kind() == 'cross':
            self.far = True
            self.cross_pending = False
            self.pages = []

    def crossing(self, **options):
        return prompts.DoorCrossing(123, Tile(3000, 3000), lambda: self.far,
                                    self.logs.append, **options)

    def cross(self, **options):
        return self.run(prompts.cross_teleport_door(self.crossing(**options)))


def test_drive_choice_continues_then_selects_preferred_option():
    with PromptWorld() as world:
        world.pages = [('continue', ['Hello']), ('options', ['Leave', 'Yes, please'])]
        assert world.run(prompts.drive_choice(['PLEASE'], world.logs.append))
        assert world.clicks == ['continue', 111]
        assert not world.pages


def test_drive_choice_stops_on_unmatched_options_without_clicking_refusal():
    with PromptWorld() as world:
        world.pages = [('options', ["I don't think so", 'Leave'])]
        assert world.run(prompts.drive_choice(['Yes'], world.logs.append)) is False
        assert world.clicks == []
        assert 'no preferred option' in world.logs[0]


def test_drive_choice_bounds_wait_for_chat_page_that_never_changes():
    with PromptWorld() as world:
        world.pages = [('waiting', ['Loading'])]
        assert world.run(prompts.drive_choice([], world.logs.append)) is False
        assert len(world.waits) == 60


def test_drive_boxes_preserves_goal_page_instead_of_clicking_it_away():
    with PromptWorld() as world:
        world.pages = [('main', ['First message']), ('continue', ['Next']), ('goal', ['Answer'])]
        assert world.run(prompts.drive_boxes(lambda: world.kind() == 'goal', 10000))
        assert world.clicks == ['close', 'continue']
        assert world.kind() == 'goal'


def test_drive_boxes_uses_preferred_option_and_logs_choice():
    with PromptWorld() as world:
        world.pages = [('options', ['Refuse', 'Yes, enter']), ('goal', ['Welcome'])]
        assert world.run(prompts.drive_boxes(lambda: world.kind() == 'goal', 10000,
                                             ['enter'], world.logs.append))
        assert world.clicks == [111]
        assert 'chose "Yes, enter"' in world.logs[0]


def test_drive_boxes_does_not_guess_when_preferred_option_is_missing():
    with PromptWorld() as world:
        world.pages = [('options', ['Refuse', 'Leave'])]
        assert world.run(prompts.drive_boxes(lambda: False, 10000, ['enter'], world.logs.append)) is False
        assert world.clicks == []
        assert world.now == 0


def test_drive_boxes_feeds_sustain_while_waiting_between_boxes():
    with PromptWorld() as world:
        assert world.run(prompts.drive_boxes(lambda: world.now >= 1500, 5000))
        assert world.sustain_calls == 3
        assert world.clicks == []


def test_drive_boxes_with_unclosable_modal_yields_and_times_out():
    with PromptWorld() as world:
        world.pages = [('main', ['Message'])]
        world.respond = False
        assert world.run(prompts.drive_boxes(lambda: False, 3000)) is False
        assert world.now >= 3000
        assert world.clicks == ['close']


def test_drive_until_pumps_prayer_while_waiting_and_checks_final_deadline():
    with PromptWorld() as world:
        assert world.run(prompts.drive_until(lambda: world.now >= 1500, [], world.logs.append, ms=1500))
        assert world.prayer_calls == 3
        assert world.run(prompts.drive_until(lambda: False, [], world.logs.append, ms=1000)) is False


def test_drive_until_stops_on_unmatched_option_chain():
    with PromptWorld() as world:
        world.pages = [('continue', ['Hello']), ('options', ['Leave'])]
        assert world.run(prompts.drive_until(lambda: world.far, ['enter'], world.logs.append)) is False
        assert world.clicks == ['continue']


def test_clear_boxes_handles_both_modals_and_respects_box_limit():
    with PromptWorld() as world:
        world.pages = [('continue', ['One']), ('main', ['Two']), ('continue', ['Three'])]
        world.run(prompts.clear_boxes(max_boxes=2))
        assert world.clicks == ['continue', 'close']
        assert world.kind() == 'continue'
        world.run(prompts.clear_boxes())
        assert not world.pages


def test_clear_boxes_stops_when_main_modal_does_not_close():
    with PromptWorld() as world:
        world.pages = [('main', ['Message'])]
        world.respond = False
        world.run(prompts.clear_boxes())
        assert world.clicks == ['close']
        assert world.kind() == 'main'


def test_door_crossing_waits_for_position_and_settles_scene():
    with PromptWorld() as world:
        assert world.cross(stand_radius=0)
        assert world.far and world.door_clicks == [(123, 'Open')]
        assert world.walks[0][1]['radius'] == 0
        assert isinstance(world.waits[-1], execution.Ticks) and world.waits[-1].count == 2


def test_already_crossed_door_does_not_walk_or_click():
    with PromptWorld() as world:
        world.far = True
        assert world.cross()
        assert world.walks == [] and world.door_clicks == []


def test_door_crossing_clears_leftover_main_message_before_walking():
    with PromptWorld() as world:
        world.pages = [('main', ['Old message'])]
        assert world.cross()
        assert world.clicks == ['close'] and world.far


def test_door_crossing_answers_challenge_without_selecting_refusal():
    with PromptWorld() as world:
        world.outcome = 'dialogue'
        assert world.cross(prefer=['enter'])
        assert world.clicks == ['continue', 111]
        assert world.far


def test_door_refusal_is_failure_even_when_click_was_accepted():
    with PromptWorld() as world:
        world.outcome = 'refusal'
        assert world.cross() is False
        assert world.door_clicks == [(123, 'Open')]
        assert not world.far


def test_silent_door_does_not_count_as_crossed_and_waits_are_bounded():
    with PromptWorld() as world:
        world.outcome = 'silent'
        assert world.cross() is False
        assert world.now >= prompts.DIALOG_MS + prompts.DOOR_MS
        assert not world.far


def test_door_walk_failure_and_missing_scene_loc_do_not_send_clicks():
    for walk_fails in [True, False]:
        with PromptWorld() as world:
            world.can_walk = not walk_fails
            if not walk_fails:
                world.locations = []
            assert world.cross() is False
            assert world.door_clicks == []
            if not walk_fails:
                assert 'no door 123' in world.logs[-1]


def test_opened_door_can_be_found_by_neighboring_name_after_id_changes():
    with PromptWorld() as world:
        world.locations = [Door(world, id=124)]
        assert world.cross()
        assert world.door_clicks == [(124, 'Open')]


def test_key_door_selects_key_by_id_instead_of_using_open():
    with PromptWorld() as world:
        world.pack = [FakeModule(id=777, count=1, use_on=world.use_key)]
        assert world.cross(use_item=777)
        assert world.key_uses == [123] and world.door_clicks == []


def test_key_door_missing_or_rejected_key_does_not_claim_crossing():
    for held in [True, False]:
        with PromptWorld() as world:
            world.door_accepts = False
            if held:
                world.pack = [FakeModule(id=777, count=1, use_on=world.use_key)]
            assert world.cross(use_item=777) is False
            assert not world.far and world.door_clicks == []
            assert ('refused the key' if held else 'no key 777') in world.logs[-1]


def test_door_rejected_open_click_stops_without_waiting_for_crossing():
    with PromptWorld() as world:
        world.door_accepts = False
        assert world.cross() is False
        assert 'refused the Open click' in world.logs[-1]
        assert len(world.waits) == 1


def test_use_on_loc_selects_exact_loc_id_when_names_are_shared():
    with PromptWorld() as world:
        world.locations = [Door(world, id=122), Door(world, id=123)]
        world.pack = [FakeModule(id=777, count=2, use_on=world.use_key)]
        loc = FakeModule(name='Door', near=Tile(3000, 3000), id=123, within=None)
        assert prompts.held_id(777) == 2
        assert prompts.loc_near('Door', 'Open').id == 122
        assert world.run(prompts.use_on_loc(777, loc, [], lambda: world.far, world.logs.append))
        assert world.key_uses == [123]


def test_use_on_loc_missing_item_or_loc_returns_failure_without_use():
    for missing_item in [True, False]:
        with PromptWorld() as world:
            if not missing_item:
                world.pack = [FakeModule(id=777, count=1, use_on=world.use_key)]
                world.locations = []
            loc = FakeModule(name='Door', near=Tile(3000, 3000), id=123, within=5)
            assert world.run(prompts.use_on_loc(777, loc, [], lambda: False, world.logs.append)) is False
            assert world.key_uses == []
            assert 'no item 777' in world.logs[-1]


def test_prompt_loc_answers_boxes_and_preserves_goal_screen():
    with PromptWorld() as world:
        world.prompt_pages = [('continue', ['Message']), ('goal', ['Door panel'])]
        step = prompts.LocPrompt('Door', 'Search', Tile(3000, 3000), lambda: world.kind() == 'goal',
                                  id=123, within=4, refused='locked')
        assert world.run(prompts.prompt_loc(step, world.logs.append))
        assert world.clicks == ['continue']
        assert world.kind() == 'goal'
        options = world.loc_requests[0][3]
        assert options['within'] == 4 and options['id'] == 123 and options['refused'] == 'locked'


def test_prompt_loc_with_already_satisfied_goal_does_not_click_again():
    with PromptWorld() as world:
        step = prompts.LocPrompt('Door', 'Search', Tile(3000, 3000), lambda: True)
        assert world.run(prompts.prompt_loc(step, world.logs.append))
        assert world.loc_requests == [] and world.clicks == []


def test_prompt_loc_reports_failed_reach_without_driving_dialogue():
    for status in ['missing', 'refused', 'timeout']:
        with PromptWorld() as world:
            world.loc_status = status
            step = prompts.LocPrompt('Door', 'Search', Tile(3000, 3000), lambda: False)
            assert world.run(prompts.prompt_loc(step, world.logs.append)) is False
            assert status in world.logs[-1]
            assert world.loc_requests[0][3]['within'] == 10
            assert world.clicks == []


def test_prompt_loc_reports_unmatched_option_chain_as_unsatisfied_goal():
    with PromptWorld() as world:
        world.prompt_pages = [('options', ['Leave'])]
        step = prompts.LocPrompt('Door', 'Search', Tile(3000, 3000), lambda: False, prefer=['enter'])
        assert world.run(prompts.prompt_loc(step, world.logs.append)) is False
        assert 'goal never came' in world.logs[-1]
        assert 'no preferred option' in world.logs[0]


def test_use_on_loc_skips_completed_goal_and_stops_on_failed_walk_or_use():
    with PromptWorld() as world:
        loc = FakeModule(name='Door', near=Tile(3000, 3000), id=123, within=None)
        assert world.run(prompts.use_on_loc(777, loc, [], lambda: True, world.logs.append))
        assert world.walks == []
        world.can_walk = False
        assert world.run(prompts.use_on_loc(777, loc, [], lambda: False, world.logs.append)) is False
        assert world.key_uses == []
        world.can_walk = True
        world.pack = [FakeModule(id=777, count=1, use_on=world.use_key)]
        world.door_accepts = False
        assert world.run(prompts.use_on_loc(777, loc, [], lambda: False, world.logs.append)) is False
        assert world.key_uses == [123]
