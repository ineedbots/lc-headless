"""Regression outcomes for the Superheater, shield farm and quest supply activity ports."""

import _core
from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.execution import event_signal
from rs2004.game import reader
from rs2004.settings import SettingsBag
from bots.superheater import Superheater, EnsureGauntlets, recipe_for_bar
from bots.dragonfire_shield import DragonfireShield, LootShields, BankTrip
from bots.potion_maker import PotionMaker, secondary_by_name
from bots.herblore_secondaries import secondary_by_name as secondary_source, keep_on_deposit, needs_restock


def result(value):
    yield from ()
    return value


def fast_bank():
    scene = Scene()
    spy_on(event_signal, 'pending', returns=False)
    bot = Superheater()
    bot.recipe = recipe_for_bar('Gold')
    bot.fast_bank = True
    scene.item(561, 'Nature rune', count=50)
    bars = scene.item(2357, 'Gold bar', count=27, actions=['Deposit-All'])
    ops = []
    bars._fields['interact'] = lambda op: ops.append(op) or True
    spy_on(bank, 'side_items', returns=[bars, scene.pack[0]])
    spy_on(bank, 'is_open', returns=False)
    def withdraw(name, op):
        ops.append(op)
        scene.item(444, 'Gold ore', count=27)
        return True
    spy_on(bank, 'withdraw', impl=withdraw)
    expect(run_wait(bot.fast_restock())).to_be(True)
    expect(ops).to_equal(['Deposit-All', 'Withdraw All'])
    bot.recipe = recipe_for_bar('Steel')
    expect(run_wait(bot.fast_restock())).to_be(False)
    expect(len(ops)).to_be(2)
    bot.recipe = recipe_for_bar('Gold')
    spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(bot.fast_restock())).to_be(False)
    expect(len(ops)).to_be(2)


test('instant banking sends deposit and withdrawal in order and yields to random events', fast_bank)


def fast_bank_fallback():
    scene = Scene()
    spy_on(event_signal, 'pending', returns=False)
    bot = Superheater()
    bot.recipe = recipe_for_bar('Gold')
    bot.fast_bank = True
    bars = scene.item(2357, 'Gold bar', actions=['Deposit-All'])
    side = [bars, scene.item(0, 'Unknown junk')]
    spy_on(bank, 'side_items', impl=lambda: side)
    withdraw = spy_on(bank, 'withdraw', returns=False)
    expect(run_wait(bot.fast_restock())).to_be(False)
    expect(withdraw.calls).to_equal([])
    side.pop()
    expect(run_wait(bot.fast_restock())).to_be(False)
    expect(len(withdraw.calls)).to_be(1)


test('instant banking rejects unknown cargo and reports a missed withdrawal to the confirmed route', fast_bank_fallback)


def required_gauntlets():
    scene = Scene()
    spy_on(event_signal, 'pending', returns=False)
    missing = []
    bot = Fake(recipe=recipe_for_bar('Gold'), goldsmith=True, open_bank=lambda: result(True),
               bank_truly_out_of=lambda names: result(True), request_finish=lambda reason: missing.append(reason))
    task = EnsureGauntlets(bot)
    expect(task.validate()).to_be(True)
    spy_on(bank, 'withdraw_x', impl=lambda name, count: result(False))
    run_wait(task.execute())
    expect(missing).to_equal(['no Goldsmith gauntlet in the bank'])
    bot.goldsmith = False
    expect(task.validate()).to_be(False)


test('gold stops when requested gauntlets are absent rather than silently smelting at base experience', required_gauntlets)


def potion_target_and_scales():
    scene = Scene()
    maker = PotionMaker()
    maker.settings = SettingsBag({'output_id': 3034, 'output_count': 6})
    spy_on(bank, 'count_by_id', returns=3)
    scene.item(3034, 'Agility potion(3)', count=1)
    expect(maker.batch_size()).to_be(2)
    scene.pack[0].count = 3
    expect(maker.batch_size()).to_be(0)
    expect(secondary_by_name("Toad's legs").id).to_be(2152)
    scale = secondary_source('Blue dragon scale')
    expect(scale.key_name).to_be('Dusty key')
    expect(keep_on_deposit(scale, 'Trout')).to_contain('Dusty key')
    expect(needs_restock(scale, 8, 8, 500, True, False, 0, has_key=False)).to_be(True)
    expect(needs_restock(scale, 8, 8, 500, True, False, 0, has_key=True)).to_be(False)


test('preparation makes only the remaining potion batch and protects the dusty key on scale trips', potion_target_and_scales)


def shields():
    scene = Scene(Tile(3212, 3220, 1))
    bot = DragonfireShield()
    spy_on(reader, 'obj_catalog', returns=[Record({'id': 1541, 'note_of': 1540})])
    bot.note_id = bot.find_note_id()
    expect(bot.note_id).to_be(1541)
    bot.initial_setup_done = True
    bot.trip_active = False
    bot.redropped_at = -4000
    bot.carry_notes = True
    bot.has_banked_shields = False
    for n in range(28):
        scene.item(1540, 'Dragonfire shield')
    expect(BankTrip(bot).validate()).to_be(True)
    expect(LootShields(bot).validate()).to_be(False)
    scene.pack = []
    expect(BankTrip(bot).validate()).to_be(False)


test('shield farming resolves native note ids and hands full backpacks to the bank task', shields)
