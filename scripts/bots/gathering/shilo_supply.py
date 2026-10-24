# The Shilo Village fly-fisher's supply run: bank for coins, buy feathers from Fernahei and vials of water from Obli,
# bank the vials, and walk back to the river. rs2b0t's scripts/GatheringBot/ShiloSupplyTrip.ts (MIT, see
# thirdparty/rs2b0t).

from rs2004.catalogs import COINS, SHILO_WATER_VENDOR, Record, shop_db, unit_price

INFINITE = 1 << 60


def shop_record(key):
    """A shop database entry as a Record whose items are Records, or None."""
    shop = shop_db().get(key)
    if shop is None:
        return None
    fields = {}
    for field in shop:
        fields[field] = shop[field]
    fields['items'] = [Record(item) for item in shop['items']]
    return Record(fields)


class Shelf:
    def __init__(self, shop, name, keeper, stand):
        self.shop = shop
        self.name = name
        self.keeper = keeper
        self.stand = stand


def cart(shelf, stock, coins, slots):
    """How many of the shelf's item the coins and slots buy with `stock` on it, and what they cost: a Record of
    quantity and cost."""
    item = None
    for line in shelf.shop.items:
        if line.name == shelf.name:
            item = line
            break
    quantity = 0
    cost = 0
    if item is not None:
        room = (item.baseline if slots > 0 else 0) if item.stackable else slots
        cap = min(stock, item.baseline, room)
        while quantity < cap:
            price = unit_price(item, shelf.shop, stock - quantity)
            if cost + price > coins:
                break
            cost += price
            quantity += 1
    return Record({'quantity': quantity, 'cost': cost})


class ShiloSupplyTrip:
    """A run in phases, one step a call: 'idle', 'bank-outbound', 'feathers', 'water-vials', 'bank-return' and
    'home'."""

    def __init__(self):
        self.phase = 'idle'

    @property
    def active(self):
        return self.phase != 'idle'

    def step(self, bot):
        """Use with yield from."""
        vendor = bot.bait_vendor()
        feather_shop = shop_record('shilofishingshop')
        vial_shop = shop_record('shilojunglestore')
        if vendor is None or feather_shop is None or vial_shop is None:
            return
        feathers = Shelf(feather_shop, vendor.item, vendor.keeper, vendor.stand)
        vials = Shelf(vial_shop, SHILO_WATER_VENDOR.item, SHILO_WATER_VENDOR.keeper, SHILO_WATER_VENDOR.stand)
        if self.phase == 'idle' or self.phase == 'bank-outbound':
            if not self.active:
                bot.note_guild_feather_trip()
            self.phase = 'bank-outbound'
            banked = yield from self.bank(bot, feathers, vials)
            if banked:
                self.phase = 'feathers'
        elif self.phase == 'feathers':
            yield from self.buy(bot, feathers)
            self.phase = 'water-vials'
        elif self.phase == 'water-vials':
            yield from self.buy(bot, vials)
            self.phase = 'bank-return' if inventory.contains(vials.name) else 'home'
        elif self.phase == 'bank-return':
            banked = yield from self.bank(bot)
            if banked:
                self.phase = 'home'
        elif self.phase == 'home':
            home = yield from bot.walk_home_if_needed()
            if home:
                bot.note_guild_feather_trip()
                self.phase = 'idle'

    def bank(self, bot, feathers=None, vials=None):
        """Banks all but the coins and the fishing gear, and on the way out draws what the feathers and the most a
        trip of vials can cost. Use with yield from."""
        log = lambda message: bot.log(f'  {message}')
        bot.set_status('supplies: banking')
        if bank.is_open():
            closed = yield from bot.close_script_bank(log, False)
            if not closed:
                return False
        snapshot = bank.normal_backpack_snapshot()
        if snapshot is None:
            return False
        opened = yield from bot.open_script_bank(log)
        if not opened:
            return False
        ready = yield from bank.wait_ready(4000)
        settled = False
        if ready:
            settled = yield from bank.backpack_ready(snapshot, log)
        if not settled:
            yield from bot.close_script_bank(log, False)
            return False
        gear = bot.fish_method.gear if bot.fish_method is not None else []
        keep = set(['coins'] + [piece.name.lower() for piece in gear])
        expected = [item for item in snapshot if (item.name or '').lower() in keep]
        yield from bank.deposit_all_matching(lambda name, id: name.lower() not in keep)
        cleared = yield from bank.backpack_ready(expected, log)
        if cleared and feathers is not None:
            slots = max(0, inventory.free() - (0 if inventory.contains('Coins') else 1) - (0 if inventory.contains('Feather') else 1))
            vial_baseline = 0
            for item in vials.shop.items:
                if item.name == vials.name:
                    vial_baseline = item.baseline
            vial_reserve = 0
            for stock in range(1, vial_baseline + 1):
                vial_reserve = max(vial_reserve, cart(vials, stock, INFINITE, slots).cost)
            budget = cart(feathers, 800, INFINITE, 1).cost + vial_reserve
            draw = min(bank.count('Coins'), max(0, budget - inventory.count('Coins')))
            if draw > 0:
                yield from bank.withdraw_x('Coins', draw)
        closed = yield from bot.close_script_bank(log, False)
        return cleared and closed

    def buy(self, bot, shelf):
        """Use with yield from."""
        bot.set_status(f'supplies: {shelf.keeper}')
        log = lambda message: bot.log(f'  {message}')
        arrived = yield from traversal.walk_resilient(shelf.stand, radius=0, attempts=3, timeout_ms=60000, log=log)
        if not arrived:
            return
        opened = yield from shop.open(shelf.keeper)
        if not opened:
            return
        stock = 0
        for line in shop.stock():
            if line.name == shelf.name:
                stock = line.count
                break
        slots = inventory.free() + (1 if shelf.name == 'Feather' and inventory.contains(shelf.name) else 0)
        quantity = cart(shelf, stock, inventory.count(COINS), slots).quantity
        if quantity > 0:
            yield from shop.buy(shelf.name, quantity)
        # rs2b0t's finally: a raise ends the bot, so only the normal exit needs it.
        yield from shop.close()
