"""Reusable tasks for a TaskBot: get missing items, click through dialogue, recover from a death, and go
back to camp. Ported from rs2b0t's api/acquisition/ItemAcquisition.ts, api/tasks/ContinueDialog.ts,
DeathRecovery.ts and Anchor.ts, and api/sustain/Sustain.ts (MIT, see third_party/rs2b0t). PeriodicBank is
rs2004.bank's.
"""

import _core
from rs2004 import execution
from rs2004.bot import Task, is_generator
from rs2004.catalogs.gathering import DEFAULT_CAMP_RADIUS
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, local_tile
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.traversal import traversal
from rs2004.trade import shop


class ItemNeed:
    """A count of an item and where to get it: source is ('shop', keeper, near tile), ('ground', tile),
    ('gather',) or ('make',)."""

    def __init__(self, name, count, source):
        self.name = name
        self.count = count
        self.source = source

    def __repr__(self):
        return f'ItemNeed({repr(self.name)}, {self.count}, {self.source[0]})'


def held(name):
    return inventory.count(name)


def has_all(needs):
    return len([n for n in needs if held(n.name) < n.count]) == 0


class AcquireTask(Task):
    """Gets the first need not met: walks to the shop and buys it, or to its spawn and takes it."""

    def __init__(self, bot, needs):
        Task.__init__(self, label='acquire')
        self.bot = bot
        self.needs = needs

    def validate(self):
        return not has_all(self.needs)

    def execute(self):
        need = None
        for candidate in self.needs:
            if held(candidate.name) < candidate.count:
                need = candidate
                break
        if need is None:
            return
        kind = need.source[0]
        if kind == 'shop':
            keeper = need.source[1]
            near = need.source[2]
            self.bot.log(f'acquiring {need.name}: walking to {keeper}')
            arrived = yield from traversal.walk_resilient(near, radius=4, timeout_ms=120000)
            if not arrived:
                self.bot.log(f'could not reach {keeper} for {need.name} at {near}; will retry')
                return
            opened = yield from shop.open(keeper)
            if opened:
                bought = yield from shop.buy(need.name, need.count - held(need.name))
                if bought == 0:
                    self.bot.log(f'bought no {need.name}: out of stock or coins')
                    yield from execution.delay_ticks(5)
                shop.close()
            return
        if kind == 'ground':
            at = need.source[1]
            self.bot.log(f'acquiring {need.name}: walking to its spawn')
            arrived = yield from traversal.walk_resilient(at, radius=3, timeout_ms=120000)
            if not arrived:
                self.bot.log(f'could not reach the spawn of {need.name} at {at}; will retry')
                return
            item = ground_items.query().name(need.name).within(6).nearest()
            if item is None:
                yield from execution.delay_ticks(5)
                return
            before = held(need.name)
            name = need.name
            item.interact('Take')
            yield from execution.delay_until(lambda: held(name) > before, 5000)
            return
        raise NotImplementedError(f"an item source of '{kind}' isn't done yet")


class ContinueDialog(Task):
    """Clicks through a dialogue page whenever one can be continued."""

    def __init__(self, on_continue=None):
        Task.__init__(self, label='continue dialogue')
        self.on_continue = on_continue

    def validate(self):
        return chat_dialog.can_continue()

    def execute(self):
        if self.on_continue is not None:
            self.on_continue()
        yield from chat_dialog.continue_()


def _near(a, b, radius):
    return a.level == b.level and abs(a.x - b.x) <= radius and abs(a.z - b.z) <= radius


class DeathRecovery(Task):
    """After a death, gets the needs back (when given) and walks back to the anchor. It hears the death from
    the bot's death event."""

    def __init__(self, bot, anchor, radius=6, needs=None, on_death=None, on_recovered=None, walk_back=None):
        Task.__init__(self, label='death recovery')
        self.bot = bot
        self.anchor = anchor
        self.radius = radius
        self.needs = needs
        self.on_death = on_death
        self.on_recovered = on_recovered
        self.walk_back = walk_back
        self.died = False
        self.reacquire = AcquireTask(bot, needs) if needs else None
        bot.on('death', lambda: self._died())

    def _died(self):
        self.died = True
        if self.on_death is not None:
            self.on_death()

    def validate(self):
        if not self.died:
            return False
        here = local_tile()
        done = _near(here, self.anchor, self.radius) and (not self.needs or has_all(self.needs))
        if done:
            self.died = False
            if self.on_recovered is not None:
                self.on_recovered()
        return self.died

    def execute(self):
        yield from execution.delay_until(lambda: _core.is_placed(), 20000)
        yield from execution.delay_ticks(3)
        if self.reacquire is not None and self.reacquire.validate():
            yield from self.reacquire.execute()
            return
        if self.walk_back is not None:
            result = self.walk_back()
            if is_generator(result):
                yield from result
            return
        bot = self.bot
        yield from traversal.walk_resilient(self.anchor, radius=self.radius, log=lambda m: bot.log(f'  {m}'))


# Going back to camp.

HOME_ARRIVE_RADIUS = 8


def should_walk_home_to_gather_anchor(dist_to_anchor, arrive_radius=8):
    """Whether, after banking or finding nothing, to walk back toward the camp's anchor."""
    if dist_to_anchor is None:
        return False
    return dist_to_anchor > max(0, int(arrive_radius))


def should_soft_home_from_gather_miss(dist_to_anchor, leash=64):
    """Whether a gather that found nothing has wandered far enough to go home: 20 tiles, or the leash up to
    28."""
    if dist_to_anchor is None:
        return False
    limit = max(2, int(leash))
    return dist_to_anchor > max(HOME_ARRIVE_RADIUS + 12, min(limit, 28))


class AnchorHost:
    """What the anchor helpers need: anchor (a Tile) and leash_radius, with an optional log."""

    def __init__(self, anchor, leash_radius, log=None):
        self.anchor = anchor
        self.leash_radius = leash_radius
        self.log = log


def beyond_leash(host, here, slack=0):
    return here is not None and host.anchor.distance_to(here) > host.leash_radius + slack


def tile_within_leash(host, tile, slack=0):
    return host.anchor.distance_to(tile) <= host.leash_radius + slack


def resolve_run_anchor(here, location_spot):
    """The camp's spot, or where you stand when there's no camp."""
    if location_spot is not None:
        return location_spot
    return Tile(here.x, here.z, here.level)


def create_return_to_anchor_task(host, slack=6, arrive_radius=8, timeout_ms=90000, long_range_tiles=0, suppress=None):
    """A task that walks back within arrive_radius of the anchor once you're past the leash plus slack.
    Doors on the way are opened by the walker."""

    def validate():
        if suppress is not None and suppress():
            return False
        return beyond_leash(host, local_tile(), slack)

    def execute():
        say = host.log if host.log is not None else (lambda message: None)
        here = local_tile()
        if host.anchor.distance_to(here) <= arrive_radius:
            return
        if long_range_tiles > 0 and host.anchor.distance_to(here) > long_range_tiles:
            yield from traversal.walk_resilient(host.anchor, radius=arrive_radius, timeout_ms=timeout_ms, log=say)
            return
        yield from traversal.walk_to(host.anchor, radius=arrive_radius, timeout_ms=timeout_ms)

    return Task(validate, execute, 'return to anchor')


class _Sustain:
    """Upkeep a long loop must keep doing, such as eating: set(hook), then yield from sustain.run() in the
    loop's waits. The hook may be a generator function."""

    def __init__(self):
        self.hook = None
        self.running = False

    def set(self, hook):
        self.hook = hook

    def run(self):
        if self.hook is None or self.running:
            return
        self.running = True
        try:
            result = self.hook()
            if is_generator(result):
                yield from result
        except Exception as e:
            self.running = False
            raise e
        self.running = False


sustain = _Sustain()
