"""Balls of wool from the sheep up: rs2b0t's api/ai/quests/exec/wool.ts (MIT, see thirdparty/rs2b0t). Shears from
their spawn, a sheep sheared at a time, then the lot spun at a wheel."""

from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.items import inventory
from rs2004.navigation import reachability
from rs2004.quests.engine.types import quest_step
from rs2004.traversal import traversal

__all__ = ['UNSHEARED_SHEEP_ID', 'WoolSites', 'gather_wool']

UNSHEARED_SHEEP_ID = 43


class WoolSites:
    """The sheep pen, where to stand for the spinning wheel, the shears' spawn, and the spin step's label."""

    def __init__(self, pen, wheel_stand, shears_spawn, spin_label):
        self.pen = pen
        self.wheel_stand = wheel_stand
        self.shears_spawn = shears_spawn
        self.spin_label = spin_label


def _shearable(n):
    return n.id == UNSHEARED_SHEEP_ID and reachability.can_reach(n.tile(), True)


def shear_one(pen, log):
    """Shears one sheep in reach, or walks to the pen. Use with yield from."""
    before = inventory.count('Wool')
    sheep = npcs.query().name('Sheep').within(8).where(_shearable).nearest()
    if sheep is None:
        yield from traversal.walk_resilient(pen, radius=2, attempts=2, timeout_ms=60000, log=log)
        return False
    shears = inventory.first('Shears')
    log('shearing a sheep for its wool')
    if shears is None or not shears.use_on(sheep):
        return False
    sheared = yield from execution.delay_until(lambda: inventory.count('Wool') > before, 6000)
    return sheared


def spin_all_wool(wheel_stand, log):
    """Spins every wool in the pack at the wheel by wheel_stand. Use with yield from.

    See rs2b0t's docs/decisions/level-change-lag.md: a wheel on an upper floor reads empty for a tick."""
    balls_before = inventory.count('Ball of wool')
    if not chat_dialog.is_make_menu():
        wheel = locs.query().name('Spinning wheel').action('Spin').within(8).nearest()
        if wheel is None:
            yield from traversal.walk_resilient(wheel_stand, radius=2, attempts=3, timeout_ms=300000, log=log)
            yield from execution.delay_ticks(2)
            return False
        log('spinning wool into a ball at the spinning wheel')
        if not wheel.interact('Spin'):
            return False
        opened = yield from execution.delay_until(lambda: chat_dialog.is_make_menu(), 8000)
        if not opened:
            log('Spin menu never opened')
            return False
    made = yield from chat_dialog.make_x('Wool', inventory.count('Wool'))
    if not made:
        log(f"Spin menu open but couldn't Make-X — products: [{', '.join(chat_dialog.make_products())}]")
        return False
    last = inventory.count('Wool')
    idle = 0
    while inventory.count('Wool') > 0 and idle < 10:
        yield from execution.delay_ticks(2)
        now = inventory.count('Wool')
        if now < last:
            last = now
            idle = 0
        else:
            idle += 1
    return inventory.count('Ball of wool') > balls_before


def gather_wool(snap, need, sites):
    """The next step towards need balls of wool."""
    if snap.inv.get('wool', 0) >= need:
        return quest_step('custom', name=sites.spin_label, run=lambda log: spin_all_wool(sites.wheel_stand, log))
    if 'shears' not in snap.inv:
        return quest_step('grab_ground', item='Shears', anchor=sites.shears_spawn)
    return quest_step('custom', name='shear a sheep', run=lambda log: shear_one(sites.pen, log))
