"""Seed preparation; selected targets stay unstarted, with explicit quest prerequisites."""

import json
import _core
from rs2004 import execution
from rs2004.bank import bank
from rs2004.game import chat, game
from rs2004.tabs import quests
from rs2004.quests.data import quest_record
from rs2004.quests.journal_text import normalize_journal
from seed_helpers import send, stash
from phase17i_cases import CASES, prerequisite_flags, initial_points, preparation_flags, preparation_items

QUEST_IDS = list(CASES.values())
started = False


def loop():
    global started
    if started:
        return 600
    started = True
    yield from execution.delay_ticks(5)
    kind = settings.get('kind')
    target = settings.get('target')
    targets = [target]
    assert all([id in QUEST_IDS for id in targets]), 'unknown phase 17i quest'
    assert kind in CASES and CASES[kind] == target, 'unknown phase 17i case'
    assert quests.points() == 0, 'fresh character must have zero quest points'
    for id in targets:
        assert quests.status(quest_record(id).name) == 'not_started', 'quest must be unstarted: ' + id
    yield from send('tele 0,50,53,5,8')
    yield from stash()
    for name, level in [('attack', 75), ('strength', 75), ('defence', 75), ('hitpoints', 85), ('prayer', 70), ('magic', 70), ('mining', 70), ('smithing', 70), ('cooking', 70), ('crafting', 70), ('fishing', 70), ('woodcutting', 70), ('firemaking', 70), ('thieving', 70), ('agility', 70), ('ranged', 70), ('herblore', 70), ('fletching', 70)]:
        yield from send('setstat ' + name + ' ' + str(level))
    # Ordinary supplies only; target-specific quest items must be obtained live.
    supplies = ['coins 1000000', 'cert_lobster 1000', 'cert_3doseprayerrestore 100', 'rune_chainbody 1', 'rune_platelegs 1', 'rune_longsword 1',
                'iron_chainbody 1', 'bronze_med_helm 1', 'bronze_pickaxe 1', 'bronze_axe 1', 'knife 1',
                'tinderbox 1', 'hammer 1', 'shears 1', 'spade 1', 'bucket_empty 1', 'pot_empty 1',
                'mindrune 2000', 'airrune 4000', 'firerune 6000']
    for item in supplies:
        yield from send('give ' + item)
    yield from stash()
    # Stash the ordinary loadout before adding case-specific preparation.
    for symbol, name, count in preparation_items(target):
        yield from send('give ' + symbol + ' ' + str(count))
    if preparation_items(target):
        yield from stash()
    chat.command('~bank')
    ok = yield from execution.delay_until(bank.is_open, 8000)
    assert ok, 'verification bank absent'
    ok = yield from bank.wait_ready()
    assert ok, 'verification bank contents absent'
    for name, count in [('Coins', 1000000), ('Lobster', 1000), ('Prayer potion(3)', 100), ('Rune chainbody', 1), ('Rune platelegs', 1), ('Rune longsword', 1), ('Iron chainbody', 1), ('Bronze med helm', 1), ('Mind rune', 2000), ('Air rune', 4000), ('Fire rune', 6000), ('Bucket', 1), ('Pot', 1), ('Hammer', 1), ('Shears', 1), ('Spade', 1), ('Knife', 1), ('Tinderbox', 1), ('Bronze pickaxe', 1), ('Bronze axe', 1)]:
        assert bank.count(name) >= count, 'missing seeded supply: ' + name
    for symbol, name, count in preparation_items(target):
        assert bank.count(name) >= count, 'missing preparation item: ' + name
    yield from bank.close()
    for id in targets:
        assert quests.status(quest_record(id).name) == 'not_started', 'preparation changed quest: ' + id
    assert quests.points() == 0, 'ordinary preparation must not award quest points'
    flags = prerequisite_flags(target)
    for id, variable, value in flags:
        assert id not in targets, 'must never seed the target quest'
        yield from send('setvar ' + variable + ' ' + str(value))
    for variable, value in preparation_flags(target):
        yield from send('setvar ' + variable + ' ' + str(value))
    if flags:
        yield from send('setvar qp ' + str(initial_points(target)))
    assert quests.points() == initial_points(target), 'prerequisite quest points mismatch'
    for id, variable, value in flags:
        # setvar updates the server flag, but list colours refresh only on login.
        _core.close_interfaces()
        closed = yield from execution.delay_until(lambda: _core.get_main_modal() == -1, 8000)
        assert closed, 'previous interface did not close'
        yield from execution.delay_ticks(2)
        lines = yield from quests.journal(quest_record(id).name)
        log('SEED prerequisite journal', id, lines)
        assert 'quest complete!' in normalize_journal(lines), 'prerequisite journal not complete: ' + id
        _core.close_interfaces()
        yield from execution.delay_ticks(2)
    assert quests.status(quest_record(target).name) == 'not_started', 'target changed during prerequisite setup'
    tick = game.tick()
    start = _core.step_time()
    yield from execution.delay_ticks(20)
    elapsed = _core.step_time() - start
    log('TICK_PROBE', game.tick() - tick, elapsed)
    assert 11000 <= elapsed <= 15000, 'expected normal 600 ms server ticks'
    log('E2E_SEEDED ' + json.dumps({'case': kind, 'name': game.my_name(), 'passed': True, 'quests': targets, 'seeded_prerequisites': [row[0] for row in flags], 'expected_initial_qp': initial_points(target), 'qp': quests.points(), 'tile': str(game.tile())}))
    stop_account()
    return 600
