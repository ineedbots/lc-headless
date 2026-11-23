from rs2004 import execution
from rs2004.bank import bank
from rs2004.dialogue import chat_dialog
from rs2004.game import chat, game
from rs2004.items import inventory
from rs2004.tabs import quests
import json

started = False


def send(command):
    chat.command(command)
    yield from execution.delay_ticks(2)


def stash():
    chat.command('~bank')
    ok = yield from execution.delay_until(bank.is_open, 8000)
    assert ok, 'seed bank absent'
    ok = yield from bank.wait_ready()
    assert ok, 'seed bank contents absent'
    yield from bank.deposit_inventory()
    yield from execution.delay_ticks(2)
    assert inventory.used() == 0, 'seed deposit incomplete'
    log('SEED bank', [(i.id, i.name, i.count) for i in bank.items()])
    yield from bank.close()


def loop():
    global started
    if started:
        return 600
    started = True
    yield from execution.delay_ticks(5)
    kind = settings.get('kind')
    yield from send('tele 0,50,53,5,8')
    yield from stash()
    if kind in ['ph', 'ba']:
        chat.command('~hero')
        ok = yield from execution.delay_until(lambda: bool(chat_dialog.options()), 10000)
        assert ok, 'hero setup absent'
        ok = yield from chat_dialog.choose_option('Start Heros Quest')
        assert ok, 'hero start absent'
        yield from execution.delay_ticks(2)
        ok = yield from chat_dialog.choose_option('Phoenix' if kind == 'ph' else 'Blackarm')
        assert ok, 'gang choice failed'
        yield from execution.delay_ticks(3)
        for item in inventory.items():
            if item.id == 1580:
                assert item.interact('Drop'), 'seed gloves drop failed'
                yield from execution.delay_ticks(2)
        for name, value in [('rjquest', 100), ('goblinquest', 6), ('haunted', 3), ('princequest', 110), ('spy', 4), ('demonstart', 30), ('druidquest', 4), ('grandtree', 160), ('treequest', 9), ('cookquest', 2), ('doricquest', 100), ('sheep', 22), ('imp', 2), ('hetty', 3), ('runemysteries', 6), ('squire', 7), ('prieststart', 5), ('hunt', 4), ('qp', 56)]:
            yield from send('setvar ' + name + ' ' + str(value))
        yield from stash()
    for name, level in [('attack', 75), ('strength', 75), ('defence', 75), ('hitpoints', 85), ('ranged', 75), ('prayer', 70), ('magic', 60), ('mining', 55), ('fishing', 65), ('cooking', 65), ('herblore', 35), ('agility', 50), ('thieving', 50), ('woodcutting', 60), ('crafting', 50), ('fletching', 65)]:
        yield from send('setstat ' + name + ' ' + str(level))
    supplies = ['coins 1000000', 'cert_lobster 1000', 'cert_3doseprayerrestore 100', 'rune_chainbody 1', 'rune_platelegs 1', 'rune_longsword 1', 'bronze_pickaxe 1', 'bronze_axe 1', 'knife 1', 'tinderbox 1']
    if kind in ['ph', 'ba']:
        supplies.extend(['oak_longbow 1', 'steel_arrow 500', 'fishing_bait 100'])
    if kind == 'ik':
        supplies.extend(['yew_shortbow 1', 'coif 1', 'dragonhide_body 1', 'dragonhide_chaps 1', 'dragon_vambraces 1', 'unlit_candle 2', 'bow_string 1', 'yew_logs 1'])
    if kind == 'ft':
        supplies.extend(['raw_shark 2'])
    for item in supplies:
        yield from send('give ' + item)
    yield from stash()
    chat.command('~bank')
    ok = yield from execution.delay_until(bank.is_open, 8000)
    assert ok, 'verification bank absent'
    ok = yield from bank.wait_ready()
    assert ok, 'verification bank contents absent'
    for name, count in [('Coins', 1000000), ('Lobster', 1000), ('Prayer potion(3)', 100), ('Rune chainbody', 1), ('Rune platelegs', 1), ('Rune longsword', 1)]:
        assert bank.count(name) >= count, 'missing seeded supply: ' + name
    assert bank.count_by_id(1580) == 0, 'setup gloves must not skip the Ice Queen'
    if kind == 'ik':
        assert bank.count_by_id(36) >= 2, 'unlit candles absent'
        assert bank.count_by_id(225) == 0, 'limpwurt roots must be earned'
    if kind == 'ft':
        assert bank.count('Raw shark') >= 2, 'raw sharks absent'
    yield from bank.close()
    if kind in ['ph', 'ba']:
        yield from send('getvar heroquest')
        yield from send('getvar qp')
    if kind == 'ft':
        yield from send('tele 0,42,54,37,35')
    else:
        yield from send('tele 0,45,54,24,53' if kind in ['ph', 'ba'] else 'tele 0,50,53,5,8')
    names = {'ph': "Hero's Quest", 'ba': "Hero's Quest", 'ik': 'Temple of Ikov', 'ft': 'The Fremennik Trials'}
    assert quests.status(names[kind]) != 'complete', 'target quest already complete'
    log('E2E_SEEDED ' + json.dumps({'case': kind, 'name': game.my_name(), 'passed': True, 'tile': str(game.tile())}))
    stop_account()
    return 600

