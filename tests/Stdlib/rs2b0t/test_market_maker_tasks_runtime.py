"""rs2b0t's MarketMaker/tasks.test.ts through the headless task scheduler (MIT, see thirdparty/rs2b0t)."""

import bots.market_maker as market
from bots.market_maker import Accepted, MarketMaker
from rs2004.bank import bank, banking
from rs2004.bot import TaskBot
from rs2004.catalogs import Record
from rs2004.dialogue import modals
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.market import PriceBooks, catalog
from rs2004.settings import SettingsBag, settings_store
from rs2004.trade import trade

after_each(catalog.reset_live_catalog)


def result(value):
    return value
    yield


class MarketWorld(Scene):
    def __init__(self, stock=None, settings=None):
        Scene.__init__(self, Tile(2725, 3491))
        self.money = {995: 200000}
        self.stock = {989: 24, 995: 200000}
        if stock is not None:
            self.stock.update(stock)
        self.open = False
        self.note_mode = False
        self.offered = []
        self.record_list = [Record({'id': 995, 'name': 'Coins', 'cost': 1, 'stackable': True, 'certlink': -1, 'certtemplate': -1}),
                            Record({'id': 989, 'name': 'Crystal key', 'cost': 100, 'stackable': False, 'certlink': -1, 'certtemplate': -1})]
        for id, name in [[1163, 'Rune full helm'], [1127, 'Rune platebody'], [1079, 'Rune platelegs']]:
            self.record_list.append(Record({'id': id, 'name': name, 'cost': 100, 'stackable': False, 'equippable': True, 'certlink': -1, 'certtemplate': -1}))
            self.record_list.append(Record({'id': id + 1, 'name': name, 'cost': 100, 'stackable': True, 'certlink': id, 'certtemplate': 799}))
        catalog.reset_live_catalog()
        settings_store.load({})
        spy_on(reader, 'obj_catalog', impl=lambda: self.record_list)
        spy_on(game, 'ingame', returns=True)
        spy_on(game, 'scene_ready', returns=True)
        spy_on(modals, 'main', impl=lambda: 5292 if self.open else -1)
        spy_on(market, 'nearest_bank', returns={'name': 'Seers', 'tile': {'x': 2725, 'z': 3491, 'level': 0}})
        spy_on(market, 'now_ms', impl=lambda: 1000000 + self.clock)
        spy_on(bank, 'is_open', impl=lambda: self.open)
        spy_on(bank, 'snapshot_ready', impl=lambda: self.open)
        spy_on(bank, 'items', impl=lambda: self.snapshots(self.stock, True))
        spy_on(bank, 'close', impl=self.close_bank)
        spy_on(bank, 'set_note_mode', impl=self.notes)
        spy_on(bank, 'withdraw_x_by_id', impl=self.withdraw)
        spy_on(bank, 'deposit_all_matching', impl=self.deposit)
        spy_on(banking, 'open', impl=self.open_bank)
        spy_on(trade, 'active', returns=False)
        spy_on(trade, 'request', returns=True)
        spy_on(PriceBooks, 'by_name', returns=Record({'name': 'Keys', 'margin': 0, 'max_trade_value': 1000000,
            'rows': [Record({'id': id, 'mid': 100, 'cap': 100, 'buying': True, 'selling': True}) for id in [989, 1163, 1127, 1079]]}))
        self.bot = MarketMaker()
        self.bot.settings = SettingsBag(settings or {})
        self.bot.bind_log(self.log)
        spy_on(self.bot, 'sort_bank_now', impl=self.sort_bank)
        self.sync()
        run_wait(self.bot.on_start())
        run_wait(bank.close())
        self.bot.sort_owed = False

    def snapshots(self, counts, stacked=False):
        rows = []
        for id, count in counts.items():
            if count <= 0:
                continue
            record = [r for r in self.record_list if r.id == id][0]
            stack = stacked or record.stackable
            for n in range(1 if stack else count):
                rows.append(Fake(id=id, name=record.name, count=count if stack else 1,
                                 slot=len(rows), noted=id in [1164, 1128, 1080]))
        return rows

    def sync(self):
        self.pack = self.snapshots(self.money)

    def open_bank(self, **opts):
        self.open = True
        return True
        yield

    def close_bank(self):
        self.open = False
        return True
        yield

    def notes(self, on):
        self.note_mode = on
        return
        yield

    def withdraw(self, id, count, lands_as_id=None):
        target = id + 1 if self.note_mode and id in [1163, 1127, 1079] else id
        record = [r for r in self.record_list if r.id == target][0]
        room = count if record.stackable else 28 - len(self.pack)
        take = min(count, self.stock.get(id, 0), room)
        self.money[target] = self.money.get(target, 0) + take
        self.stock[id] = self.stock.get(id, 0) - take
        self.sync()
        return take == count
        yield

    def deposit(self, predicate):
        for id in list(self.money.keys()):
            name = [r.name for r in self.record_list if r.id == id][0]
            if predicate(name, id):
                self.stock[id] = self.stock.get(id, 0) + self.money.pop(id)
        self.sync()
        return
        yield

    def sort_bank(self):
        self.bot.sort_owed = False
        return
        yield

    def tick(self):
        self.sync()
        run_wait(TaskBot.loop(self.bot))

    def order(self):
        self.bot.desk.remember(Record({'customer': 'Alice', 'item_id': 989, 'max_qty': 24, 'asked_at_ms': 1000000 + self.clock}))

    def fail_trade(self, name, opened=True):
        window = self.bot.desk.open(name, 900000 + self.clock)
        window.saw_open = opened
        self.bot.drop_expired()


def rune_sets(short=False):
    return MarketWorld({1163: 10, 1127: 4 if short else 10, 1079: 8 if short else 10})


def sale_as_notes():
    world = rune_sets()
    bot = world.bot
    bot.handle_command('Alice', 'Buying 10 rune sets')
    expect(bot.desk.intent_for('Alice', 1000000, 90000).max_qty).to_be(10)
    bot.trade_requests.add('Alice')
    world.tick()
    for id in [1164, 1128, 1080]:
        expect(world.money.get(id)).to_be(10)
    expect(bot.sale_ready()).to_be(True)
    world.tick()
    expect(bot.desk.current().customer).to_be('Alice')


test('a chat order fetches ten complete rune sets as notes before opening its trade', sale_as_notes)


def scarce_set():
    world = rune_sets(True)
    world.bot.handle_command('Alice', 'buying 10 rune sets')
    expect(world.bot.desk.intent_for('Alice', 1000000, 90000).max_qty).to_be(4)


test('a set quote is limited by the least-stocked piece', scarce_set)


def offers_each_component(confirmed):
    world = rune_sets()
    world.bot.handle_command('Alice', 'buying 10 rune sets')
    world.tick()
    offered = []
    attempts = []
    spy_on(trade, 'my_offer', impl=lambda: offered)
    spy_on(trade, 'remove_all', impl=lambda: result(True))

    def offer(name, count, pick=None):
        attempts.append(name)
        item = [i for i in world.pack if i.name == name and (pick is None or pick(i))][0]
        if confirmed or name == 'Rune full helm':
            offered.append(Fake(id=item.id, name=name, count=count))
        return True
        yield

    spy_on(trade, 'offer', impl=offer)
    expect(run_wait(world.bot.put_up({1163: 10, 1127: 10, 1079: 10}))).to_be(confirmed)
    expect(attempts).to_equal(['Rune full helm', 'Rune platebody', 'Rune platelegs'] if confirmed else ['Rune full helm', 'Rune platebody'])
    if confirmed:
        expect([(item.id, item.count) for item in offered]).to_equal([(1164, 10), (1128, 10), (1080, 10)])


test_each([True, False])('every noted set component needs its own offer acknowledgement: %s', offers_each_component)


def mid_trip_shortage():
    world = rune_sets()
    world.bot.handle_command('Alice', 'buying 10 rune sets')
    world.stock[1127] = 3
    world.tick()
    expect(world.bot.desk.intent_for('Alice', 1000000, 90000).max_qty).to_be(3)
    expect(world.bot.sale_ready()).to_be(True)


test('a restock shortage reduces every component to complete sets', mid_trip_shortage)


def prepared_keys(request_first):
    world = MarketWorld()
    world.order()
    if request_first:
        world.bot.trade_requests.add('Alice')
    world.tick()
    expect(world.money.get(989)).to_be(24)
    expect(world.stock.get(989)).to_be(0)
    expect(len(world.pack)).to_be(25)
    if not request_first:
        world.tick()
        expect(world.money.get(989)).to_be(24)
        world.bot.trade_requests.add('Alice')
    world.tick()
    expect(world.bot.desk.current().customer).to_be('Alice')


test_each([True, False])('prepared nonnoteable keys stay in the pack until the buyer trades, request_first=%s', prepared_keys)


def crowded_purchase():
    world = MarketWorld()
    world.money[989] = 24
    world.bot.trade_requests.add('Bob')
    world.tick()
    expect(world.bot.desk.current()).to_be_null()
    expect(world.money.get(989, 0)).to_be(0)
    world.tick()
    expect(world.bot.desk.current().customer).to_be('Bob')


test('a crowded pack banks before accepting an incoming purchase', crowded_purchase)


def settle_before_sale(reason):
    world = MarketWorld()
    world.order()
    world.tick()
    if reason == 'cash':
        world.money[995] = 250000
    else:
        run_wait(world.bot.reset_state())
        world.order()
    world.bot.trade_requests.add('Alice')
    world.tick()
    expect(world.bot.desk.current()).to_be_null()
    expect(world.money.get(989, 0)).to_be(0)
    expect(world.stock.get(989)).to_be(24)
    world.tick()
    expect(world.money.get(989)).to_be(24)
    world.tick()
    expect(world.bot.desk.current().customer).to_be('Alice')


test_each(['cash', 'reset'])('settles %s before re-fetching and opening a prepared sale', settle_before_sale)


def blacklist_fifth():
    world = MarketWorld(settings={'blacklist': ['Eve'], 'cooldown_seconds': 0})
    for n in range(4):
        world.fail_trade('Alice' if n % 2 == 0 else ' alice ')
        expect(world.bot.blocked('Alice')).to_be(False)
    world.fail_trade('ALICE')
    expect(world.bot.blocked('Alice')).to_be(True)
    expect(world.bot.blocked('Eve')).to_be(True)
    expect(settings_store.saved('MarketMaker', 'blacklist')).to_equal(['eve', 'alice'])
    world.bot.trade_requests.add('Alice')
    world.tick()
    expect(world.bot.desk.current()).to_be_null()
    expect('Alice' in world.bot.trade_requests).to_be(False)


test('the fifth opened failure persists a normalized blacklist and rejects later requests', blacklist_fifth)


def completed_resets_only_customer():
    world = MarketWorld()
    for n in range(4):
        world.fail_trade('Alice')
        world.fail_trade('Bob')
    world.bot.completed(Accepted({989: 1}, {995: 100}), ' ALICE ')
    world.fail_trade('Bob')
    expect(world.bot.blocked('Bob')).to_be(True)
    for n in range(4):
        world.fail_trade('Alice')
        expect(world.bot.blocked('Alice')).to_be(False)
    world.fail_trade('Alice')
    expect(world.bot.blocked('Alice')).to_be(True)


test('completion resets consecutive failures only for the completed customer', completed_resets_only_customer)


def unopened_not_counted():
    world = MarketWorld()
    for n in range(5):
        world.fail_trade('Alice', False)
    for n in range(4):
        world.fail_trade('Alice')
    expect(world.bot.blocked('Alice')).to_be(False)
    world.fail_trade('Alice')
    expect(world.bot.blocked('Alice')).to_be(True)


test('requests that never opened do not count toward blacklisting', unopened_not_counted)


def closure_grace():
    world = MarketWorld()
    for n in range(5):
        world.bot.desk.open('Alice', 1000000 + world.clock).saw_open = True
        world.bot.drop_expired()
        world.clock += 2999
        world.bot.drop_expired()
        expect(world.bot.blocked('Alice')).to_be(False)
        world.clock += 1
        world.bot.drop_expired()
        world.bot.drop_expired()
        expect(world.bot.blocked('Alice')).to_be(n == 4)


test('the screen-transition grace period counts each closed trade only once', closure_grace)


def release_not_failure():
    world = MarketWorld()
    for n in range(4):
        world.fail_trade('Alice')
    world.bot.desk.open('Alice', 1000000).saw_open = True
    world.bot.release('Alice', 'shop could not offer items')
    expect(world.bot.blocked('Alice')).to_be(False)
    world.fail_trade('Alice')
    expect(world.bot.blocked('Alice')).to_be(True)


test('releasing an opened trade leaves the failure streak unchanged', release_not_failure)


def confirmation(outcome):
    world = MarketWorld()
    for n in range(4):
        world.fail_trade('Alice')
    window = world.bot.desk.open('Alice', 1000000)
    window.accepted = Accepted({989: 1}, {995: 100})
    active = [True]
    spy_on(trade, 'active', impl=lambda: active[0])
    spy_on(trade, 'partner', returns='Alice')
    spy_on(trade, 'on_confirm_screen', returns=True)
    spy_on(trade, 'confirm_ready', returns=True)
    spy_on(trade, 'my_offer', returns=[Fake(id=989, name='Crystal key', count=1)])
    spy_on(trade, 'their_offer', returns=[Fake(id=995, name='Coins', count=100)])

    def accept():
        if outcome == 'late':
            return True
        active[0] = False
        world.money[995 if outcome == 'completed' else 989] = 200100 if outcome == 'completed' else 1
        world.sync()
        return True

    spy_on(trade, 'accept', impl=accept)
    world.tick()
    if outcome == 'late':
        active[0] = False
        world.money[995] = 200100
        world.tick()
    expect(world.bot.desk.current()).to_be_null()
    expect(world.bot.blocked('Alice')).to_be(outcome == 'cancelled')
    if outcome != 'cancelled':
        world.fail_trade('Alice')
        expect(world.bot.blocked('Alice')).to_be(False)


test_each(['cancelled', 'completed', 'late'])('reconciles a %s confirmation by actual inventory receipt', confirmation)


def stalled_confirmation():
    world = MarketWorld()
    for n in range(4):
        world.fail_trade('Alice')
    world.bot.desk.open('Alice', 900000).saw_open = True
    spy_on(trade, 'active', returns=True)
    spy_on(trade, 'partner', returns='Alice')
    spy_on(trade, 'on_confirm_screen', returns=True)
    declined = spy_on(trade, 'decline', impl=lambda: result(True))
    world.tick()
    expect(len(declined.calls)).to_be(1)
    expect(world.bot.blocked('Alice')).to_be(True)


test('an abandoned confirmation screen still times out and counts an opened failure', stalled_confirmation)
