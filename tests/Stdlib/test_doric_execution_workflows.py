"""Doric's mining and completion queue use inventory changes as their oracle."""

import rs2004.quests.defs.doric as doric
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


def test_doric_talk_at_stage_propagates_arrival_and_dialogue_failure():
    for reached, talked in [(False, False), (True, False), (True, True)]:
        with QuestWorld() as w:
            w.patch(doric, 'goto_npc', lambda *a: w.reply(reached))
            w.patch(doric, 'talk_strict', lambda *a: w.reply(talked))
            assert w.run(doric.talk_at_stage(0, 'accept job').run(w.logs.append)) == (reached and talked)


def test_doric_mines_one_ore_or_yields_to_missing_tools_respawn_and_randoms():
    for mode in ['full', 'no_pick', 'walk_failed', 'empty', 'respawn', 'event', 'refused', 'silent', 'mined']:
        with QuestWorld() as w:
            w.install(doric)
            w.position = doric.ORE_ANCHORS.Clay
            pick = QuestObject(w, 'Bronze pickaxe', 1265)
            ore = QuestObject(w, 'Clay', 434)
            rock = QuestObject(w, 'Rocks', doric.ROCK_TYPES.get('Clay')[0], ['Mine'],
                               effect=lambda: w.pack.append(ore))
            rock.accept = mode != 'refused'
            w.pack = [] if mode == 'no_pick' else [pick]
            if mode == 'full':
                w.pack += [QuestObject(w, 'Junk') for i in range(27)]
            w.scene = [rock] if mode in ['refused', 'silent', 'mined', 'event'] else []
            w.can_walk = mode != 'walk_failed'
            w.respond = mode != 'silent'
            if mode == 'event':
                rock.effect = lambda: setattr(w, 'interrupted', True)
            if mode == 'respawn':
                w.on_update = lambda: setattr(w, 'scene', [rock]) if w.now >= 2000 else None
            assert w.run(doric.mine_one('Clay', doric.DORIC_ITEM.CLAY, w.logs.append)) == (mode in ['mined', 'respawn'])
            if mode in ['mined', 'respawn']:
                assert w.count_by_id(434) == 1


def test_doric_free_pickaxe_handles_full_pack_respawn_competition_and_ack():
    for mode in ['held', 'full', 'walk_failed', 'empty', 'event', 'respawn', 'refused', 'silent', 'taken']:
        with QuestWorld() as w:
            w.install(doric)
            w.position = doric.BRONZE_PICKAXE_SPAWN
            pick = QuestObject(w, 'Bronze pickaxe', 1265, effect=lambda: w.pack.append(QuestObject(w, 'Bronze pickaxe', 1265)))
            pick.accept = mode != 'refused'
            if mode == 'held':
                w.pack = [pick]
            elif mode == 'full':
                w.pack = [QuestObject(w, 'Junk') for i in range(28)]
            w.can_walk = mode != 'walk_failed'
            w.scene = [pick] if mode in ['refused', 'silent', 'taken'] else []
            w.respond = mode != 'silent'
            w.interrupted = mode == 'event'
            if mode == 'respawn':
                w.on_update = lambda: setattr(w, 'scene', [pick]) if w.now >= 2000 else None
            assert w.run(doric.acquire_bronze_pickaxe(w.logs.append)) == (mode in ['held', 'respawn', 'taken'])


def test_doric_training_drops_only_surplus_copper_and_waits_for_it_to_leave():
    for mode in ['enough', 'refused', 'silent', 'dropped']:
        with QuestWorld() as w:
            w.install(doric)
            ore = QuestObject(w, 'Copper ore', 436)
            ore.count = 4 if mode == 'enough' else 5
            ore.effect = lambda: setattr(ore, 'count', ore.count - 1)
            ore.accept = mode != 'refused'
            w.pack = [ore]
            w.respond = mode != 'silent'
            assert w.run(doric.drop_one_copper(w.logs.append)) == (mode in ['enough', 'dropped'])
            if mode == 'dropped':
                assert w.count_by_id(436) == 4


def test_doric_handin_drains_scroll_dialogue_and_delayed_coin_reward():
    for mode in ['unreachable', 'refused', 'close_failed', 'continue_failed', 'options', 'unpaid', 'paid']:
        with QuestWorld() as w:
            w.install(doric)
            w.patch(doric, 'reader', FakeModule(modals=lambda: FakeModule(main=w.get_main_modal())))
            w.patch(doric, 'quests', FakeModule(status=lambda name: 'in_progress'))
            w.patch(doric, 'goto_npc', lambda *a: w.reply(mode != 'unreachable'))
            coins = QuestObject(w, 'Coins', 995)
            coins.count = 0
            def close_scroll():
                if mode == 'close_failed':
                    return False
                w.pending = 'page'
                return True
            w.patch(doric, '_core', FakeModule(close_interfaces=close_scroll))
            def talk(*args):
                yield from w.reply()
                if mode == 'refused':
                    return False
                w.pages = [('main', []), ('continue', ['Thank you!'])]
                if mode == 'options':
                    w.pages = [('options', ['Unexpected reward choice'])]
                return True
            w.patch(doric, 'talk_strict', talk)
            w.pack = [coins]
            w.accept_click = mode != 'continue_failed'
            if mode == 'paid':
                w.on_update = lambda: setattr(coins, 'count', 180) if w.now >= 4000 else None
            assert w.run(doric.hand_in_materials(w.logs.append)) == (mode == 'paid')
            if mode == 'paid':
                assert not w.pages and w.count_by_id(995) == 180
