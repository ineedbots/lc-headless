"""Patrolling Hans and the mountain pilot yield safely to interruption, combat and death."""

import rs2004.clues.steps as steps
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


class TalkWorld(QuestWorld):
    def __init__(self):
        QuestWorld.__init__(self)
        self.hp = 20
        self.retaliate = False
        self.running = True
        self.direct_ok = True

    def __enter__(self):
        QuestWorld.__enter__(self)
        self.install(steps)
        self.patch(steps, 'sustain', FakeModule(run=lambda: self.reply()))
        self.patch(steps, 'game', FakeModule(tile=lambda: self.position, tick=self.tick, in_combat=lambda: self.fighting,
            energy=lambda: 100, run_enabled=lambda: self.running, set_run=lambda on: setattr(self, 'running', on),
            auto_retaliate_on=lambda: self.retaliate, set_auto_retaliate=lambda on: setattr(self, 'retaliate', on)))
        self.patch(steps, 'skills', FakeModule(effective=lambda n: self.hp))
        self.patch(steps, 'direct_navigator', FakeModule(walk=lambda t: self.direct_ok))
        self.patch(steps, 'primitives', FakeModule(drive_dialog=lambda *a: self.reply(True),
                                                  talk_through=lambda *a: self.reply(True)))
        return self


def test_hans_dialogue_handles_interruption_refused_talk_and_already_consumed_clue():
    with TalkWorld() as w:
        w.position = steps.HANS_WAIT_SPOT
        hans = QuestObject(w, 'Hans', ops=['Talk-to'])
        w.scene = [hans]
        w.hold('Clue scroll', id=123)
        hans.accept = False
        assert not w.run(steps._talk(hans, 123, False, 2, w.logs.append))
        hans.accept = True
        w.on_update = lambda: setattr(w, 'pack', [])
        assert w.run(steps._talk(hans, 123, False, 2, w.logs.append))
        w.interrupted = True
        assert not w.run(steps._return_to_spot(w.walk))
        assert w.run(steps.solve_hans(123, w.walk, w.logs.append)) == 'yield'
        w.interrupted = False
        w.on_update = None
        w.direct_ok = False
        assert not w.run(steps._return_to_spot(w.walk))
        w.pages = [('continue', ['A clue for you'])]
        assert w.run(steps.solve_hans(123, w.walk, w.logs.append)) is None
        w.pages = []
        w.can_walk = False
        assert w.run(steps.solve_hans(123, w.walk, w.logs.append)) == 'yield'


def test_hans_patrol_checks_for_clue_consumption_and_dialogue_between_ticks():
    for mode in ['consumed', 'dialogue', 'interrupted']:
        with TalkWorld() as w:
            w.hold('Clue scroll', id=123)
            def update():
                if mode == 'consumed':
                    w.pack = []
                elif mode == 'dialogue':
                    w.pages = [('continue', ['Next clue'])]
                else:
                    w.interrupted = True
            w.on_update = update
            assert w.run(steps.solve_hans(123, w.walk, w.logs.append)) == ('yield' if mode == 'interrupted' else None)


def test_pilot_stops_for_retaliation_death_interruption_or_failed_approach():
    for mode in ['retaliation', 'dead', 'event', 'walk_failed', 'attacked', 'silent', 'done']:
        with TalkWorld() as w:
            w.position = steps.PILOT_APPROACH
            w.hold('Shark', 10, steps.SHARK_ID)
            w.retaliate = mode == 'retaliation'
            w.hp = 0 if mode == 'dead' else 20
            w.interrupted = mode == 'event'
            w.can_walk = mode != 'walk_failed'
            pilot = QuestObject(w, 'Gnome pilot', ops=['Talk-to'], at=steps.TALK_ANCHORS[steps.PILOT_CLUE])
            if mode == 'done':
                pilot.effect = lambda: setattr(w, 'pages', [('continue', ['Next clue'])])
            elif mode == 'attacked':
                pilot.effect = lambda: setattr(w, 'fighting', True)
            w.scene = [pilot]
            result = w.run(steps._run_pilot(w.walk, w.logs.append))
            assert result == ('dead' if mode == 'dead' else ('yield' if mode in ['retaliation', 'event', 'walk_failed', 'attacked'] else None))


def test_pilot_rechecks_health_and_event_after_approach_and_after_dialogue():
    for mode in ['dead_approach', 'event_approach', 'combat_approach', 'dead_reply', 'event_reply', 'combat_reply']:
        with TalkWorld() as w:
            w.position = steps.PILOT_APPROACH
            w.hold('Shark', 10, steps.SHARK_ID)
            pilot = QuestObject(w, 'Gnome pilot', ops=['Talk-to'], at=steps.TALK_ANCHORS[steps.PILOT_CLUE])
            w.scene = [pilot]
            def change():
                if mode.startswith('dead'):
                    w.hp = 0
                elif mode.startswith('event'):
                    w.interrupted = True
                else:
                    w.fighting = True
            if mode.endswith('approach'):
                w.on_walk = change
            else:
                pilot.effect = change
            assert w.run(steps._run_pilot(w.walk, w.logs.append)) == ('dead' if mode.startswith('dead') else 'yield')


def test_hans_talk_rechecks_final_tick_and_pilot_rejects_unsolved_box():
    for interrupted in [True, False]:
        with TalkWorld() as w:
            hans = QuestObject(w, 'Hans', ops=['Talk-to'])
            w.scene = [hans]
            w.hold('Clue scroll', id=123)
            def final_tick():
                if w.now >= 1000:
                    w.interrupted = interrupted
                    if not interrupted:
                        w.pack = []
            w.on_update = final_tick
            assert w.run(steps._talk(hans, 123, False, 1, w.logs.append)) == (not interrupted)
    with TalkWorld() as w:
        w.interrupted = True
        assert not w.run(steps._shelter(w.walk, w.logs.append))
        w.interrupted = False
        w.hold('Shark', 10, steps.SHARK_ID)
        w.hold('Puzzle box', id=steps.PILOT_PUZZLE_ID)
        w.patch(steps, 'puzzle_box', FakeModule(solve_held=lambda *a: w.reply(False)))
        assert w.run(steps._run_pilot(w.walk, w.logs.append)) == 'yield'


def test_hans_handles_dialogue_that_arrives_as_patrol_budget_expires():
    with TalkWorld() as w:
        w.hold('Clue scroll', id=123)
        w.patch(steps, 'PATROL_TICKS', 1)
        w.on_update = lambda: setattr(w, 'pages', [('continue', ['A clue for you'])]) if w.now >= 1500 else None
        assert w.run(steps.solve_hans(123, w.walk, w.logs.append)) is None
        assert w.now >= 1500
