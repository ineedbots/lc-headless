# Cooks raw fish from the bank on the range nearest it, or on a fire it lights outside, one at a time, and banks
# the lot: rs2b0t's CookBot (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import COOK_LOCATION_OPTIONS, CUSTOM_LOCATION, FIRE_SPOTS, LOG_LEVELS, MAX_SURFACE_CHEB, NoLightTiles
from rs2004.catalogs import TINDERBOX, ContinueDialog, find_burn_lane, fire_reaction_ticks, light_fire, local_fire_plot
from rs2004.catalogs import resolve_cook_location, tile_key

DEFAULT_BANK_STAND = Tile(2809, 3441, 0)
DEFAULT_RANGE_STAND = Tile(2817, 3443, 0)
BOOTH_OP = 'Use-quickly'
# How close a lit fire counts as the one to cook on.
FIRE_REACH = 2
SURFACE_OPTIONS = ['Range', 'Fire']
# Why: one log a trip, so a fire that burns out early leaves nothing to relight with and the bot banks rather
# than stall on the spot.
LOGS_PER_TRIP = 1

SETTINGS = {
    'fish': SettingDef('string', 'Raw salmon', 'Raw fish to cook (contains)', help='e.g. Raw salmon / Raw shark / Raw lobster'),
    'location': SettingDef('string', 'Catherby', 'Where to cook', options=COOK_LOCATION_OPTIONS, help='Auto takes the nearest bank you can open. Custom uses the tiles below.'),
    'surface': SettingDef('string', 'Range', 'Cook on', options=SURFACE_OPTIONS,
                          help='Range walks to the oven or fireplace nearest the bank. Fire carries one log out to free ground beside the bank, lights it, and cooks there, which no closed door can reach.'),
    'log_type': SettingDef('string', 'Logs', 'Logs to burn (Fire only)', options=list(LOG_LEVELS.keys())),
    'fire_plot_radius': SettingDef('number', 8, 'Fire ground search radius (Fire only)', 2, 16),
    'bank_stand': SettingDef('tile', DEFAULT_BANK_STAND, 'Bank stand tile (Custom only)'),
    'range_stand': SettingDef('tile', DEFAULT_RANGE_STAND, 'Range stand tile (Custom only)'),
    'range_name': SettingDef('string', 'Range', 'Range loc name (Custom only)'),
    'bank_booth': SettingDef('string', 'Bank booth', 'Bank booth loc name'),
    'obstacle': SettingDef('string', 'door, gate', 'Openable obstacles (contains)', help='doors on the way to the bank or the range get opened'),
    'leash_radius': SettingDef('number', 8, 'Cook surface search radius (tiles)', 2, 20),
}


def _matches(name, pattern):
    return name is not None and pattern.strip().lower() in name.lower()


def count_raw(items, pattern):
    return len([i for i in items if _matches(i.name, pattern)])


def last_raw_index(items, pattern):
    for i in range(len(items) - 1, -1, -1):
        if _matches(items[i].name, pattern):
            return i
    return -1


def fire_plot_for(location_name, bank_tile, half):
    """The burn strip a location has in FIRE_SPOTS, walked by hand, else a box around the bank stand: Varrock
    East's strip is the street north of the bank, which an 8-tile box only clips."""
    return FIRE_SPOTS.get(location_name) or local_fire_plot(bank_tile, half)


def parse_surface_mode(label):
    """'range' walks to a catalogued oven or fireplace, 'fire' lights one beside the bank."""
    return 'fire' if label.strip().lower() == 'fire' else 'range'


def cook_keep_names(mode, tinderbox, log_name):
    """What the bank leg holds back before it withdraws the next load."""
    return [tinderbox, log_name] if mode == 'fire' else []


def logs_to_withdraw(mode, held):
    if mode != 'fire':
        return 0
    return max(0, LOGS_PER_TRIP - max(0, held))


class CookState:
    def __init__(self, mode, raw_left, logs_left, fire_lit):
        self.mode = mode
        self.raw_left = raw_left
        self.logs_left = logs_left
        self.fire_lit = fire_lit


# Why: an empty log pack sends the bot back to the bank only when nothing is burning; otherwise it finishes the
# load on the fire it has.
def needs_bank(s):
    return s.raw_left == 0 or (s.mode == 'fire' and s.logs_left == 0 and not s.fire_lit)


def needs_light(s):
    return s.mode == 'fire' and s.raw_left > 0 and s.logs_left > 0 and not s.fire_lit


def can_cook(s):
    return s.raw_left > 0 and (s.mode == 'range' or s.fire_lit)


def _plain(record):
    return {key: record.get(key) for key in record.keys()}


class CookDialog(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Cook dialog')
        self.bot = bot

    def validate(self):
        return chat_dialog.is_make_menu()

    def execute(self):
        self.bot.status = 'choosing product'
        made = yield from chat_dialog.make(self.bot.fish)
        if not made:
            yield from chat_dialog.make()
        yield from execution.delay_ticks(1)


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Bank trip')
        self.bot = bot

    def validate(self):
        return needs_bank(self.bot.state())

    def execute(self):
        bot = self.bot
        bot.status = 'banking'
        yield from walk_opening(bot.bank_stand, 0, bot.obstacles, bot.log)
        opened = yield from self.open()
        if not opened:
            bot.log('could not open the bank; will retry')
            return
        fire = bot.mode == 'fire'
        yield from bank.deposit_all_matching(deposit_all_except(cook_keep_names(bot.mode, TINDERBOX, bot.log_name)))
        yield from execution.delay_ticks(1)
        bot.trips += 1
        if fire:
            stocked = yield from self.stock_fire()
            if not stocked:
                return

        banked = [i for i in bank.items() if _matches(i.name, bot.fish)]
        if len(banked) == 0:
            bot.log(f"no '{bot.fish}' in the bank; idling")
            yield from execution.delay_ticks(5)
            return
        name = banked[0].name
        bot.log(f'withdrawing {name}')
        withdrawn = yield from bank.withdraw_load(name)
        if not withdrawn:
            bot.log(f'could not withdraw {name}; will retry')

    def open(self):
        """The booth, chest or banker this location uses."""
        place = self.bot.where.bank if self.bot.where is not None else None
        if place is not None and place.npc_access is not None:
            opened = yield from bank.open_npc_access(_plain(place.npc_access))
            return opened
        if place is not None and place.access is not None:
            opened = yield from bank.open_nearest_access(_plain(place.access))
            return opened
        opened = yield from bank.open_booth(self.bot.bank_stand, self.bot.booth_name, BOOTH_OP)
        return opened

    def stock_fire(self):
        """The tinderbox and logs, before the fish take the rest of the pack."""
        bot = self.bot
        if inventory.count(TINDERBOX) == 0:
            bank.withdraw(TINDERBOX)
            taken = yield from execution.delay_until_ticks(lambda: inventory.count(TINDERBOX) > 0, 5)
            if not taken:
                bot.request_finish('no tinderbox in the bank or pack')
                return False
        want = logs_to_withdraw('fire', inventory.count(bot.log_name))
        if want > 0:
            withdrawn = yield from bank.withdraw_x(bot.log_name, want)
            if not withdrawn:
                bot.log(f'could not withdraw {bot.log_name}; will retry')
        if inventory.count(bot.log_name) == 0:
            bot.request_finish(f'no {bot.log_name} left in the bank')
            return False
        return True


class LightTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Light trip')
        self.bot = bot

    def validate(self):
        return needs_light(self.bot.state())

    def execute(self):
        bot = self.bot
        refused = bot.no_light
        occupied = refused.merge([tile_key(l.tile()) for l in locs.query().results()])
        lane = find_burn_lane(bot.fire_plot(), game.tile(), occupied, 1, reachability.walkable, reachability.can_step)
        if lane is None:
            ruled = f' ({refused.size} tiles refused a light)' if refused.size > 0 else ''
            bot.log(f'no free ground left in the {bot.where_name} burn plot{ruled}; waiting for fires to burn out')
            bot.status = 'waiting for clear ground'
            yield from execution.delay_ticks(25)
            return

        start = lane.start
        bot.status = f'walking out to {start.x},{start.z}'
        yield from walk_opening(start, 0, bot.obstacles, bot.log)
        at = game.tile()
        if at is None or at.x != start.x or at.z != start.z or at.level != start.level:
            # Why: ruling the tile out stops the next scan handing back the one that couldn't be reached.
            refused.add(start)
            where = f'{at.x},{at.z}' if at is not None else 'nowhere'
            bot.log(f'stopped at {where} short of {start.x},{start.z}; ruling it out')
            return

        bot.status = 'lighting a fire'
        outcome = yield from light_fire(bot.log_name)
        if outcome == 'lit':
            bot.fires += 1
            yield from execution.delay_ticks(fire_reaction_ticks())
            return
        if outcome == 'blocked':
            refused.add(at)
            bot.log(f'{at.x},{at.z} will not take a fire; {refused.size} tiles ruled out so far')


class CookTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Cook trip')
        self.bot = bot

    def validate(self):
        return can_cook(self.bot.state()) and not chat_dialog.is_open()

    def surface(self):
        bot = self.bot
        if bot.mode == 'fire':
            return bot.lit_fire()
        return locs.query().name(bot.surface_name).within_of(bot.surface_stand, bot.leash).nearest()

    def reach_range(self):
        bot = self.bot
        here = game.tile()
        radius = bot.arrive_radius
        if here is not None and bot.surface_stand.distance_to(here) <= max(radius, 1) and self.surface() is not None:
            return True
        bot.status = f'crossing to the {bot.surface_name.lower()}'
        if bot.surface_approach is not None:
            yield from walk_opening(bot.surface_approach, 0, bot.obstacles, bot.log)
        yield from walk_opening(bot.surface_stand, radius, bot.obstacles, bot.log)
        return True

    def execute(self):
        bot = self.bot
        if bot.mode == 'range':
            reached = yield from self.reach_range()
            if not reached:
                return
        for _ in range(30):
            if bot.raw_count() == 0 or chat_dialog.is_make_menu() or chat_dialog.can_continue() or event_signal.pending():
                return
            raw = bot.last_raw()
            oven = self.surface()
            if raw is None or oven is None:
                yield from execution.delay_ticks(2)
                return
            bot.status = f'cooking {raw.name}'
            before = bot.raw_count()
            if not raw.use_on(oven):
                yield from execution.delay_ticks(2)
                continue
            done = yield from execution.delay_until(lambda: bot.raw_count() < before or chat_dialog.is_make_menu() or chat_dialog.can_continue(), 6000)
            if done and bot.raw_count() < before:
                bot.cooked += before - bot.raw_count()


class CookBot(TaskBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.fish = s.str('fish', 'Raw salmon')
        self.mode = parse_surface_mode(s.str('surface', 'Range'))
        self.booth_name = s.str('bank_booth', 'Bank booth')
        self.obstacles = [o.strip().lower() for o in s.str('obstacle', 'door, gate').split(',') if o.strip()]
        self.leash = s.num('leash_radius', 8)
        self.cooked = 0
        self.trips = 0
        self.fires = 0
        self.status = 'starting'
        self.xp_at_start = skills.xp('cooking')
        self.where = None
        self.surface_approach = None
        self.arrive_radius = 0
        self.log_name = 'Logs'
        self.plot_half = 8
        self.no_light = NoLightTiles()
        if not self.resolve_where() or not self.resolve_surface():
            return
        on = f'{self.log_name} fires beside the bank {self.bank_stand}' if self.mode == 'fire' else f'{self.surface_name} {self.surface_stand}'
        self.log(f"CookBot cooking '{self.fish}' at {self.where_name}, {on}")
        self.add(ContinueDialog(), CookDialog(self), BankTrip(self), LightTrip(self), CookTrip(self))

    def resolve_where(self):
        setting = self.settings.str('location', 'Catherby')
        custom = setting.strip().lower() == CUSTOM_LOCATION.lower()
        self.where = None if custom else resolve_cook_location(setting, game.tile())
        if not custom and self.where is None:
            self.request_finish(f"no bank called '{setting}' that this account can open")
            return False
        self.where_name = self.where.name if self.where is not None else CUSTOM_LOCATION
        self.bank_stand = self.where.bank.tile if self.where is not None else self.settings.tile('bank_stand', DEFAULT_BANK_STAND)
        return True

    def resolve_surface(self):
        if self.mode == 'fire':
            self.surface_name = 'Fire'
            self.surface_stand = self.bank_stand
            self.log_name = self.settings.str('log_type', 'Logs')
            self.plot_half = self.settings.num('fire_plot_radius', 8)
            need = LOG_LEVELS.get(self.log_name)
            have = skills.level('firemaking')
            if need is None:
                self.request_finish(f"unknown log_type '{self.log_name}'")
                return False
            if have < need:
                self.request_finish(f'{self.log_name} need Firemaking {need}, you have {have}')
                return False
            return True
        plan = self.where.surface if self.where is not None else None
        if self.where is not None and plan is None:
            self.request_finish(f"nothing cookable within {MAX_SURFACE_CHEB} tiles of the {self.where.name} bank, set 'Cook on' to Fire")
            return False
        self.surface_stand = plan.stand if plan is not None else self.settings.tile('range_stand', DEFAULT_RANGE_STAND)
        self.surface_approach = plan.approach if plan is not None else None
        self.surface_name = plan.loc_name if plan is not None else self.settings.str('range_name', 'Range')
        self.arrive_radius = (plan.arrive_radius or 0) if plan is not None else 0
        return True

    def fire_plot(self):
        return fire_plot_for(self.where_name, self.bank_stand, self.plot_half)

    def raw_count(self):
        return count_raw(inventory.items(), self.fish)

    def log_count(self):
        return inventory.count(self.log_name) if self.mode == 'fire' else 0

    def lit_fire(self):
        """A fire close enough to cook on, or None in range mode."""
        here = game.tile()
        if self.mode != 'fire' or here is None:
            return None
        return locs.query().name('Fire').within_of(here, FIRE_REACH).nearest()

    def state(self):
        return CookState(self.mode, self.raw_count(), self.log_count(), self.lit_fire() is not None)

    def last_raw(self):
        items = inventory.items()
        index = last_raw_index(items, self.fish)
        return items[index] if index >= 0 else None

    def on_progress_report(self):
        report = {'Status': self.status, 'Cooked': self.cooked, 'Cooking xp': skills.xp('cooking') - self.xp_at_start,
                  'Cooking': self.fish, 'Raw left': self.raw_count(), 'Bank trips': self.trips, 'At': self.where_name}
        if self.mode == 'fire':
            report['Fires'] = self.fires
        return report


BOT = define_bot(
    name='CookBot',
    create=CookBot,
    description='Bank cook loop — withdraw raw fish, cook it one at a time on the range nearest the bank or on a fire you light outside, bank everything, repeat',
    category='Cooking',
    tags=['cooking', 'banking', 'firemaking', 'afk'],
    settings_schema=SETTINGS,
)
