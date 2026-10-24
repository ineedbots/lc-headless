# Parks at one shop and buys it out again and again on a total gp budget, banking between passes: rs2b0t's
# ShopBuyout (MIT, see thirdparty/rs2b0t). It plans each pass with the engine's own price curve, the dearest
# items first, and waits for the stock to come back when it's drained.

import time

from rs2004.catalogs import ContinueDialog, Record, buyout_plan, shop_db
from rs2004.quests.exec.primitives import talk_through


class ShopPreset:
    def __init__(self, label, keeper, shop_stand, bank_stand, banker=None, booth_name=None, booth_op=None):
        self.label = label
        self.keeper = keeper
        self.shop_stand = shop_stand
        self.bank_stand = bank_stand
        self.banker = banker
        self.booth_name = booth_name
        self.booth_op = booth_op


# shopPresets.ts
SHOP_PRESETS = [
    ShopPreset("Aemad's vials — East Ardougne (Ardougne East bank)", 'Aemad', Tile(2613, 3294, 0), Tile(2655, 3283, 0), None, 'Bank booth', 'Use-quickly'),
    ShopPreset('Mage Arena runes — Lundail (Gundai bank)', 'Lundail', Tile(2535, 4719, 0), Tile(2533, 4714, 0), 'Gundai'),
    ShopPreset("Betty's runes — Port Sarim (Falador West bank)", 'Betty', Tile(3012, 3258, 0), Tile(2946, 3369, 0)),
    ShopPreset("Aubury's runes — Varrock (Varrock East bank)", 'Aubury', Tile(3253, 3401, 0), Tile(3251, 3420, 0)),
    ShopPreset("Lowe's arrows — Varrock (Varrock East bank)", 'Lowe', Tile(3231, 3421, 0), Tile(3251, 3420, 0)),
    ShopPreset("Hickton's arrows — Catherby (Catherby bank)", 'Hickton', Tile(2821, 3442, 0), Tile(2809, 3441, 0)),
    ShopPreset("Gerrant's feathers — Port Sarim (Draynor bank)", 'Gerrant', Tile(3013, 3224, 0), Tile(3092, 3243, 0)),
    ShopPreset("Harry's fishing — Catherby (Catherby bank)", 'Harry', Tile(2833, 3443, 0), Tile(2809, 3441, 0)),
    ShopPreset("Fernahei's fishing — Shilo Village (Shilo bank)", 'Fernahei', Tile(2870, 2971, 0), Tile(2852, 2954, 0), 'Banker'),
    ShopPreset("Bob's axes — Lumbridge (Draynor bank)", 'Bob', Tile(3231, 3203, 0), Tile(3093, 3243, 0)),
    ShopPreset("Nurmof's pickaxes — Dwarven Mine (Falador East bank)", 'Nurmof', Tile(2997, 9844, 0), Tile(3013, 3355, 0)),
    ShopPreset('Wizard Guild runes — Yanille (Yanille bank)', 'Magic Store owner', Tile(2594, 3090, 1), Tile(2613, 3092, 0)),
]
DEFAULT_PRESET = SHOP_PRESETS[0]


def preset_by_label(label):
    for p in SHOP_PRESETS:
        if p.label == label:
            return p
    return None


def shop_record_of(keeper):
    """The shop database's record for the shop the keeper runs, as a Record, or None."""
    for key in shop_db():
        shop = shop_db()[key]
        if keeper in shop['keepers']:
            fields = {}
            for field in shop:
                fields[field] = shop[field]
            # A Record makes only its own dict fields Records, not those in a list.
            fields['items'] = [Record(item) for item in shop['items']]
            return Record(fields)
    return None


def preset_buyable_names():
    names = set()
    for p in SHOP_PRESETS:
        rec = shop_record_of(p.keeper)
        if rec is not None:
            for item in rec.items:
                names.add(item.name)
    return sorted(list(names))


SETTINGS = {
    'shop': SettingDef('string', DEFAULT_PRESET.label, 'Shop', options=[p.label for p in SHOP_PRESETS],
                       help='the shop to buy out — its trade tile and nearest bank are baked in'),
    'budget_gp': SettingDef('number', 250000, 'Total gp to spend', min=100, help='the session budget — the bot stops cleanly once roughly this much has been spent'),
    'per_trip_gp': SettingDef('number', 100000, 'Gp per bank trip', min=100),
    'stop_floor_gp': SettingDef('number', 5000, 'Stop below bank gp', min=0),
    'buy_items': SettingDef('string[]', [], 'Items to buy (empty = all stock)', options=preset_buyable_names(),
                            help='multi-select, valuable-first under the coin budget; leave empty to buy the shop out'),
    'recheck_seconds': SettingDef('number', 60, 'Restock recheck (s)', min=5, max=600,
                                  help='wait between buy passes once the stock is drained (elemental runes restock 1/30s, law/nature 1/3min)'),
}


class ShopBuyout(TaskBot):
    loop_delay = 600

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.status = 'starting'
        self.phase = 'bank'
        self.session_spent = 0
        self.session_haul = {}
        self.budget_gp = self.settings.num('budget_gp', 250000)
        self.per_trip_gp = self.settings.num('per_trip_gp', 100000)
        self.stop_floor_gp = self.settings.num('stop_floor_gp', 5000)
        preset = preset_by_label(self.settings.str('shop', DEFAULT_PRESET.label)) or DEFAULT_PRESET
        self.chosen = set([s.lower() for s in self.settings.list('buy_items', [])])
        self.keeper = preset.keeper
        self.banker = preset.banker or ''
        self.shop_stand = preset.shop_stand
        self.bank_stand = preset.bank_stand
        self.booth_name = preset.booth_name or 'Bank booth'
        self.booth_op = preset.booth_op or 'Use-quickly'
        self.recheck_ms = self.settings.num('recheck_seconds', 60) * 1000
        self.rec = shop_record_of(self.keeper)
        if self.rec is None:
            self.log(f"[buyout] '{self.keeper}' isn't a known shopkeeper — will buy ALL stock in shop order (no price model)")
        self.started_at = time.time()
        self.log(f'[buyout] {self.keeper} — budget {self.budget_gp}gp, {self.per_trip_gp}gp/trip, {len(self.chosen)} item names selected')
        self.add(ContinueDialog(), BankTrip(self), BuyoutPass(self))

    def set_status(self, s):
        self.status = s

    def budget_left(self):
        return max(0, self.budget_gp - self.session_spent)

    def haul_text(self):
        return ', '.join([f'{obj}×{self.session_haul[obj]}' for obj in self.session_haul]) or '(nothing)'

    def on_progress_report(self):
        minutes = int((time.time() - self.started_at) / 60)
        return {'Status': self.status, 'Runtime': f'{minutes}m', 'Coins': inventory.count('Coins'), 'Spent': f'{self.session_spent} of {self.budget_gp}', 'Haul': self.haul_text()}


class BankTrip(Task):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        return self.bot.phase == 'bank'

    def execute(self):
        bot = self.bot
        bot.set_status('banking')
        arrived = yield from traversal.walk_resilient(bot.bank_stand, radius=2, attempts=4, timeout_ms=60000, log=lambda m: bot.log(f'  {m}'))
        if not arrived:
            bot.log('[buyout] walk to the bank stand failed — will retry')
            return
        opened = yield from self.open_bank()
        if not opened:
            bot.log('[buyout] could not open the bank — will retry')
            return

        yield from bank.deposit_all_matching(lambda name, id: name != 'Coins')
        yield from execution.delay_ticks(1)

        if bot.budget_left() == 0:
            yield from bank.deposit_all_matching(lambda name, id: True)
            bot.set_status('budget spent — stopped')
            bot.request_finish(f'[buyout] budget spent ({bot.session_spent}gp). Haul: {bot.haul_text()}')
            return
        bank_gp = bank.count('Coins')
        if bank_gp < bot.stop_floor_gp:
            bot.set_status('bank dry — stopped')
            bot.request_finish(f'[buyout] bank coins {bank_gp} below floor {bot.stop_floor_gp}')
            return

        want = min(bot.per_trip_gp, bot.budget_left())
        need = want - inventory.count('Coins')
        if need > 0:
            took = yield from bank.withdraw_x('Coins', min(need, bank_gp))
            if not took:
                bot.log('[buyout] coin withdrawal failed — will retry')
                return
            bot.log(f'[buyout] withdraw {min(need, bank_gp)}gp ({bot.budget_left()}gp of the budget left)')
        bot.phase = 'buy'

    def open_bank(self):
        bot = self.bot
        if bank.is_open():
            return True
        if bot.banker == '':
            opened = yield from bank.open_nearest(bot.booth_name, bot.booth_op)
            return opened
        yield from talk_through(bot.banker, ['access my bank'], lambda m: bot.log(f'  {m}'))
        opened = yield from execution.delay_until(lambda: bank.is_open(), 4000)
        return opened


class BuyoutPass(Task):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        return self.bot.phase == 'buy'

    def need_space_for(self, want):
        rec = self.bot.rec
        if rec is None:
            return False
        defs = [i for i in rec.items if i.obj == want.obj]
        if len(defs) == 0:
            return False
        if defs[0].stackable:
            # A stackable needs a slot only when there's no stack yet.
            return inventory.count(defs[0].name) == 0 and inventory.is_full()
        return inventory.is_full()

    def needs_bank_first(self):
        """Some item the next pass would buy has no room in the pack."""
        if self.bot.rec is None:
            return False
        for want in self.plan(min(inventory.count('Coins'), self.bot.budget_left())):
            if self.need_space_for(want):
                return True
        return False

    def execute(self):
        bot = self.bot
        bot.set_status(f'buying out {bot.keeper}')
        arrived = yield from traversal.walk_resilient(bot.shop_stand, radius=2, attempts=4, timeout_ms=60000, log=lambda m: bot.log(f'  {m}'))
        if not arrived:
            bot.log('[buyout] walk to the shop failed — will retry')
            return

        # Room for every planned purchase before the shop opens.
        if self.needs_bank_first():
            bot.log('[buyout] inventory full — banking before opening shop')
            bot.phase = 'bank'
            return

        opened = yield from shop.open(bot.keeper)
        if not opened:
            bot.log(f"[buyout] could not open {bot.keeper}'s shop — will retry")
            return

        coins = min(inventory.count('Coins'), bot.budget_left())
        bought_units = 0
        for want in self.plan(coins):
            gp_before = inventory.count('Coins')
            bought = yield from shop.buy(want.name, want.units)
            spent = gp_before - inventory.count('Coins')
            if bought > 0:
                bot.session_haul[want.obj] = bot.session_haul.get(want.obj, 0) + bought
                bot.session_spent += spent
                bought_units += bought
                bot.log(f'[buyout] buy {want.obj} n={bought} spent={spent} (session {bot.session_spent}/{bot.budget_gp}gp)')
                if self.needs_bank_first():
                    bot.log(f'[buyout] inventory full after {want.obj} — banking before next')
                    bot.phase = 'bank'
                    return
            else:
                bot.log(f'[buyout] buy {want.obj} n=0 of {want.units} — stock gone or coins short')
            if bot.budget_left() == 0:
                break
        yield from shop.close()

        if bot.budget_left() == 0 or (bought_units > 0 and inventory.count('Coins') < 100):
            bot.phase = 'bank'
            return
        if bought_units > 0:
            if self.needs_bank_first():
                bot.log('[buyout] inventory full after buying — banking before next')
                bot.phase = 'bank'
            elif inventory.is_full():
                bot.log('[buyout] inventory full after buying — banking to make space')
                bot.phase = 'bank'
            return
        if self.needs_bank_first():
            bot.log('[buyout] inventory full — banking before waiting for restock')
            bot.phase = 'bank'
            return
        # Nothing bought and the pack full, of unstackables and no coins, say: bank to make space.
        if inventory.is_full():
            bot.log('[buyout] inventory full and nothing bought — banking to make space')
            bot.phase = 'bank'
            return
        bot.set_status(f'waiting for restock ({round(bot.recheck_ms / 1000)}s)')
        yield from execution.delay_until(lambda: event_signal.pending(), bot.recheck_ms)

    def plan(self, coins):
        """What to buy with the coins, each with obj, name and units."""
        bot = self.bot
        stock = shop.stock()
        if bot.rec is None:
            return [Record({'obj': r.name.lower(), 'name': r.name, 'units': r.count}) for r in stock if r.count > 0]
        by_name = {}
        for item in bot.rec.items:
            by_name[item.name.lower()] = item.obj
        stock_by_obj = {}
        for row in stock:
            obj = by_name.get(row.name.lower())
            if obj is not None:
                stock_by_obj[obj] = row.count
        # A selection sticks even when it's out of stock, to wait for the restock; no selection buys everything.
        chosen = bot.chosen if len(bot.chosen) > 0 else set([i.name.lower() for i in bot.rec.items])
        if len(bot.chosen) > 0:
            available = [i for i in bot.rec.items if i.name.lower() in bot.chosen and stock_by_obj.get(i.obj, 0) > 0]
            if len(available) == 0 and len(stock) > 0:
                bot.log('[buyout] selected items out of stock — waiting for restock')
        return buyout_plan(bot.rec, stock_by_obj, coins, chosen)


BOT = define_bot(
    name='ShopBuyout',
    create=ShopBuyout,
    description="Parks at ONE shop and buys it out repeatedly on a total gp budget — no routing. Defaults to Aemad's vials in East Ardougne; get the bot to the shop yourself.",
    category='Money making',
    tags=['wilderness', 'shopping', 'banking', 'runes', 'afk'],
    settings_schema=SETTINGS,
)
