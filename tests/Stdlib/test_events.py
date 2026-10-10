from helpers import raises
from rs2004 import events as event_module


def test_subscribing_lists_the_event_as_listened_to():
    events.clear()
    seen = []
    unsubscribe = events.on('tick', lambda e: seen.append(e.tick))
    assert 'tick' in _listening

    for callback in events.subscribers('tick'):
        callback(*event_module.make_args('tick', (7,)))
    assert seen == [7]

    unsubscribe()
    assert events.subscribers('tick') == []
    assert 'tick' not in _listening


def test_unknown_events_are_refused():
    assert 'is not an event' in raises(ValueError, lambda: events.on('on_tick', lambda e: None))
    assert 'callable' in raises(TypeError, lambda: events.on('tick', 5))


def test_rs2b0t_events_pass_one_payload():
    (xp,) = event_module.make_args('skill_xp', (8, 25, 25))
    assert (xp.skill, xp.name, xp.xp, xp.delta) == (8, 'woodcutting', 25, 25)

    (runecraft,) = event_module.make_args('skill_level', (20, 2, 1))
    assert (runecraft.name, runecraft.level, runecraft.previous) == ('runecraft', 2, 1)

    (slot,) = event_module.make_args('inventory_changed', (0, 1511, 'Logs', 1, -1, 0))
    assert (slot.slot, slot.id, slot.name, slot.count, slot.previous_id, slot.previous_count) == (0, 1511, 'Logs', 1, -1, 0)


def test_other_events_pass_their_values():
    assert event_module.make_args('npc_damaged', ('npc', 3)) == ('npc', 3)
