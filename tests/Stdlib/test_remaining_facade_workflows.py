"""Duel helper lifecycle and recovery errors preserve their caller's state."""

import rs2004.duel as arena
import rs2004.karamja_recovery as recovery
import rs2004.traversal as routes
import rs2004.quests.exec.primitives as primitives
import rs2004.catalogs.partner as partner
from rs2004 import execution
from helpers import FakeModule
from coverage_world import PatchWorld
from test_duel_workflows import DuelWorld, Player
from test_handoff_edge_workflows import MeetingWorld, Item


def test_duel_helper_lobby_challenges_active_handshake_and_win_close():
    with DuelWorld() as world:
        helper = arena.ClueDuelHelper('Alice', world.logs.append)
        assert helper.validate() and helper.label == 'clue duel helper'
        assert world.run(helper.execute()) is None
        world.mode = 'win'
        world.run(helper.execute())
        assert world.mode is None
        world.scene = [Player(world, 'Alice')]
        world.run(helper.execute())
        assert world.challenges[-1][0] == 'Alice'
        assert arena.duel.fight(world.scene[0])
        assert world.challenges[-1][1] == arena.FIGHT_OP
        assert 'DuelOffers' in repr(arena.duel.offers())


def test_duel_helper_walks_to_lobby_and_tracks_pen_deadline():
    with DuelWorld() as world:
        with PatchWorld() as patch:
            calls = []
            def walk(tile, **kwargs):
                calls.append(tile)
                yield execution.Ticks(1)
                return True
            patch.patch(arena, 'traversal', FakeModule(walk_resilient=walk))
            helper = arena.ClueDuelHelper('Alice', world.logs.append)
            world.mode, world.position = None, Tile(0, 0)
            world.run(helper.execute())
            assert calls == [arena.CLUE_DUEL_LOBBY]
            patch.patch(arena, 'fight_arena_at', lambda tile: True)
            world.run(helper.execute())
            assert helper.entered_at == world.now
            world.now += 180000
            patch.patch(arena, 'locs', FakeModule(query=lambda: FakeModule(action=lambda name: FakeModule(nearest=lambda: None))))
            world.run(helper.execute())
            assert 'forfeiting' in world.logs[-1]


def test_duel_closed_confirm_cannot_toggle_obstacles():
    with DuelWorld() as world:
        world.mode = 'confirm'
        assert arena.duel.partner() is None and not arena.duel.toggle_obstacles()
        world.mode = 'offer'
        with PatchWorld() as patch:
            patch.patch(arena, '_core', FakeModule(get_main_modal=lambda: 200,
                get_texts=lambda root: ['Dueling with: Alice'], find_components=lambda *args: []))
            assert not arena.duel.toggle_obstacles()


def test_boat_fare_failed_walk_or_conversation_returns_failure():
    for walk_ok in [True, False]:
        with PatchWorld() as world:
            def walk(tile, **kwargs):
                yield execution.Ticks(1)
                return walk_ok
            def talk(name, prefer, log):
                yield execution.Ticks(1)
                return False
            world.patch(routes, 'traversal', FakeModule(walk_to=walk))
            world.patch(primitives, 'talk_strict', talk)
            world.patch(recovery, 'event_signal', FakeModule(pending=lambda: False))
            assert world.run(recovery._earn(world.logs.append)) is False


def test_catalog_handoff_closes_unrelated_modal_before_meeting():
    with MeetingWorld() as world:
        calls = []
        def close():
            calls.append('closed')
            yield execution.Ticks(1)
        world.patch(partner, 'modals', FakeModule(main=lambda: 100, close=close))
        world.theirs = [Item(989, 'Key', 1, [])]
        assert world.handoff(False) and calls == ['closed']


def test_catalog_open_trade_times_out_without_partner():
    with MeetingWorld() as world:
        world.scene = []
        task = partner._open_trade('Alice', world.logs.append)
        next(task)
        world.now = partner.MEET_MS
        try:
            next(task)
        except StopIteration as stopped:
            assert stopped.value is False
        assert 'never opened' in world.logs[-1]


def test_boat_fare_interrupt_before_plantation_walk_is_noop():
    with PatchWorld() as world:
        world.patch(recovery, 'event_signal', FakeModule(pending=lambda: True))
        assert world.run(recovery._earn(world.logs.append)) is False
        assert world.waits == []
