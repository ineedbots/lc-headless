"""Regressions from rs2b0t #892, #902 and #910 (MIT, see thirdparty/rs2b0t)."""

import bots.fire_giant as giants
import bots.flax_spinner as spinner
import bots.jive_crafting as crafting
import bots.mule_crafter as mule
import rs2004.catalogs.partner as partner_trade
from rs2004.catalogs.record import Record
from rs2004.bank import bank, banking
from rs2004.dialogue import chat_dialog
from rs2004.items import inventory
from rs2004 import execution
from rs2004.execution import event_signal
from rs2004.trade import trade


def result(value):
    return value
    yield


def fire_pack(style, names, bury=False, weapon='Staff of air'):
    bot = giants.FireGiant()
    bot.style = style
    bot.food_name = 'Lobster'
    bot.weapon = weapon
    bot.ammo = 'Iron arrow'
    bot.spell = 'Wind Strike'
    bot.tele = giants.ESCAPE_TELES['Camelot']
    bot.bury_bones = bury
    bot.bank_common = True
    bot.loot_set = set(['lobster', 'law rune', 'air rune', 'iron arrow', 'big bones', 'rune scimitar'])
    spy_on(bot, 'wielded_names', returns=[weapon])
    spy_on(inventory, 'items', returns=[Fake(name=name) for name in names])
    spy_on(inventory, 'is_full', returns=True)
    spy_on(bot, 'need_style_supplies', returns=False)
    spy_on(bot, 'has_food', returns=True)
    return bot


def fresh_restock():
    bot = fire_pack('mage', ['Lobster'] * 24 + [giants.AMULET, giants.ROPE, 'Law rune', 'Mind rune'])
    expect(bot.bankable_loot_slots()).to_be(0)
    expect(giants.BankRun(bot).validate()).to_be(False)


test('FireGiant stays to fight when restocking filled every slot', fresh_restock)


def loot_threshold():
    bot = fire_pack('melee', ['Lobster'] * 23 + [giants.AMULET, giants.ROPE, 'Law rune', 'Air rune', 'Rune scimitar'])
    expect(bot.bankable_loot_slots()).to_be(1)
    expect(giants.BankRun(bot).validate()).to_be(False)
    spy_on(inventory, 'items', returns=[Fake(name='Rune scimitar'), Fake(name='Uncut sapphire')])
    expect(giants.BankRun(bot).validate()).to_be(True)
    spy_on(inventory, 'is_full', returns=False)
    expect(giants.BankRun(bot).validate()).to_be(False)


test('FireGiant banks a full pack only when at least two slots are bankable loot', loot_threshold)


def spell_kit():
    bot = fire_pack('mage', ['Earth rune', 'Mind rune', 'Big bones'], True, 'Staff of air')
    bot.spell = 'Earth Strike'
    bot.loot_set.add('earth rune')
    expect(bot.bankable_loot_slots()).to_be(0)
    spy_on(bot, 'wielded_names', returns=['Staff of earth'])
    expect(bot.bankable_loot_slots()).to_be(1)
    bot.bury_bones = False
    expect(bot.bankable_loot_slots()).to_be(2)
    bot.bank_common = False
    spy_on(inventory, 'items', returns=[Fake(name='Uncut sapphire'), Fake(name=None)])
    expect(bot.bankable_loot_slots()).to_be(0)


test('spell withdrawals distinguish staff-supplied loot runes and bones to bury', spell_kit)


def wool_banking(raw_count):
    def run():
        bot = spinner.FlaxSpinner()
        bot.product = 'Wool'
        bot.bank_stand = spinner.DEFAULT_BANK_STAND
        bot.obstacles = []
        bot.booth_name = 'Bank booth'
        bot.trips = 0
        spy_on(spinner, 'walk_opening', impl=lambda *args: result(True))
        spy_on(bank, 'open_booth', impl=lambda *args: result(True))
        spy_on(bank, 'deposit_inventory', impl=instant_ticks)
        spy_on(execution, 'delay_ticks', impl=instant_ticks)
        spy_on(execution, 'delay_until', impl=instant_until)
        spy_on(bank, 'items', returns=[Fake(name='Ball of wool', count=200), Fake(name='Wool', count=raw_count, actions=lambda: ['Withdraw-All'])])
        spy_on(inventory, 'count', returns=0)
        spy_on(bank, 'count', returns=0)
        drawn = spy_on(bank, 'withdraw', returns=True)
        finish = spy_on(bot, 'request_finish')
        run_wait(spinner.BankTrip(bot).execute())
        expect(drawn.calls).to_equal([('Wool', 'Withdraw-All')] if raw_count else [])
        expect(len(finish.calls)).to_be(0 if raw_count else 1)
    return run


test('spinner selects raw wool even when balls of wool are listed first', wool_banking(28))
test('spinner stops when the bank holds only finished wool', wool_banking(0))


def spinner_count():
    bot = spinner.FlaxSpinner()
    bot.product = 'Wool'
    counted = spy_on(inventory, 'count', returns=0)
    expect(bot.fibre_count()).to_be(0)
    expect(counted.calls).to_equal([('Wool',)])


test('finished balls of wool do not send the spinner upstairs', spinner_count)


def string_task():
    bot = crafting.JiveCrafting()
    bot.made = 0
    bot.trips = 0
    bot.banked = 0
    spy_on(event_signal, 'pending', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(execution, 'delay_until', impl=instant_until)
    return bot, crafting.StringAmulets(bot, crafting.AMULETS[0])


def string_one():
    bot, task = string_task()
    counts = {1673: 1, 1759: 1, 1692: 0}
    def join(raw):
        expect(raw.id).to_be(1673)
        counts[1692] = 1
        return True
    spy_on(inventory, 'count_by_id', impl=lambda id: counts.get(id, 0))
    spy_on(inventory, 'items', returns=[Fake(id=1759, use_on=join), Fake(id=1673)])
    spy_on(bank, 'is_open', returns=False)
    expect(task.validate()).to_be(True)
    run_wait(task.execute())
    expect(bot.made).to_be(1)


test('stringing uses wool on the exact unstrung amulet id', string_one)


def string_bank(raw, wool, first_draw=True):
    def run():
        raw_stock = raw
        wool_stock = wool
        accept_first = first_draw
        bot, task = string_task()
        spy_on(inventory, 'count_by_id', impl=lambda id: 5 if id == 1692 else 0)
        spy_on(inventory, 'used', returns=0)
        spy_on(banking, 'open', impl=lambda **kwargs: result(True))
        spy_on(bank, 'is_open', returns=True)
        spy_on(bank, 'deposit_inventory', impl=instant_ticks)
        spy_on(bank, 'wait_ready', impl=lambda: result(True))
        spy_on(bank, 'count_by_id', impl=lambda id: raw_stock if id == 1673 else wool_stock)
        spy_on(bank, 'set_note_mode', impl=instant_ticks)
        closed = spy_on(bank, 'close', impl=lambda: result(True))
        drawn = spy_on(bank, 'withdraw_x_by_id', impl=lambda id, count: result(accept_first or id != 1673))
        finish = spy_on(bot, 'request_finish')
        run_wait(task.execute())
        expect(bot.trips).to_be(1)
        expect(bot.banked).to_be(5)
        if raw and wool:
            pairs = min(14, raw, wool)
            expect(drawn.calls).to_equal([(1673, pairs), (1759, pairs)] if first_draw else [(1673, pairs)])
            expect(len(closed.calls)).to_be(1 if first_draw else 0)
        else:
            expect(len(finish.calls)).to_be(1)
            expect(drawn.calls).to_equal([])
    return run


test('stringing draws fourteen unnoted pairs', string_bank(50, 50))
test('stringing uses a partial supply load', string_bank(3, 8))
test('stringing stops without unstrung amulets', string_bank(0, 8))
test('stringing stops without wool', string_bank(8, 0))
test('stringing retries a refused withdrawal', string_bank(8, 8, False))


def trade_closure(crafter):
    def run():
        state = Record({'now': 0, 'active': True, 'essence': 0 if crafter else 27})
        bot = mule.MuleCrafter()
        bot._trades = 0
        spy_on(bot, 'set_status')
        spy_on(bot, 'log')
        counted = spy_on(bot, 'count_trade')
        marked = spy_on(bot, 'mark_mule_traded')
        spy_on(trade, 'on_offer_screen', returns=False)
        spy_on(trade, 'on_confirm_screen', returns=True)
        spy_on(trade, 'partner', impl=lambda: 'Runner' if state.active else None)
        spy_on(trade, 'accept', returns=True)
        spy_on(trade, 'active', impl=lambda: state.active)
        spy_on(mule, 'ess_count', impl=lambda: state.essence)
        spy_on(partner_trade._core, 'step_time', impl=lambda: state.now)
        incoming = crafter
        def wait(cond, timeout):
            expect(timeout).to_be(5000)
            observed = []
            for now, active in [(0, False), (300, False), (600, True), (900, False), (1200, False), (1500, False)]:
                state.now = now
                state.active = active
                observed.append(cond())
            expect(observed).to_equal([False, False, False, False, False, True])
            state.essence = 27 if incoming else 0
            return True
            yield
        spy_on(execution, 'delay_until', impl=wait)
        task = mule.CrafterTradeAtRuins(bot) if crafter else mule.MuleTradeExecute(bot)
        if not crafter:
            task._before_ess = 27
        run_wait(task.execute())
        expect(len(counted.calls)).to_be(1)
        expect(marked.calls).to_equal([('Runner',)] if crafter else [])
    return run


test('crafter waits through trade-screen flicker and retains the partner after closure', trade_closure(True))
test('mule counts delivery only after stable trade closure and an essence debit', trade_closure(False))
