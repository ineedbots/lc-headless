"""Trail banking retries incomplete transfers and restores prayer and stripped equipment."""

import rs2004.clues.solve as solve
import rs2004.clues.guardian as guardian
from rs2004.clues.teleports import TeleportKit
from rs2004.geometry import Tile
from helpers import FakeModule
from clue_world import ClueWorld
from quest_world import QuestObject


def solver(w):
    return solve.SolveClue(solve.SolveClueHost(log=w.logs.append, set_status=lambda m: w.logs.append(m),
        food_name=lambda: '', food_withdraw=lambda: 0, is_food=lambda i: False))


def test_trail_teleport_runes_stock_to_target_or_stop_on_refused_and_silent_transfer():
    for mode in ['stocked', 'refused', 'silent']:
        with ClueWorld() as w:
            w.install(solve)
            bot = solver(w)
            w.bank_item('Law rune', 100)
            w.accept_bank = mode != 'refused'
            w.respond = mode != 'silent'
            kit = TeleportKit([('Law rune', 1)], [], ['varrock'])
            w.run(bot._stock_teleports(kit))
            assert w.count('Law rune') == (solve.teleport_rune_target(1) if mode == 'stocked' else 0)
            assert bot._describe_teleports(kit).startswith('1/1' if mode == 'stocked' else '0/1')


def test_trail_gear_restore_handles_no_bank_refused_open_unready_and_failed_close():
    for mode in ['no_bank', 'walk_failed', 'open_failed', 'not_ready', 'close_failed']:
        with ClueWorld() as w:
            w.install(solve)
            bot = solver(w)
            bot.stripped_gear = ['Iron sword']
            w.bank_item('Iron sword')
            near = {'tile': {'x': 3000, 'z': 3000, 'level': 0}, 'name': 'Test'}
            w.patch(solve, 'nearest_bank', lambda t: None if mode == 'no_bank' else near)
            w.patch(solve, 'walk_to_bank', lambda *a: w.reply(mode != 'walk_failed'))
            w.patch(solve, 'open_clue_bank', lambda *a: w.reply(mode != 'open_failed'))
            w.bank_ready = mode != 'not_ready'
            if mode == 'close_failed':
                # The withdrawal lands; the subsequent close is refused.
                w.on_update = lambda: setattr(w, 'accept_bank', False) if w.count('Iron sword') else None
            assert not w.run(bot._restore_stripped_gear())
            assert bot.stripped_gear == ['Iron sword']


def test_trail_jungle_stock_checks_ready_bank_notes_and_missing_machete():
    with ClueWorld() as w:
        w.install(solve)
        bot = solver(w)
        w.bank_open = False
        assert w.run(bot._stock_jungle_kit()) == 'retry'
        w.bank_open = True
        w.patch(solve, 'held_axe', lambda: 'Bronze axe')
        w.patch(solve, 'has_jungle_map', lambda: False)
        assert w.run(bot._stock_jungle_kit()) == 'missing'
        w.bank_item(solve.MACHETE)
        w.bank_item(solve.RADIMUS_NOTES)
        w.patch(solve, 'jungle_kit_missing', lambda: [])
        assert w.run(bot._stock_jungle_kit()) == 'ready'
        assert w.count(solve.RADIMUS_NOTES) == 1


def test_trail_bank_first_handles_no_known_bank_and_failed_access():
    for hard in [False, True]:
        with ClueWorld() as w:
            w.install(solve)
            bot = solver(w)
            bot.hard_trail = hard
            w.patch(solve, 'nearest_bank', lambda t: None)
            assert w.run(bot._bank_first()) == (not hard)
            assert not w.run(bot._bank_first(rebuild=True))
            w.patch(solve, 'open_clue_bank', lambda *a: w.reply(False))
            assert not w.run(bot._bank_first(True))


def test_trail_bank_first_refuses_to_continue_when_loot_remains_in_pack():
    with ClueWorld() as w:
        w.install(solve)
        bot = solver(w)
        w.hold('Loot')
        w.hold('Clue scroll', id=list(solve.CLUE_DB.keys())[0])
        w.patch(solve, 'open_clue_bank', lambda *a: w.reply(True))
        w.patch(solve, 'world_state', lambda: {})
        w.patch(solve, 'teleport_kit_for', lambda state: TeleportKit([], [], []))
        w.bank.deposit_all_matching = lambda predicate: w.reply(True)
        assert not w.run(bot._bank_first(True))
        assert bot.status == 'bank preparation blocked' and w.count('Loot') == 1


def test_trail_prayer_topup_handles_missing_altar_failed_walk_and_restore():
    for mode in ['no_altar', 'walk_failed', 'restored']:
        with ClueWorld() as w:
            w.install(solve)
            bot = solver(w)
            state = FakeModule(points=5)
            w.patch(solve, 'prayer', FakeModule(max=lambda: 50, full=lambda: state.points == 50, points=lambda: state.points))
            altar = FakeModule(name='Test', tile=w.position, loc='Altar')
            w.patch(solve, 'nearest_altar', lambda t: None if mode == 'no_altar' else altar)
            w.can_walk = mode != 'walk_failed'
            w.scene = [QuestObject(w, 'Altar', ops=[solve.ALTAR_OP], effect=lambda: setattr(state, 'points', 50))]
            hard_id = [id for id, row in solve.CLUE_DB.items() if solve._is_hard(id)][0]
            w.run(bot._top_up_prayer(hard_id))
            assert state.points == (50 if mode == 'restored' else 5)


def test_guardian_ranged_equipping_stops_on_failed_close_missing_weapon_or_ack():
    ranged = FakeModule(weapon='Magic shortbow', ammo='Rune arrow', quantity=100)
    for mode in ['close_failed', 'missing_weapon', 'weapon_refused', 'weapon_silent', 'ammo_refused', 'ammo_silent']:
        with ClueWorld() as w:
            w.install(guardian)
            w.accept_bank = mode != 'close_failed'
            w.bank_open = mode == 'close_failed'
            id = guardian.ranged_weapon_id(ranged.weapon)
            weapon = w.hold(ranged.weapon, id=id)
            if mode == 'missing_weapon':
                w.pack = []
            weapon.accept = mode != 'weapon_refused'
            if mode in ['ammo_refused', 'ammo_silent']:
                w.pack = []
                w.worn = [weapon]
                ammo = w.hold(ranged.ammo, 100)
                ammo.accept = mode != 'ammo_refused'
            assert not w.run(guardian.equip_guardian_weapon(ranged))


def test_guardian_supply_stock_rejects_unready_missing_dose_and_unacknowledged_dose():
    with ClueWorld() as w:
        w.install(guardian)
        w.bank_ready = False
        assert not w.run(guardian.stock_hard_supplies(0, []))
        w.bank_ready = True
        assert not w.run(guardian.stock_hard_supplies(0, []))
        w.bank_item(guardian.SUPERANTI[0]['name'], id=guardian.SUPERANTI[0]['id'])
        w.respond = False
        assert not w.run(guardian.stock_hard_supplies(0, []))


def test_guardian_weapon_stock_requires_a_ready_bank_and_a_real_weapon():
    with ClueWorld() as w:
        w.install(guardian)
        w.bank_ready = False
        assert not w.run(guardian.stock_hard_weapon(False, lambda n: None))
        w.bank_ready = True
        w.patch(guardian, 'hard_clue_kit', lambda *a: 'ready')
        w.patch(guardian, 'quests', FakeModule(status=lambda n: 'complete'))
        assert not w.run(guardian.stock_hard_weapon(False, lambda n: None))
        assert not w.run(guardian.equip_guardian_weapon())
        remembered = []
        w.worn = [QuestObject(w, 'Iron scimitar', 1323)]
        for name in ['Imaginary bow', 'Magic shortbow']:
            ranged = FakeModule(weapon=name, ammo='Rune arrow', quantity=100)
            assert not w.run(guardian.stock_hard_weapon(False, remembered.append, ranged=ranged))
        assert remembered == ['Iron scimitar', 'Iron scimitar']
        w.patch(guardian, 'hard_clue_kit', lambda *a: 'not ready')
        protection = guardian.GuardianProtection('Saradomin Wizard')
        assert protection._dose() is None
        assert not w.run(protection.prepare())
