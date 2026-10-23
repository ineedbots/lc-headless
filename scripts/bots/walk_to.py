# Walks to a named destination or a tile and stops: rs2b0t's WalkToBot, registered as WalkTo (MIT, see
# thirdparty/rs2b0t). A destination saved while it runs, with settings_store, is walked to instead.

from rs2004.catalogs import WALK_OPTIONS, resolve_destination

NAME = 'WalkTo'
MAP_PICK = 'Map pick'
UNSET_TILE = Tile(0, 0, 0)
DEST_OPTIONS = [MAP_PICK] + WALK_OPTIONS
STALL_LIMIT = 3

SETTINGS = {
    'destination': SettingDef('string', WALK_OPTIONS[0], 'Destination', options=DEST_OPTIONS, help='Pick on Map sets Map pick. Choosing a named destination clears the map pick.'),
    'custom_tile': SettingDef('tile', UNSET_TILE, 'Map pick tile (x,z)', help='set by Pick on Map. A named Destination above clears this.'),
    'arrive_radius': SettingDef('number', 0, 'Arrive within (tiles)', 0, 12, help='0 = stand on the destination tile, then the script stops'),
}


def is_set_custom_tile(tile):
    return tile.x != 0 or tile.z != 0


def has_arrived(here, dest, radius):
    return here.level == dest.level and max(abs(here.x - dest.x), abs(here.z - dest.z)) <= radius


class WalkTarget:
    def __init__(self, tile, label, named):
        self.tile = tile
        self.label = label
        self.named = named


def resolve_walk_target(destination, custom):
    """The tile to walk to. A named destination wins over a leftover map pick: Pick on Map writes the custom
    tile, which used to keep winning after a city was chosen."""
    named = resolve_destination(destination)
    if named is not None:
        return WalkTarget(named.tile, named.name, True)
    if destination == MAP_PICK or is_set_custom_tile(custom):
        if not is_set_custom_tile(custom):
            return None
        return WalkTarget(Tile(custom.x, custom.z, custom.level), f'{MAP_PICK} {custom.x},{custom.z}', False)
    return None


class WalkTask(Task):
    def __init__(self, bot):
        Task.__init__(self, label='walk to')
        self.bot = bot
        self.last_dist = None
        self.stalls = 0

    def validate(self):
        return not self.bot.arrived

    def execute(self):
        bot = self.bot
        target = bot.target
        radius = bot.radius
        start = game.tile()
        if start is not None and has_arrived(start, target, radius):
            self.arrive(start)
            return

        bot.status = f'walking to {bot.label}'
        yield from traversal.walk_to(target, radius=radius, timeout_ms=15000, log=lambda m: bot.log(f'  {m}'))
        here = game.tile()
        if bot.target != target:
            self.last_dist = None
            self.stalls = 0
            return
        if here is not None and has_arrived(here, target, radius):
            self.arrive(here)
            return

        dist = target.distance_to(here) if here is not None else None
        stalled = dist is None or (self.last_dist is not None and dist >= self.last_dist - 1)
        self.stalls = self.stalls + 1 if stalled else 0
        self.last_dist = dist
        if self.stalls >= STALL_LIMIT:
            self.stalls = 0
            bot.status = f'stuck {dist} tiles out; recovery walk'
            bot.log(f'no progress toward {bot.label}; escalating to a resilient pass')
            yield from traversal.walk_resilient(target, radius=radius, attempts=2, timeout_ms=60000, log=lambda m: bot.log(f'  {m}'))

    def arrive(self, here):
        bot = self.bot
        bot.arrived = True
        bot.status = f'arrived at {bot.label}'
        bot.log(f'arrived at {bot.label} ({here.x}, {here.z}, {here.level})')
        bot.request_finish(f'WalkTo: arrived at {bot.label}')


class WalkToBot(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.target = None
        self.label = ''
        self.radius = 0
        self.arrived = False
        self.status = 'starting'
        self.syncing = False
        self.destination = self.settings.str('destination', WALK_OPTIONS[0])
        self.custom = self.settings.tile('custom_tile', UNSET_TILE)
        self.radius = self.settings.num('arrive_radius', 0)
        self.apply_destination()
        if self.target is None:
            self.log('WalkTo: no destination set; stopping')
            raise ValueError('WalkTo: no destination')
        self.log(f'walking to {self.label} at {self.target} (arrive within {self.radius})')
        self.add(WalkTask(self))
        self.unsubscribe = settings_store.on_change(self.setting_saved)

    def on_stop(self, reason):
        self.unsubscribe()

    def setting_saved(self, name, key, value):
        """A destination saved while walking, through settings_store, is walked to instead."""
        if name != NAME or self.syncing:
            return
        # A named destination clears the map pick, and a map pick selects it, as rs2b0t's panel keeps them.
        self.syncing = True
        if key == 'destination':
            self.destination = value
            if value != MAP_PICK:
                self.custom = UNSET_TILE
                settings_store.save(NAME, 'custom_tile', [0, 0, 0])
        if key == 'custom_tile' and isinstance(value, list) and len(value) >= 2:
            self.custom = Tile(value[0], value[1], value[2] if len(value) > 2 else 0)
            if is_set_custom_tile(self.custom):
                self.destination = MAP_PICK
                settings_store.save(NAME, 'destination', MAP_PICK)
        if key == 'arrive_radius':
            self.radius = int(value)
        self.syncing = False
        if key == 'destination' or key == 'custom_tile':
            self.apply_destination()

    def apply_destination(self):
        found = resolve_walk_target(self.destination, self.custom)
        if found is None:
            return
        same = self.target is not None and found.tile == self.target and found.label == self.label
        self.target = found.tile
        self.label = found.label
        if not same:
            self.arrived = False

    def on_progress_report(self):
        here = game.tile()
        dist = self.target.distance_to(here) if here is not None and self.target is not None else -1
        return {'Status': self.status, 'Destination': self.label, 'Distance': 'arrived' if self.arrived else dist, 'Arrive within': self.radius}


BOT = define_bot(
    name=NAME,
    create=WalkToBot,
    description='Walks to a chosen destination and stops — Lumbridge, Varrock, Falador, Ardougne, Rellekka, Taverley (centre); Draynor, Al Kharid, Edgeville, Seers, Catherby, Yanille (bank); or a custom tile',
    category='Navigation',
    tags=['navigation', 'utility', 'web-walk'],
    settings_schema=SETTINGS,
)
