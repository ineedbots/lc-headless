"""Behavioral regressions for rs2b0t #899, #903, #912 and #878."""

import _core
import bots.nature_crafter as rc
import bots.mule_crafter as mc
import bots.mule_depot as depot
import bots.depot.logic as logic
import bots.depot.tasks as tasks
import bots.gathering.three_tick as fly
from bots.gathering.bot import GatheringBot
from bots.gathering.tick_manip import three_tick_fly_profile
from rs2004.catalogs import Record
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.bank import bank
from rs2004.trade import trade
from rs2004.game import game
from rs2004 import execution


def done(value=True):
    return value
    yield


def row(id, name, count=1):
    return Fake(id=id, name=name, count=count, slot=0, noted=False)


def cosmic_identity():
    cosmic = rc.RUNES['Cosmic runes']
    expect(cosmic.level).to_be(27)
    expect(rc.in_rune_temple(Tile(2142, 4830), cosmic)).to_be(True)
    expect(rc.in_rune_temple(Tile(3152, 9575), cosmic)).to_be(False)
    expect(rc.in_rune_temple(Tile(2840, 4830), cosmic)).to_be(False)
    expect(rc.in_rune_temple(Tile(2142, 4830, 1), cosmic)).to_be(False)
    expect(rc.in_rune_temple(None, cosmic)).to_be(False)
    expect(rc.in_zanaris(Tile(3152, 9575))).to_be(True)
    expect(rc.in_zanaris(Tile(2142, 4830))).to_be(False)
    expect(rc.in_zanaris(None)).to_be(False)
    expect(rc.is_litter('Dramen staff', rc.keep_names(cosmic.talisman, cosmic.rune, cosmic.keep_items))).to_be(False)
    called = spy_on(bank, 'open_npc_access', impl=lambda access: done(access['choose'] == "I'd like to access my bank account"))
    expect(run_wait(rc.open_route_bank(cosmic, cosmic.runner_bank))).to_be(True)
    expect(len(called.calls)).to_be(1)
    spy_on(bank, 'open_booth', impl=lambda *args: done(False))
    spy_on(bank, 'open_nearest', impl=lambda *args: done(True))
    expect(run_wait(rc.open_route_bank(rc.RUNES['Air runes'], Tile(1, 1)))).to_be(True)


test('Cosmic altar identity excludes underground Zanaris and retains travel gear', cosmic_identity)


def fly_cadence():
    cycle = fly.FlyCycle()
    expect(cycle.step(10, -1, 0)).to_be('wait')
    expect(cycle.step(11, 623, 11)).to_be('batch')
    expect(cycle.step(11, 623, 11)).to_be('wait')
    expect(cycle.step(12, 1248, 12)).to_be('wait')
    expect(cycle.state).to_be('armed')
    expect(cycle.step(13, 1248, 12)).to_be('wait')
    expect(cycle.step(14, 623, 14)).to_be('batch')
    expect(cycle.step(15, 623, 15)).to_be('wait')
    expect(cycle.step(17, 623, 17)).to_be('batch')
    expect(cycle.step(18, -1, 18)).to_be('wait')
    expect(cycle.step(19, -1, 18)).to_be('fallback')
    expect(cycle.state).to_be('native')
    expect(cycle.step(20, 623, 20)).to_be('batch')
    expect(cycle.step(22, 623, 20)).to_be('fallback')
    profile = three_tick_fly_profile()
    expect(profile.native_cycle_ticks).to_be(3)
    expect(profile.use_knife_delay).to_be(True)


test('three-tick cycle recognizes landing, keeps quiet between rolls and falls back after misses', fly_cadence)


def depot_planners():
    expect(logic.resolve_role(' dump ', 'MULE')).to_be('Mule')
    expect(logic.resolve_role('dump', 'Supplier')).to_be(None)
    expect(logic.is_giver_role('Supplier')).to_be(True)
    expect(logic.is_receiver_role('Client')).to_be(True)
    expect(logic.parse_accounts(' Alice_Bot,alice bot, Bob,,')).to_equal(['alice bot', 'bob'])
    expect(logic.is_configured_account(None, ['a'])).to_be(False)
    expect(logic.is_configured_account('A', ['a'])).to_be(True)
    expect(logic.parse_item_names(['  Herb', 'herb', '', 'Air rune'])).to_equal(['Herb', 'Air rune'])
    parsed = logic.parse_loadout(['# comment', '', '30 Lobster', '2 lobster', '100 995', '995', '0 Logs', '999999999999 Logs', '9999999'])
    expect(len(parsed.problems)).to_be(3)
    expect([l.quantity for l in parsed.lines]).to_equal([32, 101])
    batches = logic.plan_deliveries(parsed.lines, lambda l: l.quantity if l.name else 1, 28)
    expect([len(b.lines) for b in batches]).to_equal([1, 2])
    expect(batches[0].lines[0].quantity).to_be(28)
    expect(batches[1].lines[0].quantity).to_be(4)
    expect(batches[1].lines[1].quantity).to_be(101)
    expect(logic.next_batch_index(0, 2).client_done).to_be(False)
    expect(logic.next_batch_index(1, 2).client_done).to_be(True)
    expect(logic.next_unserved(['a', 'b'], set(['a']))).to_be('b')
    expect(logic.next_unserved(['a'], set(['a']))).to_be(None)
    expect(logic.pick_request_target('b', ['a', 'b'], 0, lambda n: True, lambda n: True)).to_be('b')
    expect(logic.pick_request_target(None, ['a', 'b'], 1, lambda n: True, lambda n: True)).to_be('b')
    expect(logic.pick_request_target(None, ['a'], 0, lambda n: False, lambda n: True)).to_be(None)
    expect(logic.pick_request_target(None, ['a'], 0, lambda n: True, lambda n: False)).to_be(None)
    rows = [row(1, 'Herb', 10), row(2, 'Herb', 20), row(3, 'Herb', 0), row(4, 'Coins', 100)]
    expect([r.id for r in logic.pick_bank_rows('herb', rows, set([1]))]).to_equal([2, 1])
    expect(logic.pick_bank_row('missing', rows)).to_be(None)
    expect(len(logic.listed_rows(['herb', 'herb'], rows))).to_be(2)
    expect([r.id for r in logic.plan_withdrawal(['Herb', 'Coins'], rows, 2)]).to_equal([1, 2])
    expect(logic.plan_withdrawal(['Herb'], rows, 0)).to_equal([])
    expect(logic.describe_lines([])).to_be('nothing')
    expect(logic.describe_lines(parsed.lines)).to_be('32 Lobster + 101 995')
    expect(len(logic.shortfall_for(parsed.lines, lambda l: 0))).to_be(2)
    expect(logic.shortfall_for(parsed.lines, lambda l: 1000)).to_equal([])
    stub(logic, BANK_LOCATIONS=[{'name': 'Seers', 'tile': {'x': 2725, 'z': 3493, 'level': 0}}])
    expect(logic.bank_choice('unknown')['name']).to_be('Seers')
    expect(logic.bank_tile('Seers').x > 0).to_be(True)


test('depot planners normalize names, merge quantities and deliver every oversized line', depot_planners)


def delivery_ledger():
    bot = depot.MuleDepot()
    bot.role = 'Supplier'
    bot.partners = ['a', 'b']
    bot.lines = logic.parse_loadout(['30 Lobster']).lines
    bot.batches = logic.plan_deliveries(bot.lines, lambda l: l.quantity)
    finished = spy_on(bot, 'request_finish')
    bot.pending = bot.batches[0].lines
    bot.advance_batch()
    expect(bot.current_client()).to_be('a')
    expect(bot.batch_index).to_be(1)
    bot.pending = bot.batches[1].lines
    bot.advance_batch()
    expect(bot.current_client()).to_be('b')
    bot.pending = bot.batches[0].lines
    bot.advance_batch()
    bot.advance_batch()
    expect(bot.current_client()).to_be(None)
    expect('b: 2 Lobster' in finished.calls[0][0]).to_be(True)
    expect(bot.current_batch()).to_be(None)
    expect(bot.shortfall()).to_equal([])
    expect(bot.on_progress_report()['Clients served']).to_be(2)


test('supplier advances clients only after all batches and reports per-client shortages', delivery_ledger)


def mule_meeting_policy():
    bot = mc.MuleCrafter()
    bot._mode = 'Crafter'
    bot._partners = ['mule']
    bot._bank_fill = False
    bot._meeting = 'Altar (inside)'
    bot._trade_limit = 0
    bot._trades_since_bank = 0
    bot._trades = 0
    expect(bot.trading_active()).to_be(True)
    expect(bot.bank_due()).to_be(False)
    bot._bank_fill = True
    spy_on(mc, 'ess_count', returns=0)
    expect(bot.trading_active()).to_be(False)
    expect(bot.bank_due()).to_be(True)
    bot._trade_limit = 2
    expect(bot.bank_due()).to_be(False)
    bot.count_trade()
    expect(bot.bank_due()).to_be(False)
    bot.count_trade()
    expect(bot.bank_due()).to_be(True)
    spy_on(mc, 'in_temple', returns=True)
    spy_on(trade, 'active', returns=False)
    expect(mc.ExitAltar(bot).validate()).to_be(True)
    bot._bank_fill = False
    expect(mc.ExitAltar(bot).validate()).to_be(False)
    expect(bot.at_meeting()).to_be(True)
    bot._mode = 'Mule'
    expect(mc.MuleExitAltar(bot).validate()).to_be(True)


test('MuleCrafter stays inside between trades and honors disabled or scheduled bank visits', mule_meeting_policy)


def depot_stub(role='Supplier'):
    bot = depot.MuleDepot()
    bot.role = role
    bot.partners = ['alice']
    bot.bank_tile = Tile(2725, 3493)
    bot.items = ['Coins']
    bot.lines = logic.parse_loadout(['100 Coins']).lines
    bot.batches = logic.plan_deliveries(bot.lines, lambda l: 1)
    bot.settings = Fake(str=lambda key, default: default)
    spy_on(bot, 'log')
    spy_on(bot, 'request_finish')
    spy_on(execution, 'delay_ticks', impl=lambda *args: done())
    spy_on(execution, 'delay_until', impl=lambda fn, *args: done(fn()))
    spy_on(execution, 'delay_until_ticks', impl=lambda fn, *args: done(fn()))
    spy_on(bank, 'close', impl=lambda *args: done())
    spy_on(bank, 'set_note_mode', impl=lambda *args: done())
    spy_on(bank, 'is_open', returns=False)
    spy_on(trade, 'active', returns=False)
    spy_on(inventory, 'used', returns=0)
    spy_on(inventory, 'free', returns=28)
    spy_on(inventory, 'items', returns=[])
    spy_on(bank, 'items', returns=[])
    spy_on(inventory, 'count_by_id', returns=0)
    spy_on(inventory, 'count', returns=0)
    catalog = Fake(by_id={}, noted_of={})
    spy_on(tasks, 'live_catalog', returns=catalog)
    spy_on(depot, 'live_catalog', returns=catalog)
    spy_on(tasks, 'noted_id', returns=None)
    spy_on(depot, 'noted_id', returns=None)
    return bot


def depot_bank_shortages():
    bot = depot_stub()
    task = tasks.DepotBank(bot)
    spy_on(bank, 'deposit_all_matching', impl=lambda fn: done())
    expect(task.validate()).to_be(True)
    for _ in range(3):
        run_wait(task.supply())
    expect(bot.client_index).to_be(1)
    expect('short:' in bot.request_finish.calls[0][0]).to_be(True)
    bot = depot_stub('Mule')
    task = tasks.DepotBank(bot)
    for _ in range(3):
        run_wait(task.dump())
    expect('exhausted' in bot.request_finish.calls[0][0]).to_be(True)


test('depot banks stop on sustained empty stock and report unsupplied batches', depot_bank_shortages)


def depot_dump_withdrawal():
    bot = depot_stub('Mule')
    task = tasks.DepotBank(bot)
    spy_on(bank, 'items', returns=[row(995, 'Coins', 500)])
    spy_on(bank, 'deposit_all_matching', impl=lambda fn: done())
    held = [0]
    def withdraw(id, op):
        held[0] = 500
        return True
    drawn = spy_on(bank, 'withdraw_by_id', impl=withdraw)
    spy_on(inventory, 'count_by_id', impl=lambda id: held[0])
    run_wait(task.dump())
    expect(drawn.calls).to_equal([(995, 'Withdraw All')])
    expect(task.empty_reads).to_be(0)


test('dump withdrawals drain named bank rows in note mode', depot_dump_withdrawal)


def depot_supply_withdrawal():
    bot = depot_stub()
    task = tasks.DepotBank(bot)
    spy_on(bank, 'items', returns=[row(995, 'Coins', 1000)])
    spy_on(bank, 'deposit_all_matching', impl=lambda fn: done())
    held = []
    spy_on(inventory, 'items', impl=lambda: held)
    def draw(id, qty, lands_as_id=None):
        held.append(row(995, 'Coins', qty))
        return done()
    taken = spy_on(bank, 'withdraw_x_by_id', impl=draw)
    run_wait(task.supply())
    expect(taken.calls[0][:2]).to_equal((995, 100))
    expect(bot.shortfall()).to_equal([])
    expect(task.validate()).to_be(False)


test('supplier withdraws only the outstanding batch quantity', depot_supply_withdrawal)


def depot_trade_transition(success=True, giver=False):
    def run():
        bot = depot_stub('Supplier' if giver else 'Supermule')
        held = [100 if giver else 0]
        spy_on(bot, 'pack_units', impl=lambda: held[0])
        now = [0]
        spy_on(_core, 'step_time', impl=lambda: now[0])
        active = [True]
        spy_on(trade, 'active', impl=lambda: active[0])
        spy_on(trade, 'partner', returns='Alice')
        spy_on(trade, 'on_confirm_screen', returns=True)
        spy_on(trade, 'accept', returns=True)
        task = tasks.DepotTrade(bot)
        bot.pending = bot.lines
        run_wait(task.execute())
        active[0] = False
        now[0] = 100
        run_wait(task.execute())
        expect(bot.transfers).to_be(0)
        active[0] = True
        now[0] = 500
        run_wait(task.execute())
        active[0] = False
        now[0] = 1000
        run_wait(task.execute())
        if success:
            held[0] = 0 if giver else 100
        now[0] = 1700
        run_wait(task.execute())
        expect(bot.transfers).to_be(1 if success else 0)
        expect(bot.client_index).to_be(1 if success and giver else 0)
        expect(task.before).to_be(None)
    return run


test('receiver ignores inactive-screen flicker and confirms inventory credit', depot_trade_transition())
test('supplier credits a client only after confirmed inventory debit', depot_trade_transition(True, True))
test('trade closure without item transfer preserves the batch', depot_trade_transition(False, True))


def depot_stranger():
    bot = depot_stub('Supermule')
    spy_on(trade, 'active', returns=True)
    spy_on(trade, 'partner', returns='stranger')
    declined = spy_on(trade, 'decline', impl=lambda: done())
    task = tasks.DepotTrade(bot)
    run_wait(task.execute())
    expect(len(declined.calls)).to_be(1)
    expect(bot.transfers).to_be(0)


test('depot declines an unconfigured partner before touching offers', depot_stranger)


def fishing_batches():
    bot = depot_stub()
    calls = []
    tick = [0]
    target = Fake(index=7, id=309, tile=lambda: Tile(3100, 3400), interact=lambda action: calls.append('lure'))
    spy_on(fly.npcs, 'query', impl=lambda: FakeQuery([target] if tick[0] <= 5 else []))
    spy_on(execution, 'delay_ticks', impl=lambda n: advance_tick(tick))
    spy_on(game, 'tick', impl=lambda: tick[0])
    spy_on(game, 'in_combat', returns=False)
    spy_on(fly.event_signal, 'pending', returns=False)
    spy_on(_core, 'get_local_player', impl=lambda: Fake(animation_id=623 if tick[0] in [1, 4] else 1248, animation_tick=tick[0]))
    spy_on(_core, 'click_button', impl=lambda id: calls.append('make'))
    spy_on(fly.chat_dialog, 'is_make_menu', returns=False)
    knife = Fake(use_on=lambda log: calls.append('knife'))
    spy_on(inventory, 'first', returns=knife)
    spy_on(bot, 'has_gear', returns=True)
    spy_on(bot, 'away_from_gather_spot', returns=False)
    spy_on(bot, 'delay_log_item', returns=Fake())
    spy_on(bot, 'set_status')
    spy_on(bot, 'products', returns=[Fake(interact=lambda op: calls.append('drop')), Fake(interact=lambda op: calls.append('drop'))])
    run_wait(fly.fish(bot, target))
    expect(calls).to_equal(['lure', 'drop', 'drop', 'knife', 'make', 'lure', 'drop', 'drop', 'knife', 'make', 'lure'])


def advance_tick(tick):
    tick[0] += 1
    return done()


test('fly fishing batches drop, knife, make-one and lure in order with no intervening actions', fishing_batches)


def fisher_settings():
    from rs2004.settings import SettingsBag
    from rs2004.catalogs.fishing import resolve_fish_method
    bot = GatheringBot()
    bot.fishing = True
    bot.settings = SettingsBag({'three_tick_fly': True})
    bot.fish_method = resolve_fish_method('Fly fishing — trout/salmon')
    bot.mule_mode = 'off'
    bot.cook_mode = 'off'
    bot.power_mode = True
    spy_on(bot, 'log')
    bot.configure_tick_manip({})
    expect(bot.tick_manip.method).to_be('three-tick-fly')
    expect([g.name for g in bot.fish_method.gear]).to_equal(['Fly fishing rod', 'Feather', 'Knife', 'Logs'])
    expect(len(resolve_fish_method('Fly fishing — trout/salmon').gear)).to_be(2)
    bot.fish_method = resolve_fish_method('Small net — shrimp/anchovy')
    caught = False
    try:
        bot.configure_tick_manip({})
    except RuntimeError:
        caught = True
    expect(caught).to_be(True)


test('three-tick configuration adds retained gear without changing other fishers', fisher_settings)


def depot_startup_roles():
    from rs2004.settings import SettingsBag
    bot = depot_stub()
    coin = Fake(id=995, name='Coins', stackable=True, note_of=None)
    catalog = Fake(by_id={995: coin}, noted_of={}, unnoted_of={})
    spy_on(depot, 'live_catalog', returns=catalog)
    spy_on(game, 'ingame', returns=True)
    spy_on(game, 'tile', returns=Tile(2725, 3493))
    spy_on(tasks.traversal, 'walk_resilient', impl=lambda *args, **kwargs: done(True))
    spy_on(tasks, 'open_bank_access', impl=lambda *args: done(True))
    spy_on(bank, 'wait_ready', impl=lambda *args: done(True))
    spy_on(bank, 'deposit_all_matching', impl=lambda *args: done(True))
    spy_on(bot, 'on')
    stub(logic, BANK_LOCATIONS=[{'name': 'Seers', 'tile': {'x': 2725, 'z': 3493, 'level': 0}}])
    for mode, role in [('Dump', 'Mule'), ('Dump', 'Supermule'), ('Supply', 'Supplier'), ('Supply', 'Client')]:
        fresh = depot.MuleDepot()
        fresh.settings = SettingsBag({'mode': mode, 'designation': role, 'accounts': 'Alice_Bot', 'items': ['Coins'], 'loadout': ['100 Coins', '50 995']})
        run_wait(fresh.on_start())
        expect(fresh.role).to_be(role)
        expect(fresh.partners).to_equal(['alice bot'])
        expect(len(fresh._tasks)).to_be(5)
        if mode == 'Supply':
            expect(fresh.lines[0].quantity).to_be(150)
            expect(fresh.batches[0].lines[0].id).to_be(995)
    fresh = depot.MuleDepot()
    fresh.settings = SettingsBag({'mode': 'Supply', 'designation': 'Mule'})
    failed = False
    try:
        run_wait(fresh.on_start())
    except RuntimeError:
        failed = True
    expect(failed).to_be(True)


test('all four depot roles start with bank cleanup and resolve name/id aliases once', depot_startup_roles)


def crafter_without_bank_visits():
    from rs2004.settings import SettingsBag
    spy_on(game, 'ingame', returns=True)
    spy_on(game, 'tile', returns=Tile(2983, 3288))
    spy_on(execution, 'delay_until', impl=lambda fn, *args: done(fn()))
    spy_on(mc, 'bank_tile', returns=Tile(3013, 3355))
    spy_on(inventory, 'contains', returns=True)
    bot = mc.MuleCrafter()
    spy_on(bot, 'log')
    spy_on(bot, 'on')
    clean = spy_on(bot, '_clean_crafter_inventory', impl=lambda: done())
    bot.settings = SettingsBag({'mode': 'Crafter', 'partner': 'Runner_One', 'bank_fill': False})
    run_wait(bot.on_start())
    expect(clean.calls).to_equal([])
    expect(bot.partner_names()).to_equal(['runner one'])
    expect(bot.inside_meeting()).to_be(True)
    expect(bot.trading_active()).to_be(True)
    expect(bot.bank_due()).to_be(False)
    spy_on(mc, 'in_temple', returns=False)
    spy_on(mc, 'ess_count', returns=0)
    spy_on(trade, 'active', returns=False)
    expect(mc.EnterAltar(bot).validate()).to_be(True)
    expect(mc.CrafterGoBank(bot).validate()).to_be(False)
    expect(type(bot._tasks[0]).__name__).to_be('CrafterTradeAtRuins')
    bot.heard_trade_request(Fake(type='trade_request', username='Runner One'))
    expect(bot._requested_partner).to_be('Runner One')


test('crafter with bank visits disabled starts directly at the meeting without bank cleanup', crafter_without_bank_visits)


def kit_bank_first():
    bot = depot_stub()
    spy_on(bot, 'delay_log_item', returns=None)
    spy_on(bot, 'held_count', returns=0)
    spy_on(bank, 'count', impl=lambda name: 1 if name == 'Iron axe' else 0)
    withdrawn = spy_on(bank, 'withdraw_x', impl=lambda name, n: done())
    run_wait(fly.restock_axe(bot))
    expect(withdrawn.calls).to_equal([('Iron axe', 1)])
    spy_on(bot, 'delay_log_item', returns=Fake())
    run_wait(fly.restock_axe(bot))
    expect(len(withdrawn.calls)).to_be(1)


test('knife/log provisioning uses a banked axe only when a carrier log is missing', kit_bank_first)


def kit_ground_and_tree():
    bot = depot_stub()
    held = []
    spy_on(bot, 'held_count', impl=lambda name: 1 if name in held else 0)
    spy_on(inventory, 'count', impl=lambda name: 1 if name in held else 0)
    spy_on(bot, 'delay_log_item', impl=lambda: Fake() if 'Logs' in held else None)
    spy_on(bot, 'walk_home_if_needed', impl=lambda log: done())
    spy_on(execution, 'delay_until_ticks', impl=lambda fn, *args: done(fn()))
    def take(name):
        held.append(name)
        return True
    drops = [Fake(name='Knife', distance=lambda: 1, interact=lambda op: take('Knife')),
             Fake(name='Bronze axe', distance=lambda: 1, interact=lambda op: take('Bronze axe'))]
    spy_on(fly.ground_items, 'query', impl=lambda: FakeQuery(drops))
    tree = Fake(name='Tree', actions=lambda: ['Chop down'], interact=lambda op: take('Logs'), tile=lambda: Tile(3100, 3400), distance=lambda: 1)
    spy_on(fly.locs, 'query', impl=lambda: FakeQuery([tree]))
    spy_on(fly.traversal, 'walk_to', impl=lambda *args, **kwargs: done(True))
    expect(run_wait(fly.acquire_kit(bot))).to_be(True)
    expect(held).to_equal(['Knife', 'Bronze axe', 'Logs'])
    expect(run_wait(fly.acquire_kit(bot))).to_be(True)


test('missing fishing kit takes ground tools and chops a carrier log before returning to fish', kit_ground_and_tree)


def supply_same_named_ids():
    bot = depot_stub()
    spy_on(inventory, 'items', returns=[row(199, 'Herb', 5), row(201, 'Herb', 7)])
    first = Record({'id': 199, 'name': 'Herb', 'quantity': 10})
    second = Record({'id': 201, 'name': 'Herb', 'quantity': 10})
    expect(bot.held(first)).to_be(5)
    expect(bot.held(second)).to_be(7)
    expect(logic.line_key(first) != logic.line_key(second)).to_be(True)


test('supply keeps separate quantities for same-named item ids', supply_same_named_ids)


def cosmic_trade_kit():
    cosmic = rc.RUNES['Cosmic runes']
    bot = Fake(conf=cosmic, is_partner=lambda name: True, last_requester='Runner', adjacent_runner=lambda: None,
               say=lambda message: None)
    spy_on(trade, 'partner', returns='Runner')
    spy_on(trade, 'their_offer', returns=[row(1436, 'Rune essence', 25)])
    spy_on(trade, 'my_offer', returns=[row(772, 'Dramen staff')])
    declined = spy_on(trade, 'decline', impl=lambda: done())
    task = rc.HandleOpenTrade(bot)
    expect(run_wait(task.drive_offer_screen())).to_be(False)
    expect(len(declined.calls)).to_be(1)


test('Cosmic trade acceptance refuses to give away the retained Dramen staff', cosmic_trade_kit)


def mule_trade_screen_gap():
    clock = [0]
    active = [True]
    spy_on(trade, 'active', impl=lambda: active[0])
    spy_on(_core, 'step_time', impl=lambda: clock[0])
    for mode, task_class in [('Crafter', mc.CrafterTradeAtRuins), ('Mule', mc.MuleTradeExecute)]:
        bot = Fake(get_mode=lambda: mode, has_partners=lambda: True)
        task = task_class(bot)
        active[0] = True
        expect(task.validate()).to_be(True)
        # Neither screen is visible during the swap. The active task must still
        # outrank movement and a fresh request, which would decline the trade.
        active[0] = False
        expect(task.validate()).to_be(True)
        clock[0] += 300
        expect(task.validate()).to_be(True)
        active[0] = True
        expect(task.validate()).to_be(True)
        active[0] = False
        expect(task.validate()).to_be(True)
        clock[0] += 601
        expect(task.validate()).to_be(False)


test('both MuleCrafter roles retain trade priority across the screen transition', mule_trade_screen_gap)
