# Picks flax in Seers' Village's field until the pack is full, banks it, and repeats: rs2b0t's FlaxPicker (MIT,
# see thirdparty/rs2b0t). Boxed in by flax with a full pack, it drops a few and picks a way out.

from rs2004.catalogs import ContinueDialog

DEFAULT_FIELD = Tile(2741, 3444, 0)
# The opening on the field's west side.
DEFAULT_FIELD_GATE = Tile(2736, 3443, 0)
DEFAULT_BANK_ENTRANCE = Tile(2726, 3487, 0)
# The middle of the booth stands, which run 4 tiles either side along the same z.
DEFAULT_BANK_STAND = Tile(2725, 3493, 0)
BANK_STAND_SPAN = 4
BOOTH_OP = 'Use-quickly'
FIELD_SCOPE = 12
FIELD_ARRIVE = 3
POCKET_CAP = 40
# Flax to drop to free slots for picking a way out.
CARVE_DROP = 5
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

SETTINGS = {
    'flax_name': SettingDef('string', 'Flax', 'Flax loc name'),
    'pick_op': SettingDef('string', 'Pick', 'Interact op'),
    'field_tile': SettingDef('tile', DEFAULT_FIELD, 'Field centre tile (x,z)', help='centre of the flax field'),
    'field_gate': SettingDef('tile', DEFAULT_FIELD_GATE, 'Field gate/opening (x,z)', help='the opening on the west side — run out here before banking'),
    'bank_entrance': SettingDef('tile', DEFAULT_BANK_ENTRANCE, 'Bank entrance tile (x,z)', help='doorway into the bank, walked to on the way in and out'),
    'bank_stand': SettingDef('tile', DEFAULT_BANK_STAND, 'Bank stand tile (x,z)', help='a booth-adjacent tile; the bot uses the nearest reachable one along this row'),
    'bank_booth': SettingDef('string', 'Bank booth', 'Bank booth loc name'),
}


def _key(x, z):
    return f'{x},{z}'


class EscapeFlaxTrap(Task):
    def __init__(self, bot):
        Task.__init__(self, label='escape flax trap')
        self.bot = bot

    def validate(self):
        return self.bot.boxed_by_flax()

    def execute(self):
        yield from self.bot.carve_out()


class StartupReset(Task):
    def __init__(self, bot):
        Task.__init__(self, label='startup reset')
        self.bot = bot

    def validate(self):
        return self.bot.startup_pending

    def execute(self):
        self.bot.startup_pending = False
        if inventory.used() == 0:
            return
        self.bot.log('startup: emptying the pack at the bank before picking')
        yield from self.bot.bank_run()


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return inventory.is_full()

    def execute(self):
        yield from self.bot.bank_run()


class Pick(Task):
    def __init__(self, bot):
        Task.__init__(self, label='pick')
        self.bot = bot

    def validate(self):
        return not inventory.is_full() and self.bot.at_field() and self.bot.nearest_flax() is not None

    def execute(self):
        bot = self.bot
        for _ in range(30):
            if inventory.is_full() or chat_dialog.can_continue():
                return
            flax = bot.nearest_flax()
            if flax is None:
                return
            target = flax.tile()
            bot.status = f'picking {bot.flax_name} at {target}'
            before = bot.flax_count()
            if not flax.interact(bot.pick_op):
                yield from execution.delay_ticks(2)
                continue
            yield from execution.delay_until(lambda: bot.flax_count() > before or inventory.is_full() or chat_dialog.can_continue() or not bot.flax_still_at(target), 6000)


class GoToField(Task):
    def __init__(self, bot):
        Task.__init__(self, label='go to field')
        self.bot = bot

    def validate(self):
        return not inventory.is_full() and self.bot.nearest_flax() is None

    def execute(self):
        bot = self.bot
        here = game.tile()
        if here is not None and bot.field_tile.distance_to(here) <= FIELD_ARRIVE:
            # At the centre while the flax grows back.
            yield from execution.delay_ticks(2)
            return
        bot.status = 'travelling to the flax field'
        yield from bot.travel_to(bot.field_tile, FIELD_ARRIVE)


class FlaxPicker(TaskBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.flax_name = s.str('flax_name', 'Flax')
        self.pick_op = s.str('pick_op', 'Pick')
        self.field_tile = s.tile('field_tile', DEFAULT_FIELD)
        self.field_gate = s.tile('field_gate', DEFAULT_FIELD_GATE)
        self.bank_entrance = s.tile('bank_entrance', DEFAULT_BANK_ENTRANCE)
        self.bank_stand = s.tile('bank_stand', DEFAULT_BANK_STAND)
        self.booth_name = s.str('bank_booth', 'Bank booth')
        self.picked = 0
        self.trips = 0
        self.status = 'starting'
        self.startup_pending = True
        self.log(f"FlaxPicker picking '{self.flax_name}' ({self.pick_op}) at {self.field_tile}; gate {self.field_gate}, bank entrance {self.bank_entrance}, stand {self.bank_stand}")
        self.on('inventory_changed', self.slot_changed)
        self.add(ContinueDialog(), EscapeFlaxTrap(self), StartupReset(self), BankTrip(self), Pick(self), GoToField(self))

    def slot_changed(self, e):
        if e.id != -1 and self.is_flax(e.name) and e.previous_id != e.id:
            self.picked += 1

    def recovery_anchor(self):
        return self.field_tile

    def flax_count(self):
        return inventory.count(self.flax_name)

    def is_flax(self, name):
        return self.flax_name.lower() in (name or '').lower()

    def at_field(self):
        here = game.tile()
        return here is not None and self.field_tile.distance_to(here) <= FIELD_SCOPE

    def nearest_flax(self):
        field = self.field_tile
        flax = locs.query().name(self.flax_name).action(self.pick_op).where(lambda l: l.tile().distance_to(field) <= FIELD_SCOPE).results()
        me = game.tile()
        if me is not None:
            flax.sort(key=lambda l: l.tile().distance_to(me))
        for f in flax:
            if reachability.can_reach(f.tile(), adjacent_ok=True, max_steps=400):
                return f
        return None

    def flax_loc_at(self, x, z, level):
        return locs.query().name(self.flax_name).action(self.pick_op).where(lambda l: l.tile().x == x and l.tile().z == z and l.tile().level == level).nearest()

    def flax_still_at(self, tile):
        return self.flax_loc_at(tile.x, tile.z, tile.level) is not None

    def pocket_tiles(self, cap):
        """The tiles you can walk to, up to cap of them, nearest first."""
        me = game.tile()
        if me is None:
            return []
        level = me.level
        seen = [_key(me.x, me.z)]
        out = [(me.x, me.z)]
        queue = [(me.x, me.z)]
        while len(queue) > 0 and len(out) < cap:
            x, z = queue.pop(0)
            here = Tile(x, z, level)
            for dx, dz in DIRS:
                nx = x + dx
                nz = z + dz
                k = _key(nx, nz)
                if k in seen or not reachability.can_step(here, Tile(nx, nz, level)):
                    continue
                seen.append(k)
                out.append((nx, nz))
                queue.append((nx, nz))
        return out

    def boundary_flax(self, pocket):
        me = game.tile()
        level = me.level if me is not None else 0
        inside = [_key(x, z) for x, z in pocket]
        seen = []
        walls = []
        for x, z in pocket:
            for dx, dz in DIRS:
                nx = x + dx
                nz = z + dz
                k = _key(nx, nz)
                if k in inside or k in seen:
                    continue
                seen.append(k)
                flax = self.flax_loc_at(nx, nz, level)
                if flax is not None:
                    walls.append(flax)
        return walls

    def boxed_by_flax(self):
        if not inventory.is_full():
            return False
        pocket = self.pocket_tiles(POCKET_CAP)
        return len(pocket) < POCKET_CAP and len(self.boundary_flax(pocket)) > 0

    def drop_flax(self, n):
        for _ in range(n):
            flax = None
            for item in inventory.items():
                if self.is_flax(item.name):
                    flax = item
                    break
            if flax is None:
                return
            before = self.flax_count()
            if not flax.interact('Drop'):
                return
            yield from execution.delay_until(lambda: self.flax_count() < before, 2000)

    def carve_out(self):
        self.status = 'boxed in by flax; carving a way out'
        self.log(f'boxed in by flax with a full pack; dropping {CARVE_DROP} flax to pick a way out')
        yield from self.drop_flax(CARVE_DROP)
        gate = self.field_gate
        for _ in range(20):
            if chat_dialog.can_continue() or event_signal.pending():
                return
            pocket = self.pocket_tiles(POCKET_CAP)
            if len(pocket) >= POCKET_CAP:
                self.log('carved back out to open ground')
                return
            walls = self.boundary_flax(pocket)
            # Walled in by the map, not flax: nothing to carve.
            if len(walls) == 0:
                return
            if inventory.is_full():
                yield from self.drop_flax(CARVE_DROP)
            walls.sort(key=lambda w: w.tile().distance_to(gate))
            target = walls[0]
            t = target.tile()
            if not target.interact(self.pick_op):
                yield from execution.delay_ticks(2)
                continue
            yield from execution.delay_until(lambda: not self.flax_still_at(t), 4000)

    def nearest_stand(self):
        me = game.tile()
        stand = self.bank_stand
        row = [Tile(x, stand.z, stand.level) for x in range(stand.x - BANK_STAND_SPAN, stand.x + BANK_STAND_SPAN + 1)]
        pool = [t for t in row if reachability.can_reach(t)]
        pick = pool if len(pool) > 0 else row
        if me is None:
            return pick[len(pick) // 2]
        pick.sort(key=lambda t: t.distance_to(me))
        return pick[0]

    def walk_local(self, dest, radius):
        last = None
        for _ in range(30):
            now = game.tile()
            if now is not None and dest.distance_to(now) <= radius:
                return True
            if not reachability.probeable(dest):
                return False
            direct_navigator.walk(dest)

            def near():
                t = game.tile()
                return t is not None and dest.distance_to(t) <= radius

            yield from execution.delay_until(near, 1800)
            moved = game.tile()
            if moved is not None and last is not None and moved.x == last.x and moved.z == last.z:
                return False
            last = moved
        end = game.tile()
        return end is not None and dest.distance_to(end) <= radius

    def travel_to(self, dest, radius):
        if reachability.probeable(dest):
            walked = yield from self.walk_local(dest, radius)
            if walked:
                return True
        arrived = yield from traversal.walk_resilient(dest, radius=max(radius, 2), attempts=4, timeout_ms=180000, log=lambda m: self.log(f'  {m}'))
        return arrived

    def bank_run(self):
        had = self.flax_count()
        if self.at_field():
            self.status = 'leaving the field via the gate'
            yield from self.travel_to(self.field_gate, 0)
        self.status = 'walking to the bank entrance'
        arrived = yield from self.travel_to(self.bank_entrance, 1)
        if not arrived:
            self.log('could not reach the bank entrance; will retry')
            return False
        stand = self.nearest_stand()
        self.status = 'stepping to the bank counter'
        yield from self.travel_to(stand, 0)
        opened = yield from bank.open_booth(stand, self.booth_name, BOOTH_OP)
        if not opened:
            opened = yield from bank.open_nearest(self.booth_name, BOOTH_OP)
        if not opened:
            self.log('could not open the bank; will retry')
            return False
        yield from bank.deposit_inventory()
        yield from execution.delay_ticks(1)
        self.trips += 1
        self.log(f'banked {had} {self.flax_name} (+ any junk)')
        self.status = 'returning to the field'
        yield from self.travel_to(self.bank_entrance, 1)
        yield from self.travel_to(self.field_gate, 0)
        yield from self.travel_to(self.field_tile, FIELD_ARRIVE)
        return True

    def on_progress_report(self):
        return {'Status': self.status, 'Picked': self.picked, 'Trips': self.trips, 'Free slots': inventory.free(), 'Held': self.flax_count()}


BOT = define_bot(
    name='FlaxPicker',
    create=FlaxPicker,
    description='Seers flax field picker — pick flax until full, bank it at Seers, repeat',
    category='Crafting',
    tags=['seers', 'gathering', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
