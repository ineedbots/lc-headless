"""Gathering camps for fishing, mining and woodcutting: a home spot, a bank stand and the booth to use.
Ported from rs2b0t's data/gatheringLocations.ts, fishingLocations.ts, miningLocations.ts and
woodcuttingLocations.ts (MIT, see third_party/rs2b0t).

A location is a Record: name, spot, bank_stand, booth_name, booth_op, verified, and where set, camp_radius,
chase_radius, resources, obstacles, sweep, avoid_spots, bait_vendor, range_stand, range_name, notes and, for a
mine, recommended_combat. A missing field reads as None.
"""

from rs2004.catalogs import _data
from rs2004.catalogs.record import Record, records

DEFAULT_BOOTH_NAME = 'Bank booth'
DEFAULT_BOOTH_OP = 'Use-quickly'
DEFAULT_CAMP_RADIUS = 64
DEFAULT_CHASE_RADIUS = 40
MAP_SQUARE = 64

USE_CLOSEST = 'Use Closest'
USE_START_POSITION = 'Use Start Position'
USE_CUSTOM_POSITION = 'Use Custom Position'
AUTO_LEGACY = 'Auto'
NONE_LEGACY = 'None'


def resolve_camp_radius(camp_radius, fallback=64):
    raw = camp_radius if camp_radius is not None else fallback
    return max(2, int(raw))


def resolve_chase_radius(chase_radius, fallback=40):
    raw = chase_radius if chase_radius is not None else fallback
    return max(2, int(raw))


def same_map_square(a, b):
    """Whether two tiles are on the same level of the same 64x64 map square."""
    if a.level != b.level:
        return False
    return a.x // MAP_SQUARE == b.x // MAP_SQUARE and a.z // MAP_SQUARE == b.z // MAP_SQUARE


def bank_distance(start, tile):
    """Straight-line distance, whatever the level, as rs2b0t ranks banks and camps."""
    dx = tile.x - start.x
    dz = tile.z - start.z
    return (dx * dx + dz * dz) ** 0.5


def location_options(table):
    """A location setting's options: the special choices, then each camp's name."""
    return [AUTO_LEGACY, USE_CLOSEST, USE_START_POSITION, USE_CUSTOM_POSITION, NONE_LEGACY] + [loc.name for loc in table]


def booth_fields(loc):
    """(booth_name, booth_op), the defaults when loc is None or doesn't say."""
    if loc is None:
        return (DEFAULT_BOOTH_NAME, DEFAULT_BOOTH_OP)
    return (loc.booth_name or DEFAULT_BOOTH_NAME, loc.booth_op or DEFAULT_BOOTH_OP)


def resolve_gathering_location(setting, start_tile, table):
    """The camp a setting names: 'Use Closest' is the nearest in a straight line, 'Auto' the nearest in the
    start tile's map square, the start and custom positions are None (freeform), and a name matches without
    regard to case."""
    wanted = setting.strip().lower()
    if wanted == USE_CUSTOM_POSITION.lower() or wanted == USE_START_POSITION.lower():
        return None
    if wanted == USE_CLOSEST.lower() or wanted == AUTO_LEGACY.lower():
        pool = table
        if wanted == AUTO_LEGACY.lower():
            pool = [loc for loc in table if same_map_square(start_tile, loc.spot)]
        best = None
        best_distance = 0
        for loc in pool:
            distance = bank_distance(start_tile, loc.spot)
            if best is None or distance < best_distance:
                best = loc
                best_distance = distance
        return best
    for loc in table:
        if loc.name.lower() == wanted:
            return loc
    return None


def _by_name(table):
    return sorted(table, key=lambda loc: loc.name.lower())


FISHING_LOCATIONS = records(_data.FISHING_LOCATIONS)
FISHING_LOCATION_OPTIONS = location_options(FISHING_LOCATIONS)
SHILO_WATER_VENDOR = Record(_data.SHILO_WATER_VENDOR)

WOODCUTTING_LOCATIONS = records(_data.WOODCUTTING_LOCATIONS)
WOODCUTTING_LOCATION_OPTIONS = location_options(WOODCUTTING_LOCATIONS)
# The ent random event's NPCs, which share trees' names and Chop down, so they're told apart by id.
ENT_NPC_IDS = _data.ENT_NPC_IDS
ENT_LIFE_TICKS = _data.ENT_LIFE_TICKS

MINING_LOCATIONS = records(_data.MINING_LOCATIONS)
MINING_LOCATION_OPTIONS = location_options(MINING_LOCATIONS)


def mining_location_label(loc):
    """'Dwarven Mine (65 Combat recommended)' when a combat level is recommended there."""
    if loc.recommended_combat is not None:
        return f'{loc.name} ({loc.recommended_combat} Combat recommended)'
    return loc.name


MINING_LOCATION_OPTION_LABELS = {}
for _loc in MINING_LOCATIONS:
    if _loc.recommended_combat is not None:
        MINING_LOCATION_OPTION_LABELS[_loc.name] = mining_location_label(_loc)


def resolve_fishing_location(setting, start_tile):
    return resolve_gathering_location(setting, start_tile, FISHING_LOCATIONS)


def resolve_mining_location(setting, start_tile):
    return resolve_gathering_location(setting, start_tile, MINING_LOCATIONS)


def resolve_woodcutting_location(setting, start_tile):
    return resolve_gathering_location(setting, start_tile, WOODCUTTING_LOCATIONS)


def is_ent_npc_id(id):
    return id in ENT_NPC_IDS


def ent_npc_on_tile(npcs, tile):
    """Whether an ent stands on the tile, of NPCs with id and tile()."""
    for npc in npcs:
        at = npc.tile()
        if is_ent_npc_id(npc.id) and at.x == tile.x and at.z == tile.z and at.level == tile.level:
            return True
    return False


# Picking a rock or tree, from rs2b0t's scripts/GatheringBot/TargetPick.ts.

# Rocks and trees within this many tiles are preferred to farther ones; iron grows back in about six ticks.
LOCAL_MINE_PREFER_RADIUS = 12


def pick_nearest_prefer_local(candidates, distance, prefer_radius=12):
    """The nearest candidate, of those within prefer_radius when there are any, so a nearer cluster wins over
    one through a tunnel."""
    if not candidates:
        return None
    pool = candidates
    if prefer_radius > 0:
        local = [c for c in candidates if distance(c) <= prefer_radius]
        if local:
            pool = local
    best = None
    best_distance = 0
    for candidate in pool:
        d = distance(candidate)
        if best is None or d < best_distance:
            best = candidate
            best_distance = d
    return best


def pick_bucket_nearest(candidates, bucket, distance, prefer_radius=12):
    """The nearest of the candidates in the best bucket, such as the best ore in camp."""
    if not candidates:
        return None
    best_bucket = max([bucket(c) for c in candidates])
    return pick_nearest_prefer_local([c for c in candidates if bucket(c) == best_bucket], distance, prefer_radius)


def should_cooldown_gather_tile(got_product, other_targets):
    """Whether to leave a rock or tree alone for a while after a click that gave nothing."""
    return not got_product and other_targets
