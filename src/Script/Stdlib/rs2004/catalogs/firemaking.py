"""Burning logs: choosing a lane of tiles to light along, and one light. Ported from rs2b0t's
api/firemaking/Firemaking.ts and LightFire.ts (MIT, see thirdparty/rs2b0t). The fire spots and log levels are
rs2004.catalogs.tables'.

A successful light steps you a tile west, so a lane runs west: find_burn_lane looks for a run of free tiles that
fits the load, westward first, and lights on the others only one at a time.

    lane = find_burn_lane(plot, game.tile(), no_light.merge(fires), logs, reachability.walkable, reachability.can_step)
"""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tables import CANT_LIGHT, FIRE_LIGHT_TICKS, FIRE_START_TICKS, in_fire_plot
from rs2004.catalogs.tools import TINDERBOX
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages

BURN_WEST = (-1, 0)
# West first, for lanes, then the other ways, for one light wherever there's room.
BURN_DIRS = [BURN_WEST, (1, 0), (0, -1), (0, 1)]
# A backpack holds at most 27 logs beside a tinderbox.
MAX_BURN_LANE = 27


def tile_key(tile):
    return f'{tile.x},{tile.z}'


def burn_lane_want(log_count):
    """How many lights to want from one lane: the logs held, 1 to 27."""
    return max(1, min(MAX_BURN_LANE, int(log_count) or 1))


def is_burn_west(direction):
    return direction[0] == BURN_WEST[0] and direction[1] == BURN_WEST[1]


def run_in_dir(start, plot, direction, occupied, walkable, can_step, cap):
    """How many free tiles in a row from start, going direction, inside the plot, up to cap: free is walkable(t)
    and its tile_key not in occupied, and each step on must be can_step(a, b)."""
    n = 0
    current = start
    while n < cap:
        if not in_fire_plot(current, plot) or tile_key(current) in occupied or not walkable(current):
            break
        n += 1
        following = Tile(current.x + direction[0], current.z + direction[1], current.level)
        if not can_step(current, following):
            break
        current = following
    return n


def run_west(start, plot, occupied, walkable, can_step, cap):
    return run_in_dir(start, plot, BURN_WEST, occupied, walkable, can_step, cap)


def _better(run, distance, direction, best, need):
    full = run >= need
    best_full = best.run >= need
    west = is_burn_west(direction)
    best_west = is_burn_west(best.dir)
    if full and west and not (best_full and best_west):
        return True
    if best_full and best_west and not (full and west):
        return False
    if full != best_full:
        return full
    if west != best_west:
        return west
    if run != best.run:
        return run > best.run
    return distance < best.d


def find_burn_lane(plot, here, occupied, want, walkable, can_step, dirs=None):
    """The best lane start in the plot as a Record of start (a Tile), run and dir, or None: a westward run that
    fits want logs, else the longest westward run, else any free tile, nearest first."""
    need = burn_lane_want(want)
    best = None
    for direction in (dirs if dirs is not None else BURN_DIRS):
        cap = need if is_burn_west(direction) else 1
        for z in range(plot.z0, plot.z1 + 1):
            for x in range(plot.x0, plot.x1 + 1):
                start = Tile(x, z, plot.bank.level)
                run = run_in_dir(start, plot, direction, occupied, walkable, can_step, cap)
                if run == 0:
                    continue
                distance = max(abs(x - here.x), abs(z - here.z))
                if best is None or _better(run, distance, direction, best, need):
                    best = Record({'start': start, 'run': run, 'd': distance, 'dir': direction})
    if best is None:
        return None
    return Record({'start': best.start, 'run': best.run, 'dir': best.dir})


def fire_reaction_ticks():
    """Ticks between lights along a lane."""
    return 1


class NoLightTiles:
    """Tiles that answered "You can't light a fire here" this session, which find_burn_lane would otherwise
    choose again and again."""

    def __init__(self):
        self._refused = set()

    def add(self, tile):
        self._refused.add(tile_key(tile))

    def has(self, tile):
        return tile_key(tile) in self._refused

    @property
    def size(self):
        return len(self._refused)

    def merge(self, occupied):
        """occupied for find_burn_lane, with the refused tiles added."""
        merged = set(occupied)
        for key in self._refused:
            merged.add(key)
        return merged

    def clear(self):
        self._refused = set()


def light_fire(log_name):
    """Lights the logs on the tile you stand on: 'lit', 'blocked' (the game refused the tile) or 'stalled' (no
    answer). Use with yield from."""
    logs = inventory.first(log_name)
    tinder = inventory.first(TINDERBOX)
    if logs is None or tinder is None:
        return 'stalled'
    mark = game_messages.mark()
    xp = skills.xp('firemaking')
    held = inventory.count(log_name)

    def lit():
        return skills.xp('firemaking') > xp

    def blocked():
        return game_messages.saw_since(mark, CANT_LIGHT)

    # The tinderbox on the logs; the logs on the tinderbox do nothing.
    if not tinder.use_on(logs):
        return 'stalled'
    started = yield from execution.delay_until_ticks(lambda: inventory.count(log_name) < held or blocked() or game.animating(), FIRE_START_TICKS)
    if not started:
        return 'stalled'
    answered = yield from execution.delay_until_ticks(lambda: lit() or blocked() or event_signal.pending(), FIRE_LIGHT_TICKS)
    if not answered:
        return 'stalled'
    if blocked():
        return 'blocked'
    return 'lit' if lit() else 'stalled'
