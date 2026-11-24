"""Seed only the checkpoint and ordinary loadout for focused combat acceptance."""

import json
from rs2004 import execution
from rs2004.game import game
from rs2004.items import equipment
from seed_helpers import send, stash

started = False


def loop():
    global started
    if started:
        return 600
    started = True
    kind = settings.get('kind')
    assert kind in ['hq', 'rg', 'lq'], 'unknown combat leg'
    yield from execution.delay_ticks(5)
    yield from send('tele 0,50,53,5,8')
    yield from stash()
    for name, level in [('attack', 75), ('strength', 75), ('defence', 75), ('hitpoints', 85), ('prayer', 70), ('mining', 70), ('agility', 70), ('magic', 70), ('cooking', 70), ('crafting', 70)]:
        yield from send('setstat ' + name + ' ' + str(level))
    for symbol, name in [('rune_chainbody', 'Rune chainbody'), ('rune_platelegs', 'Rune platelegs'), ('rune_longsword', 'Rune longsword')]:
        yield from send('give ' + symbol + ' 1')
        equipped = yield from equipment.equip(name)
        assert equipped, 'could not equip ' + name
    food = 'shark' if kind == 'rg' else 'lobster'
    count = 9 if kind == 'lq' else 8
    yield from send('give ' + food + ' ' + str(count))
    yield from send('give 3doseprayerrestore ' + ('3' if kind == 'lq' else '2'))
    yield from send('give coins 10000')
    if kind == 'hq':
        yield from send('give bronze_pickaxe 1')
        # Queen is required; no gloves are seeded.
        x, z = 2865, 9955
    elif kind == 'rg':
        yield from send('setvar regicide_quest 8')
        x, z = 2240, 3151
    else:
        yield from send('setvar legendsquest 16')
        x, z = 2378, 4717
    yield from send('tele 0,' + str(x // 64) + ',' + str(z // 64) + ',' + str(x % 64) + ',' + str(z % 64))
    log('E2E_SEEDED ' + json.dumps({'case': kind, 'name': game.my_name(), 'passed': True, 'tile': str(game.tile())}))
    stop_account()
    return 600
