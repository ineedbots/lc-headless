"""Strike preparation safely removes armour and handles failed or interrupted casts."""

import rs2004.quests.strike_combat as strike
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


def test_strike_readiness_waits_for_retaliation_and_autocast_before_removing_armour():
    for mode in ['retaliation', 'tab', 'autocast', 'no_room', 'ready']:
        with QuestWorld() as w:
            w.install(strike)
            removed = []
            w.patch(strike, 'game', FakeModule(set_auto_retaliate=lambda on: None,
                auto_retaliate_on=lambda: mode == 'retaliation', open_side_tab=lambda n: w.reply(mode != 'tab')))
            w.patch(strike, 'autocast', FakeModule(armed=lambda: True, disarm=lambda: w.reply(mode != 'autocast')))
            def unequip(name):
                removed.append(name)
                yield from w.reply()
                return mode != 'no_room'
            w.patch(strike, 'equipment', FakeModule(items=lambda: [FakeModule(name='Wizard robe'),
                FakeModule(name=''), FakeModule(name='Iron platebody')], unequip=unequip))
            rune = QuestObject(w, 'Mind rune')
            rune.count = 1000
            air = QuestObject(w, 'Air rune')
            air.count = 1000
            w.pack = [rune, air]
            assert w.run(strike.ready_strikes(w.logs.append)) == (mode == 'ready')
            assert removed == (['Iron platebody'] if mode in ['ready', 'no_room'] else [])


def test_strike_cover_validates_lane_and_stops_for_event_or_failed_walk():
    with QuestWorld() as w:
        w.install(strike)
        w.patch(strike, 'sustain', FakeModule(run=lambda: w.reply()))
        w.position = strike.ARENA_COVER
        assert w.run(strike.take_strike_cover(strike.ARENA_COVER, w.logs.append))
        w.interrupted = True
        assert not w.run(strike.take_strike_cover(Tile(3000, 3000), w.logs.append))
        w.interrupted = False
        w.can_walk = False
        assert not w.run(strike.take_strike_cover(Tile(3000, 3000), w.logs.append))
        assert not strike.cast_from_cover(strike.ARENA_COVER, QuestObject(w, 'Target', at=Tile(2594, 3168)))
        assert not strike.cast_from_cover(strike.EXPERIMENT_COVER, QuestObject(w, 'Target', at=Tile(2937, 3467)))


def test_strike_watch_rejected_interrupted_and_silent_casts_never_settle():
    for mode in ['rejected', 'event', 'silent']:
        with QuestWorld() as w:
            w.install(strike)
            w.position = Tile(3000, 3000)
            target = QuestObject(w, 'Target', at=Tile(3002, 3000))
            w.patch(strike, 'sustain', FakeModule(run=lambda: w.reply()))
            w.patch(strike, 'game', FakeModule(tile=lambda: w.position, cast_on_npc=lambda *a: mode != 'rejected',
                auto_retaliate_on=lambda: False, set_auto_retaliate=lambda on: None))
            w.patch(strike, 'autocast', FakeModule(armed=lambda: False))
            w.interrupted = mode == 'event'
            state = strike._Cast()
            assert not w.run(strike._cast_and_watch(w.position, target, 'Wind Strike', 0, state))
            assert not state.settled
            assert strike._same_npc(target) is None
