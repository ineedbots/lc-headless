"""Seed preparation; selected targets stay unstarted, with no quest progress or completed prerequisites."""

import json
from rs2004 import execution
from rs2004.bank import bank
from rs2004.game import chat, game
from rs2004.tabs import quests
from rs2004.quests.data import quest_record
from seed_helpers import send, stash
from phase17b_cases import CASES

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
    assert all([id in QUEST_IDS for id in targets]), 'unknown phase 17b quest'
    assert kind in CASES and CASES[kind] == target, 'unknown phase 17b case'
    assert quests.points() == 0, 'fresh character must have zero quest points'
    for id in targets:
        assert quests.status(quest_record(id).name) == 'not_started', 'quest must be unstarted: ' + id
    yield from send('tele 0,50,53,5,8')
    yield from stash()
    for name, level in [('attack', 75), ('strength', 75), ('defence', 75), ('hitpoints', 85), ('prayer', 70), ('magic', 60), ('mining', 40), ('smithing', 40), ('cooking', 50), ('crafting', 40), ('fishing', 40), ('woodcutting', 40), ('firemaking', 40), ('thieving', 40), ('agility', 40)]:
        yield from send('setstat ' + name + ' ' + str(level))
    # Equipment and consumables only. No quest keys, cage, orb, mould, amulet,
    # urn, candle, Dramen staff, objective supplies or barcrawl card are seeded.
    supplies = ['coins 1000000', 'cert_lobster 1000', 'cert_3doseprayerrestore 100', 'rune_chainbody 1', 'rune_platelegs 1', 'rune_longsword 1',
                'iron_chainbody 1', 'bronze_med_helm 1', 'bronze_pickaxe 1', 'bronze_axe 1', 'knife 1',
                'tinderbox 1', 'hammer 1', 'shears 1', 'spade 1', 'bucket_empty 1', 'pot_empty 1',
                'mindrune 2000', 'airrune 4000', 'firerune 6000']
    for item in supplies:
        yield from send('give ' + item)
    yield from stash()
    chat.command('~bank')
    ok = yield from execution.delay_until(bank.is_open, 8000)
    assert ok, 'verification bank absent'
    ok = yield from bank.wait_ready()
    assert ok, 'verification bank contents absent'
    for name, count in [('Coins', 1000000), ('Lobster', 1000), ('Prayer potion(3)', 100), ('Rune chainbody', 1), ('Rune platelegs', 1), ('Rune longsword', 1), ('Iron chainbody', 1), ('Bronze med helm', 1), ('Mind rune', 2000), ('Air rune', 4000), ('Fire rune', 6000), ('Bucket', 1), ('Pot', 1), ('Hammer', 1), ('Shears', 1), ('Spade', 1), ('Knife', 1), ('Tinderbox', 1), ('Bronze pickaxe', 1), ('Bronze axe', 1)]:
        assert bank.count(name) >= count, 'missing seeded supply: ' + name
    yield from bank.close()
    for id in targets:
        assert quests.status(quest_record(id).name) == 'not_started', 'preparation changed quest: ' + id
    assert quests.points() == 0, 'ordinary preparation must not award quest points'
    log('E2E_SEEDED ' + json.dumps({'case': kind, 'name': game.my_name(), 'passed': True, 'quests': targets, 'seeded_prerequisites': [], 'expected_initial_qp': 0, 'qp': quests.points(), 'tile': str(game.tile())}))
    stop_account()
    return 600
