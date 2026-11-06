"""rs2b0t's GatheringBot/ShiloSupplyTrip scenarios (MIT, see thirdparty/rs2b0t)."""

import _core
import bots.gathering.bot as gathering
from bots.gathering.bot import GatheringBot
from bots.gathering.shilo_supply import ShiloSupplyTrip, shop_record
from bots.gathering.tasks import BuyShiloSupplies, Gather
from rs2004.bank import bank
from rs2004.catalogs import unit_price
from rs2004.game import game
from rs2004.execution import event_signal
from rs2004.geometry import Tile
from rs2004.trade import shop


class ShiloWorld(Scene):
    def __init__(self, shilo=True):
        Scene.__init__(self, Tile(2852, 2954))
        self.contents = {'Coins': 10000, 'Fly fishing rod': 1, 'Feather': 10, 'Raw trout': 24, 'Hammer': 1}
        self.bank_coins = 10000
        self.drawn = 0
        self.deposited = {}
        self.bank_open = False
        self.open_ok = True
        self.ready = True
        self.deposit_ok = True
        self.side_ready = True
        self.lose_snapshot = False
        self.close_ok = True
        self.feather_stock = 800
        self.vial_stock = 50
        self.vial_listed = True
        self.keeper = ''
        self.events = []
        self.purchases = []
        self.shopping_packs = []
        self.bot = GatheringBot()
        self.bot.fishing = True
        self.bot.guild_feather_minutes = 15
        self.bot.last_guild_feather_at = 0
        self.bot.location = Fake(bait_vendor=Fake(item='Feather', keeper='Fernahei' if shilo else 'Gerrant', stand=self.at))
        self.bot.fish_method = Fake(gear=[Fake(name='Fly fishing rod'), Fake(name='Feather')])
        self.bot.shilo_supply_trip = ShiloSupplyTrip()
        self.bot.bind_log(self.log)
        spy_on(self.bot, 'set_status', returns=None)
        spy_on(self.bot, 'open_script_bank', impl=self.open_bank)
        spy_on(self.bot, 'close_script_bank', impl=self.close_bank)
        spy_on(self.bot, 'walk_home_if_needed', impl=self.home)
        spy_on(self.bot, 'allow_combat_gather', returns=False)
        spy_on(self.bot, 'should_suppress_camp_reentry', returns=False)
        spy_on(self.bot, 'cook_enabled', returns=False)
        spy_on(self.bot, 'burn_enabled', returns=False)
        spy_on(self.bot, 'has_gear', returns=True)
        spy_on(gathering, 'now_ms', impl=lambda: 1000000 + self.clock)
        spy_on(event_signal, 'pending', returns=False)
        spy_on(game, 'animating', returns=True)
        spy_on(bank, 'is_open', impl=lambda: self.bank_open)
        spy_on(bank, 'wait_ready', impl=lambda timeout_ms=4000: self.result(self.ready))
        spy_on(bank, 'side_items', impl=lambda: list(self.pack) if self.side_ready else [])
        spy_on(_core, 'has_inventory', impl=lambda com: self.side_ready)
        spy_on(bank, 'count', impl=lambda name: self.bank_coins)
        spy_on(bank, 'withdraw_x', impl=self.withdraw)
        spy_on(bank, 'deposit_all_matching', impl=self.deposit)
        spy_on(shop, 'open', impl=self.open_shop)
        spy_on(shop, 'stock', impl=self.stock)
        spy_on(shop, 'buy', impl=self.buy)
        spy_on(shop, 'close', impl=lambda: self.result(True))
        self.task = BuyShiloSupplies(self.bot)
        self.sync()

    def result(self, value):
        return value
        yield

    def sync(self):
        self.pack = []
        for name, count in self.contents.items():
            if count <= 0:
                continue
            stacked = name in ['Coins', 'Feather']
            for n in range(1 if stacked else count):
                self.pack.append(Fake(name=name, id=995 if name == 'Coins' else len(self.pack),
                                      count=count if stacked else 1, slot=len(self.pack)))

    def open_bank(self, log):
        self.events.append('bank')
        self.bank_open = self.open_ok
        return self.open_ok
        yield

    def close_bank(self, log, force=False):
        if self.close_ok:
            self.bank_open = False
        return self.close_ok
        yield

    def withdraw(self, name, count):
        self.drawn += count
        self.bank_coins -= count
        self.contents['Coins'] = self.contents.get('Coins', 0) + count
        self.sync()
        return True
        yield

    def deposit(self, matches):
        self.events.append('deposit')
        if self.lose_snapshot:
            self.side_ready = False
            return
        if self.deposit_ok:
            for name in list(self.contents.keys()):
                if matches(name, 0):
                    self.deposited[name] = self.deposited.get(name, 0) + self.contents.pop(name)
        self.sync()
        return
        yield

    def home(self):
        self.events.append('home')
        return True
        yield

    def open_shop(self, keeper):
        self.keeper = keeper
        self.events.append(keeper)
        self.shopping_packs.append([name for name in self.contents if self.contents[name] > 0])
        return True
        yield

    def stock(self):
        if self.keeper == 'Obli':
            return [Fake(name='Vial of water', count=self.vial_stock)] if self.vial_listed else []
        return [Fake(name='Feather', count=self.feather_stock)]

    def buy(self, name, count):
        record = shop_record('shilojunglestore' if name == 'Vial of water' else 'shilofishingshop')
        item = [item for item in record.items if item.name == name][0]
        stock = self.vial_stock if name == 'Vial of water' else self.feather_stock
        cost = sum([unit_price(item, record, stock - n) for n in range(count)])
        expect(cost <= self.contents.get('Coins', 0)).to_be(True)
        self.contents['Coins'] -= cost
        self.contents[name] = self.contents.get(name, 0) + count
        self.purchases.append((name, count))
        self.sync()
        return count
        yield

    def run(self):
        self.sync()
        for leg in range(8):
            if not self.task.validate():
                return
            run_wait(self.task.execute())


def successful_trip(banked_coins):
    world = ShiloWorld()
    if banked_coins:
        world.contents.pop('Coins')
    world.run()
    expect(world.purchases).to_equal([('Feather', 800), ('Vial of water', 25)])
    expect(world.deposited.get('Vial of water')).to_be(25)
    expect(world.contents.get('Vial of water', 0)).to_be(0)
    expect(world.events[-1]).to_be('home')
    expect(world.task.validate()).to_be(False)
    if banked_coins:
        expect(world.drawn).to_be(8325)
    expect([sorted(pack) for pack in world.shopping_packs]).to_equal([sorted(['Coins', 'Fly fishing rod', 'Feather'])] * 2)


test_each([False, True])('banks fish and junk, shops, banks vials and returns; coins banked=%s', successful_trip)


def initial_failure(failure, partial=False):
    world = ShiloWorld()
    if partial:
        world.contents['Raw trout'] = 1
    setattr(world, failure, False)
    world.run()
    expect(world.purchases).to_equal([])
    expect(world.shopping_packs).to_equal([])
    expect(world.bot.shilo_supply_trip.phase).to_be('bank-outbound')
    expect(world.task.validate()).to_be(True)
    expect(Gather(world.bot).validate()).to_be(False)


test_each(['open_ok', 'ready', 'deposit_ok', 'close_ok'])('outbound bank failure remains latched: %s', initial_failure)
test_each([['open_ok', True], ['deposit_ok', True]])('partial-pack outbound bank failure remains latched: %s partial=%s', initial_failure)


def final_failure(failure):
    world = ShiloWorld()
    for _ in range(3):
        run_wait(world.task.execute())
    setattr(world, failure, False)
    run_wait(world.task.execute())
    expect(world.bot.shilo_supply_trip.phase).to_be('bank-return')
    expect(world.task.validate()).to_be(True)
    expect(Gather(world.bot).validate()).to_be(False)
    expect(world.shopping_packs).to_have_length(2)
    setattr(world, failure, True)
    run_wait(world.task.execute())
    run_wait(world.task.execute())
    expect(world.task.validate()).to_be(False)


test_each(['open_ok', 'deposit_ok', 'close_ok'])('final bank failure blocks gathering until confirmed: %s', final_failure)


def unavailable_stock(absent):
    world = ShiloWorld()
    world.vial_stock = 0
    world.vial_listed = not absent
    world.run()
    expect(world.purchases).to_equal([('Feather', 800)])
    expect(world.events.count('Obli')).to_be(1)
    expect(world.events[-1]).to_be('home')
    expect(world.task.validate()).to_be(False)


test_each([False, True])('missing optional vial stock does not wait for a restock; absent=%s', unavailable_stock)


def budget(coins, feather_stock, expected):
    world = ShiloWorld()
    world.contents['Coins'] = coins
    world.bank_coins = 0
    world.feather_stock = feather_stock
    world.run()
    expect(world.purchases).to_equal(expected)
    expect(world.task.validate()).to_be(False)


test_each([[10, 800, [('Feather', 5)]], [10, 1, [('Vial of water', 3)]], [1, 800, []]])(
    'small shared budget prioritizes affordable feathers: coins=%s stock=%s purchases=%s', budget)


def empty_shelves():
    world = ShiloWorld()
    world.feather_stock = 0
    world.vial_stock = 0
    world.run()
    expect(world.purchases).to_equal([])
    expect(world.events[-1]).to_be('home')
    expect(world.task.validate()).to_be(False)


test('empty shelves finish the trip without retrying either shop', empty_shelves)


def lost_side_snapshot():
    world = ShiloWorld()
    world.lose_snapshot = True
    world.run()
    expect(world.shopping_packs).to_equal([])
    expect(world.task.validate()).to_be(True)


test('an unloaded side snapshot cannot masquerade as a successful empty deposit', lost_side_snapshot)


def other_camp():
    world = ShiloWorld(False)
    expect(world.task.validate()).to_be(False)


test('the Shilo trip does not replace the Fishing Guild supplier', other_camp)
