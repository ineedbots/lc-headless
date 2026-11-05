"""Three-tick fly fishing from rs2b0t #912 (MIT, see thirdparty/rs2b0t)."""

import _core

from rs2004 import execution
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.bank import bank
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs, locs, ground_items
from rs2004.geometry import Tile
from rs2004.traversal import traversal
from rs2004.catalogs import AXES

KNIFE_SPAWN = Tile(2704, 3475, 0)
AXE_SPAWN = Tile(2678, 3731, 0)
MAKE_SHAFTS = 8889


class FlyCycle:
    """A fresh roll starts a batch; next-tick landing arms the roll two ticks later."""

    def __init__(self):
        self.state = 'native'
        self.serial = None
        self.sent = -1
        self.due = -1

    def step(self, tick, seq, started):
        serial = (seq, started)
        fresh = serial != self.serial
        self.serial = serial
        if self.state == 'native':
            if fresh and seq == 623:
                self.state = 'sent'
                self.sent = tick
                return 'batch'
        elif self.state == 'sent':
            if tick == self.sent + 1:
                if fresh and seq in [1248, 623]:
                    self.state = 'armed'
                    self.due = tick + 2
            elif tick >= self.sent + 2:
                self.state = 'native'
                return 'fallback'
        elif tick >= self.due:
            self.state = 'sent'
            self.sent = tick
            return 'batch'
        return 'wait'


def fish(bot, target):
    cycle = FlyCycle()
    me = _core.get_local_player()
    cycle.serial = (me.animation_id, me.animation_tick)
    index = target.index
    tile = target.tile()
    target.interact('Lure')
    for _ in range(200):
        yield from execution.delay_ticks(1)
        live = npcs.query().where(lambda n: n.index == index).nearest()
        if live is None or live.tile() != tile or live.id in [403, 404, 405, 406]:
            return
        if bank.is_open() or event_signal.pending() or game.in_combat() or not bot.has_gear() or bot.away_from_gather_spot(6):
            return
        me = _core.get_local_player()
        action = cycle.step(game.tick(), me.animation_id, me.animation_tick)
        if action == 'batch':
            knife = inventory.first('Knife')
            carrier = bot.delay_log_item()
            if knife is None or carrier is None:
                return
            for item in bot.products()[:2]:
                item.interact('Drop')
            if not chat_dialog.is_make_menu():
                knife.use_on(carrier)
            # The knife request opens the menu on the server within this same packet batch.
            _core.click_button(MAKE_SHAFTS)
            live.interact('Lure')
            bot.set_status(f'3-tick fly: batch @{game.tick()}')
        elif action == 'fallback':
            live.interact('Lure')
            bot.set_status('3-tick fly: fallback click')
        elif inventory.is_full() and cycle.state == 'native':
            return


def take_ground(bot, names, spawn):
    drop = ground_items.query().name(*names).within(12).nearest()
    if drop is None:
        reached = yield from traversal.walk_resilient(spawn, radius=2, attempts=3, timeout_ms=180000)
        if not reached:
            return False
        drop = ground_items.query().name(*names).within(8).nearest()
    if drop is None or not drop.interact('Take'):
        return False
    held = yield from execution.delay_until_ticks(lambda: any([bot.held_count(n) > 0 for n in names]), 6)
    return held


def restock_axe(bot):
    if bot.delay_log_item() is not None or any([bot.held_count(axe.name) > 0 for axe in AXES]):
        return
    for axe in AXES:
        if bank.count(axe.name) > 0:
            yield from bank.withdraw_x(axe.name, 1)
            return


def acquire_kit(bot):
    if inventory.count('Knife') == 0:
        taken = yield from take_ground(bot, ['Knife'], KNIFE_SPAWN)
        if not taken:
            return False
    if bot.delay_log_item() is not None:
        return True
    axes = [axe.name for axe in AXES]
    if not any([bot.held_count(n) > 0 for n in axes]):
        taken = yield from take_ground(bot, axes, AXE_SPAWN)
        if not taken:
            return False
    yield from bot.walk_home_if_needed(lambda m: bot.log(m))
    for tree in locs.query().name('Tree', 'Dead tree').action('Chop down').results()[:6]:
        reached = yield from traversal.walk_to(tree.tile(), radius=2, timeout_ms=90000)
        if not reached:
            continue
        tree.interact('Chop down')
        held = yield from execution.delay_until_ticks(lambda: bot.delay_log_item() is not None, 20)
        if held:
            return True
    return False
