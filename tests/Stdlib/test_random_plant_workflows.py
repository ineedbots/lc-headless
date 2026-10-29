"""Plant harvesting and guardian retries follow delayed server acknowledgements."""

import rs2004.random_events as events
from helpers import FakeModule, raises
from test_random_recovery_workflows import RecoveryWorld, EventNpc


class ObservedGuardian(events._RandomEvents):
    def __init__(self, world):
        events._RandomEvents.__init__(self)
        self.world = world

    def _detect_raw(self):
        if self.world.detection_fails:
            raise RuntimeError('scene unavailable')
        return self.world.after_event


class Plant(EventNpc):
    def __init__(self, world):
        EventNpc.__init__(self, world, name='Strange plant', id=408)
        self.index = 12
        self.ops = ['Pick']

    def actions(self):
        return self.ops

    def interact(self, op):
        self.world.picks.append(op)
        self.world.handling_seen.append(self.world.guardian.handling)
        if self.world.pick_raises:
            raise RuntimeError('pick failed')
        self.world.pending_pick = True
        return self.world.accept_items


class PlantWorld(RecoveryWorld):
    def __init__(self):
        RecoveryWorld.__init__(self)
        self.guardian = ObservedGuardian(self)
        self.plant = Plant(self)
        self.scene = [self.plant]
        self.picks = []
        self.handling_seen = []
        self.messages = []
        self.pending_pick = False
        self.pick_result = 'fruit'
        self.pick_raises = False
        self.ripen_at = None
        self.vanish_at = None
        self.after_event = None
        self.detection_fails = False
        self.damaged = False

    def count(self, name):
        return len([item for item in self.pack if item.name == name])

    def is_placed(self):
        return True

    def tick(self):
        return self.now // 600

    def get_npc(self, index):
        return self.plant if self.plant in self.scene and index == self.plant.index else None

    def took_damage(self, ticks):
        assert ticks == 4
        return self.damaged

    def message_mark(self):
        return len(self.messages)

    def game_messages_since(self, mark):
        return list(enumerate(self.messages[mark:], mark))

    def advance(self):
        RecoveryWorld.advance(self)
        if self.pending_pick:
            self.pending_pick = False
            if self.pick_result == 'fruit':
                self.carry('Strange fruit')
            elif self.pick_result == 'vanish':
                self.scene = []
            elif self.pick_result == 'foreign':
                self.messages.append('This plant is NOT HERE FOR YOU.')
            elif self.pick_result == 'attack':
                self.plant.ops = ['Attack']
        if self.ripen_at is not None and self.now >= self.ripen_at:
            self.plant.ops = ['Take-fruit']
        if self.vanish_at is not None and self.now >= self.vanish_at:
            self.scene = []

    def pick(self):
        return self.run(self.guardian._pick('strange plant', self.logs.append))

    def handle(self, kind='pick', name='strange plant'):
        return self.run(self.guardian.handle(events.Event(kind, name), self.logs.append))


def test_random_plant_pick_waits_for_fruit_arrival():
    with PlantWorld() as world:
        assert world.pick()
        assert world.picks == ['Pick'] and world.count('Strange fruit') == 1
        assert world.now == 500 and 'fruit picked' in world.logs[-1]


def test_random_plant_take_action_and_existing_fruit_require_a_new_fruit():
    with PlantWorld() as world:
        world.carry('Strange fruit')
        world.plant.ops = ['Inspect', 'Take-fruit']
        assert world.pick()
        assert world.picks == ['Take-fruit'] and world.count('Strange fruit') == 2


def test_random_plant_disappearance_after_pick_finishes_without_inventory_gain():
    with PlantWorld() as world:
        world.pick_result = 'vanish'
        assert world.pick()
        assert world.count('Strange fruit') == 0 and 'fruit picked' in world.logs[-1]


def test_random_plant_missing_at_start_needs_no_click_or_wait():
    with PlantWorld() as world:
        world.scene = []
        assert world.pick()
        assert world.picks == [] and world.waits == []


def test_random_plant_ownership_refusal_sets_cooldown():
    with PlantWorld() as world:
        world.pick_result = 'foreign'
        assert world.pick()
        assert world.guardian.cooldown_until['pick:strange plant'] == world.now + events.GIVE_UP_COOLDOWN_MS
        assert world.picks == ['Pick'] and "isn't ours" in world.logs[-1]


def test_random_plant_old_ownership_message_does_not_reject_new_pick():
    with PlantWorld() as world:
        world.messages = ['The plant is not here for you.']
        assert world.pick()
        assert world.count('Strange fruit') == 1 and world.guardian.cooldown_until == {}


def test_random_plant_waits_for_ripening_before_picking():
    with PlantWorld() as world:
        world.plant.ops = ['Inspect']
        world.ripen_at = 3000
        assert world.pick()
        assert world.picks == ['Take-fruit'] and world.now >= 3000
        assert world.count('Strange fruit') == 1


def test_random_plant_unripe_disappearance_stops_waiting():
    with PlantWorld() as world:
        world.plant.ops = []
        world.vanish_at = 1000
        assert world.pick()
        assert world.now == 1000 and world.picks == []


def test_random_plant_never_ripens_has_bounded_total_wait():
    with PlantWorld() as world:
        world.plant.ops = []
        assert world.pick()
        assert events.PICK_WAIT_MS <= world.now < events.PICK_WAIT_MS + 2500
        assert world.picks == [] and 'never ripened' in world.logs[-1]


def test_random_plant_unacknowledged_pick_retries_until_deadline():
    with PlantWorld() as world:
        world.pick_result = 'silent'
        assert world.pick()
        assert len(world.picks) > 1 and world.count('Strange fruit') == 0
        assert events.PICK_WAIT_MS <= world.now < events.PICK_WAIT_MS + 8500
        assert 'never ripened' in world.logs[-1]


def test_random_plant_turning_hostile_without_damage_stops_harvest():
    with PlantWorld() as world:
        world.pick_result = 'attack'
        assert world.pick()
        assert world.picks == ['Pick'] and world.now == 500


def test_random_plant_already_hostile_without_damage_needs_no_pick():
    with PlantWorld() as world:
        world.plant.ops = ['Attack']
        assert world.pick()
        assert world.picks == [] and world.waits == []


def test_random_guardian_marks_handling_during_pick_and_clears_after_success():
    with PlantWorld() as world:
        assert world.handle()
        assert world.handling_seen == [True] and not world.guardian.handling
        assert world.guardian.attempts == {}


def test_random_guardian_clears_handling_before_propagating_solver_error():
    with PlantWorld() as world:
        world.pick_raises = True
        assert raises(RuntimeError, world.handle) == 'pick failed'
        assert world.handling_seen == [True] and not world.guardian.handling


def test_random_guardian_retains_attempt_count_while_same_event_remains():
    with PlantWorld() as world:
        world.after_event = events.Event('pick', 'strange plant')
        assert world.handle() and world.handle()
        assert world.guardian.attempts == {'pick:strange plant': 2}


def test_random_guardian_fifth_optional_attempt_cools_down_without_clicking():
    with PlantWorld() as world:
        world.guardian.attempts['pick:strange plant'] = events.MAX_ATTEMPTS
        assert world.handle() is False
        assert world.picks == [] and world.guardian.attempts == {}
        assert world.guardian.cooldown_until['pick:strange plant'] == events.GIVE_UP_COOLDOWN_MS
        assert not world.guardian.handling


def test_random_guardian_changed_event_clears_only_completed_event_attempts():
    with PlantWorld() as world:
        world.after_event = events.Event('dialog', 'genie')
        world.guardian.attempts['dialog:genie'] = 2
        assert world.handle()
        assert world.guardian.attempts == {'dialog:genie': 2}


def test_random_guardian_scene_detection_failure_still_clears_completed_attempt():
    with PlantWorld() as world:
        world.detection_fails = True
        assert world.handle()
        assert world.guardian.attempts == {} and not world.guardian.handling


def test_random_guardian_unknown_event_returns_false_and_releases_handling():
    with PlantWorld() as world:
        assert world.handle('unknown', 'unknown') is False
        assert world.guardian.attempts == {} and not world.guardian.handling


def event_bot():
    return FakeModule(ignored_randoms=lambda: ['FROG'], grind_targets=lambda: ['ZOMBIE'],
                      lamp_skill=lambda: 'mining')


def test_random_guardian_detect_suppresses_ignored_names_and_scene_errors():
    with PlantWorld() as world:
        world.guardian.configure(event_bot())
        world.after_event = events.Event('dialog', 'frog')
        assert world.guardian.detect() is None
        assert world.guardian.grind_targets == ['zombie']
        assert world.guardian.lamp_skill == 'mining'
        world.detection_fails = True
        assert world.guardian.detect() is None


def test_random_guardian_detect_resumes_at_cooldown_expiry():
    with PlantWorld() as world:
        world.after_event = events.Event('pick', 'strange plant')
        world.guardian.cooldown_until['pick:strange plant'] = 1000
        assert world.guardian.detect() is None
        world.now = 1000
        assert world.guardian.detect() is world.after_event


def test_random_guardian_check_runs_only_once_each_server_tick():
    with PlantWorld() as world:
        world.after_event = events.Event('pick', 'strange plant')
        bot = event_bot()
        assert world.guardian.check(bot) is world.after_event
        assert world.guardian.check(bot) is None
        world.now = 600
        assert world.guardian.check(bot) is world.after_event


def test_random_guardian_pending_caches_until_next_tick():
    with PlantWorld() as world:
        bot = event_bot()
        assert world.guardian.pending(bot) is False
        world.after_event = events.Event('pick', 'strange plant')
        assert world.guardian.pending(bot) is False
        world.now = 600
        assert world.guardian.pending(bot) is True
        world.after_event = None
        assert world.guardian.pending(bot) is True
        world.now = 1200
        assert world.guardian.pending(bot) is False


def test_random_guardian_active_solver_suppresses_check_and_pending():
    with PlantWorld() as world:
        world.guardian.handling = True
        world.after_event = events.Event('pick', 'strange plant')
        assert world.guardian.check(None) is None
        assert world.guardian.pending(None) is False
        assert world.guardian._last_tick == -1 and world.guardian._pending_tick == -1
