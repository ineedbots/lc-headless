"""Tutorial departure checks character design, guide replies, and server arrival."""

import rs2004.tutorial as tutorial
from rs2004.entities import EntityQuery
from helpers import FakeModule
from test_dialogue_workflows import DialogueWorld


class Guide:
    name = 'RuneScape Guide'
    id = 1

    def __init__(self, world):
        self.world = world

    def distance(self):
        return 1

    def interact(self, op):
        assert op == 'Talk-to'
        self.world.talks += 1
        if self.world.accept_talk and self.world.talks > self.world.failed_attempts:
            self.world.pages = list(self.world.guide_pages)
        return self.world.accept_talk


class TutorialWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.placed = True
        self.x = 3090
        self.z = 3100
        self.design = False
        self.design_at = None
        self.design_saved = False
        self.design_closes = True
        self.designs = []
        self.has_guide = True
        self.accept_talk = True
        self.failed_attempts = 0
        self.talks = 0
        self.guide_pages = [('continue', ['Welcome']), ('options', ['Stay', 'Yes please, skip'])]
        self.leaves = True
        self.depart_at = None

    def __enter__(self):
        DialogueWorld.__enter__(self)
        self.tutorial_saved = (tutorial._core, tutorial.game, tutorial.npcs)
        tutorial._core = self
        tutorial.game = FakeModule(appearance_screen_open=self.appearance_screen_open,
                                   set_appearance=self.set_appearance)
        tutorial.npcs = FakeModule(query=lambda: EntityQuery(self.guides, lambda npc: True))
        return self

    def __exit__(self, *args):
        tutorial._core, tutorial.game, tutorial.npcs = self.tutorial_saved
        DialogueWorld.__exit__(self, *args)

    def is_placed(self):
        return self.placed

    def get_x(self):
        return self.x

    def get_z(self):
        return self.z

    def appearance_screen_open(self):
        return self.design

    def set_appearance(self, female, kits, colours):
        self.designs.append((female, list(kits), list(colours)))
        self.design_saved = True

    def guides(self, ids, names, radius, layer):
        return [Guide(self)] if self.has_guide else []

    def click_component(self, com):
        accepted = DialogueWorld.click_component(self, com)
        if accepted and self.kind() == 'options' and tutorial.offers_skip(self.pages[0][1]):
            if self.leaves:
                self.depart_at = self.now + 1500
        return accepted

    def advance(self):
        DialogueWorld.advance(self)
        if self.design_at is not None and self.now >= self.design_at:
            self.design = True
            self.design_at = None
        if self.design_saved and self.design_closes:
            self.design = False
        if self.depart_at is not None and self.now >= self.depart_at:
            self.x = 3222
            self.z = 3218

    def skip(self):
        return self.run(tutorial.skip(self.logs.append))

    def talk(self):
        return self.run(tutorial._talk(self.logs.append))


def test_tutorial_design_waits_for_late_screen_and_saves_allowed_body():
    with TutorialWorld() as world:
        world.design_at = 1000
        world.run(tutorial._finish_design(world.logs.append))
        assert world.designs == [(False, [0, 10, 18, 26, 33, 36, 42], [0, 0, 0, 0, 0])]
        assert world.now >= 1500 and not world.design


def test_tutorial_absent_design_screen_is_bounded_and_does_not_save():
    with TutorialWorld() as world:
        world.run(tutorial._finish_design(world.logs.append))
        assert world.designs == [] and world.logs == []
        assert world.now >= tutorial.DESIGN_WAIT_MS


def test_tutorial_design_close_timeout_does_not_loop_forever():
    with TutorialWorld() as world:
        world.design = True
        world.design_closes = False
        world.run(tutorial._finish_design(world.logs.append))
        assert len(world.designs) == 1 and world.design
        assert world.now == tutorial.DESIGN_CLOSE_MS


def test_tutorial_skip_answers_guide_and_waits_for_mainland():
    with TutorialWorld() as world:
        assert world.skip()
        assert world.talks == 1 and world.clicks == ['continue', 111]
        assert not tutorial.on_tutorial_island()
        assert world.logs[-1] == 'tutorial: skipped'


def test_tutorial_skip_retries_failed_dialogue_opening():
    with TutorialWorld() as world:
        world.failed_attempts = 2
        assert world.skip()
        assert world.talks == 3
        assert world.now >= 2 * tutorial.TALK_OPEN_MS


def test_tutorial_skip_stops_on_explicit_refusal():
    with TutorialWorld() as world:
        world.guide_pages = [('options', ['Stay', 'Tell me more'])]
        assert world.skip() is False
        assert world.talks == 1 and world.clicks == []
        assert 'still on the island' in world.logs[-1]


def test_tutorial_skip_requires_departure_after_accepting_option():
    with TutorialWorld() as world:
        world.leaves = False
        assert world.skip() is False
        assert world.talks == tutorial.TALK_ATTEMPTS
        assert tutorial.on_tutorial_island()
        assert world.now >= tutorial.LEAVE_MS * tutorial.TALK_ATTEMPTS


def test_tutorial_missing_guide_exhausts_attempts_without_clicking():
    with TutorialWorld() as world:
        world.has_guide = False
        assert world.skip() is False
        assert world.talks == 0 and world.clicks == []
        assert len([line for line in world.logs if "can't see" in line]) == 3


def test_tutorial_rejected_talk_does_not_wait_for_response():
    with TutorialWorld() as world:
        world.accept_talk = False
        assert world.talk() == 'failed'
        assert world.waits == [] and world.talks == 1


def test_tutorial_unanswered_talk_times_out():
    with TutorialWorld() as world:
        world.guide_pages = []
        assert world.talk() == 'failed'
        assert world.now == tutorial.TALK_OPEN_MS


def test_tutorial_chat_closing_without_skip_is_refusal():
    with TutorialWorld() as world:
        world.guide_pages = [('continue', ['Goodbye'])]
        assert world.talk() == 'refused'
        assert world.clicks == ['continue']


def test_tutorial_waiting_chat_has_bounded_steps():
    with TutorialWorld() as world:
        world.guide_pages = [('waiting', ['Loading'])]
        assert world.talk() == 'refused'
        assert len(world.waits) == tutorial.DIALOGUE_STEPS


def test_tutorial_rejected_continue_is_bounded():
    with TutorialWorld() as world:
        world.guide_pages = [('continue', ['Welcome'])]
        world.accept_click = False
        assert world.talk() == 'refused'
        assert len(world.clicks) == tutorial.DIALOGUE_STEPS
        assert world.waits == []
