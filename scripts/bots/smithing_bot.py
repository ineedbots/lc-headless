# Smiths at Varrock west's anvil: withdraws bars and a hammer, makes the chosen item, banks the products and
# repeats. rs2b0t's SmithingBot (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import ContinueDialog

DEFAULT_ANVIL_STAND = Tile(3188, 3425, 0)
DEFAULT_BANK_STAND = Tile(3185, 3440, 0)
BOOTH_OP = 'Use-quickly'
HAMMER = 'Hammer'
ANVIL = 'Anvil'
OPENABLE_OBSTACLES = ['door', 'gate']
# Why: the step through a door goes out on the tick its leaf swings, so the crossing lands the tick after the open.
DOOR_STEP_TICKS = 0
BAR_OPTIONS = ['Bronze', 'Iron', 'Steel', 'Mithril', 'Adamantite', 'Runite']
PRODUCT_OPTIONS = ['Dagger', 'Sword', 'Scimitar', 'Longsword', '2h sword', 'Axe', 'Mace', 'Warhammer', 'Battleaxe', 'Chainbody', 'Platelegs', 'Plateskirt', 'Platebody', 'Med helm', 'Full helm', 'Sq shield', 'Kiteshield', 'Nails', 'Dart tip', 'Arrowtips', 'Knife', 'Wire', 'Claws']

# Why: a product needs this many bars to forge even one, so smithing starts only when the pack holds that many.
# Below it the make panel opens, forges nothing and loops.
BARS_PER_PRODUCT = {
    'Dagger': 1, 'Sword': 1, 'Scimitar': 2, 'Longsword': 2, '2h sword': 3, 'Axe': 1, 'Mace': 1,
    'Warhammer': 3, 'Battleaxe': 3, 'Chainbody': 2, 'Platelegs': 3, 'Plateskirt': 3, 'Platebody': 5,
    'Med helm': 1, 'Full helm': 2, 'Sq shield': 2, 'Kiteshield': 3, 'Nails': 1, 'Dart tip': 1,
    'Arrowtips': 1, 'Knife': 1, 'Wire': 1, 'Claws': 2,
}

SETTINGS = {
    'bar': SettingDef('string', 'Bronze', 'Bar tier', options=BAR_OPTIONS),
    'product': SettingDef('string', 'Dagger', 'Item to smith', options=PRODUCT_OPTIONS, help='matched against the anvil panel by keyword (the panel names are tier-specific, e.g. "Bronze dagger")'),
    'anvil_stand': SettingDef('tile', DEFAULT_ANVIL_STAND, 'Anvil stand tile (x,z)'),
    'bank_stand': SettingDef('tile', DEFAULT_BANK_STAND, 'Bank stand tile (x,z)'),
    'bank_booth': SettingDef('string', 'Bank booth', 'Bank booth loc name'),
    'leash_radius': SettingDef('number', 6, 'Anvil search radius (tiles)', 2, 20),
}


def _named_like(item, pattern):
    return item.name is not None and pattern in item.name.lower()


class SmithPanel(Task):
    def __init__(self, bot):
        Task.__init__(self, label='smith panel')
        self.bot = bot

    def validate(self):
        return chat_dialog.is_main_make_panel()

    def execute(self):
        bot = self.bot
        bot.status = 'choosing item'
        start = bot.bar_count()
        made = yield from chat_dialog.make_from_panel_max(bot.product)
        if not made:
            products = [p for p in chat_dialog.main_make_products() if p]
            if len(products) == 0:
                yield from execution.delay_ticks(1)
                return
            bot.status = f"'{bot.product}' not available; stopped"
            bot.request_finish(f"'{bot.product}' isn't on the {bot.bar_item_name()} anvil panel; available: [{', '.join(products)}]; pick a listed item")
            return

        def stopped():
            return chat_dialog.is_main_make_panel() or chat_dialog.can_continue()

        yield from execution.delay_until(lambda: game.animating() or bot.bar_count() < start or stopped(), 3000)
        mark = bot.bar_count()
        for _ in range(200):
            if bot.bar_count() == 0 or stopped():
                return
            seen = mark
            progressed = yield from execution.delay_until(lambda: bot.bar_count() < seen or stopped(), 4000)
            now = bot.bar_count()
            if now < mark:
                bot.made += mark - now
                mark = now
            elif not progressed or not game.animating():
                return


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return self.bot.bar_count() < self.bot.bars_needed()

    def execute(self):
        bot = self.bot
        bot.status = 'banking'
        yield from walk_opening(bot.bank_stand, 0, OPENABLE_OBSTACLES, bot.log, DOOR_STEP_TICKS)
        opened = yield from bank.open_booth(bot.bank_stand, bot.booth_name, BOOTH_OP)
        if not opened:
            bot.log('could not open the bank; will retry')
            return
        hammer = HAMMER.lower()
        yield from bank.deposit_all_matching(lambda name, id: hammer not in name.lower())
        yield from execution.delay_ticks(1)
        bot.trips += 1

        if bot.hammer_item() is None:
            banked = [i for i in bank.items() if _named_like(i, hammer)]
            if len(banked) == 0:
                bot.log(f"no '{HAMMER}' carried or in the bank; idling")
                yield from execution.delay_ticks(5)
                return
            ops = [o for o in banked[0].actions() if o is not None]
            op = withdraw_op(ops, '1') or withdraw_op(ops, 'any') or 'Withdraw-1'
            bank.withdraw(banked[0].name, op)
            yield from execution.delay_until(lambda: bot.hammer_item() is not None, 3000)

        bar = bot.bar_item_name().lower()
        banked = [i for i in bank.items() if _named_like(i, bar)]
        if len(banked) == 0:
            bot.log(f"no '{bot.bar_item_name()}' in the bank; idling")
            yield from execution.delay_ticks(5)
            return
        name = banked[0].name
        bot.log(f'withdrawing {name}')
        withdrawn = yield from bank.withdraw_load(name)
        if not withdrawn:
            bot.log(f'could not withdraw {name}; will retry')


class Smith(Task):
    def __init__(self, bot):
        Task.__init__(self, label='smith')
        self.bot = bot

    def validate(self):
        return self.bot.bar_count() >= self.bot.bars_needed() and not chat_dialog.is_open() and not chat_dialog.is_main_make_panel()

    def execute(self):
        bot = self.bot
        here = game.tile()
        if here is None or bot.anvil_stand.distance_to(here) > 1 or bot.anvil() is None:
            bot.status = 'walking to the anvil'
            yield from walk_opening(bot.anvil_stand, 0, OPENABLE_OBSTACLES, bot.log, DOOR_STEP_TICKS)
        if bot.hammer_item() is None:
            bot.log('no hammer in the pack; idling (need a hammer to smith)')
            yield from execution.delay_ticks(5)
            return
        bar = bot.last_bar()
        anvil = bot.anvil()
        if bar is None or anvil is None:
            yield from execution.delay_ticks(2)
            return
        bot.status = f'smithing {bot.product}'
        if not bar.use_on(anvil):
            yield from execution.delay_ticks(2)
            return
        yield from execution.delay_until(lambda: chat_dialog.is_main_make_panel() or chat_dialog.can_continue() or bot.bar_count() == 0, 6000)


class SmithingBot(TaskBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.bar = s.str('bar', 'Bronze')
        self.product = s.str('product', 'Dagger')
        self.anvil_stand = s.tile('anvil_stand', DEFAULT_ANVIL_STAND)
        self.bank_stand = s.tile('bank_stand', DEFAULT_BANK_STAND)
        self.booth_name = s.str('bank_booth', 'Bank booth')
        self.leash = s.num('leash_radius', 6)
        self.made = 0
        self.trips = 0
        self.status = 'starting'
        self.xp_at_start = skills.xp('smithing')
        self.log(f'SmithingBot smithing {self.bar} -> {self.product}; anvil {self.anvil_stand}, bank {self.bank_stand}')
        self.add(ContinueDialog(), SmithPanel(self), BankTrip(self), Smith(self))

    def bar_item_name(self):
        return f'{self.bar} bar'

    def bars_needed(self):
        return BARS_PER_PRODUCT.get(self.product, 1)

    def bar_count(self):
        pattern = self.bar_item_name().lower()
        return sum([max(1, i.count) for i in inventory.items() if _named_like(i, pattern)])

    def last_bar(self):
        pattern = self.bar_item_name().lower()
        items = inventory.items()
        for i in range(len(items) - 1, -1, -1):
            if _named_like(items[i], pattern):
                return items[i]
        return None

    def hammer_item(self):
        for item in inventory.items():
            if _named_like(item, HAMMER.lower()):
                return item
        return None

    def anvil(self):
        return locs.query().name(ANVIL).within_of(self.anvil_stand, self.leash).nearest()

    def on_progress_report(self):
        return {'Status': self.status, 'Bars used': self.made, 'Smithing xp': skills.xp('smithing') - self.xp_at_start,
                'Item': f'{self.bar} {self.product}', 'Bars left': self.bar_count(), 'Bank trips': self.trips}


BOT = define_bot(
    name='SmithingBot',
    create=SmithingBot,
    description='Varrock anvil smithing — withdraw bars + a hammer, make the chosen item at the anvil, bank the products, repeat',
    category='Smithing',
    tags=['smithing', 'anvil', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
