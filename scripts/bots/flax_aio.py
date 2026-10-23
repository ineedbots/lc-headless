# Picks flax at the Seers' field and/or spins it at the wheel upstairs into bow strings, banking between:
# rs2b0t's FlaxAIO (MIT, see thirdparty/rs2b0t). With both on it picks a full pack, spins it, and banks the strings.

import time

from rs2004.catalogs import ContinueDialog

# Why: these are Seers' village layout, not player choices; a location preset would swap the set at once.
FIELD = Tile(2741, 3444, 0)
FIELD_GATE = Tile(2736, 3443, 0)
BANK_STAND = Tile(2725, 3493, 0)
LADDER = Tile(2714, 3471, 0)
WHEEL = Tile(2711, 3471, 1)
BANK_STAND_SPAN = 4
FIELD_SCOPE = 12
FIELD_ARRIVE = 3
FLAX_NAME = 'Flax'
PICK_OP = 'Pick'
BOOTH = 'Bank booth'
BOOTH_OP = 'Use-quickly'
LADDER_NAME = 'Ladder'
CLIMB_UP = 'Climb-up'
CLIMB_DOWN = 'Climb-down'
WHEEL_NAME = 'Spinning wheel'
SPIN_OP = 'Spin'
OBSTACLES = ['door']
LEASH = 8
SPUN_NAME = {'Flax': 'Bow string', 'Wool': 'Ball of wool'}
POCKET_CAP = 40
CARVE_DROP = 5
RESPIN_AFTER_TICKS = 6
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
# How far the local walk is tried before the web walker takes over; about half a loaded scene.
LOCAL_WALK_RANGE = 40
LOCAL_WALK_MS = 18000

SETTINGS = {
    'picking': SettingDef('boolean', True, 'Pick flax', help='pick flax at the Seers field before spinning'),
    'spinning': SettingDef('boolean', True, 'Spin flax', help='spin flax at the Seers wheel into bow strings'),
}


def _key(x, z):
    return f'{x},{z}'


def is_flax(name):
    return FLAX_NAME.lower() in (name or '').lower()


def flax_count():
    return inventory.count(FLAX_NAME)


def stack_count(pattern):
    return sum([max(1, i.count) for i in inventory.items() if pattern in (i.name or '').lower()])


def fibre_count():
    return stack_count(FLAX_NAME.lower())


def bowstring_count():
    return stack_count((SPUN_NAME.get(FLAX_NAME) or 'Bow string').lower())


def on_level(level):
    here = game.tile()
    return here is not None and here.level == level


# Walking

def nearest_stand():
    """A stand along the bank's counter: the nearest one already reachable, or of the whole row."""
    me = game.tile()
    row = [Tile(x, BANK_STAND.z, BANK_STAND.level) for x in range(BANK_STAND.x - BANK_STAND_SPAN, BANK_STAND.x + BANK_STAND_SPAN + 1)]
    # Why: a stand already reachable is preferred, falling back to the full row if the nav graph sees none of them.
    pool = [t for t in row if reachability.can_reach(t)]
    pick = pool if len(pool) > 0 else row
    if me is None:
        return pick[len(pick) // 2]
    pick.sort(key=lambda t: t.distance_to(me))
    return pick[0]


def travel_to(bot, dest, radius):
    """A local walk while dest is close, then the web walker. Use with yield from."""
    here = game.tile()
    if here is not None and dest.distance_to(here) <= radius:
        return True
    # Why: rs2b0t clicks scene-local tiles first; the direct navigator's clicks stand in for its local walk.
    if here is not None and here.level == dest.level and dest.distance_to(here) <= LOCAL_WALK_RANGE:
        arrived = yield from direct_navigator.walk_to(dest, radius, LOCAL_WALK_MS)
        if arrived:
            return True
    walked = yield from traversal.walk_resilient(dest, radius=max(radius, 2), attempts=4, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))
    return walked


# Banking

def bank_run(bot):
    """Use with yield from."""
    def log(m):
        bot.log(f'  {m}')

    stand = nearest_stand()
    bot.status = 'stepping to the bank counter'
    arrived = yield from travel_to(bot, stand, 0)
    if not arrived:
        return False
    opened = yield from bank.open_booth(stand, BOOTH, BOOTH_OP)
    if not opened:
        opened = yield from bank.open_nearest(BOOTH, BOOTH_OP)
    if not opened:
        log('could not open the bank — will retry')
        return False
    yield from bank.deposit_inventory()
    yield from execution.delay_ticks(1)
    # Why: spinning alone takes its flax from the bank, so it refills after depositing the product.
    if bot.spinning and not bot.picking and fibre_count() == 0:
        found = [i for i in bank.items() if i.name is not None and FLAX_NAME.lower() in i.name.lower()]
        if len(found) == 0 or bank.count(found[0].name) == 0:
            bot.status = f'out of {FLAX_NAME} — stopped'
            bot.request_finish(f"out of '{FLAX_NAME}' in the bank")
            return False
        name = found[0].name
        ops = found[0].actions()
        op = withdraw_op(ops, 'all') or withdraw_op(ops, 'any') or 'Withdraw-All'
        bot.status = f'withdrawing {name}'
        bank.withdraw(name, op)
        yield from execution.delay_until(lambda: fibre_count() > 0 or bank.count(name) == 0, 4000)
    return True


class BankTask(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank')
        self.bot = bot

    def validate(self):
        return self.bot.needs_bank()

    def execute(self):
        yield from bank_run(self.bot)


# Picking

def at_field():
    here = game.tile()
    return here is not None and FIELD.distance_to(here) <= FIELD_SCOPE


def nearest_flax():
    me = game.tile()
    flax = locs.query().name(FLAX_NAME).action(PICK_OP).where(lambda l: l.tile().distance_to(FIELD) <= FIELD_SCOPE).results()
    if me is not None:
        flax.sort(key=lambda l: l.tile().distance_to(me))
    for f in flax:
        if reachability.can_reach(f.tile(), adjacent_ok=True, max_steps=400):
            return f
    return None


def flax_loc_at(x, z, level):
    return locs.query().name(FLAX_NAME).action(PICK_OP).where(lambda l: l.tile().x == x and l.tile().z == z and l.tile().level == level).nearest()


def pocket_tiles():
    """The tiles you can walk to, up to POCKET_CAP of them, nearest first."""
    me = game.tile()
    if me is None:
        return []
    level = me.level
    seen = [_key(me.x, me.z)]
    out = [(me.x, me.z)]
    queue = [(me.x, me.z)]
    while len(queue) > 0 and len(out) < POCKET_CAP:
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


def boundary_flax(pocket):
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
            flax = flax_loc_at(nx, nz, level)
            if flax is not None:
                walls.append(flax)
    return walls


def boxed_by_flax():
    if not inventory.is_full():
        return False
    pocket = pocket_tiles()
    return len(pocket) < POCKET_CAP and len(boundary_flax(pocket)) > 0


def drop_flax(n):
    """Use with yield from."""
    for _ in range(n):
        flax = None
        for item in inventory.items():
            if is_flax(item.name):
                flax = item
                break
        if flax is None:
            return
        before = flax_count()
        if not flax.interact('Drop'):
            return
        yield from execution.delay_until(lambda: flax_count() < before, 2000)


def carve_out(bot):
    """Use with yield from."""
    bot.status = 'boxed in by flax — carving a way out'
    bot.log('boxed in by flax with a full pack — dropping flax to pick a way out')
    yield from drop_flax(CARVE_DROP)
    for _ in range(20):
        if chat_dialog.can_continue() or event_signal.pending():
            return
        pocket = pocket_tiles()
        if len(pocket) >= POCKET_CAP:
            bot.log('carved back out to open ground')
            return
        walls = boundary_flax(pocket)
        if len(walls) == 0:
            return
        if inventory.is_full():
            yield from drop_flax(CARVE_DROP)
        walls.sort(key=lambda w: w.tile().distance_to(FIELD_GATE))
        target = walls[0]
        t = target.tile()
        if not target.interact(PICK_OP):
            yield from execution.delay_ticks(2)
            continue
        yield from execution.delay_until(lambda: flax_loc_at(t.x, t.z, t.level) is None, 4000)


class EscapeFlaxTrap(Task):
    def __init__(self, bot):
        Task.__init__(self, label='escape flax trap')
        self.bot = bot

    def validate(self):
        return self.bot.picking and boxed_by_flax()

    def execute(self):
        yield from carve_out(self.bot)


class PickTask(Task):
    def __init__(self, bot):
        Task.__init__(self, label='pick')
        self.bot = bot

    def validate(self):
        return self.bot.picking and not inventory.is_full() and at_field() and nearest_flax() is not None

    def execute(self):
        bot = self.bot
        for _ in range(30):
            if inventory.is_full() or chat_dialog.can_continue():
                return
            flax = nearest_flax()
            if flax is None:
                return
            target = flax.tile()
            bot.status = f'picking {FLAX_NAME} at {target}'
            before = flax_count()
            if not flax.interact(PICK_OP):
                yield from execution.delay_ticks(2)
                continue
            yield from execution.delay_until(lambda: flax_count() > before or inventory.is_full() or chat_dialog.can_continue() or flax_loc_at(target.x, target.z, target.level) is None, 6000)


class GoToFieldTask(Task):
    def __init__(self, bot):
        Task.__init__(self, label='go to field')
        self.bot = bot

    def validate(self):
        return self.bot.picking and not inventory.is_full() and nearest_flax() is None

    def execute(self):
        here = game.tile()
        if here is not None and FIELD.distance_to(here) <= FIELD_ARRIVE:
            yield from execution.delay_ticks(2)
            return
        self.bot.status = 'travelling to the flax field'
        yield from travel_to(self.bot, FIELD, FIELD_ARRIVE)


# Spinning

def climb_ladder(bot, op):
    """Use with yield from."""
    ladder = locs.query().name(LADDER_NAME).action(op).nearest()
    if ladder is None:
        bot.log(f"no '{LADDER_NAME}' offering '{op}' nearby")
        return False
    here = game.tile()
    before = here.level if here is not None else None
    ladder.interact(op)
    climbed = yield from execution.delay_until(lambda: game.tile() is not None and game.tile().level != before, 8000)
    return climbed


class AscendTask(Task):
    def __init__(self, bot):
        Task.__init__(self, label='ascend')
        self.bot = bot

    # Why: picking and spinning both fill the pack with flax before heading up, so it climbs once the pack is full.
    def validate(self):
        bot = self.bot
        return bot.spinning and on_level(0) and fibre_count() > 0 and (not bot.picking or inventory.is_full())

    def execute(self):
        bot = self.bot
        bot.status = 'heading up to the wheel'
        ladder = locs.query().name(LADDER_NAME).action(CLIMB_UP).nearest()
        if ladder is None or ladder.distance() > 1:
            yield from walk_opening(LADDER, 1, OBSTACLES, bot.log)
        yield from climb_ladder(bot, CLIMB_UP)


class SpinTask(Task):
    def __init__(self, bot):
        Task.__init__(self, label='spin')
        self.bot = bot

    def validate(self):
        return self.bot.spinning and on_level(1) and fibre_count() > 0 and not chat_dialog.can_continue()

    def execute(self):
        bot = self.bot
        if game.animating() and not chat_dialog.is_make_menu():
            yield from self.ride()
            return
        if not chat_dialog.is_make_menu():
            wheel = locs.query().name(WHEEL_NAME).action(SPIN_OP).within_of(WHEEL, LEASH).nearest()
            if wheel is None:
                yield from execution.delay_ticks(2)
                return
            bot.status = 'opening the spinning wheel'
            if not wheel.interact(SPIN_OP):
                yield from execution.delay_ticks(2)
                return
            opened = yield from execution.delay_until(lambda: chat_dialog.is_make_menu() or chat_dialog.can_continue() or game.animating(), 6000)
            if not opened:
                return
        if chat_dialog.is_make_menu():
            # Why: the wheel's menu asks which fibre to spin, so its entries are Wool and Flax, not their products.
            made = yield from chat_dialog.make_x(FLAX_NAME, fibre_count())
            if not made:
                bot.log(f"Spin menu open but Make-X '{FLAX_NAME}' missed; menu offers [{', '.join(chat_dialog.make_products())}]")
                yield from execution.delay_ticks(2)
                return
            bot.log(f"Make-X '{FLAX_NAME}' x{fibre_count()} accepted")
        yield from self.ride()

    def ride(self):
        bot = self.bot
        bot.status = 'spinning'
        last = fibre_count()
        idle = 0
        bot.log(f"riding the wheel with {last} '{FLAX_NAME}'")
        while fibre_count() > 0:
            if chat_dialog.can_continue() or not on_level(1):
                return
            yield from execution.delay_ticks(1)
            now = fibre_count()
            if now < last:
                bot.spun += last - now
                last = now
                idle = 0
            else:
                idle += 1
                if idle >= RESPIN_AFTER_TICKS:
                    return


class DescendTask(Task):
    def __init__(self, bot):
        Task.__init__(self, label='descend')
        self.bot = bot

    def validate(self):
        return self.bot.spinning and on_level(1) and fibre_count() == 0

    def execute(self):
        self.bot.status = 'heading back down'
        yield from climb_ladder(self.bot, CLIMB_DOWN)


class FlaxAIO(TaskBot):
    def on_start(self):
        self.loop_delay = 600
        self.picked = 0
        self.spun = 0
        self.trips = 0
        self.status = 'starting'
        self.started_at = time.time()
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.picking = self.settings.bool('picking', True)
        self.spinning = self.settings.bool('spinning', True)
        if not self.picking and not self.spinning:
            self.request_finish('FlaxAIO needs at least one of Pick or Spin enabled')
            return
        self.started_at = time.time()
        mode = ' + '.join([m for m in ['pick' if self.picking else '', 'spin' if self.spinning else ''] if m])
        self.log(f"FlaxAIO ({mode}) — flax '{FLAX_NAME}' at {FIELD}, wheel {WHEEL}")
        self.on('inventory_changed', self.inventory_changed)
        self.add(ContinueDialog(), EscapeFlaxTrap(self), BankTask(self), AscendTask(self), SpinTask(self), DescendTask(self), PickTask(self), GoToFieldTask(self))

    def inventory_changed(self, e):
        if e.id != -1 and is_flax(e.name):
            self.picked += 1

    def recovery_anchor(self):
        return FIELD

    # Why: banking only happens on the ground floor, so never mid-climb or at the wheel.
    def needs_bank(self):
        if not on_level(0):
            return False
        if bowstring_count() > 0:
            return True
        if self.spinning and not self.picking and fibre_count() == 0:
            return True
        return self.picking and not self.spinning and inventory.is_full()

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        xph = f'{self.spun * 15 / minutes * 60 / 1000:.1f}k' if minutes > 0.5 else '—'
        return {'Status': self.status, 'Picked': self.picked, 'Spun': self.spun, 'XP/hr': xph, 'Flax': flax_count(),
                'Bow strings': bowstring_count(), 'Bank trips': self.trips}


BOT = define_bot(
    name='FlaxAIO',
    create=FlaxAIO,
    description='Seers flax all-in-one — pick flax at the field and/or spin it at the wheel into bow strings, banking between. Pick and Spin are both optional toggles (at least one must be on); with both on it picks, spins on the way back, and banks the bow strings',
    category='Crafting',
    tags=['seers', 'crafting', 'gathering', 'banking', 'afk', 'flax', 'bow-strings'],
    settings_schema=SETTINGS,
)
