# Collects one herblore secondary: looted, bought, bought and ground, pulled from swamp toads, or ground from banked
# unicorn horns: rs2b0t's HerbloreSecondaries (MIT, see thirdparty/rs2b0t). Food rides along on dangerous routes, and
# shop trips carry at most 5000 coins.

import math

from rs2004.catalogs import LOADOUT_SETTING, ContinueDialog, Record, food_count, food_forms, food_heal_amount, script_food, should_eat_to_use_food, sustain

FOOD_DEFAULT = 'Lobster'
FOOD_DEFAULT_COUNT = 10
SHOP_COIN_CAP = 5000
# Below this a shop route goes back for coins.
SHOP_COIN_FLOOR = 50
SHIELD_NAME = 'Dragonfire shield'
BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}

SECONDARIES = [
    Record({'id': 'red_spiders_eggs', 'name': "Red spiders' eggs", 'mode': 'loot', 'anchor': Tile(3120, 9952, 0), 'search_radius': 14,
            'bank': Tile(3094, 3493, 0), 'bank_name': 'Edgeville', 'take_food': True, 'need_shield': False}),
    Record({'id': 'snape_grass', 'name': 'Snape grass', 'mode': 'loot', 'anchor': Tile(2908, 3294, 0), 'search_radius': 16,
            'bank': Tile(3013, 3355, 0), 'bank_name': 'Falador East', 'take_food': True, 'need_shield': False}),
    Record({'id': 'eye_of_newt', 'name': 'Eye of newt', 'mode': 'buy', 'anchor': Tile(3012, 3259, 0), 'search_radius': 6,
            'bank': Tile(3093, 3243, 0), 'bank_name': 'Draynor', 'take_food': False, 'need_shield': False,
            'shop_npc': 'Betty', 'shop_stand': Tile(3012, 3259, 0)}),
    Record({'id': 'chocolate_dust', 'name': 'Chocolate dust', 'mode': 'buy_grind', 'anchor': Tile(3014, 3204, 0), 'search_radius': 6,
            'bank': Tile(3093, 3243, 0), 'bank_name': 'Draynor', 'take_food': False, 'need_shield': False,
            'shop_npc': 'Wydin', 'shop_stand': Tile(3014, 3204, 0), 'tool_shop_npc': 'Jatix', 'tool_shop_stand': Tile(2899, 3427, 0),
            'tool_name': 'Pestle and mortar', 'grind_from': 'Chocolate bar'}),
    Record({'id': 'white_berries', 'name': 'White berries', 'mode': 'loot', 'anchor': Tile(3216, 3812, 0), 'search_radius': 12,
            'bank': Tile(2616, 3332, 0), 'bank_name': 'Ardougne West', 'take_food': True, 'need_shield': True}),
    Record({'id': 'toads_legs', 'name': "Toad's legs", 'mode': 'loot_process', 'anchor': Tile(2415, 3514, 0), 'search_radius': 18,
            'bank': Tile(2449, 3482, 1), 'bank_name': 'Grand Tree', 'take_food': False, 'need_shield': False, 'source_name': 'Swamp toad'}),
    Record({'id': 'unicorn_horn_dust', 'name': 'Unicorn horn dust', 'mode': 'bank_grind', 'search_radius': 6, 'take_food': False,
            'need_shield': False, 'tool_name': 'Pestle and mortar', 'grind_from': 'Unicorn horn'}),
]
SECONDARY_OPTIONS = [s.name for s in SECONDARIES]

SETTINGS = {
    'secondary': SettingDef('string', "Red spiders' eggs", 'Secondary', options=SECONDARY_OPTIONS, help='which herblore secondary to collect this session'),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', FOOD_DEFAULT_COUNT, 'Food to withdraw', 0, 27, help='0 = never withdraw food'),
}


# The pure decisions, kept apart from the game so they can be tested without a client.

def secondary_by_name(name):
    want = name.strip().lower()
    for s in SECONDARIES:
        if s.name.lower() == want or s.id == want:
            return s
    return None


def grinds(d):
    return d.mode == 'buy_grind' or d.mode == 'bank_grind'


def buys(d):
    return d.mode == 'buy' or d.mode == 'buy_grind'


def shop_coins_to_withdraw(in_pack, banked, want=None):
    """Coins to withdraw for a shop trip, never above SHOP_COIN_CAP."""
    target = SHOP_COIN_CAP if want is None else min(SHOP_COIN_CAP, want)
    if in_pack >= target:
        return 0
    return min(target - in_pack, max(0, banked))


def should_eat(hp, max_hp, heal, count, free_slots, collecting):
    """Eats when a full heal fits, HP reaches the 60% safety floor, or the pack is full and eating frees a slot for
    loot."""
    min_hp = max(5, min(max_hp - 1, math.ceil(max_hp * 0.6)))
    if should_eat_to_use_food(hp, max_hp, heal, count, min_hp):
        return True
    return count > 0 and collecting and free_slots == 0


# Why: everything not kept is deposited, random-event loot such as coins, runes and arrows included. The product
# and its source are left off on purpose, since they're the loot being banked; keeping them leaves the pack full
# after closing and opens and closes the bank over and over.
def keep_on_deposit(d, food):
    """What stays in the pack when banking."""
    keep = []
    # Coins buy stock on shop routes; anywhere else they're random-event pickups.
    if buys(d):
        keep.append('Coins')
    if d.take_food:
        keep.append(food)
    if d.need_shield:
        keep.append(SHIELD_NAME)
    if d.tool_name:
        keep.append(d.tool_name)
    # Bars mid-grind stay, so the dust is finished after restocking; finished dust is deposited.
    if d.grind_from:
        keep.append(d.grind_from)
    return keep


def needs_restock(d, food_in_pack, food_want, coins, has_shield, pack_full, grind_left):
    mid_grind = grinds(d) and grind_left > 0
    if pack_full and not mid_grind:
        return True
    if d.mode == 'bank_grind' and grind_left == 0:
        return True
    # Food is restocked only once it's gone; eating mid-trip is fine until then.
    if d.take_food and food_want > 0 and food_in_pack < 1:
        return True
    if d.need_shield and not has_shield:
        return True
    if buys(d) and coins < SHOP_COIN_FLOOR:
        return True
    # A missing pestle is BuyTool's job, at a shop, not the bank's.
    return False


def near(tile, r):
    t = game.tile()
    return t is not None and t.level == tile.level and max(abs(t.x - tile.x), abs(t.z - tile.z)) <= r


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        bot = self.bot
        d = bot.secondary
        collecting = (d.mode == 'loot' or d.mode == 'loot_process') and near(bot.anchor, d.search_radius + 4)
        return should_eat(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(bot.food_name), bot.food_in_pack(),
                          inventory.free(), collecting)

    def execute(self):
        bot = self.bot
        forms = food_forms(bot.food_name)
        items = [i for i in inventory.items() if (i.name or '').lower() in forms]
        if len(items) == 0:
            return
        item = items[0]
        bot.status = f'eating {item.name}'
        before = inventory.used()
        item.interact('Eat')
        yield from execution.delay_until(lambda: inventory.used() < before, 3000)


class GearUp(Task):
    def __init__(self, bot):
        Task.__init__(self, label='gear up')
        self.bot = bot

    def validate(self):
        return self.bot.secondary.need_shield and inventory.contains(SHIELD_NAME) and not equipment.contains(SHIELD_NAME)

    def execute(self):
        self.bot.status = f'wielding {SHIELD_NAME}'
        yield from equipment.equip(SHIELD_NAME)


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return needs_restock(bot.secondary, bot.food_in_pack(), bot.food_want, bot.coin_count(), bot.has_shield(),
                             inventory.is_full() and bot.product_count() + bot.source_count() > 0, bot.grind_left())

    def stop(self, reason):
        """Use with yield from."""
        yield from bank.close()
        self.bot.request_finish(reason)

    def execute(self):
        bot = self.bot
        d = bot.secondary
        food = bot.food_name
        bot.status = f'banking at {bot.bank_name}'
        arrived = yield from bot.walk_to(bot.bank_tile, f'{bot.bank_name} bank')
        if not arrived:
            return
        opened = yield from bot.open_bank()
        if not opened:
            bot.log('could not open bank')
            return
        keep = [n.lower() for n in keep_on_deposit(d, food)]
        yield from bank.deposit_all_matching(lambda name, *_args: name.lower() not in keep)
        if d.need_shield and not bot.has_shield():
            if bank.count(SHIELD_NAME) < 1:
                yield from self.stop(f'no {SHIELD_NAME} banked for white berries')
                return
            yield from bank.withdraw_x(SHIELD_NAME, 1)
        if d.take_food and bot.food_want > 0:
            have = bot.food_in_pack()
            if have < bot.food_want:
                if bank.count(food) < 1 and have < 1:
                    yield from self.stop(f'out of {food} in the bank')
                    return
                yield from bank.withdraw_x(food, bot.food_want - have)
        if buys(d):
            need = shop_coins_to_withdraw(bot.coin_count(), bank.count('Coins'))
            if need > 0:
                if bank.count('Coins') < need and bot.coin_count() < SHOP_COIN_FLOOR:
                    yield from self.stop('not enough coins in the bank for shopping')
                    return
                yield from bank.withdraw_x('Coins', need)
            # It never leaves with more than the cap.
            if bot.coin_count() > SHOP_COIN_CAP:
                yield from bank.deposit_all_matching(lambda name, *_args: name.lower() == 'coins')
                yield from bank.withdraw_x('Coins', SHOP_COIN_CAP)
        if grinds(d) and d.tool_name and not inventory.contains(d.tool_name):
            if bank.count(d.tool_name) > 0:
                yield from bank.withdraw_x(d.tool_name, 1)
            elif d.mode == 'bank_grind':
                yield from self.stop(f'no {d.tool_name} in the bank')
                return
        if d.mode == 'bank_grind' and d.grind_from:
            if bank.count(d.grind_from) < 1:
                yield from self.stop(f'out of {d.grind_from} in the bank')
                return
            yield from bank.withdraw_load(d.grind_from)
        yield from bank.close()
        bot.trips += 1
        stock = f', {d.grind_from} {bot.grind_left()}' if d.grind_from else ''
        bot.log(f'restocked @ {bot.bank_name}: food {bot.food_in_pack()}, coins {bot.coin_count()}{stock}')


class BuyTool(Task):
    def __init__(self, bot):
        Task.__init__(self, label='buy tool')
        self.bot = bot

    def validate(self):
        bot = self.bot
        d = bot.secondary
        return d.mode == 'buy_grind' and bool(d.tool_name) and not bot.has_tool() and bot.coin_count() > 0

    def execute(self):
        bot = self.bot
        d = bot.secondary
        if not d.tool_shop_stand or not d.tool_shop_npc or not d.tool_name:
            return
        bot.status = f'buying {d.tool_name}'
        arrived = yield from bot.walk_to(d.tool_shop_stand, d.tool_shop_npc)
        if not arrived:
            return
        opened = yield from shop.open(d.tool_shop_npc)
        if not opened:
            bot.log(f"could not open {d.tool_shop_npc}'s shop")
            return
        bought = yield from shop.buy(d.tool_name, 1)
        yield from shop.close()
        bot.log(f'bought {d.tool_name}' if bought > 0 else f'{d.tool_name} not in stock')


class BuyGoods(Task):
    def __init__(self, bot):
        Task.__init__(self, label='buy goods')
        self.bot = bot

    def validate(self):
        bot = self.bot
        d = bot.secondary
        if d.mode == 'buy':
            return bot.coin_count() > 0 and not inventory.is_full()
        if d.mode == 'buy_grind':
            # Bars already held are ground before buying more.
            if d.grind_from and inventory.count(d.grind_from) > 0 and bot.has_tool():
                return False
            return bot.has_tool() and bot.coin_count() > 0 and not inventory.is_full() and inventory.count(d.grind_from or '') + bot.product_count() < 27
        return False

    def execute(self):
        bot = self.bot
        d = bot.secondary
        if not d.shop_stand or not d.shop_npc:
            return
        buy_name = (d.grind_from or d.name) if d.mode == 'buy_grind' else d.name
        bot.status = f'buying {buy_name}'
        arrived = yield from bot.walk_to(d.shop_stand, d.shop_npc)
        if not arrived:
            return
        opened = yield from shop.open(d.shop_npc)
        if not opened:
            bot.log(f"could not open {d.shop_npc}'s shop")
            return
        room = max(0, inventory.free() - (1 if d.mode == 'buy_grind' else 0))
        bought = yield from shop.buy(buy_name, min(room, 50))
        yield from shop.close()
        if bought > 0:
            bot.log(f'bought {bought}× {buy_name}')
            if d.mode == 'buy':
                bot.gathered += bought
        else:
            bot.log(f'{buy_name} out of stock — waiting')
            yield from execution.delay_ticks(20)


class Grind(Task):
    def __init__(self, bot):
        Task.__init__(self, label='grind')
        self.bot = bot

    def validate(self):
        d = self.bot.secondary
        return (grinds(d) and bool(d.grind_from) and bool(d.tool_name) and game.ingame() and game.scene_ready() and not event_signal.pending()
                and not chat_dialog.is_open() and not bank.is_open() and inventory.contains(d.grind_from) and inventory.contains(d.tool_name))

    def execute(self):
        bot = self.bot
        d = bot.secondary
        bot.status = f'grinding {d.grind_from}'
        no_progress = 0
        for _ in range(28):
            if not self.validate():
                return
            sources = [i for i in inventory.items() if i.name == d.grind_from]
            sources.sort(key=lambda b: b.slot, reverse=True)
            pestle = inventory.first(d.tool_name)
            if len(sources) == 0 or pestle is None:
                return
            source = sources[0]
            before = bot.product_count()
            want = min(5, bot.grind_left())
            sent = 0
            for _ in range(want):
                if event_signal.pending() or not pestle.use_on(source):
                    break
                sent += 1
            if sent == 0:
                return
            yield from execution.delay_ticks(1)
            got = bot.product_count() - before
            if got > 0:
                bot.gathered += got
                bot.log(f'ground {got}× {d.name}')
                no_progress = 0
            else:
                no_progress += 1
                if no_progress >= 3:
                    return


class ProcessSource(Task):
    def __init__(self, bot):
        Task.__init__(self, label='process source')
        self.bot = bot

    def validate(self):
        return self.bot.secondary.mode == 'loot_process' and self.bot.source_count() > 0

    def execute(self):
        bot = self.bot
        toad = inventory.first(bot.secondary.source_name)
        if toad is None:
            return
        bot.status = 'pulling toad legs'
        before = bot.product_count()
        actions = toad.actions()
        removes = [a for a in actions if 'remove-legs' in a.lower() or 'remove legs' in a.lower()]
        op = removes[0] if len(removes) > 0 else (actions[0] if len(actions) > 0 else None)
        if not op:
            return
        toad.interact(op)
        pulled = yield from execution.delay_until(lambda: bot.product_count() > before or bot.source_count() == 0, 3000)
        if pulled:
            bot.gathered += max(0, bot.product_count() - before)


class Loot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot')
        self.bot = bot

    def find(self):
        d = self.bot.secondary
        return ground_items.query().name(d.source_name or d.name).within(d.search_radius).nearest()

    def validate(self):
        bot = self.bot
        d = bot.secondary
        if d.mode != 'loot' and d.mode != 'loot_process':
            return False
        if inventory.is_full() or not near(bot.anchor, d.search_radius + 4):
            return False
        return self.find() is not None

    def execute(self):
        bot = self.bot
        drop = self.find()
        if drop is None:
            return
        bot.status = f'taking {drop.name}'
        before = inventory.used()
        drop.interact('Take')
        took = yield from execution.delay_until(lambda: inventory.used() > before, 4000)
        if took:
            if bot.secondary.mode == 'loot':
                bot.gathered += 1
            bot.log(f'looted {drop.name}')


class Travel(Task):
    def __init__(self, bot):
        Task.__init__(self, label='travel')
        self.bot = bot

    def dest(self):
        return self.bot.secondary.shop_stand or self.bot.anchor

    # To the field or shop when not near it already, and the pack isn't forcing a bank trip.
    def validate(self):
        bot = self.bot
        if inventory.is_full() and (bot.product_count() > 0 or bot.source_count() > 0):
            return False
        return not near(self.dest(), bot.secondary.search_radius)

    def execute(self):
        yield from self.bot.walk_to(self.dest(), self.bot.secondary.name)


class HerbloreSecondaries(TaskBot):
    def on_start(self):
        self.loop_delay = 400
        self.gathered = 0
        self.trips = 0
        self.status = 'starting'
        self.known_bank = None
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        pick = self.settings.str('secondary', "Red spiders' eggs")
        d = secondary_by_name(pick)
        if d is None:
            self.request_finish(f"unknown secondary '{pick}'")
            return
        self.secondary = d
        if not self.resolve_site(d):
            return
        self.food_name = script_food(self.settings, FOOD_DEFAULT)
        self.food_want = self.settings.num('food_withdraw', FOOD_DEFAULT_COUNT)
        shield = f", shield '{SHIELD_NAME}'" if d.need_shield else ''
        self.log(f"HerbloreSecondaries — {d.name} ({d.mode}) bank {self.bank_name}, food '{self.food_name}' x{self.food_want}{shield}")
        # Why: ProcessSource comes before BankTrip so swamp toads become legs before the deposit, and Eat does too,
        # since a full pack with food left is one free slot from more loot and BankTrip would bank the food.
        eat = Eat(self)

        def eat_on_the_way():
            if not bank.is_open() and eat.validate():
                yield from eat.execute()

        sustain.set(eat_on_the_way)
        self.add(ContinueDialog(), GearUp(self), ProcessSource(self), eat, BankTrip(self), BuyTool(self), BuyGoods(self), Grind(self), Loot(self), Travel(self))

    def on_stop(self, reason):
        sustain.set(None)

    def resolve_site(self, d):
        if d.mode != 'bank_grind':
            if not d.anchor or not d.bank or not d.bank_name:
                self.request_finish(f'{d.name} has no site')
                return False
            self.anchor = d.anchor
            self.bank_tile = d.bank
            self.bank_name = d.bank_name
            return True
        here = game.tile()
        known = nearest_bank(here) if here is not None else None
        if known is None:
            self.request_finish('no reachable bank')
            return False
        t = known['tile']
        self.known_bank = known
        self.anchor = Tile(t['x'], t['z'], t['level'])
        self.bank_tile = self.anchor
        self.bank_name = known['name']
        return True

    def open_bank(self):
        """Use with yield from."""
        known = self.known_bank
        if known is not None and (known.get('access') or known.get('npc_access')):
            opened = yield from open_bank_access(known, known.get('access') or BOOTH, lambda m: self.log(f'  {m}'))
            return opened
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            opened = yield from bank.open_nearest('Bank booth', 'Bank')
        return opened

    def food_in_pack(self):
        return food_count(inventory.items(), self.food_name)

    def product_count(self):
        return inventory.count(self.secondary.name)

    def source_count(self):
        return inventory.count(self.secondary.source_name) if self.secondary.source_name else 0

    def grind_left(self):
        return inventory.count(self.secondary.grind_from) if self.secondary.grind_from else 0

    def coin_count(self):
        return inventory.count('Coins')

    def has_shield(self):
        return equipment.contains(SHIELD_NAME) or inventory.contains(SHIELD_NAME)

    def has_tool(self):
        tool = self.secondary.tool_name
        return not tool or inventory.contains(tool) or equipment.contains(tool)

    def walk_to(self, dest, what):
        """Use with yield from."""
        if near(dest, 3):
            return True
        self.status = f'walking to {what}'
        walked = yield from traversal.walk_resilient(dest, radius=3, attempts=3, timeout_ms=180000, log=lambda m: self.log(f'  {m}'))
        return walked

    def on_progress_report(self):
        return {'Status': self.status, 'Secondary': self.secondary.name, 'Gathered': self.gathered, 'Trips': self.trips,
                'Food': self.food_in_pack(), 'Coins': self.coin_count()}


BOT = define_bot(
    name='HerbloreSecondaries',
    create=HerbloreSecondaries,
    description="Collects one herblore secondary — red spiders' eggs, snape grass, eye of newt, chocolate dust (buy+grind), white berries (dragonfire shield), toad's legs, or unicorn horn dust (grinds banked horns at the nearest bank) — with food on dangerous routes and a 5k coin cap for shops",
    category='Herblore',
    tags=['herblore', 'secondaries', 'banking', 'shopping', 'loot'],
    settings_schema=SETTINGS,
)
