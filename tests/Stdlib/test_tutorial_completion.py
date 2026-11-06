"""Playable tutorial resumes from wire-visible instructions and bounds failures."""

import rs2004.tutorial as tutorial
from helpers import FakeModule
from rs2004.entities import EntityQuery
from test_tutorial_workflows import TutorialWorld
from test_dialogue_workflows import PanelItem


class CompletionWorld(TutorialWorld):
    def __init__(self):
        TutorialWorld.__init__(self)
        self.instruction = 'Getting started'
        self.stages = []
        self.actions = []
        self.refuse = False
        self.progress_notes = 0

    def __enter__(self):
        TutorialWorld.__enter__(self)
        self.completion_saved = (tutorial._perform_stage, tutorial.STAGE_TIMEOUT_MS, tutorial._last_stage)
        tutorial._perform_stage = self.perform
        tutorial.STAGE_TIMEOUT_MS = 10000
        tutorial._last_stage = 0
        return self

    def __exit__(self, *args):
        tutorial._perform_stage, tutorial.STAGE_TIMEOUT_MS, tutorial._last_stage = self.completion_saved
        TutorialWorld.__exit__(self, *args)

    def get_tutorial_modal(self):
        return 300

    def get_texts(self, root):
        return [self.instruction] if root == 300 else []

    def note_progress(self):
        self.progress_notes += 1

    def perform(self, stage):
        self.actions.append(stage)
        if False:
            yield
        if self.refuse:
            return False
        if self.stages:
            self.instruction = self.stages.pop(0)
        else:
            self.x, self.z = 3222, 3218
        return True


class ActionWorld(CompletionWorld):
    def __init__(self):
        CompletionWorld.__init__(self)
        self.pack = {}
        self.scenery = []
        self.uses = []
        self.walks = []
        self.tabs = []
        self.run_clicks = []

    def __enter__(self):
        CompletionWorld.__enter__(self)
        self.action_saved = (tutorial.inventory, tutorial.locs, tutorial.direct_navigator)
        tutorial.inventory = FakeModule(first=lambda name: self.pack.get(name), contains=lambda name: name in self.pack)
        tutorial.locs = FakeModule(query=lambda: EntityQuery(self.supply, lambda loc: True))
        tutorial.direct_navigator = FakeModule(walk_to=self.walk)
        tutorial.game.open_side_tab = self.open_tab
        tutorial.game.set_run = lambda enabled: self.run_clicks.append(enabled)
        return self

    def __exit__(self, *args):
        tutorial.inventory, tutorial.locs, tutorial.direct_navigator = self.action_saved
        CompletionWorld.__exit__(self, *args)

    def supply(self, ids, names, radius, layer):
        return [loc for loc in self.scenery if (ids is None or loc.id in ids) and (names is None or loc.name in names)]

    def walk(self, tile, radius=2, timeout_ms=20000):
        self.walks.append(tile)
        if False:
            yield
        return True

    def open_tab(self, tab):
        self.tabs.append(tab)
        if False:
            yield
        return True

    def item(self, name):
        self.pack[name] = FakeModule(name=name, use_on=lambda target: self.use(name, target))

    def use(self, name, target):
        self.uses.append((name, target.name))
        return True

    def loc(self, id, name):
        self.scenery.append(FakeModule(id=id, name=name, distance=lambda: 1,
                                      interact=lambda action: self.uses.append((name, action)) or True))

    def stage(self, stage):
        return self.run(self.completion_saved[0](stage))


class SkillWorld(ActionWorld):
    def __init__(self):
        ActionWorld.__init__(self)
        self.actors = []
        self.worn = []
        self.reach_status = 'done'

    def __enter__(self):
        ActionWorld.__enter__(self)
        self.skill_saved = (tutorial.npcs, tutorial.equipment, tutorial.reach)
        tutorial.npcs = FakeModule(query=lambda: EntityQuery(self.actor_supply, lambda n: True))
        tutorial.equipment = FakeModule(equip=self.equip, unequip=self.unequip)
        tutorial.reach = FakeModule(entity_op=self.reach_op)
        tutorial.game.cast_on_npc = lambda spell, npc: self.uses.append((spell, npc.name)) or True
        return self

    def __exit__(self, *args):
        tutorial.npcs, tutorial.equipment, tutorial.reach = self.skill_saved
        ActionWorld.__exit__(self, *args)

    def actor_supply(self, ids, names, radius, layer):
        return [npc for npc in self.actors if names is None or npc.name in names]

    def actor(self, name):
        self.actors.append(FakeModule(name=name, distance=lambda: 15, targets_me=lambda: False,
                                     targets_another_player=lambda: False, valid=lambda: False,
                                     interact=lambda op: self.actor_op(name, op)))

    def actor_op(self, name, op):
        self.uses.append((name, op))
        if op == 'Net':
            self.item('Raw shrimps')
        return True

    def reach_op(self, find, op, expect, open_when_unreachable=False, expect_ms=10000):
        if False:
            yield
        assert find() is not None and open_when_unreachable
        if self.reach_status == 'done':
            self.pages = [('continue', ['Welcome'])]
        return self.reach_status

    def equip(self, name):
        if False:
            yield
        self.worn.append(name)
        return True

    def unequip(self, name):
        if False:
            yield
        self.worn = [item for item in self.worn if item != name]
        return True

    def use(self, name, target):
        ActionWorld.use(self, name, target)
        if name == 'Tinderbox':
            self.loc(2732, 'Fire')
        return True


def test_tutorial_relights_an_expired_fire_and_cooks_newly_caught_shrimp():
    with SkillWorld() as world:
        assert world.run(tutorial._light_fire()) is False
        world.loc(3033, 'Tree')
        world.item('Tinderbox')
        world.item('Logs')
        world.actor('Fishing spot')
        assert world.stage(90)
        assert world.uses == [('Fishing spot', 'Net'), ('Tinderbox', 'Logs'), ('Raw shrimps', 'Fire')]
        assert world.stage(80)
        assert world.uses[-1] == ('Raw shrimps', 'Fire')


def test_tutorial_missing_fishing_spot_and_missing_wood_fail_without_using_items():
    with SkillWorld() as world:
        assert world.stage(70) is False
        assert world.run(tutorial._shrimp()) is False
        world.loc(3033, 'Tree')
        assert world.run(tutorial._light_fire()) is False
        assert world.uses == [('Tree', 'Chop down')]


def test_tutorial_instructor_requires_a_door_aware_dialogue_to_open():
    with SkillWorld() as world:
        assert world.stage(10) is False
        world.actor('Survival Expert')
        world.reach_status = 'retry'
        assert world.stage(10) is False
        world.reach_status = 'done'
        assert world.stage(10)
        assert world.clicks == ['continue']


def test_tutorial_skill_stages_operate_the_right_rocks_and_equip_training_weapons():
    with SkillWorld() as world:
        world.loc(3033, 'Tree')
        assert world.stage(30)
        world.item('Logs')
        world.item('Tinderbox')
        assert world.stage(40)
        world.actor('Fishing spot')
        assert world.stage(70)
        world.loc(3042, 'Copper rock')
        world.loc(3043, 'Tin rock')
        for stage in (270, 274, 275, 290, 294, 295):
            assert world.stage(stage)
        assert world.uses[-6:] == [('Copper rock', 'Prospect'), ('Tin rock', 'Prospect'), ('Copper rock', 'Prospect'),
                                  ('Tin rock', 'Mine'), ('Tin rock', 'Mine'), ('Copper rock', 'Mine')]
        assert world.stage(380)
        assert world.stage(400)
        assert world.worn == ['Bronze sword', 'Wooden shield']
        world.actor('Giant rat')
        assert world.stage(460)
        assert world.worn == ['Bronze sword', 'Shortbow', 'Bronze arrow']
        assert world.uses[-1] == ('Giant rat', 'Attack')


def test_tutorial_magic_requires_runes_and_a_chicken_before_casting():
    with SkillWorld() as world:
        assert world.stage(640) is False
        world.item('Air rune')
        world.item('Mind rune')
        assert world.stage(640) is False
        world.actor('Chicken')
        assert world.stage(650)
        assert world.uses == [('Wind Strike', 'Chicken')]


def test_tutorial_banking_uses_the_booth_and_unknown_dialogue_is_bounded():
    with SkillWorld() as world:
        world.loc(3045, 'Bank booth')
        assert world.stage(500)
        assert world.uses == [('Bank booth', 1)]
        assert world.stage(510) is False
        world.pages = [('waiting', ['Loading'])]
        assert world.stage(620) is False
        assert world.tabs == []


def test_tutorial_uses_the_bar_on_an_anvil_then_selects_the_dagger_product():
    with SkillWorld() as world:
        world.loc(2783, 'Anvil')
        world.item('Bronze bar')
        assert world.stage(340)
        assert world.uses == [('Bronze bar', 'Anvil')]
        world.pages = [('main', [])]
        world.panel = [(PanelItem(world, 51, 'Bronze dagger', ['Make 1']), 51)]
        assert world.stage(340)
        assert world.clicks == [(51, 'Make 1')]


def test_tutorial_recipes_require_materials_and_use_the_correct_target():
    with ActionWorld() as world:
        assert world.stage(150) is False
        world.item('Bucket of water')
        assert world.stage(150) is False
        world.item('Pot of flour')
        assert world.stage(150)
        world.item('Bread dough')
        assert world.stage(160) is False
        world.loc(3039, 'Range')
        assert world.stage(160)
        world.item('Copper ore')
        world.loc(3044, 'Furnace')
        assert world.stage(320)
        assert world.uses == [('Bucket of water', 'Pot of flour'), ('Bread dough', 'Range'), ('Copper ore', 'Furnace')]


def test_tutorial_controls_open_the_run_panel_before_enabling_run():
    with ActionWorld() as world:
        assert world.stage(190)
        assert world.tabs == [12] and world.run_clicks == [True]
        assert world.stage(570)
        assert world.stage(580)
        assert world.tabs == [12, 8, 9]


def test_tutorial_passage_missing_then_available_and_unknown_stage_refusal():
    with ActionWorld() as world:
        assert world.stage(4) is False
        world.loc(3014, 'Door')
        assert world.stage(4)
        assert world.walks == [(3098, 3107), (3098, 3107)]
        assert world.uses == [('Door', 'Open')]
        assert world.stage(999) is False


def test_tutorial_exits_the_southern_edge_of_the_rat_pen_before_talking():
    with ActionWorld() as world:
        world.x, world.z = 3105, 9511
        world.loc(3022, 'Gate')
        assert world.stage(450)
        assert world.uses == [('Gate', 'Open')]
        assert world.talks == 0


def test_tutorial_instructions_reconstruct_each_stage_after_restart():
    with CompletionWorld() as world:
        for phrase, stage in tutorial.INSTRUCTIONS:
            tutorial._last_stage = 0
            world.instruction = phrase
            assert tutorial.progress() == stage
        world.instruction = 'Please wait... Your character is now attempting to mine the rock.'
        assert tutorial.progress() == 660


def test_tutorial_completion_resumes_midway_and_requires_mainland_arrival():
    with CompletionWorld() as world:
        world.instruction = "You've made a bronze bar!"
        world.stages = ['Smithing a dagger', "You've finished this area", 'You have almost completed the tutorial']
        assert world.run(tutorial.complete(world.logs.append))
        assert world.actions == [330, 340, 350, 660]
        assert world.progress_notes == 4
        assert world.logs[-1] == 'tutorial: completed; arrived on the mainland'


def test_tutorial_refused_or_unknown_stage_is_bounded_and_stays_on_island():
    with CompletionWorld() as world:
        world.instruction = 'An unsupported tutorial instruction'
        world.refuse = True
        assert world.run(tutorial.complete(world.logs.append)) is False
        assert tutorial.on_tutorial_island()
        assert world.actions and set(world.actions) == {0}
        assert 'stalled at stage 0' in world.logs[-1]


def test_tutorial_dialogue_declines_skip_and_accepts_only_bank_or_final_departure():
    with CompletionWorld() as world:
        world.pages = [('options', ['Yes please.', 'No, thank you.']), ('continue', ['Welcome'])]
        assert world.run(tutorial._drain_dialogue())
        assert world.clicks == [111, 'continue']
        world.instruction = "This is the 'Bank of RuneScape'"
        world.pages = [('options', ['Yes.', 'No thanks.'])]
        assert world.run(tutorial._drain_dialogue())
        assert world.clicks[-1] == 110
        world.instruction = 'You have almost completed the tutorial'
        world.pages = [('options', ['Yes.', 'No.'])]
        assert world.run(tutorial._drain_dialogue())
        assert world.clicks[-1] == 110


def test_tutorial_unfamiliar_option_is_not_guessed():
    with CompletionWorld() as world:
        world.pages = [('options', ['Something unexpected', 'Something else'])]
        assert world.run(tutorial._drain_dialogue()) is False
        assert world.clicks == []


def test_startup_accepts_an_initial_skip_and_waits_for_mainland():
    with ActionWorld() as world:
        tutorial._perform_stage = world.completion_saved[0]
        world.pages = [('options', ['Yes please.', 'No, thank you.'])]
        assert world.run(tutorial.complete(world.logs.append))
        assert world.clicks == [110]
        assert not tutorial.on_tutorial_island()
        assert world.now >= tutorial.DESIGN_WAIT_MS + 1500


def test_initial_dialogue_without_a_skip_continues_into_playable_tasks():
    with ActionWorld() as world:
        world.pages = [('continue', ['Welcome! Go through the door.'])]
        assert world.stage(1)
        assert world.clicks == ['continue'] and tutorial.on_tutorial_island()
        world.instruction = 'Interacting with scenery'
        world.loc(3014, 'Door')
        assert world.stage(tutorial.progress())
        assert world.uses == [('Door', 'Open')]
        assert world.talks == 0


def test_skip_preference_does_not_apply_after_the_start():
    with ActionWorld() as world:
        world.instruction = 'Moving around'
        world.leaves = False
        world.pages = [('options', ['Yes please.', 'No, thank you.'])]
        assert world.stage(10)
        assert world.clicks == [111] and tutorial.on_tutorial_island()


def test_initial_skip_requires_actual_arrival_and_times_out_safely():
    with ActionWorld() as world:
        world.leaves = False
        world.pages = [('options', ['Yes please.', 'No, thank you.'])]
        assert world.stage(1) is False
        assert world.clicks == [110] and tutorial.on_tutorial_island()
        assert world.now >= tutorial.LEAVE_MS


def test_stale_instruction_packets_do_not_repeat_completed_tasks():
    with CompletionWorld() as world:
        world.instruction = 'These are your stats'
        assert tutorial.progress() == 60
        world.instruction = 'Building a fire'
        assert tutorial.progress() == 60


def test_disconnect_is_not_reported_as_mainland_arrival():
    with CompletionWorld() as world:
        def disconnect(stage):
            world.placed = False
            if False:
                yield
            return True
        tutorial._perform_stage = disconnect
        assert world.run(tutorial.complete(world.logs.append)) is False
        assert world.logs[-1] == 'tutorial: disconnected before mainland arrival'


def test_melee_chooses_a_reachable_rat_and_handles_a_disappearing_target():
    with CompletionWorld() as world:
        attacks = []
        blocked = FakeModule(distance=lambda: 1, targets_me=lambda: False, targets_another_player=lambda: False,
                             reachable=False, valid=lambda: False, interact=lambda op: attacks.append('blocked') or True)
        reachable = FakeModule(distance=lambda: 3, targets_me=lambda: False, targets_another_player=lambda: False,
                               reachable=True, valid=lambda: False, interact=lambda op: attacks.append('reachable') or True)
        saved = tutorial.npcs
        def supply(ids, names, radius, layer):
            return [blocked, reachable]
        tutorial.npcs = FakeModule(query=lambda: EntityQuery(supply, lambda n: n.reachable))
        assert world.run(tutorial._fight(False))
        assert attacks == ['reachable']
        tutorial.npcs = saved


def test_burnt_shrimp_instructions_do_not_restart_the_initial_fishing_stage():
    with CompletionWorld() as world:
        world.instruction = ('Burning your shrimp. You have just burnt your first shrimp. ' +
                             'First catch some shrimp, then use them on a fire.')
        assert tutorial.progress() == 90


def test_runtime_starts_only_after_successful_tutorial_and_resumes_on_reset():
    from rs2004 import _runtime as runtime
    saved = (runtime._tutorial.complete, runtime._start_bot, runtime.request_finish,
             runtime._guardian, runtime._completing_tutorial, runtime._generator, runtime._starting)
    calls = []

    def succeeded(say):
        if False:
            yield
        return True

    def failed(say):
        if False:
            yield
        return False

    with CompletionWorld() as world:
        runtime._start_bot = lambda: calls.append('start')
        runtime.request_finish = lambda reason: calls.append('stop')
        runtime._tutorial.complete = failed
        world.run(runtime._complete_tutorial())
        assert calls == ['stop']
        runtime._tutorial.complete = succeeded
        world.run(runtime._complete_tutorial())
        assert calls == ['stop', 'start']
        runtime._completing_tutorial = True
        runtime.reset()
        assert runtime._completing_tutorial and runtime._guardian is not None
    (runtime._tutorial.complete, runtime._start_bot, runtime.request_finish,
     runtime._guardian, runtime._completing_tutorial, runtime._generator, runtime._starting) = saved
