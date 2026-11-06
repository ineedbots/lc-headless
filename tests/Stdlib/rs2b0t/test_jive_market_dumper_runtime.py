"""rs2b0t's JiveMarketDumper/runtime.test.ts (MIT, see thirdparty/rs2b0t)."""

from bots.jive_market_dumper import JiveMarketDumper, bank_choice
import bots.jive_market_dumper as dumper
from rs2004.bank import bank
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.market import catalog
from rs2004.settings import SettingsBag

after_each(catalog.reset_live_catalog)


def named_access(name):
    patch(dumper, 'BANK_LOCATIONS', [
        {'name': 'Shilo Village', 'tile': {'x': 2852, 'z': 2954, 'level': 0}, 'npcAccess': {'name': 'Banker', 'op': 'Bank'}},
        {'name': 'Duel Arena', 'tile': {'x': 3382, 'z': 3269, 'level': 0}, 'access': {'name': 'Open chest', 'op': 'Bank',
            'openFirst': {'name': 'Closed chest', 'op': 'Open'}}},
    ])
    chosen = bank_choice(name)
    point = chosen['tile']
    scene = Scene(Tile(point['x'], point['z'], point['level']))
    spy_on(game, 'ingame', returns=True)
    spy_on(reader, 'obj_catalog', returns=[Fake(id=1637, name='Sapphire ring', cost=900,
        stackable=False, members=False, equippable=True, certlink=-1, certtemplate=-1)])
    spy_on(bank, 'is_open', returns=False)
    npc = spy_on(bank, 'open_npc_access', impl=lambda access: result(True))
    loc = spy_on(bank, 'open_nearest_access', impl=lambda access: result(True))
    bot = JiveMarketDumper()
    bot.settings = SettingsBag({'maker': 'test maker', 'bank': name})
    bot.bind_log(scene.log)
    catalog.reset_live_catalog()
    run_wait(bot.on_start())
    expect(run_wait(bot.open_bank())).to_be(True)
    access = chosen.get('npcAccess', chosen.get('npc_access'))
    if access is not None:
        expect(len(npc.calls)).to_be(1)
        expect(npc.calls[0][0]['name']).to_be(access['name'])
        expect(npc.calls[0][0]['op']).to_be(access['op'])
        expect(loc.calls).to_equal([])
    else:
        expect(len(loc.calls)).to_be(1)
        expect(loc.calls[0][0]['name']).to_be(chosen['access']['name'])
        expect(npc.calls).to_equal([])


def result(value):
    return value
    yield


test_each(['Shilo Village', 'Duel Arena'])('JiveMarketDumper preserves the bank access for %s', named_access)
