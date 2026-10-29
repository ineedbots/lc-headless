"""Lever messages, room crossings and bounded maze recovery drive the oil-can leg."""

import rs2004.quests.defs.ernest.basement as basement
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


class BasementWorld(QuestWorld):
    def __enter__(self):
        QuestWorld.__enter__(self)
        self.install(basement)
        self.patch(basement, 'sustain', FakeModule(run=lambda: self.reply()))
        self.patch(basement, 'executed', 0)
        return self


def test_ernest_lever_retries_until_message_confirms_wanted_position():
    for mode in ['walk_failed', 'missing', 'refused', 'silent', 'down']:
        with BasementWorld() as w:
            w.position = basement.LEVER_TILE.A
            lever = QuestObject(w, 'Lever A', ops=['Pull'],
                                effect=lambda: w.messages.append('You pull lever A down.'))
            lever.accept = mode != 'refused'
            w.scene = [] if mode == 'missing' else [lever]
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            assert w.run(basement.set_lever('A', 'down', w.logs.append)) == (mode == 'down')


def test_ernest_door_crossing_distinguishes_locked_unanswered_and_new_room():
    move = basement.cross('4to7', 'far')
    for mode in ['already', 'walk_failed', 'missing', 'refused', 'silent', 'locked', 'crossed']:
        with BasementWorld() as w:
            w.position = move.arrive if mode == 'already' else move.stand
            door = QuestObject(w, 'Door', ops=['Open'], at=move.stand)
            door.effect = (lambda: w.messages.append('This door is locked')) if mode == 'locked' else (lambda: setattr(w, 'position', move.arrive))
            door.accept = mode != 'refused'
            w.scene = [] if mode == 'missing' else [door]
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            expected = 'crossed' if mode in ['already', 'crossed'] else ('locked' if mode == 'locked' else 'failed')
            assert w.run(basement.cross_door(move, w.logs.append)) == expected


def test_ernest_basement_and_alcove_exits_require_reach_proof():
    for mode in ['outside', 'stranded', 'walk_failed', 'reach_failed', 'left']:
        with BasementWorld() as w:
            w.position = Tile(3000, 3000) if mode == 'outside' else Tile(3102, 9750)
            if mode == 'stranded':
                w.position = Tile(3102, 9765)
            def reach(name, op, at, expect, **kw):
                yield from w.reply()
                if mode == 'left':
                    w.position = Tile(3100, 3350)
                return 'done' if mode == 'left' else 'failed'
            w.patch(basement, 'reach', FakeModule(loc_op=reach))
            w.can_walk = mode != 'walk_failed'
            assert w.run(basement.leave_basement(w.logs.append)) == (mode in ['outside', 'left'])
            w.position = basement.EC_TILE.ALCOVE_LEVER
            assert w.run(basement.leave_alcove(w.logs.append)) == (mode == 'left')


def test_ernest_basement_entry_requires_reachable_ladder_and_region_change():
    for mode in ['already', 'walk_failed', 'reach_failed', 'entered']:
        with BasementWorld() as w:
            if mode == 'already':
                w.position = Tile(3102, 9750)
            w.can_walk = mode != 'walk_failed'
            entered = lambda: setattr(w, 'position', Tile(3102, 9750))
            w.patch(basement, 'reach', FakeModule(loc_op=lambda *a, **kw: w.reply(
                'done' if mode == 'entered' else 'failed', entered if mode == 'entered' else None)))
            assert w.run(basement.enter_basement(w.logs.append)) == (mode in ['already', 'entered'])


def test_ernest_oil_can_pickup_requires_item_arrival():
    for mode in ['walk_failed', 'missing', 'refused', 'silent', 'taken']:
        with BasementWorld() as w:
            can = QuestObject(w, basement.EC_NAME.OIL_CAN, at=basement.EC_TILE.OIL_CAN_SPAWN,
                              effect=lambda: w.hold(basement.EC_NAME.OIL_CAN, id=basement.EC_ID.OIL_CAN))
            can.accept = mode != 'refused'
            w.scene = [] if mode == 'missing' else [can]
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            assert w.run(basement.take_oil_can(w.logs.append)) == (mode == 'taken')


def test_ernest_oil_can_chain_unwinds_failed_prefix_and_stops_after_three_passes():
    for mode in ['held', 'cannot_leave', 'cannot_enter', 'move_failed', 'no_can', 'taken']:
        with BasementWorld() as w:
            moves = []
            if mode == 'held':
                w.hold('Oil can', id=basement.EC_ID.OIL_CAN)
            w.patch(basement, 'leave_manor_basement', lambda *a: w.reply(True))
            w.patch(basement, 'leave_basement', lambda *a: w.reply(mode != 'cannot_leave'))
            w.patch(basement, 'enter_basement', lambda *a: w.reply(mode != 'cannot_enter'))
            def move(leg, log):
                moves.append(leg.kind)
                yield from w.reply()
                return mode != 'move_failed' or len(moves) % 3 != 0
            w.patch(basement, 'run_move', move)
            def take(log):
                yield from w.reply()
                if mode == 'taken':
                    w.hold('Oil can', id=basement.EC_ID.OIL_CAN)
                return mode == 'taken'
            w.patch(basement, 'take_oil_can', take)
            assert w.run(basement.fetch_oil_can(w.logs.append)) == (mode in ['held', 'taken'])
            if mode == 'no_can':
                assert len(moves) == 3 * len(basement.CHAIN) * 2
                assert basement.executed == 0


def test_ernest_move_dispatch_and_combined_exit_handle_room_nine_and_stranding():
    with BasementWorld() as w:
        w.patch(basement, 'set_lever', lambda *a: w.reply(True))
        w.patch(basement, 'cross_door', lambda *a: w.reply('failed'))
        assert w.run(basement.run_move(basement.CHAIN[0], w.logs.append))
        assert not w.run(basement.run_move(basement.CHAIN[2], w.logs.append))
        basement.executed = 3
        w.run(basement.unwind(w.logs.append))
        assert basement.executed == 3 and 'unwind stalled' in w.logs[-1]
        w.position = Tile(3092, 9755)
        assert not w.run(basement.leave_manor_basement(w.logs.append))
        w.position = Tile(3000, 3000)
        assert w.run(basement.leave_manor_basement(w.logs.append))
