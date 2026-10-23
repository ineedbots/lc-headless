# Makes gold jewellery at Al Kharid's furnace: banks for the mould, the gold bars and the gems, uses a bar on the
# furnace, clicks the biggest Make button that fits the load, and stops when the bank runs out of any of the
# three. rs2b0t's JiveCrafting (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import ContinueDialog

GOLD_BAR = 'Gold bar'
PACK = 28
# Al Kharid: the bank stand SmelterBot uses, and the tile east of the furnace.
BANK_STAND = Tile(3269, 3167, 0)
FURNACE_STAND = Tile(3275, 3185, 0)
FURNACE = 'Furnace'
FURNACE_REACH = 8
BOOTH = 'Bank booth'
BOOTH_OP = 'Use-quickly'
OBSTACLES = ['door', 'gate']
PANEL_WAIT_MS = 6000
# Ticks with no bar used before the batch counts as stalled; the furnace takes one every three.
STALL_TICKS = 12
CRAFT_HOLD_TICKS = 40
BATCH = {'Make 10': 10, 'Make 5': 5, 'Make': 1}
MOULD = {'ring': 'Ring mould', 'necklace': 'Necklace mould', 'amulet': 'Amulet mould'}


class Jewel:
    """item is the pack's name for it, and the furnace panel's."""

    def __init__(self, kind, gem, level, xp, item=None):
        self.label = f"{gem or 'Gold'} {kind}"
        self.item = item if item is not None else self.label
        self.kind = kind
        self.gem = gem
        self.level = level
        self.xp = xp
        self.mould = MOULD[kind]


# The content's crafting_jewelry_struct, with the xp the skill grants.
JEWELLERY = [
    Jewel('ring', None, 5, 15),
    Jewel('ring', 'Sapphire', 20, 40),
    Jewel('ring', 'Emerald', 27, 55),
    Jewel('ring', 'Ruby', 34, 70),
    Jewel('ring', 'Diamond', 43, 85),
    Jewel('ring', 'Dragonstone', 55, 100),
    Jewel('necklace', None, 6, 20),
    Jewel('necklace', 'Sapphire', 20, 55),
    Jewel('necklace', 'Emerald', 29, 60),
    Jewel('necklace', 'Ruby', 40, 75),
    Jewel('necklace', 'Diamond', 56, 90),
    Jewel('necklace', 'Dragonstone', 72, 105, 'Dragon necklace'),
    Jewel('amulet', None, 8, 30),
    Jewel('amulet', 'Sapphire', 24, 65),
    Jewel('amulet', 'Emerald', 31, 70),
    Jewel('amulet', 'Ruby', 50, 85),
    Jewel('amulet', 'Diamond', 70, 100),
    Jewel('amulet', 'Dragonstone', 80, 150, 'Dragonstoneamulet'),
]
PRODUCT_OPTIONS = [j.label for j in JEWELLERY]

SETTINGS = {
    'product': SettingDef('string', 'Sapphire ring', 'Product', options=PRODUCT_OPTIONS, help='which gold jewel to make this session'),
}


def jewel_by_name(name):
    wanted = name.strip().lower()
    for j in JEWELLERY:
        if j.label.lower() == wanted or j.item.lower() == wanted:
            return j
    return None


def sets_per_trip(j):
    """Bars a trip carries beside the mould: paired with a gem, or filling the pack for gold."""
    return (PACK - 1) // 2 if j.gem else PACK - 1


class PackState:
    def __init__(self, mould, bars, gems):
        self.mould = mould
        self.bars = bars
        self.gems = gems


def craftable(pack, j):
    if not pack.mould:
        return 0
    return min(pack.bars, pack.gems) if j.gem else pack.bars


def decide(pack, j):
    """'craft' or 'bank', read off the pack alone, so a restart lands on the same choice."""
    return 'craft' if craftable(pack, j) > 0 else 'bank'


class Plan:
    def __init__(self, ok, reason=None, mould=False, bars=0, gems=0):
        self.ok = ok
        self.reason = reason
        self.mould = mould
        self.bars = bars
        self.gems = gems


def withdraw_plan(j, mould_held, stock):
    """What a bank visit withdraws, or why the run has to stop."""
    if not mould_held and stock(j.mould) < 1:
        return Plan(False, f'no {j.mould} in the pack or the bank')
    bars = stock(GOLD_BAR)
    if bars < 1:
        return Plan(False, f'the bank has no {GOLD_BAR}')
    gems = stock(j.gem) if j.gem else 0
    if j.gem and gems < 1:
        return Plan(False, f'the bank has no {j.gem}')
    sets = min(sets_per_trip(j), bars, gems if j.gem else bars)
    return Plan(True, mould=not mould_held, bars=sets, gems=sets if j.gem else 0)


def make_op(remaining):
    """Every click reopens the panel, and a batch that outruns the bars ends in one message box, so the biggest
    button wins from six up, and Make 5 covers two to five."""
    if remaining >= 6:
        return 'Make 10'
    if remaining >= 2:
        return 'Make 5'
    return 'Make'


class _Batch:
    """A batch being made: the bars it started with, the last count seen, and ticks since one went."""

    def __init__(self, before, size):
        self.before = before
        self.size = size
        self.last = before
        self.idle = 0

    def done(self):
        now = inventory.count(GOLD_BAR)
        if now < self.last:
            self.last = now
            self.idle = 0
        else:
            self.idle += 1
        return self.before - now >= self.size or now == 0 or chat_dialog.can_continue() or self.idle >= STALL_TICKS


# Why: everything but the mould goes in, leftover bars and gems too, so a withdrawal starts from a known pack and
# a stray stack never shrinks the load.
class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return self.bot.step() == 'bank'

    def execute(self):
        bot = self.bot
        jewel = bot.jewel
        bot.status = 'walking to the bank'
        walked = yield from walk_opening(BANK_STAND, 0, OBSTACLES, lambda m: bot.log(f'  {m}'))
        if not walked:
            bot.log('[crafting] walk to the bank failed, will retry')
            return
        opened = yield from bank.open_booth(BANK_STAND, BOOTH, BOOTH_OP)
        if not opened:
            bot.log('[crafting] could not open the bank, will retry')
            return

        bot.status = 'banking the load'
        products = inventory.count(jewel.item)
        keep = jewel.mould.lower()
        yield from bank.deposit_all_matching(lambda name, id: name.lower() != keep)
        loaded = yield from execution.delay_until(lambda: bank.is_open() and bank.loaded(), 5000)
        if not loaded:
            bot.log('[crafting] the bank list has not filled in, retrying this trip' if bank.is_open() else '[crafting] the bank window closed, retrying this trip')
            return

        plan = withdraw_plan(jewel, inventory.contains(jewel.mould), bank.count)
        if not plan.ok:
            yield from bank.close()
            bot.status = 'stopped'
            bot.request_finish(f'[crafting] {plan.reason}')
            return
        lines = []
        if plan.mould:
            lines.append((jewel.mould, 1))
        lines.append((GOLD_BAR, plan.bars))
        if jewel.gem and plan.gems > 0:
            lines.append((jewel.gem, plan.gems))
        for name, count in lines:
            if not bank.is_open() or not bank.loaded():
                bot.log('[crafting] the bank window closed mid-withdrawal, retrying this trip')
                return
            bot.status = f'withdrawing {count} {name}'
            withdrawn = yield from bank.withdraw_x(name, count)
            if not withdrawn:
                bot.log(f'[crafting] could not withdraw {count} {name}, retrying this trip')
                return
        yield from bank.close()
        bot.trips += 1
        bot.banked += products
        mould = f'the {jewel.mould}, ' if plan.mould else ''
        gems = f' + {plan.gems} {jewel.gem}' if jewel.gem else ''
        bot.log(f'[crafting] banked {products} {jewel.item}, took {mould}{plan.bars} {GOLD_BAR}{gems}')


class Craft(Task):
    def __init__(self, bot):
        Task.__init__(self, label='craft')
        self.bot = bot

    def validate(self):
        return self.bot.step() == 'craft' and not chat_dialog.can_continue()

    def furnace(self):
        return locs.query().name(FURNACE).within_of(FURNACE_STAND, FURNACE_REACH).nearest()

    def execute(self):
        bot = self.bot
        jewel = bot.jewel
        here = game.tile()
        if here is None or FURNACE_STAND.distance_to(here) > 1 or self.furnace() is None:
            bot.status = 'walking to the furnace'
            walked = yield from walk_opening(FURNACE_STAND, 1, OBSTACLES, lambda m: bot.log(f'  {m}'))
            if not walked:
                bot.log('[crafting] walk to the furnace failed, will retry')
                return

        if not chat_dialog.is_main_make_panel():
            oven = self.furnace()
            bar = inventory.first(GOLD_BAR)
            if oven is None or bar is None:
                yield from execution.delay_ticks(2)
                return
            bot.status = f'using a {GOLD_BAR} on the furnace'
            bar.use_on(oven)
            panel = yield from execution.delay_until(lambda: chat_dialog.is_main_make_panel() or chat_dialog.can_continue(), PANEL_WAIT_MS)
            if not panel:
                yield from execution.delay_ticks(2)
                return
            if not chat_dialog.is_main_make_panel():
                return

        before = inventory.count(GOLD_BAR)
        want = craftable(bot.pack(), jewel)
        op = make_op(want)
        bot.status = f'{op} {jewel.label}'
        made = yield from chat_dialog.make_from_panel(jewel.item, op)
        if not made:
            bot.log(f"[crafting] the furnace panel has no '{jewel.item}' with {op}, it shows [{', '.join([p for p in chat_dialog.main_make_products() if p])}]")
            yield from execution.delay_ticks(2)
            return

        bot.status = f'making {jewel.label}'
        # Why: one bounded hold a loop, so the message box that ends a short batch reaches ContinueDialog, and a
        # furnace that stopped taking bars is retried rather than waited on.
        batch = _Batch(before, min(want, BATCH[op]))
        yield from execution.delay_until_ticks(batch.done, CRAFT_HOLD_TICKS)
        bot.made += max(0, before - inventory.count(GOLD_BAR))


class JiveCrafting(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.made = 0
        self.trips = 0
        self.banked = 0
        self.xp_start = skills.xp('crafting')
        pick = self.settings.str('product', 'Sapphire ring')
        jewel = jewel_by_name(pick)
        self.jewel = jewel if jewel is not None else JEWELLERY[1]
        if jewel is None:
            self.request_finish(f"[crafting] unknown product '{pick}'")
            return
        level = skills.level('crafting')
        if level < jewel.level:
            self.request_finish(f'[crafting] {jewel.label} needs Crafting {jewel.level}, this account has {level}')
            return
        gem = f' + {jewel.gem}' if jewel.gem else ''
        self.log(f'[crafting] making {jewel.label} from {GOLD_BAR}{gem} with the {jewel.mould}, bank {BANK_STAND}, furnace {FURNACE_STAND}')
        self.add(ContinueDialog(), BankTrip(self), Craft(self))

    def recovery_anchor(self):
        return BANK_STAND

    def pack(self):
        return PackState(inventory.contains(self.jewel.mould), inventory.count(GOLD_BAR), inventory.count(self.jewel.gem) if self.jewel.gem else 0)

    def step(self):
        return decide(self.pack(), self.jewel)

    def on_progress_report(self):
        pack = self.pack()
        return {'Status': self.status, 'Product': self.jewel.label, 'Made': self.made, 'Trips': self.trips, 'Banked': self.banked,
                'Crafting xp': skills.xp('crafting') - self.xp_start, 'Bars': pack.bars, 'Can make': craftable(pack, self.jewel)}


BOT = define_bot(
    name='JiveCrafting',
    create=JiveCrafting,
    description='Makes one gold jewel picked from the dropdown at the Al Kharid furnace: banks for the mould, the gold bars and the gems, uses a bar on the furnace, clicks the biggest Make button that fits the load and walks back with it. Stops honestly when the bank runs out of any of the three.',
    category='Crafting',
    tags=['crafting', 'jewellery', 'al kharid', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
