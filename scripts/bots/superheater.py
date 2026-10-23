# Smelts bars with the Superheat Item spell instead of a furnace: withdraws ore, casts on the primary ore, banks
# the bars and repeats. rs2b0t's Superheater (MIT, see thirdparty/rs2b0t). It wields a fire staff, so the casts
# take only nature runes.

from rs2004.catalogs import STAFF_RUNES

BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}
MAGIC_TAB = 6
SUPERHEAT_ITEM = 'Superheat Item'
# One a cast, kept in the pack through every deposit.
NATURE_RUNE = 'Nature rune'
FIRE_STAFF = 'Staff of fire'
FIRE_RUNE = 'fire rune'
# Superheat Item unlocks at 43 Magic.
MAGIC_REQUIRED = 43
# Well above one trip's 27 casts; the setting's minimum keeps it above them.
NATURES_DEFAULT = 50
NATURES_MIN = 28
# The pack's 28 slots less the nature runes' one.
SUPERHEAT_SLOTS = 27
CAST_TICKS = 3


class Recipe:
    def __init__(self, bar, level, ingredients):
        self.bar = bar
        self.level = level
        # (ore, per bar) pairs; the first is cast on.
        self.ingredients = ingredients


RECIPES = [
    Recipe('Bronze', 1, [('Copper ore', 1), ('Tin ore', 1)]),
    Recipe('Iron', 15, [('Iron ore', 1)]),
    Recipe('Silver', 20, [('Silver ore', 1)]),
    Recipe('Steel', 30, [('Iron ore', 1), ('Coal', 2)]),
    Recipe('Gold', 40, [('Gold ore', 1)]),
    Recipe('Mithril', 50, [('Mithril ore', 1), ('Coal', 4)]),
    Recipe('Adamant', 70, [('Adamantite ore', 1), ('Coal', 6)]),
    Recipe('Rune', 85, [('Runite ore', 1), ('Coal', 8)]),
]
# Thurgo smelts blurite bars in a quest; it's offered, gated by level, and listed last.
BLURITE = Recipe('Blurite', 13, [('Blurite ore', 1)])
BAR_OPTIONS = [r.bar for r in RECIPES] + [BLURITE.bar]


def _fire_staves():
    # Why: Staff of fire comes first, so a bank that has one withdraws it before a battlestaff.
    staves = [FIRE_STAFF]
    for staff, runes in STAFF_RUNES.items():
        if staff.lower() != FIRE_STAFF.lower() and len([r for r in runes if r.lower() == FIRE_RUNE]) > 0:
            staves.append(staff)
    return staves


FIRE_STAVES = _fire_staves()

SETTINGS = {
    'bar': SettingDef('string', 'Bronze', 'Bar to smelt', options=BAR_OPTIONS, help='withdraw plan + coal ratio are derived from this; cast onto the primary ore'),
    'natures': SettingDef('number', NATURES_DEFAULT, 'Nature runes to keep in the pack', NATURES_MIN, 1000,
                          help='topped up whenever the pack count drops below this; keep it above the casts-per-trip so a short bank stock never stalls the run'),
}


def pick_fire_staff(has):
    for name in FIRE_STAVES:
        if has(name):
            return name
    return None


def recipe_for_bar(bar):
    wanted = bar.strip().lower()
    for recipe in RECIPES + [BLURITE]:
        if recipe.bar.lower() == wanted:
            return recipe
    return None


def ores_per_bar(recipe):
    return sum([per for _, per in recipe.ingredients])


def bars_per_trip(recipe):
    """Full bars a 27-slot trip makes: bronze 13, steel 9, mithril 5, rune 3."""
    return SUPERHEAT_SLOTS // ores_per_bar(recipe)


def withdraw_set(recipe):
    """(ore, count) to withdraw for one trip."""
    trips = bars_per_trip(recipe)
    return [(ore, trips * per) for ore, per in recipe.ingredients]


def primary_ore(recipe):
    return recipe.ingredients[0][0]


def bars_smeltable(recipe, count):
    return min([count(ore) // per for ore, per in recipe.ingredients])


# Why: a fire staff is worn once: everything deposited, one withdrawn, the bank shut so Wield is a backpack
# option, wielded, the bank opened again.
class EnsureGear(Task):
    def __init__(self, bot):
        Task.__init__(self, label='ensure gear')
        self.bot = bot

    def validate(self):
        return pick_fire_staff(equipment.contains) is None

    def execute(self):
        bot = self.bot
        opened = yield from bot.open_bank()
        if not opened:
            return
        if inventory.used() > 0:
            yield from bank.deposit_all_matching(lambda name, id: True)
            yield from execution.delay_ticks(1)
        staff = pick_fire_staff(lambda name: inventory.count(name) > 0)
        if staff is None:
            staff = pick_fire_staff(lambda name: bank.count(name) > 0)
            taken = False
            if staff is not None:
                bot.log(f'withdrawing {staff}')
                taken = yield from bank.withdraw_x(staff, 1)
            if not taken:
                # The bank's list may still be filling after the open, so it checks before stopping.
                out = yield from bot.bank_truly_out_of(FIRE_STAVES)
                if not out:
                    bot.log('withdraw of a fire staff stalled but the bank list is still settling; retrying')
                    return
                bot.log('no fire staff in the bank; stopping')
                bot.request_finish('no fire staff in the bank')
                return
        closed = yield from bank.close()
        if not closed:
            bot.log('bank would not close; retrying')
            return

        def wieldable():
            item = inventory.first(staff)
            return not bank.is_open() and item is not None and len([o for o in item.actions() if o.lower() in ['wield', 'wear', 'equip']]) > 0

        # Why: shutting the bank leaves the deposit options on the pack for a moment, so it waits for Wield.
        yield from execution.delay_until(wieldable, 3000)
        bot.status = f'wielding {staff}'
        wielded = yield from equipment.equip(staff)
        if not wielded:
            bot.log(f'could not wield {staff}; stopping')
            bot.request_finish(f'could not wield {staff}')
            return
        bot.log(f'wore {staff}; casts need only {NATURE_RUNE}s now')
        yield from bot.open_bank()


# Why: it tops the nature runes up, withdraws a trip's ore and shuts the bank, which is normally open already.
class Restock(Task):
    def __init__(self, bot):
        Task.__init__(self, label='restock')
        self.bot = bot

    def validate(self):
        return not self.bot.can_smelt_one()

    def execute(self):
        bot = self.bot
        opened = yield from bot.open_bank()
        if not opened:
            return
        # Why: everything but the nature runes goes, bars, partial ore and junk, so a restock starts from a known pack.
        bot.status = 'restocking'
        if inventory.used() > 0:
            before = inventory.used()
            yield from bank.deposit_all_matching(lambda name, id: name.lower() != NATURE_RUNE.lower())
            yield from execution.delay_ticks(1)
            cleared = before - inventory.used()
            if cleared > 0:
                bot.log(f'cleared {cleared} items from the pack')
        topped = yield from self.top_up_natures()
        if not topped:
            return
        withdrawn = yield from self.withdraw_ores()
        if not withdrawn:
            return
        closed = yield from bank.close()
        if not closed:
            bot.log('bank would not close; retrying')
            return
        bot.trips += 1
        plan = ' + '.join([f'{n} {ore}' for ore, n in withdraw_set(bot.recipe)])
        bot.log(f'restocked: {plan} + {inventory.count(NATURE_RUNE)} {NATURE_RUNE}s')

    def top_up_natures(self):
        bot = self.bot
        have = inventory.count(NATURE_RUNE)
        # Why: it tops up only when the pack can't cover the next trip; more than a trip's casts buys nothing.
        want = bot.natures - have
        if have >= bars_per_trip(bot.recipe) or want <= 0:
            return True
        taken = yield from bank.withdraw_x(NATURE_RUNE, want)
        if taken:
            bot.log(f'topped up {NATURE_RUNE}s to {inventory.count(NATURE_RUNE)}')
            return True
        if inventory.count(NATURE_RUNE) == have and bank.count(NATURE_RUNE) == 0:
            out = yield from bot.bank_truly_out_of([NATURE_RUNE])
            if not out:
                bot.log('nature-rune count is still settling; retrying')
                return False
            bot.log(f'no {NATURE_RUNE}s in the bank; stopping')
            bot.request_finish(f'no {NATURE_RUNE}s in the bank')
        return False

    def withdraw_ores(self):
        bot = self.bot
        for ore, count in withdraw_set(bot.recipe):
            before = inventory.count(ore)
            ok = yield from bank.withdraw_x(ore, count)
            got = inventory.count(ore) - before
            if not ok or got == 0:
                # The list can read 0 while it loads after an open or a deposit, so it checks first.
                out = yield from bot.bank_truly_out_of([ore])
                if not out:
                    bot.log(f'withdraw of {ore} stalled but the bank list is still settling; retrying')
                    return False
                bot.log(f'no {ore} in the bank (wanted {count}); stopping')
                bot.request_finish(f'no {ore} in the bank')
                return False
            if got < count:
                out = yield from bot.bank_truly_out_of([ore])
                if not out:
                    bot.log(f'partial withdraw of {ore} but the bank list is still settling; retrying')
                    return False
                bot.log(f'WARNING: only {got}/{count} {ore} withdrawn; a partial recipe smelts the wrong bar')
                bot.request_finish(f'only {got} {ore} in the bank')
                return False
        return True


# Why: Superheat Item goes on the primary ore once a bar, a cast at a time, until the ore is gone.
class Smelt(Task):
    def __init__(self, bot):
        Task.__init__(self, label='smelt')
        self.bot = bot

    def validate(self):
        return not bank.is_open() and self.bot.can_smelt_one()

    def execute(self):
        bot = self.bot
        recipe = bot.recipe
        bot.status = f'casting {SUPERHEAT_ITEM} on {primary_ore(recipe)}'
        opened = yield from game.open_side_tab(MAGIC_TAB)
        if not opened:
            bot.log('could not open the magic tab; retrying')
            return
        # Why: a cast on a partial recipe smelts the wrong bar (iron without coal makes iron), so each cast needs
        # the whole set and a nature rune, and waits for the bar to form before the next.
        start = bars_smeltable(recipe, inventory.count)
        while bot.can_smelt_one():
            ore = inventory.first(primary_ore(recipe))
            if ore is None:
                break
            if not game.cast_on_item(SUPERHEAT_ITEM, ore):
                bot.log(f'cast-on-item was rejected for {ore.name}; retrying')
                yield from execution.delay_ticks(1)
                continue
            yield from execution.delay_ticks(CAST_TICKS)
        bot.smelted += start - bars_smeltable(recipe, inventory.count)
        if inventory.count(primary_ore(recipe)) > 0:
            left = bars_smeltable(recipe, inventory.count)
            if inventory.count(NATURE_RUNE) == 0:
                bot.log(f"out of {NATURE_RUNE}s with {left} bars' worth of ore left; banking to restock")
            else:
                bot.log(f"WARNING: stopped early; {left} more bars' worth of ore left, but the loop bailed. No partial-recipe casts were sent.")


# Why: the bars are banked by depositing all but the nature runes, and the bank stays open for the next restock.
class BankBars(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank bars')
        self.bot = bot

    def validate(self):
        return not bank.is_open() and inventory.count(primary_ore(self.bot.recipe)) == 0 and inventory.used() > 0

    def execute(self):
        bot = self.bot
        bot.status = 'banking bars'
        opened = yield from bot.open_bank()
        if not opened:
            bot.log('could not open the bank; retrying')
            return
        before = inventory.used()
        yield from bank.deposit_all_matching(lambda name, id: name.lower() != NATURE_RUNE.lower())
        bot.log(f'deposited {before - inventory.used()} items (kept {inventory.count(NATURE_RUNE)} {NATURE_RUNE}s), bank left open')


class Superheater(TaskBot):
    loop_delay = 400

    def on_start(self):
        s = self.settings
        self.recipe = recipe_for_bar(s.str('bar', 'Bronze')) or recipe_for_bar('Bronze')
        self.natures = s.num('natures', NATURES_DEFAULT)
        self.known_bank = None
        self.smelted = 0
        self.trips = 0
        self.status = 'starting'
        self.xp_at_start = skills.xp('smithing')
        self.magic_xp_at_start = skills.xp('magic')
        if skills.level('magic') < MAGIC_REQUIRED:
            self.log(f"Superheat Item needs {MAGIC_REQUIRED} Magic (have {skills.level('magic')}); stopping")
            self.request_finish(f'Superheat Item needs {MAGIC_REQUIRED} Magic')
            return
        if skills.level('smithing') < self.recipe.level:
            self.log(f"{self.recipe.bar} bars need {self.recipe.level} Smithing (have {skills.level('smithing')}); stopping")
            self.request_finish(f'{self.recipe.bar} bars need {self.recipe.level} Smithing')
            return
        plan = ' + '.join([f'{n} {ore}' for ore, n in withdraw_set(self.recipe)])
        self.log(f'Superheater; {self.recipe.bar} via {SUPERHEAT_ITEM} ({plan}), keeping {self.natures} {NATURE_RUNE}s')
        resolved = yield from self.resolve_bank()
        if not resolved:
            return
        self.add(EnsureGear(self), BankBars(self), Restock(self), Smelt(self))

    # Why: the nearest bank is found once and walked to; later trips only open it.
    def resolve_bank(self):
        here = game.tile()
        if here is None:
            return False
        known = nearest_bank(here)
        if known is None:
            self.log('no reachable bank; stopping')
            self.request_finish('no reachable bank')
            return False
        self.known_bank = known
        self.log(f"banking at {known['name']}")
        stand = Tile(known['tile']['x'], known['tile']['z'], known['tile']['level'])
        if stand.level == here.level and stand.distance_to(here) <= 4:
            return True
        self.status = f"walking to {known['name']}"
        walked = yield from traversal.walk_resilient(stand, radius=3, attempts=4, timeout_ms=180000, log=lambda m: self.log(f'  {m}'))
        if not walked:
            self.log('walk to the bank failed; stopping')
            self.request_finish('walk to the bank failed')
            return False
        return True

    def open_bank(self):
        if bank.is_open():
            return True
        self.status = 'opening bank'
        opened = yield from open_bank_access(self.known_bank, BOOTH, lambda m: self.log(f'  {m}'))
        if not opened:
            self.log('could not open the bank; retrying')
            return False
        return True

    # Why: a smelt needs the whole set of ore and a nature rune.
    def can_smelt_one(self):
        return all([inventory.count(ore) >= per for ore, per in self.recipe.ingredients]) and inventory.count(NATURE_RUNE) > 0

    # Why: an open bank's list fills a moment after the open and again after each deposit, so 0 can be a list not
    # loaded yet; before stopping for want of something, it waits for the list and checks every name reads 0.
    def bank_truly_out_of(self, names):
        settled = yield from execution.delay_until(lambda: bank.loaded(), 3500)
        if not settled:
            return False
        return all([bank.count(name) == 0 for name in names])

    def on_progress_report(self):
        return {'Status': self.status, 'Bars': self.smelted, 'Smithing xp': skills.xp('smithing') - self.xp_at_start,
                'Magic xp': skills.xp('magic') - self.magic_xp_at_start, 'Bank trips': self.trips,
                'Runes': f'{inventory.count(NATURE_RUNE)}/{self.natures}', 'Pack': inventory.used()}


BOT = define_bot(
    name='Superheater',
    create=Superheater,
    description='Smelts bars with the Superheat Item spell instead of a furnace — withdraws ore, casts onto the primary ore, banks the bars, repeat',
    category='Smithing',
    tags=['smithing', 'magic', 'superheat', 'banking'],
    settings_schema=SETTINGS,
)
