"""Pack budgeting, the hard-clue kit and the trace: rs2b0t's api/ai/clues/packPlan.ts, hardClueKit.ts and
ClueTrace.ts (MIT, see thirdparty/rs2b0t). Pure, so the slot arithmetic is testable without a bank."""

import json
import time

from rs2004.catalogs.tables import item_db

# Packing

# Why: hosts size food_withdraw() for sustained combat (20+), which fills the pack and starves the trail kit, the
# runes especially.
TRAIL_FOOD_CAP = 10
# Sextant, watch and chart, fetched after banking when the bank had none.
COORD_TOOL_SLOTS = 3
# Why: runes stack, so a bigger cast budget costs no extra slot, and a trail that ran dry mid-route walked the rest
# of the map (4 casts kept doing that).
TELEPORT_CASTS = 20


def teleport_rune_target(per_cast):
    """Runes to hold for a teleport that burns per_cast of them."""
    return per_cast * TELEPORT_CASTS


def trail_food_target(host_want, held_food, free_slots, reserve_slots):
    """How much food a trail carries: the host's number capped to trail size, and never more than the pack can
    spare once reserve_slots (coord tools fetched later) are set aside."""
    capped = min(host_want, TRAIL_FOOD_CAP)
    room = held_food + max(0, free_slots - reserve_slots)
    return max(0, min(capped, room))


def hard_trail_food_target(held_food, free_slots, reserve_slots, minimum_sharks=15):
    """The sharks a hard trail carries, or None when the pack can't hold the minimum."""
    target = min(minimum_sharks, held_food + max(0, free_slots - reserve_slots))
    return target if target >= minimum_sharks else None


def weapon_needed(weapon_name, in_backpack, equipped):
    """A weapon already worn is a weapon held: checking the pack alone withdrew a duplicate every prep, which on a
    full pack dropped to the floor."""
    return weapon_name != '' and not in_backpack and not equipped


# Why: the reward is rolled into a side inv and moved one slot at a time, so anything that doesn't fit hits the
# floor; the engine's reward scripts roll easy 2+random(3), medium 3+random(3), hard 4+random(3).
def casket_reward_slots(casket_obj):
    """Worst-case slots a casket needs on opening."""
    if '_hard_' in casket_obj:
        return 6
    if '_medium_' in casket_obj:
        return 5
    return 4


# The hard-clue kit

GUARDIAN_WEAPON_IDS = [1231, 1215, 1305]
SUPERANTI = [
    {'id': 2448, 'name': 'Superantipoison(4)', 'doses': 4},
    {'id': 181, 'name': 'Superantipoison(3)', 'doses': 3},
    {'id': 183, 'name': 'Superantipoison(2)', 'doses': 2},
    {'id': 185, 'name': 'Superantipoison(1)', 'doses': 1},
]
SHARK_ID = 385
MIN_SHARKS = 15
GUARDIAN_FOOD_RESERVE = 3
GUARDIAN_MIN_SHARKS = GUARDIAN_FOOD_RESERVE + 1


class GuardianRangedLoadout:
    """A ranged weapon and its ammo for the guardian, the quantity to carry and the combat mode."""

    def __init__(self, weapon, ammo, quantity, mode):
        self.weapon = weapon
        self.ammo = ammo
        self.quantity = quantity
        self.mode = mode


class HardKitSnapshot:
    """What the hard kit checks: the Attack level, whether Lost City is done, the items (each with id, count and
    name) and the ranged loadout, if the guardian is fought at range."""

    def __init__(self, attack, lost_city, items, ranged=None):
        self.attack = attack
        self.lost_city = lost_city
        self.items = items
        self.ranged = ranged


def _dose_count(id):
    for dose in SUPERANTI:
        if dose['id'] == id:
            return dose['doses']
    return 0


def superanti_doses(items):
    return sum([item.count * _dose_count(item.id) for item in items])


def ranged_weapon_id(name):
    wanted = name.lower()
    for item in item_db():
        if item.slot == 'righthand' and item.name.lower() == wanted:
            return item.id
    return None


def hard_clue_kit(kit, minimum_sharks=15, needs_antipoison=True):
    """'ready', or the first thing missing: 'attack', 'lost-city', 'weapon', 'ammo', 'superantipoison' or
    'sharks'."""
    if kit.ranged is not None:
        weapon = ranged_weapon_id(kit.ranged.weapon)
        if not any([item.id == weapon and item.count > 0 for item in kit.items]):
            return 'weapon'
        ammo = kit.ranged.ammo.lower()
        if not any([(item.name or '').lower() == ammo and item.count > 0 for item in kit.items]):
            return 'ammo'
    else:
        if kit.attack < 60:
            return 'attack'
        if not kit.lost_city:
            return 'lost-city'
        if not any([item.id in GUARDIAN_WEAPON_IDS and item.count > 0 for item in kit.items]):
            return 'weapon'
    if needs_antipoison and superanti_doses(kit.items) == 0:
        return 'superantipoison'
    if sum([item.count for item in kit.items if item.id == SHARK_ID]) < minimum_sharks:
        return 'sharks'
    return 'ready'


# The trace

TRACE_CAP = 200


def _now_ms():
    return time.time() * 1000


class ClueTrace:
    """The last cap lines of what a trail did, each stamped with the time and where the account stood, for a dump
    when the trail ends. now and pos are callables; pos gives a short position string."""

    def __init__(self, cap=200, now=None, pos=None):
        self.cap = cap
        self._now = now if now is not None else _now_ms
        self._pos = pos if pos is not None else (lambda: '?')
        self._buf = []
        self.clue_id = None
        self.name = ''
        self.started_at = 0

    def begin(self, clue_id, name):
        self._buf = []
        self.clue_id = clue_id
        self.name = name
        self.started_at = self._now()

    def note(self, m):
        self._buf.append({'t': self._now(), 'pos': self._pos(), 'm': m})
        if len(self._buf) > self.cap:
            self._buf.pop(0)

    def lines(self):
        return list(self._buf)

    def dump(self, reason, legs):
        return {'clue_id': self.clue_id, 'name': self.name, 'reason': reason, 'started_at': self.started_at, 'ended_at': self._now(),
                'legs': legs, 'lines': list(self._buf)}


def push_trace_ring(storage, key, dump, max=5):
    """Keeps the last max dumps under key. storage has get_item and set_item, as rs2b0t's localStorage."""
    ring = ([dump] + read_trace_ring(storage, key))[0:max]
    storage.set_item(key, json.dumps(ring))


def read_trace_ring(storage, key):
    raw = storage.get_item(key)
    if raw is None:
        return []
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []
