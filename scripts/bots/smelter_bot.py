# Smelts bars at Al Kharid's furnace: withdraws the ore for any of the 8 bars, smelts the load, banks and
# repeats. rs2b0t's SmelterBot (MIT, see thirdparty/rs2b0t).

import time

from rs2004.catalogs import ContinueDialog

DEFAULT_BANK_STAND = Tile(3269, 3167, 0)
DEFAULT_FURNACE_STAND = Tile(3275, 3185, 0)
BOOTH_OP = 'Use-quickly'
# Why: a pack holds 28, so 30 always clears it, and the engine caps the rest; the measured ore count instead
# makes a pack read a moment stale smelt short.
SMELT_X = 30
# Milliseconds of no ore used before the smelt task gives up its wait, rather than park the task loop.
SMELT_IDLE_MS = 8000
SMELT_DEADLINE_MS = 120000


class Ingredient:
    def __init__(self, ore, per_bar):
        self.ore = ore
        self.per_bar = per_bar


class Recipe:
    def __init__(self, bar, level, ingredients):
        self.bar = bar
        self.level = level
        self.ingredients = ingredients


RECIPES = [
    Recipe('Bronze', 1, [Ingredient('Copper ore', 1), Ingredient('Tin ore', 1)]),
    Recipe('Iron', 15, [Ingredient('Iron ore', 1)]),
    Recipe('Silver', 20, [Ingredient('Silver ore', 1)]),
    Recipe('Steel', 30, [Ingredient('Iron ore', 1), Ingredient('Coal', 2)]),
    Recipe('Gold', 40, [Ingredient('Gold ore', 1)]),
    Recipe('Mithril', 50, [Ingredient('Mithril ore', 1), Ingredient('Coal', 4)]),
    Recipe('Adamant', 70, [Ingredient('Adamantite ore', 1), Ingredient('Coal', 6)]),
    Recipe('Rune', 85, [Ingredient('Runite ore', 1), Ingredient('Coal', 8)]),
]
BAR_OPTIONS = [r.bar for r in RECIPES]
# The smelting menu's names for the bars rs2b0t calls otherwise.
BAR_KEYWORDS = {'Adamant': 'Adamantite', 'Rune': 'Runite'}


def recipe_for_bar(bar):
    wanted = bar.strip().lower()
    for recipe in RECIPES:
        if recipe.bar.lower() == wanted:
            return recipe
    return None


def primary_ore(recipe):
    return recipe.ingredients[0].ore


def sets_per_trip(recipe):
    return 28 // sum([i.per_bar for i in recipe.ingredients])


def withdraw_for(recipe, stock):
    """What to withdraw given what the bank holds, stock(ore), up to one trip: a short trip still makes bars.
    Empty only when not one bar can be made."""
    sets = min([sets_per_trip(recipe)] + [stock(i.ore) // i.per_bar for i in recipe.ingredients])
    if sets <= 0:
        return []
    return [(i.ore, sets * i.per_bar) for i in recipe.ingredients]


def withdraw_plan(recipe):
    sets = sets_per_trip(recipe)
    return [(i.ore, sets * i.per_bar) for i in recipe.ingredients]


def _matches(name, pattern):
    return name is not None and pattern.strip().lower() in name.lower()


def can_smelt(items, recipe):
    """Whether the pack holds enough of every ingredient for one bar: iron without coal smelts nothing."""
    return all([len([it for it in items if _matches(it.name, i.ore)]) >= i.per_bar for i in recipe.ingredients])


def count_primary(items, recipe):
    pattern = primary_ore(recipe)
    return len([i for i in items if _matches(i.name, pattern)])


def smelt_stalled(now_count, last_count, idle_ms, limit_ms=8000):
    """The furnace has stopped using ore, so the wait should retry."""
    return now_count >= last_count and idle_ms > limit_ms


SETTINGS = {
    'bar': SettingDef('string', 'Bronze', 'Bar to smelt', options=BAR_OPTIONS, help='withdraw plan + coal ratio are derived from this'),
    'bank_stand': SettingDef('tile', DEFAULT_BANK_STAND, 'Bank stand tile (x,z)'),
    'furnace_stand': SettingDef('tile', DEFAULT_FURNACE_STAND, 'Furnace stand tile (x,z)'),
    'furnace_name': SettingDef('string', 'Furnace', 'Furnace loc name'),
    'bank_booth': SettingDef('string', 'Bank booth', 'Bank booth loc name'),
    'obstacle': SettingDef('string', 'door, gate', 'Openable obstacles (contains)', help='the bank-building door on the route'),
    'leash_radius': SettingDef('number', 8, 'Furnace search radius (tiles)', 2, 20),
}


def _now_ms():
    return time.time() * 1000


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    # Anything the pack can't make a bar from means a restock: iron without coal is as unsmeltable as no ore.
    def validate(self):
        return not self.bot.can_smelt()

    def execute(self):
        bot = self.bot
        bot.status = 'banking'
        yield from walk_opening(bot.bank_stand, 0, bot.obstacles, bot.log)
        opened = yield from bank.open_booth(bot.bank_stand, bot.booth_name, BOOTH_OP)
        if not opened:
            bot.log('could not open the bank; will retry')
            return
        yield from bank.deposit_inventory()

        # Why: two empties look alike through bank.count, the list refills a tick after a deposit, and the window
        # can shut outright, so every ore reads 0 until the window is open and filled.
        loaded = yield from execution.delay_until(lambda: bank.is_open() and bank.loaded(), 5000)
        if not loaded:
            bot.log('the bank list has not filled in yet; retrying this trip' if bank.is_open() else 'the bank window closed; reopening and retrying this trip')
            return
        bot.trips += 1

        recipe = bot.recipe

        def bank_name_for(ore):
            for item in bank.items():
                if _matches(item.name, ore):
                    return item.name
            return None

        def stock(ore):
            name = bank_name_for(ore)
            return 0 if name is None else bank.count(name)

        plan = withdraw_for(recipe, stock)
        if len(plan) == 0:
            short = ', '.join([f'{i.ore} {stock(i.ore)}' for i in recipe.ingredients])
            bot.status = 'out of ore; stopped'
            bot.request_finish(f'the bank cannot supply even one {recipe.bar} bar ({short})')
            return

        for ore, count in plan:
            # Checked each step, since the window can shut between withdrawals too.
            if not bank.is_open() or not bank.loaded():
                bot.log('the bank window closed mid-withdrawal; reopening and retrying this trip')
                return
            name = bank_name_for(ore)
            if name is None:
                bot.log(f"'{ore}' is not in the bank list; retrying this trip")
                return
            bot.status = f'withdrawing {count} {name}'
            withdrawn = yield from bank.withdraw_x(name, count)
            if not withdrawn:
                bot.log(f'could not withdraw {count} {name}; retrying next trip')
                return


class SmeltTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='smelt trip')
        self.bot = bot

    def validate(self):
        return self.bot.can_smelt() and not chat_dialog.can_continue()

    def execute(self):
        bot = self.bot
        stand = bot.furnace_stand
        here = game.tile()
        if here is None or stand.distance_to(here) > 1 or bot.furnace() is None:
            bot.status = 'crossing to the furnace'
            yield from walk_opening(stand, 0, bot.obstacles, bot.log)
        for _ in range(5):
            now = game.tile()
            if now is not None and now.x == stand.x and now.z == stand.z:
                break
            if not reachability.probeable(stand):
                yield from execution.delay_ticks(1)
                continue
            before = game.tile()
            direct_navigator.walk(stand)

            def moved():
                t = game.tile()
                return t is not None and ((t.x == stand.x and t.z == stand.z) or (before is not None and (before.x != t.x or before.z != t.z)))

            yield from execution.delay_until(moved, 3000)

        if not chat_dialog.is_make_menu():
            oven = bot.furnace()
            if oven is None:
                yield from execution.delay_ticks(2)
                return
            oven.interact('Smelt')
            menu = yield from execution.delay_until(lambda: chat_dialog.is_make_menu() or chat_dialog.can_continue(), 6000)
            if not menu:
                yield from execution.delay_ticks(2)
                return
        if not chat_dialog.is_make_menu():
            return

        recipe = bot.recipe
        keyword = BAR_KEYWORDS.get(recipe.bar, recipe.bar)
        before = bot.primary_count()
        bot.status = f'smelting {recipe.bar}'
        made = yield from chat_dialog.make_x(keyword, SMELT_X)
        if not made:
            bot.log(f"Smelt panel open but couldn't Smelt-X '{keyword}'; products: [{', '.join(chat_dialog.make_products())}]")
            yield from execution.delay_ticks(2)
            return
        # Why: one long wait parks the task loop, so ContinueDialog never runs and a furnace that used no ore looks dead.
        last = before
        last_change = _now_ms()
        deadline = _now_ms() + SMELT_DEADLINE_MS
        while _now_ms() < deadline:
            now = bot.primary_count()
            if now == 0 or chat_dialog.can_continue():
                break
            if now < last:
                last = now
                last_change = _now_ms()
            elif smelt_stalled(now, last, _now_ms() - last_change, SMELT_IDLE_MS):
                bot.log('smelting made no progress; retrying')
                break
            yield from execution.delay_ticks(1)
        if bot.primary_count() < before:
            bot.smelted += before - bot.primary_count()


class SmelterBot(TaskBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.recipe = recipe_for_bar(s.str('bar', 'Bronze')) or recipe_for_bar('Bronze')
        self.bank_stand = s.tile('bank_stand', DEFAULT_BANK_STAND)
        self.furnace_stand = s.tile('furnace_stand', DEFAULT_FURNACE_STAND)
        self.furnace_name = s.str('furnace_name', 'Furnace')
        self.booth_name = s.str('bank_booth', 'Bank booth')
        self.obstacles = [o.strip().lower() for o in s.str('obstacle', 'door, gate').split(',') if o.strip()]
        self.leash = s.num('leash_radius', 8)
        self.smelted = 0
        self.trips = 0
        self.status = 'starting'
        self.xp_at_start = skills.xp('smithing')
        plan = ' + '.join([f'{count} {ore}' for ore, count in withdraw_plan(self.recipe)])
        self.log(f"SmelterBot smelting '{self.recipe.bar}' ({plan}); bank {self.bank_stand}, furnace {self.furnace_stand}")
        self.add(ContinueDialog(), BankTrip(self), SmeltTrip(self))

    def furnace(self):
        return locs.query().name(self.furnace_name).action('Smelt').within_of(self.furnace_stand, self.leash).nearest()

    def primary_count(self):
        return count_primary(inventory.items(), self.recipe)

    def can_smelt(self):
        return can_smelt(inventory.items(), self.recipe)

    def on_progress_report(self):
        return {'Status': self.status, 'Smelted': self.smelted, 'Smithing xp': skills.xp('smithing') - self.xp_at_start,
                'Bar': self.recipe.bar, 'Ore left': self.primary_count(), 'Bank trips': self.trips}


BOT = define_bot(
    name='SmelterBot',
    create=SmelterBot,
    description='Al Kharid smelter — withdraw ore, use it on the Furnace to smelt bars (all 8 bar types), bank, repeat',
    category='Smithing',
    tags=['smithing', 'smelting', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
