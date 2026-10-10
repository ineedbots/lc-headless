"""rs2b0t's other world tables: cow fields, runecrafting routes, pickpocket targets, herbs, the shop database,
walk destinations, cooking surfaces and fire spots, with their helpers. Ported from rs2b0t's
data/cowKillerLocations.ts, runeCraftLocations.ts, pickpocketTargets.ts, herbs.ts, shopdb.ts,
cookingRanges.ts, cookLocations.ts, api/cooking/CookLocations.ts, api/map/WalkDestinations.ts and
api/firemaking/Firemaking.ts (MIT, see third_party/rs2b0t).
"""

from rs2004.catalogs import _data
from rs2004.catalogs.record import Record, records
from rs2004.geometry import Tile

# Cow fields

COW_LOCATIONS = records(_data.COW_LOCATIONS)
COW_LOCATION_OPTIONS = ['Auto'] + [loc.name for loc in COW_LOCATIONS] + ['Start tile']
DRAYNOR_BANK = _data.DRAYNOR_BANK
FALADOR_EAST_BANK = _data.FALADOR_EAST_BANK
ARDOUGNE_WEST_BANK = _data.ARDOUGNE_WEST_BANK
AL_KHARID_BANK = _data.AL_KHARID_BANK
TOLL_COIN_TARGET = _data.TOLL_COIN_TARGET


def is_cow_field_loot_tile(anchor, leash_radius, tile):
    """Whether loot on the tile is the field's: same level, within the leash of the anchor."""
    return tile.level == anchor.level and max(abs(tile.x - anchor.x), abs(tile.z - anchor.z)) <= leash_radius


def nearest_cow_location(tile):
    best = COW_LOCATIONS[0]
    for loc in COW_LOCATIONS:
        if loc.anchor.distance_to(tile) < best.anchor.distance_to(tile):
            best = loc
    return best


def resolve_cow_location(setting, start):
    """'Auto' is the nearest field, 'Start tile' is None (fight where you stand), and a name matches without
    regard to case."""
    wanted = setting.strip().lower()
    if wanted == 'start tile':
        return None
    if wanted != 'auto':
        for loc in COW_LOCATIONS:
            if loc.name.lower() == wanted:
                return loc
        return None
    return nearest_cow_location(start)


def needs_toll_coins(location, enabled):
    return enabled and location is not None and location.uses_al_kharid_toll is True


def cow_bank_destination(location, toll_enabled):
    """(name, tile) of the bank to use: Al Kharid's when the field is past the toll, else the field's own."""
    if needs_toll_coins(location, toll_enabled):
        return ('Al Kharid', AL_KHARID_BANK)
    if location is None or location.bank_destination is None:
        return None
    return (location.bank_destination.name, location.bank_destination.tile)


def should_bootstrap_toll_coins(location, start, coins, enabled):
    """Whether to fetch toll coins from Al Kharid's bank first: short of them, and starting near it."""
    return needs_toll_coins(location, enabled) and coins < TOLL_COIN_TARGET and start.level == AL_KHARID_BANK.level \
        and AL_KHARID_BANK.distance_to(start) <= 80


# Runecrafting

RUNES = {}
for _name, _route in _data.RUNES.items():
    RUNES[_name] = Record(_route)
RUNE_OPTIONS = list(_data.RUNES.keys())
DEFAULT_RUNE = _data.DEFAULT_RUNE

# Thieving

PICKPOCKET_TARGETS = records(_data.PICKPOCKET_TARGETS)
PICKPOCKET_TARGET_NAMES = [t.name for t in PICKPOCKET_TARGETS]
ARDOUGNE_PICKPOCKET_TARGETS = _data.ARDOUGNE_PICKPOCKET_TARGETS

# Herbs: key, name (cleaned), id, unid_id (grimy) and level.

HERBS = records(_data.HERBS)
HERB_OPTIONS = [h.name for h in HERBS]

# Shops


def shop_db():
    """The shop database by inventory name: title, keepers, sell and buy rates, and items (obj, name,
    baseline, restock_ticks, cost, stackable, members). It's large, so it's read on first use."""
    from rs2004.catalogs import _shops
    return _shops.SHOP_DB


def shops_selling(item):
    """[(inventory name, shop record)] of the shops that stock the item, by name without regard to case."""
    wanted = item.lower()
    out = []
    for key, shop in shop_db().items():
        for entry in shop['items']:
            if entry['name'] is not None and entry['name'].lower() == wanted:
                out.append((key, shop))
                break
    return out


# Walk destinations

WALK_DESTINATIONS = records(_data.WALK_DESTINATIONS)
WALK_OPTIONS = [d.name for d in WALK_DESTINATIONS]


def resolve_destination(name):
    wanted = name.strip().lower()
    for destination in WALK_DESTINATIONS:
        if destination.name.lower() == wanted:
            return destination
    return None


# Cooking

COOKING_SURFACE_LOCS = records(_data.COOKING_SURFACE_LOCS)
COOKING_RANGE_LOCS = _data.COOKING_RANGE_LOCS
CATHERBY_RANGE = Record(_data.CATHERBY_RANGE)
FISH_CAMP_COOK_PLANS = {}
for _camp, _plan in _data.FISH_CAMP_COOK_PLANS.items():
    FISH_CAMP_COOK_PLANS[_camp] = Record(_plan)
COOK_LOCATIONS = records(_data.COOK_LOCATIONS)
CUSTOM_LOCATION = 'Custom'
COOK_LOCATION_OPTIONS = ['Auto'] + [loc.name for loc in COOK_LOCATIONS] + [CUSTOM_LOCATION]
MAX_SURFACE_CHEB = 20


def _chebyshev(a, b):
    if a.level != b.level:
        return 1000000
    return max(abs(a.x - b.x), abs(a.z - b.z))


def range_stand_from_loc(loc):
    """The tile south of a range's corner, a safe stand for a 1x2 range."""
    return Tile(loc.x, loc.z - 1, loc.level)


def nearest_cooking_range(origin, max_cheb=64):
    """The nearest range on origin's level within max_cheb tiles, as a Record of stand, loc, loc_name, kind,
    label and notes; None when there's none."""
    best = None
    best_distance = 0
    for loc in COOKING_RANGE_LOCS:
        distance = _chebyshev(origin, loc)
        if distance > max_cheb:
            continue
        if best is None or distance < best_distance:
            best = loc
            best_distance = distance
    if best is None:
        return None
    return Record({'stand': range_stand_from_loc(best), 'loc': best, 'loc_name': 'Range', 'kind': 'range',
                   'label': f'Range at {best.x},{best.z}', 'notes': f'{best_distance} tiles from the origin'})


def cook_surface_for_fish_camp(camp_name, role='pier'):
    """A fishing camp's curated surface: 'pier' to cook beside the spot, 'bank' to cook beside the bank."""
    plan = FISH_CAMP_COOK_PLANS.get(camp_name)
    if plan is None:
        return None
    if role == 'bank':
        return plan.bank if plan.bank is not None else plan.pier
    return plan.pier if plan.pier is not None else plan.bank


def resolve_fish_camp_cook_surface(camp_name, spot, max_cheb=64, role='pier'):
    """The camp's curated surface, or else the nearest range to spot."""
    if camp_name:
        curated = cook_surface_for_fish_camp(camp_name, role)
        if curated is not None:
            return curated
    return nearest_cooking_range(spot, max_cheb)


def nearest_cook_surface(origin, max_cheb=20):
    """The nearest cooking surface within max_cheb tiles, an oven before a fire at any distance."""
    best = None
    best_distance = 0
    for surface in COOKING_SURFACE_LOCS:
        if surface.level != origin.level:
            continue
        distance = _chebyshev(origin, surface)
        if distance > max_cheb:
            continue
        if best is None:
            better = True
        elif (surface.kind == 'oven') != (best.kind == 'oven'):
            better = surface.kind == 'oven'
        else:
            better = distance < best_distance
        if better:
            best = surface
            best_distance = distance
    return best


def cook_location(name):
    wanted = name.strip().lower()
    for loc in COOK_LOCATIONS:
        if loc.name.lower() == wanted:
            return loc
    return None


def resolve_cook_location(setting, start, unlocked=None):
    """'Custom' and unknown names are None (use the script's own tiles); 'Auto' is the nearest bank whose
    location unlocked(loc) allows, all of them by default."""
    wanted = setting.strip().lower()
    if wanted == '' or wanted == CUSTOM_LOCATION.lower():
        return None
    allowed = unlocked if unlocked is not None else (lambda loc: True)
    if wanted != 'auto':
        named = cook_location(setting)
        return named if named is not None and allowed(named) else None
    best = None
    best_distance = 0
    for loc in COOK_LOCATIONS:
        if not allowed(loc):
            continue
        bank_tile = loc.bank.approach if loc.bank.approach is not None else loc.bank.tile
        dx = bank_tile.x - start.x
        dz = bank_tile.z - start.z
        distance = (dx * dx + dz * dz) ** 0.5
        if best is None or distance < best_distance:
            best = loc
            best_distance = distance
    return best


# Firemaking: a fire spot is a plot, a box x0..x1, z0..z1 beside a bank.

FIRE_SPOTS = {}
for _spot, _plot in _data.FIRE_SPOTS.items():
    FIRE_SPOTS[_spot] = Record(_plot)
FIRE_SPOT_OPTIONS = list(_data.FIRE_SPOTS.keys())
LOG_LEVELS = _data.LOG_LEVELS
BURN_MODE_OPTIONS = ['Off', 'Chop then burn']
CANT_LIGHT = "can't light a fire here"
FIRE_START_TICKS = 14
FIRE_LIGHT_TICKS = 150


def parse_burn_mode(label):
    return 'chop-then-burn' if label.strip().lower() == 'chop then burn' else 'off'


def logs_for_tree(tree_name):
    """The logs a tree gives."""
    tree = tree_name.strip().lower()
    if tree in ['tree', 'dead tree', 'evergreen']:
        return 'Logs'
    for word, logs in [('oak', 'Oak logs'), ('willow', 'Willow logs'), ('maple', 'Maple logs'), ('yew', 'Yew logs'), ('magic', 'Magic logs')]:
        if word in tree:
            return logs
    return 'Logs'


def firemaking_level_for_logs(log_name):
    return LOG_LEVELS.get(log_name)


def resolve_fire_spot(name):
    """(name, plot) for a fire spot named without regard to case, or None."""
    wanted = name.strip().lower()
    for key in FIRE_SPOT_OPTIONS:
        if key.lower() == wanted:
            return (key, FIRE_SPOTS[key])
    return None


def nearest_fire_spot(start):
    best = None
    best_distance = 0
    for key in FIRE_SPOT_OPTIONS:
        plot = FIRE_SPOTS[key]
        distance = max(abs(start.x - plot.bank.x), abs(start.z - plot.bank.z))
        if best is None or distance < best_distance:
            best = (key, plot)
            best_distance = distance
    return best


def local_fire_plot(origin, half=8):
    """A plot centred on origin, for burning where you chopped."""
    h = max(2, int(half))
    return Record({'bank': Tile(origin.x, origin.z, origin.level), 'x0': origin.x - h, 'x1': origin.x + h, 'z0': origin.z - h, 'z1': origin.z + h})


def expand_local_fire_plot(plot, grow_by=4, max_half=24):
    """The plot grown outward, or None past max_half."""
    cx = (plot.x0 + plot.x1) // 2
    cz = (plot.z0 + plot.z1) // 2
    nxt = max((plot.x1 - plot.x0) // 2, (plot.z1 - plot.z0) // 2) + max(1, grow_by)
    if nxt > max_half:
        return None
    return local_fire_plot(Tile(cx, cz, plot.bank.level), nxt)


def in_fire_plot(tile, plot):
    return tile.level == plot.bank.level and plot.x0 <= tile.x and tile.x <= plot.x1 and plot.z0 <= tile.z and tile.z <= plot.z1


def should_burn_full_load(mode, inventory_full, log_count, has_tinderbox):
    return mode == 'chop-then-burn' and inventory_full and log_count > 0 and has_tinderbox
