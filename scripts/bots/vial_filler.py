# Fills vials at Falador's fountain: banks empty vials, fills them one by one, and every Nth trip can restock
# from Jatix in Taverley. rs2b0t's VialFiller (MIT, see thirdparty/rs2b0t).

EMPTY_VIAL = 'Vial'
WATER_VIAL = 'Vial of water'
COINS = 'Coins'
# Falador's only fountain is beside the west bank; the east bank adds about 64 tiles each way.
FOUNTAIN = Tile(2949, 3381, 0)
JATIX_STAND = Tile(2899, 3427, 0)
JATIX = 'Jatix'
BANK_STANDS = {
    'Falador West': Tile(2946, 3369, 0),
    'Falador East': Tile(3013, 3355, 0),
}

SETTINGS = {
    'bank': SettingDef('string', 'Falador West', 'Which Falador bank', options=list(BANK_STANDS.keys()), help='the fountain is 12 tiles from the west bank and 64 from the east one'),
    'buy_vials': SettingDef('boolean', False, 'Buy vials at Jatix?', help="every Nth trip, restock empty vials from Jatix's herblore shop in Taverley (members area)"),
    'buy_every_runs': SettingDef('number', 5, 'Shop run every N trips', 1, 50),
    'buy_qty': SettingDef('number', 27, 'Empty vials to buy', 1, 28, help='vials do not stack, so a restock is capped by free pack space'),
    'coins_per_trip': SettingDef('number', 1000, 'Coins to top up to', 1, 100000, help='only withdrawn on a shop run'),
}


def vials_to_buy(free_slots, want):
    """Empty vials don't stack, so a restock can only be as big as the free pack."""
    return max(0, min(free_slots, want))


def is_shop_run(runs, buy_vials, every_n):
    """A shop run happens every Nth completed trip, never the first: the first proves the bank and fountain
    loop before the walk to Taverley."""
    if not buy_vials or runs <= 0 or every_n <= 0:
        return False
    return runs % every_n == 0


class VialFiller(LoopingBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.bank_label = s.str('bank', 'Falador West')
        self.bank_stand = BANK_STANDS.get(self.bank_label, BANK_STANDS['Falador West'])
        self.buy_vials = s.bool('buy_vials', False)
        self.buy_every = s.num('buy_every_runs', 5)
        self.buy_qty = s.num('buy_qty', 27)
        self.coin_float = s.num('coins_per_trip', 1000)
        self.runs = 0
        self.filled = 0
        self.bought = 0
        self.status = 'starting'
        restock = f', Jatix restock every {self.buy_every} trips' if self.buy_vials else ''
        self.log(f'VialFiller; {self.bank_label} bank -> Falador fountain{restock}')

    # Why: vials don't stack and have nowhere to go once the pack is full of water vials.
    # Why: the restock buys what the fill leg is about to fill, so it runs while the pack is still empty.
    def loop(self):
        shop_run = is_shop_run(self.runs, self.buy_vials, self.buy_every)
        banked = yield from self.bank_leg(shop_run)
        if not banked:
            return
        if shop_run:
            shopped = yield from self.shop_leg()
            if not shopped:
                return
        filled = yield from self.fill_leg()
        if not filled:
            return
        self.runs += 1

    def walk_to(self, dest, what):
        here = game.tile()
        if here is not None and max(abs(here.x - dest.x), abs(here.z - dest.z)) <= 4:
            return True
        self.status = f'walking to {what}'
        arrived = yield from traversal.walk_resilient(dest, radius=3, attempts=2, timeout_ms=60000, log=lambda m: self.log(f'  {m}'))
        return arrived

    def bank_leg(self, shop_run):
        arrived = yield from self.walk_to(self.bank_stand, f'the {self.bank_label} bank')
        if not arrived:
            return False
        self.status = 'banking'
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            self.log('could not open the bank; retrying')
            return False

        yield from bank.deposit_all_matching(lambda name, id: name.lower() != COINS.lower())
        if shop_run:
            if inventory.count(COINS) < self.coin_float / 2 and bank.count(COINS) > 0:
                yield from bank.withdraw_x(COINS, self.coin_float)
            if inventory.count(COINS) == 0:
                self.request_finish('no coins to restock vials with')
                return False
        elif bank.count(EMPTY_VIAL) == 0:
            if self.buy_vials:
                self.log(f'no {EMPTY_VIAL}s in the bank; the Jatix restock will refill on trip {self.buy_every}, or bank some vials.')
            else:
                self.request_finish(f'no {EMPTY_VIAL}s left in the bank')
            return False
        else:
            yield from bank.withdraw_x(EMPTY_VIAL, inventory.free())

        yield from bank.close()
        return shop_run or inventory.count(EMPTY_VIAL) > 0

    def shop_leg(self):
        arrived = yield from self.walk_to(JATIX_STAND, JATIX)
        if not arrived:
            return False
        self.status = 'buying vials'
        opened = yield from shop.open(JATIX)
        if not opened:
            self.log(f"could not open {JATIX}'s shop; retrying")
            return False
        bought = yield from shop.buy(EMPTY_VIAL, vials_to_buy(inventory.free(), self.buy_qty))
        self.bought += bought
        yield from shop.close()
        self.log(f'bought {bought} {EMPTY_VIAL}s')
        if bought == 0:
            self.log(f'{JATIX} had no {EMPTY_VIAL}s in stock; waiting for a restock')
            return False
        return True

    def fill_leg(self):
        arrived = yield from self.walk_to(FOUNTAIN, 'the fountain')
        if not arrived:
            return False

        # The engine fills one container per use, so this repeats once per vial.
        guard = backpack_capacity() + 2
        while inventory.count(EMPTY_VIAL) > 0 and guard > 0:
            guard -= 1
            fountain = locs.query().name('Fountain').within(6).nearest()
            if fountain is None:
                self.log('no Fountain in reach; repathing')
                return False
            vial = inventory.first(EMPTY_VIAL)
            if vial is None:
                break
            before = inventory.count(EMPTY_VIAL)
            self.status = f'filling {before} vials'
            if not vial.use_on(fountain):
                self.log('use-on-fountain was rejected; retrying')
                return False
            filled = yield from execution.delay_until(lambda: inventory.count(EMPTY_VIAL) < before, 4000)
            if not filled:
                self.log('a vial did not fill; repathing')
                return False
            self.filled += 1
            # The fill is a protected op, so you're still busy this tick, and the next use sent at once is dropped.
            yield from execution.delay_ticks(1)

        water = inventory.count(WATER_VIAL)
        self.log(f'filled {water} {WATER_VIAL}')
        return water > 0

    def on_progress_report(self):
        return {'Status': self.status, 'Trips': self.runs, 'Filled': self.filled, 'Bought': self.bought, 'Coins': inventory.count(COINS)}


BOT = define_bot(
    name='VialFiller',
    create=VialFiller,
    description='Falador vial-filling loop — banks empty vials, fills them one by one at the fountain, and can restock from Jatix in Taverley every Nth trip',
    category='Herblore',
    tags=['falador', 'vials', 'water', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
