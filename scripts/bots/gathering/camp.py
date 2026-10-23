"""How far a gatherer ranges from its camp: rs2b0t's scripts/GatheringBot/GatherCamp.ts (MIT, see
thirdparty/rs2b0t)."""

import math

from rs2004.catalogs import AUTO_LEGACY, DEFAULT_CAMP_RADIUS, USE_CLOSEST, USE_CUSTOM_POSITION, USE_START_POSITION, Record

NAMED_CAMP_LEASH_FLOOR = DEFAULT_CAMP_RADIUS
START_TILE_LEASH_FLOOR = NAMED_CAMP_LEASH_FLOOR


def is_number(value):
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)


def number_or(value, fallback):
    return value if is_number(value) else fallback


# Why: a freeform location (Use Closest, Start or Custom Position) keeps the setting; a named camp, or power
# gathering with Bank off, ranges at least NAMED_CAMP_LEASH_FLOOR, the camp's extent.
def effective_gather_leash(setting_leash, location_setting):
    raw = max(2, math.floor(number_or(setting_leash, 10)))
    return raw if is_auto_location(location_setting) else max(NAMED_CAMP_LEASH_FLOOR, raw)


def is_auto_location(location_setting):
    """Whether the location is freeform: Auto, Use Start Position or Use Custom Position, where it doesn't babysit
    mobs by fleeing."""
    n = location_setting.strip().lower()
    return n in ['auto', AUTO_LEGACY.lower(), USE_START_POSITION.lower(), USE_CUSTOM_POSITION.lower(), USE_CLOSEST.lower()]


def is_custom_location(location_setting):
    return location_setting.strip().lower() == USE_CUSTOM_POSITION.lower()


# Why: a named camp measures from the player, so hopping along a pier or river beside the bot stays good far from
# the camp's pin, the camp's extent fencing the resources; freeform fishing does too. With no player tile it's the
# anchor.
def gather_spot_range_origin(freeform_fish, has_player_tile, named_camp=False):
    """Where a fishing spot's distance is measured from: 'player' or 'anchor'."""
    if not has_player_tile:
        return 'anchor'
    return 'player' if named_camp or freeform_fish else 'anchor'


def spot_within_gather_range(dist_from_origin, max_dist):
    return is_number(dist_from_origin) and dist_from_origin <= max_dist


def resource_within_camp(dist_from_home, camp_radius):
    """Whether a resource still belongs to the named camp, by distance from its pin; freeform has no fence."""
    r = max(2, math.floor(number_or(camp_radius, NAMED_CAMP_LEASH_FLOOR)))
    return is_number(dist_from_home) and dist_from_home <= r


def gather_hunt_radius(primary_disk):
    """How far freeform hunts past its leash; named camps take any spot in the camp."""
    leash = max(2, math.floor(number_or(primary_disk, 10)))
    return max(leash + 24, 48)


def spot_avoided(spot, avoid):
    return len([t for t in avoid if t.x == spot.x and t.z == spot.z and t.level == spot.level]) > 0


def sweep_stop_for(sweep, index, here):
    """The sweep's next stop: a Record of stop and index, stepping on once the player is at the current one."""
    if len(sweep) == 0:
        return Record({'stop': None, 'index': 0})
    at = ((index % len(sweep)) + len(sweep)) % len(sweep)
    stop = sweep[at]
    if here is not None and here.level == stop.level and max(abs(here.x - stop.x), abs(here.z - stop.z)) <= 1:
        after = (at + 1) % len(sweep)
        return Record({'stop': sweep[after], 'index': after})
    return Record({'stop': stop, 'index': at})
