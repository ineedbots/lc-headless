# Spins flax into bow string at Seers' Village: withdraws flax, climbs to the spinning wheel, spins the load,
# banks and repeats. rs2b0t's FlaxSpinner (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import ContinueDialog

RESPIN_AFTER_TICKS = 6
DEFAULT_BANK_STAND = Tile(2722, 3493, 0)
DEFAULT_LADDER_TILE = Tile(2714, 3471, 0)
DEFAULT_WHEEL_TILE = Tile(2711, 3471, 1)
BOOTH_OP = 'Use-quickly'

SETTINGS = {
    'product': SettingDef('string', 'Flax', 'Fibre to spin', options=['Flax', 'Wool'], help='matched against the "What would you like to spin?" menu'),
    'bank_stand': SettingDef('tile', DEFAULT_BANK_STAND, 'Bank stand tile (x,z)'),
    'ladder_tile': SettingDef('tile', DEFAULT_LADDER_TILE, 'Ladder stand tile (x,z) — inside the house', help='walkable tile INSIDE the wheel house beside the ladder (not the ladder tile itself — see route note); the house door is opened on the way'),
    'wheel_tile': SettingDef('tile', DEFAULT_WHEEL_TILE, 'Spinning wheel tile (x,z,level)', help='upstairs — search centre for the wheel'),
    'bank_booth': SettingDef('string', 'Bank booth', 'Bank booth loc name'),
    'ladder_name': SettingDef('string', 'Ladder', 'Ladder/staircase loc name'),
    'climb_up_op': SettingDef('string', 'Climb-up', 'Ladder up op'),
    'climb_down_op': SettingDef('string', 'Climb-down', 'Ladder down op'),
    'wheel_name': SettingDef('string', 'Spinning wheel', 'Spinning wheel loc name'),
    'spin_op': SettingDef('string', 'Spin', 'Spinning wheel op'),
    'obstacle': SettingDef('string', 'door', 'Openable obstacles (contains)', help='the house door on the bank route'),
    'leash_radius': SettingDef('number', 8, 'Wheel/ladder search radius (tiles)', 2, 20),
}


def climb_ladder(name, op, log):
    """Climbs the nearest loc of that name offering op. Use with yield from; True once your level changed."""
    ladder = locs.query().name(name).action(op).nearest()
    if ladder is None:
        log(f"no '{name}' offering '{op}' nearby")
        return False
    here = game.tile()
    before = here.level if here is not None else None
    ladder.interact(op)

    def climbed():
        t = game.tile()
        return t is not None and t.level != before

    result = yield from execution.delay_until(climbed, 8000)
    return result


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return self.bot.is_on_floor(0) and self.bot.fibre_count() == 0

    def execute(self):
        bot = self.bot
        bot.status = 'banking'
        yield from walk_opening(bot.bank_stand, 0, bot.obstacles, bot.log)
        opened = yield from bank.open_booth(bot.bank_stand, bot.booth_name, BOOTH_OP)
        if not opened:
            bot.log('could not open the bank; will retry')
            return
        yield from bank.deposit_inventory()
        yield from execution.delay_ticks(1)
        bot.trips += 1

        wanted = bot.product.lower()
        banked = [i for i in bank.items() if i.name is not None and wanted in i.name.lower()]
        if len(banked) == 0 or bank.count(banked[0].name) == 0:
            bot.status = f'out of {bot.product}; stopped'
            bot.request_finish(f"out of '{bot.product}' in the bank")
            return
        name = banked[0].name
        ops = banked[0].actions()
        op = withdraw_op(ops, 'all') or withdraw_op(ops, 'any') or 'Withdraw-All'
        bot.status = f'withdrawing {name}'
        bank.withdraw(name, op)
        yield from execution.delay_until(lambda: bot.fibre_count() > 0 or bank.count(name) == 0, 4000)


class Ascend(Task):
    def __init__(self, bot):
        Task.__init__(self, label='ascend')
        self.bot = bot

    def validate(self):
        return self.bot.is_on_floor(0) and self.bot.fibre_count() > 0

    def execute(self):
        bot = self.bot
        bot.status = 'heading up to the wheel'
        ladder = locs.query().name(bot.ladder).action(bot.up_op).nearest()
        if ladder is None or ladder.distance() > 1:
            yield from walk_opening(bot.ladder_tile, 1, bot.obstacles, bot.log)
        yield from climb_ladder(bot.ladder, bot.up_op, lambda m: bot.log(f'  {m}'))


class Spin(Task):
    def __init__(self, bot):
        Task.__init__(self, label='spin')
        self.bot = bot

    def validate(self):
        return self.bot.is_on_floor(1) and self.bot.fibre_count() > 0 and not chat_dialog.can_continue()

    def execute(self):
        bot = self.bot
        if game.animating() and not chat_dialog.is_make_menu():
            yield from self.ride()
            return
        if not chat_dialog.is_make_menu():
            wheel = locs.query().name(bot.wheel).action(bot.spin).within_of(bot.wheel_tile, bot.leash).nearest()
            if wheel is None:
                yield from execution.delay_ticks(2)
                return
            bot.status = 'opening the spinning wheel'
            if not wheel.interact(bot.spin):
                yield from execution.delay_ticks(2)
                return
            menu = yield from execution.delay_until(lambda: chat_dialog.is_make_menu() or chat_dialog.can_continue() or game.animating(), 6000)
            if not menu:
                return
        if chat_dialog.is_make_menu():
            made = yield from chat_dialog.make_x(bot.product, bot.fibre_count())
            if not made:
                bot.log(f"Spin menu open but couldn't Make-X '{bot.product}'; products: [{', '.join(chat_dialog.make_products())}]")
                yield from execution.delay_ticks(2)
                return
        yield from self.ride()

    def ride(self):
        bot = self.bot
        bot.status = 'spinning'
        last = bot.fibre_count()
        idle = 0
        while bot.fibre_count() > 0:
            if chat_dialog.can_continue() or event_signal.pending() or not bot.is_on_floor(1):
                return
            yield from execution.delay_ticks(1)
            now = bot.fibre_count()
            if now < last:
                bot.spun += last - now
                last = now
                idle = 0
            else:
                idle += 1
                if idle >= RESPIN_AFTER_TICKS:
                    return


class Descend(Task):
    def __init__(self, bot):
        Task.__init__(self, label='descend')
        self.bot = bot

    def validate(self):
        return self.bot.is_on_floor(1) and self.bot.fibre_count() == 0

    def execute(self):
        bot = self.bot
        bot.status = 'heading back down'
        yield from climb_ladder(bot.ladder, bot.down_op, lambda m: bot.log(f'  {m}'))


class FlaxSpinner(TaskBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.product = s.str('product', 'Flax')
        self.bank_stand = s.tile('bank_stand', DEFAULT_BANK_STAND)
        self.ladder_tile = s.tile('ladder_tile', DEFAULT_LADDER_TILE)
        self.wheel_tile = s.tile('wheel_tile', DEFAULT_WHEEL_TILE)
        self.booth_name = s.str('bank_booth', 'Bank booth')
        self.ladder = s.str('ladder_name', 'Ladder')
        self.up_op = s.str('climb_up_op', 'Climb-up')
        self.down_op = s.str('climb_down_op', 'Climb-down')
        self.wheel = s.str('wheel_name', 'Spinning wheel')
        self.spin = s.str('spin_op', 'Spin')
        self.obstacles = [o.strip().lower() for o in s.str('obstacle', 'door').split(',') if o.strip()]
        self.leash = s.num('leash_radius', 8)
        self.spun = 0
        self.trips = 0
        self.status = 'starting'
        self.xp_at_start = skills.xp('crafting')
        self.log(f'FlaxSpinner spinning {self.product}; bank {self.bank_stand}, ladder {self.ladder_tile}, wheel {self.wheel_tile}')
        self.add(ContinueDialog(), BankTrip(self), Ascend(self), Spin(self), Descend(self))

    def is_on_floor(self, level):
        here = game.tile()
        return here is not None and here.level == level

    def fibre_count(self):
        pattern = self.product.lower()
        return sum([max(1, i.count) for i in inventory.items() if i.name is not None and pattern in i.name.lower()])

    def on_progress_report(self):
        here = game.tile()
        return {'Status': self.status, 'Spun': self.spun, 'Crafting xp': skills.xp('crafting') - self.xp_at_start,
                f'{self.product} left': self.fibre_count(), 'Floor': here.level if here is not None else '?', 'Bank trips': self.trips}


BOT = define_bot(
    name='FlaxSpinner',
    create=FlaxSpinner,
    description='Seers flax spinner — withdraw flax, climb to the spinning wheel, Spin-X into bow string, bank, repeat',
    category='Crafting',
    tags=['seers', 'crafting', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
