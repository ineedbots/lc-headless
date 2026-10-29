"""Vampire Slayer verifies stairs, food, beer and Count Draynor's completion."""

import rs2004.quests.defs.vampireslayer as vs
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


def test_vampire_stairs_require_an_accepted_click_and_floor_change():
    for run, start, stand, name, op, dest in [
        (vs.leave_morgan_upper, vs.MORGAN_STAIRS_TOP, vs.MORGAN_STAIRS_TOP, 'Staircase', 'Climb-down', Tile(3100, 3266)),
        (vs.enter_crypt, Tile(3100, 3350), vs.MANOR_STAIRS_DOWN, 'Stairs', 'Walk-Down', vs.CRYPT_ARRIVAL),
        (vs.leave_crypt, vs.CRYPT_ARRIVAL, vs.CRYPT_STAIRS_UP, 'Stairs', 'Walk-Up', vs.MANOR_STAIRS_DOWN)]:
        for mode in ['walk_failed', 'missing', 'refused', 'silent', 'crossed']:
            with QuestWorld() as w:
                w.install(vs)
                w.position = start
                obj = QuestObject(w, name, ops=[op], at=stand, effect=lambda: setattr(w, 'position', dest))
                obj.accept = mode != 'refused'
                w.scene = [] if mode in ['missing', 'walk_failed'] else [obj]
                w.can_walk = mode != 'walk_failed'
                w.respond = mode != 'silent'
                assert w.run(run(w.logs.append)) == (mode == 'crossed')
    with QuestWorld() as w:
        w.install(vs)
        assert w.run(vs.leave_morgan_upper(w.logs.append))
        assert w.run(vs.leave_crypt(w.logs.append))
        w.position = vs.CRYPT_ARRIVAL
        assert w.run(vs.enter_crypt(w.logs.append))


def test_vampire_beer_purchase_requires_inventory_gain():
    for mode in ['held', 'walk_failed', 'refused', 'silent', 'bought']:
        with QuestWorld() as w:
            w.install(vs)
            if mode == 'held':
                w.hold(vs.ITEM.BEER)
            w.can_walk = mode != 'walk_failed'
            received = lambda: w.hold(vs.ITEM.BEER)
            w.patch(vs, 'talk_through', lambda *a: w.reply(mode != 'refused', received if mode == 'bought' else None))
            assert w.run(vs.buy_beer(w.logs.append)) == (mode in ['held', 'bought'])


def test_vampire_eating_requires_a_supported_food_and_inventory_or_hp_change():
    for mode in ['missing', 'refused', 'silent', 'eaten']:
        with QuestWorld() as w:
            w.install(vs)
            food = QuestObject(w, vs.food_names()[0], ops=['Eat'], effect=lambda: setattr(w, 'pack', []))
            food.accept = mode != 'refused'
            w.pack = [] if mode == 'missing' else [food]
            w.respond = mode != 'silent'
            assert w.run(vs.eat_food()) == (mode == 'eaten')


def test_count_fight_handles_missing_coffin_refusal_respawn_and_delayed_completion():
    for mode in ['outside', 'walk_failed', 'no_coffin', 'coffin_refused', 'no_count', 'attack_refused', 'despawn', 'complete', 'timeout']:
        with QuestWorld() as w:
            w.install(vs)
            w.patch(vs, '_core', w)
            state = FakeModule(complete=False, hp=.5 if mode == 'complete' else 1)
            w.patch(vs, 'skills', FakeModule(hp_fraction=lambda: state.hp, effective=lambda n: 10))
            w.patch(vs, 'quests', FakeModule(status=lambda n: 'complete' if state.complete else 'in_progress'))
            w.patch(vs, 'prayer_upkeep', lambda: w.reply(False))
            w.position = Tile(3100, 3350) if mode == 'outside' else vs.CRYPT_ARRIVAL
            w.can_walk = mode not in ['outside', 'walk_failed']
            count = QuestObject(w, 'Count Draynor', vs.COUNT_DRAYNOR_ID, ['Attack'], at=vs.COFFIN)
            count.accept = mode != 'attack_refused'
            if mode == 'complete':
                count.effect = lambda: setattr(state, 'complete', True)
                w.hold(vs.food_names()[0]).ops = ['Eat']
            elif mode == 'despawn':
                count.effect = lambda: setattr(w, 'scene', [])
            coffin = QuestObject(w, 'Coffin', vs.COFFIN_CLOSED_ID, ['Open'], at=vs.COFFIN,
                                 effect=lambda: setattr(w, 'scene', [count]))
            coffin.accept = mode != 'coffin_refused'
            w.scene = [] if mode == 'no_coffin' else [coffin]
            w.respond = mode != 'no_count'
            assert w.run(vs.fight_count(w.logs.append)) == (mode == 'complete'), (mode, w.logs)
