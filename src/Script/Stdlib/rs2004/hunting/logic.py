"""The hunting framework's pure decisions: the safespot ladder, retreat and loot, prayer and antifire timing,
attack and engage ranges, and the shield and style gates. Ported from rs2b0t's api/combat/hunting/logic.ts (MIT,
see thirdparty/rs2b0t). A style is 'melee', 'mage' or 'range'; a spot is anything with x and z."""

import math

from rs2004.bank import matches_common_bank_loot
from rs2004.catalogs import _clues
from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.tabs import PROTECT_FROM_MELEE

__all__ = [
    'SAFESPOT_BLIND_MS', 'next_safespot', 'hurt_on_spot', 'retreat_due', 'loot_halts', 'hold_due', 'nearest_spot', 'body_origin',
    'Sighting', 'note_sighting', 'settled', 'retreat_aim', 'chase_mode', 'PROTECT_FROM_MELEE', 'prayer_for', 'PRAYER_SIP_FLOOR',
    'PRAYER_SIP_FRACTION', 'prayer_sip_due', 'LOOT_REACH', 'LOOT_REACH_OPEN', 'loot_reach', 'attack_range_for', 'engage_range_for',
    'gap_to', 'shield_gate', 'style_gate', 'SHIELD_ABSORBS', 'POTION_PROTECTS', 'ANTIFIRE_TICKS', 'ANTIFIRE_MARGIN_TICKS',
    'antifire_due', 'antifire_lapsed', 'next_approach_index', 'is_clue_obj', 'wants_drop', 'key_status', 'site_tile_of', 'keep_doses',
]

# How long the safespot may see no adult before the bot rotates off it.
SAFESPOT_BLIND_MS = 20000


# Why: the tiles are derived as melee-proof, so a hit is the derivation being wrong, and the blind window is a dragon
# body parked across the angle.
def next_safespot(index, spots, hurt, blind_ms):
    """The safespot index to stand on next. hurt: hp fell on the current one; blind_ms: how long no adult has
    been in sight."""
    if spots <= 1:
        return 0
    if not hurt and blind_ms < SAFESPOT_BLIND_MS:
        return index
    return (index + 1) % spots


# Why: the King Black Dragon breathes at anything it can see, so on its site a hit on the tile is expected and only
# the blind clock turns the ladder.
def hurt_on_spot(ranged_threat, on_spot, last_hp, hp):
    """Whether hp lost on the current safespot says the tile is wrong. last_hp is the hp read on the previous
    pass, or -1 when the bot was off the tile."""
    return not ranged_threat and on_spot and last_hp >= 0 and hp < last_hp


# Why: eating in dragonfire is a race the bot loses, so the walk out of the fire outranks the bite.
# Why: with no food hp only falls, so there's no threshold left to wait on, and the free immune tile is where the
# walk to the bank should start.
def retreat_due(in_lair, on_safespot, hp_frac, retreat_hp, has_food, spots):
    """Whether to break off and stand on a safespot rather than hold the tile the bot is on."""
    if not in_lair or spots <= 0 or on_safespot or retreat_hp <= 0:
        return False
    return not has_food or hp_frac < retreat_hp


# Why: a loot burst that checked only whether it needed to eat, which an empty pack never does, kept picking arrows
# off a demon's feet from 64 hp down to 10.
def loot_halts(hp_frac, panic_hp, retreat_hp):
    """Whether the run is too hurt to keep walking the drop pile, so the retreat or the bank run gets the loop."""
    return hp_frac < panic_hp or (retreat_hp > 0 and hp_frac < retreat_hp)


# Why: this and retreat_due pull opposite ways, so a foodless melee run with both open to it steps off the safespot
# and back forever.
def hold_due(on_safespot, has_food):
    """Whether the walk back to the fight tile may run."""
    return has_food or not on_safespot


# Why: nothing in the walker returns a path cost here, and the spots sit within a few tiles of each other, where
# Chebyshev and a walked path agree.
def nearest_spot(from_, spots):
    """The index of the safespot fewest tiles away, ties going to the earlier one."""
    best = 0
    best_dist = -1
    for i, spot in enumerate(spots):
        dist = max(abs(spot.x - from_.x), abs(spot.z - from_.z))
        if best_dist < 0 or dist < best_dist:
            best_dist = dist
            best = i
    return best


# Why: the client reports an npc at the tile under the centre of its footprint, and the engine measures sight to
# the south-west corner.
def body_origin(tile, size):
    """The south-west tile of a body the client reports at its centre."""
    back = size >> 1
    return Record({'x': tile.x - back, 'z': tile.z - back})


class Sighting:
    """Where a body was last seen (x, z), since when it's held that tile, and when it was seen (at)."""

    def __init__(self, x, z, since, at):
        self.x = x
        self.z = z
        self.since = since
        self.at = at

    def __repr__(self):
        return f'Sighting({self.x}, {self.z}, {self.since}, {self.at})'


# Why: a wandering body steps a tile a tick, and a click sent at one on the move lands after it has left the range,
# so the server walks the bot after it.
def note_sighting(prev, tile, now):
    """Where a body was last seen, keeping since while it holds its tile."""
    if prev is not None and prev.x == tile.x and prev.z == tile.z:
        return Sighting(prev.x, prev.z, prev.since, now)
    return Sighting(tile.x, tile.z, now, now)


def settled(s, now, ms):
    """Whether the body has held its tile for ms."""
    return s is not None and now - s.since >= ms


# Why: a retry that recomputes the nearest spot from the tile it never left picks the spot that failed, so a
# rotation only sticks by being carried into the next attempt.
def retreat_aim(rotated, from_, spots):
    """(index, next): which safespot a retreat walks at, and which it tries if that one can't be reached.
    rotated is the index a failed attempt rotated to, or None for a fresh retreat."""
    index = rotated if rotated is not None else nearest_spot(from_, spots)
    return (index, (index + 1) % len(spots) if len(spots) > 0 else index)


# Why: a metal dragon walks only until the player is inside its range 10 and then stands and breathes, so a melee
# bot on a tile never gets a body beside it; it has to go to the dragon.
def chase_mode(style, fire_at_range):
    """Whether melee has to walk to its target rather than hold a tile and wait for one."""
    return style == 'melee' and bool(fire_at_range)


# Why: check_protect_prayer zeroes an npc's melee under it, and adjacent a metal dragon headbutts three swings in
# four for up to 22, so the chase prays and the shield with a dose takes the fourth.
def prayer_for(style, fire_at_range):
    """The overhead a style keeps up on the site, or None."""
    return PROTECT_FROM_MELEE if chase_mode(style, fire_at_range) else None


PRAYER_SIP_FLOOR = 8
PRAYER_SIP_FRACTION = 0.15


# Why: the overhead drops the moment points hit 0 and the next headbutt lands full, so the sip goes in with a margin
# a swing can't cross.
def prayer_sip_due(points, max_points):
    """Whether the prayer pool is low enough to sip: under the floor, or under the fraction of the level."""
    return max_points > 0 and points <= max(PRAYER_SIP_FLOOR, math.floor(max_points * PRAYER_SIP_FRACTION))


LOOT_REACH = 10
LOOT_REACH_OPEN = 14


# Why: a metal dragon killed at gap 9 drops at its own corner, up to thirteen tiles off the camp, and ten left both
# kills of a live run unlooted; under a dose the walk is fire-proof and the dragons don't chase.
def loot_reach(fire_at_range):
    """How far from the bot a drop is worth walking to."""
    return LOOT_REACH_OPEN if fire_at_range else LOOT_REACH


# Why: clicking Attack beyond weapon range makes the server walk you into range, which steps off the safespot.
_ATTACK_RANGE = {'melee': 1, 'range': 7, 'mage': 10}


def attack_range_for(style):
    return _ATTACK_RANGE[style]


# Why: a body on the last tile of the range is one wander step from out of it by the time the click lands, and the
# third demon run was walked off the tile that way at gap 7.
def engage_range_for(style):
    """How far a body may stand for the click to be sent."""
    return _ATTACK_RANGE['melee'] if style == 'melee' else _ATTACK_RANGE[style] - 1


# Why: the engine measures range between the closest tiles of the two footprints, and an npc's distance() measures
# to the centre of one, so a size-4 dragon read 2 at its north and east faces and 3 at its south and west, and a
# size-3 demon read 1 past its near face.
def gap_to(from_, tile, size):
    """The gap the server measures from from_ to a body the client reports at tile."""
    o = body_origin(tile, size)
    dx = max(o.x - from_.x, from_.x - (o.x + size - 1), 0)
    dz = max(o.z - from_.z, from_.z - (o.z + size - 1), 0)
    return max(dx, dz)


# Why: dragonfire is 5 through the shield and 30 without, rising to 50 when the attack roll beats the defence roll.
# Why: mage and range fight from a tile no footprint touches, and the op trigger is the only thing that breathes,
# so the shield would only cost the slot the weapon needs.
# Why: a metal dragon breathes at anything inside ten tiles by script, so on that site the shield goes on whatever
# the style.
def shield_gate(style, fire_at_range, has_shield):
    """Why the run may not start without the shield, or None when it may."""
    if has_shield or (style != 'melee' and not fire_at_range):
        return None
    if fire_at_range:
        return ('the metal dragons breathe fire at range, so every style here wears the Dragonfire shield, and there is none in the '
                + 'bank or worn. Duke Horacio in Lumbridge Castle hands one out free.')
    return ('melee needs the Dragonfire shield and there is none in the bank or worn. Duke Horacio in Lumbridge Castle hands one '
            + 'out free, or switch to mage or range, which fight from a fire-proof safespot.')


# Why: every bow in the era takes both hands, so a range run on a site that wears the shield has nowhere to put it.
def style_gate(style, fire_at_range):
    """Why the style can't be used on the site, or None when it can."""
    if style != 'range' or not fire_at_range:
        return None
    return ('range cannot fight the metal dragons: every style here wears the Dragonfire shield against the far breath, and a bow '
            + 'needs both hands. Switch to mage or melee.')


# The far breath through the shield, printed whether or not a dose is up; matched without regard to case.
SHIELD_ABSORBS = 'your shield absorbs most of the dragon fire'
# Printed after the shield line only while an Antifire dose is up.
POTION_PROTECTS = 'your potion protects you from the heat'
# How long a dose lasts: `%dragonresist = map_clock + 600`.
ANTIFIRE_TICKS = 600
# Ticks before the lapse that the next dose goes down, so no breath lands in the gap.
ANTIFIRE_MARGIN_TICKS = 20


# Why: `%dragonresist` never reaches the client, so the clock is kept here from the sip, and a breath the shield took
# with no potion line after it says the clock is wrong.
# Why: an empty pack isn't "not due": the caller warns on it, since a due dose with nothing to drink is what the
# operator has to hear about.
def antifire_due(in_lair, tick, until):
    """Whether an Antifire dose is due. until is the tick the last dose lapses, 0 when none has been drunk."""
    return in_lair and tick >= until - ANTIFIRE_MARGIN_TICKS


def antifire_lapsed(saw_shield, saw_potion):
    """Whether a breath's chat lines say the dose has lapsed."""
    return saw_shield and not saw_potion


# Why: the approach stops are one obstacle apart, and a walk that always started at the first would recross every
# obstacle whenever the bot drifted past the last one.
def next_approach_index(stops, here):
    """The index of the approach stop to start from: the nearest one, ties to the earlier."""
    return nearest_spot(here, stops)


def is_clue_obj(id):
    """Every hard trail is a distinct obj all displaying "Clue scroll", so the id is the only match."""
    return id in _clues.CLUE_DB or id in _clues.CASKET_IDS


# Why: clues and burial bones ignore the loot list, so unticking a box can't silently stop clue solving or leave the
# bones the run was told to bury.
def wants_drop(item, f):
    """Whether a ground item (id and name) is worth a slot. f is the filter: loot, the lower-case names to take,
    and bank_common, solve_clues, bury_bones and bone_name."""
    if f.solve_clues and is_clue_obj(item.id):
        return True
    name = item.name if item.name is not None else ''
    if len(name) == 0:
        return False
    lower = name.lower()
    if f.bury_bones and lower == f.bone_name.lower():
        return True
    return lower in f.loot or (f.bank_common and matches_common_bank_loot(name, item.id))


def key_status(held, banked):
    """Where the next dusty key comes from: 'held', 'bank' or 'fetch'."""
    if held > 0:
        return 'held'
    return 'bank' if banked > 0 else 'fetch'


# Why: the settings store fills every key with the schema's default, so an untouched tile setting reads back as the
# schema's tile and would beat the tile the chosen site carries.
def site_tile_of(schema, bag, key, site):
    """The site's own tile, unless the tile setting has been moved off its schema default."""
    definition = schema.get(key) if key is not None else None
    default = definition.default if definition is not None else None
    if key is None or not isinstance(default, Tile):
        return site
    chosen = bag.tile(key, site)
    return site if chosen.equals(default) else chosen


# Why: every bank stop deposits what the keep list doesn't name, the key stop included, and that one runs before
# the first full trip; a dose left off the list is banked and the walk in goes unprotected.
def keep_doses(potion_doses, antipoison_doses, carries_antipoison):
    """The dose forms a deposit keeps: the boost flasks, plus the antipoison on a site that carries one."""
    return list(potion_doses) + list(antipoison_doses) if carries_antipoison else list(potion_doses)
