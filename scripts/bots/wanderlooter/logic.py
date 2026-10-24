"""WanderLooter's pure decisions: rs2b0t's scripts/WanderLooter/WanderLooterLogic.ts (MIT, see thirdparty/rs2b0t)."""

import math
import random
import time

DEFAULT_LOOT = ['Pumpkin']
LOOT_STUCK_MS = 30000
LOOT_BLACKLIST_MS = 30 * 60000

# A hit this soon before or after a pickup marks that item and tile as dangerous.
DANGER_WINDOW_MS = 15000
DANGER_RADIUS = 8

# The eight compass directions, from north clockwise.
WANDER_DIRECTIONS = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]


def now_ms():
    return time.time() * 1000


def normalize_name(name):
    return (name or '').strip().lower()


def matches_loot(name, configured):
    """Loot entries are exact names, without regard to case."""
    wanted = normalize_name(name)
    return len(wanted) > 0 and len([entry for entry in configured if normalize_name(entry) == wanted]) > 0


def tile_key(tile):
    return f'{tile.x}:{tile.z}:{tile.level}'


def loot_key(id, tile):
    return f'{id}:{tile_key(tile)}'


def should_deposit_on_bank(name, food, food_count, food_wanted):
    """Banks everything but coins, and keeps the food only up to the amount wanted."""
    normalized = normalize_name(name)
    if len(normalized) == 0 or normalized == 'coins':
        return False
    return normalized != normalize_name(food) or food_count > food_wanted


def should_bank_loot(loot_slots, bank_at, inventory_full):
    return loot_slots > 0 and (loot_slots >= bank_at or inventory_full)


def should_idle_bank(now, last_loot_at, quit_ms):
    return now - last_loot_at >= quit_ms


class LootBlacklist:
    """Item and tile pairs that failed, ignored for 30 minutes: at once when the server says unreachable, else after
    30 seconds stuck. now is a clock in milliseconds, the wall clock by default."""

    def __init__(self, now=None):
        self.now = now if now is not None else now_ms
        self.blocked_until = {}
        self.stuck = {}

    def blocked(self, id, tile):
        key = loot_key(id, tile)
        now = self.now()
        for entry in list(self.blocked_until.keys()):
            if self.blocked_until[entry] <= now:
                self.blocked_until.pop(entry)
        return self.blocked_until.get(key, 0) > now

    def success(self, id, tile):
        key = loot_key(id, tile)
        self.blocked_until.pop(key, None)
        self.stuck.pop(key, None)

    def failure(self, id, tile, status):
        """'blacklisted' or 'retrying', for a pickup that ended with status."""
        key = loot_key(id, tile)
        now = self.now()
        if status == 'unreachable':
            self.stuck.pop(key, None)
            self.blocked_until[key] = now + LOOT_BLACKLIST_MS
            return 'blacklisted'
        prev = self.stuck.get(key)
        started = prev[0] if prev is not None and now - prev[1] <= LOOT_STUCK_MS else now
        self.stuck[key] = (started, now)
        if now - started < LOOT_STUCK_MS:
            return 'retrying'
        self.stuck.pop(key, None)
        self.blocked_until[key] = now + LOOT_BLACKLIST_MS
        return 'blacklisted'

    def mark_unsafe(self, id, tile):
        """Damage near a pickup blocks that item and tile for 30 minutes at once."""
        key = loot_key(id, tile)
        self.stuck.pop(key, None)
        self.blocked_until[key] = self.now() + LOOT_BLACKLIST_MS

    def count(self):
        self.blocked(0, Tile(0, 0, 0))
        return len(self.blocked_until)


def shuffled_directions(rand):
    dirs = list(WANDER_DIRECTIONS)
    for i in range(len(dirs) - 1, 0, -1):
        j = math.floor(rand() * (i + 1))
        swap = dirs[i]
        dirs[i] = dirs[j]
        dirs[j] = swap
    return dirs


def pick_wander_tile(here, distance, navigable, rand=None, avoid_direction=None):
    """The full distance first, then a shorter hop, but never a tile navigable(tile) turns down. Upstairs, the floor
    below comes first."""
    if here.level > 0:
        down = Tile(here.x, here.z, here.level - 1)
        if navigable(down):
            return down
    distances = []
    for steps in [distance, max(1, math.floor(distance / 2)), 5]:
        if steps not in distances:
            distances.append(steps)
    directions = shuffled_directions(rand if rand is not None else random.random)
    forward = directions
    if avoid_direction is not None:
        forward = [d for d in directions if d[0] * avoid_direction[0] + d[1] * avoid_direction[1] >= 0]
    # Forward and sideways first, then a hop back if that's all the map offers.
    passes = [directions] if avoid_direction is None else [forward, directions]
    for dirs in passes:
        for steps in distances:
            for d in dirs:
                tile = Tile(here.x + d[0] * steps, here.z + d[1] * steps, here.level)
                if navigable(tile):
                    return tile
    return None
