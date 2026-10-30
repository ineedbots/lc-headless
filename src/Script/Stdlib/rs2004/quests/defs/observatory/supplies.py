"""Ported from rs2b0t's src/bot/api/ai/quests/defs/observatory/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.observatory.areas import OBS_ID, OBS_ITEM, OBS_LOC_NAME, OBS_TILE, PLANKS_NEEDED
from rs2004.traversal import traversal

__all__ = ['KHAZARD_SHOP', 'held_id', 'banked_id', 'from_bank', 'planks', 'ore', 'ore_short', 'smelt_bronze', 'sand', 'soda_ash', 'smelt_glass']

SHOP_GP = 200
KHAZARD_SHOP = Record({'npc': 'Shop keeper', 'anchor': Tile(2641, 3171, 0)})


def held_id(snap, id):
    _v1 = snap.inv_ids.get(id)
    return (_v1 if _v1 is not None else 0)


def banked_id(snap, id):
    _v2 = snap.bank_ids.get(id)
    return (_v2 if _v2 is not None else 0)


def withdraw(items):
    return (Record({'kind': 'withdraw', 'items': items}))


scan_bank = Record({'kind': 'scan_bank'})


# Why: `snap.bankIds` is empty before the first bank scan, so do not start mining from unknown state.
def from_bank(snap, id, name, qty):
    """Withdraw from the bank when it can help, before any trip to fetch one."""
    if not snap.bank_known:
        return scan_bank
    banked = banked_id(snap, id)
    if banked <= 0:
        return None
    return withdraw([{'name': name, 'qty': min(qty, banked), 'id': id}])


def nearest_plank_spawn():
    """4 spawns lie in a 5-tile square, so the nearest bare one is still the right walk."""
    here = game.tile()
    if not here:
        return OBS_TILE.PLANK_SPAWNS[0]
    return (sorted(list(OBS_TILE.PLANK_SPAWNS), key=lambda a: a.distance_to(here)) or [None])[0]


def planks(snap):
    """The tripod's 3 planks: the Barbarian Outpost spawns, as no shop sells one."""
    need = PLANKS_NEEDED - held_id(snap, OBS_ID.PLANK)
    _v3 = from_bank(snap, OBS_ID.PLANK, OBS_ITEM.PLANK, need)
    return (_v3 if _v3 is not None else Record({'kind': 'grab_ground', 'item': OBS_ITEM.PLANK, 'anchor': nearest_plank_spawn(), 'wait_if_missing': True}))


# Why: no shop this side of the Karamja ferry stocks a bronze bar, and the Fight Arena seam carries copper and tin in one radius.
def ore(snap):
    """The pickaxe, then one copper and one tin, everything the bar needs before the furnace."""
    if not any([('pickaxe' in name) for name in list(list(snap.inv.keys()))]):
        _v4 = from_bank(snap, OBS_ID.BRONZE_PICKAXE, OBS_ITEM.BRONZE_PICKAXE, 1)
        return (_v4 if _v4 is not None else Record({'kind': 'buy', 'item': OBS_ITEM.BRONZE_PICKAXE, 'qty': 1, 'shop': KHAZARD_SHOP, 'est_gp': SHOP_GP}))
    return (Record({
        'kind': 'mine_rock',
        'rock': OBS_ITEM.TIN_ORE,
        'item': OBS_ITEM.TIN_ORE,
        'qty': 1,
        'anchor': OBS_TILE.MINE,
    }) if held_id(snap, OBS_ID.COPPER_ORE) > 0 else Record({
        'kind': 'mine_rock',
        'rock': OBS_ITEM.COPPER_ORE,
        'item': OBS_ITEM.COPPER_ORE,
        'qty': 1,
        'anchor': OBS_TILE.MINE,
    }))


def ore_short(snap):
    """True while the ore for the bar is still in the ground."""
    return held_id(snap, OBS_ID.COPPER_ORE) == 0 or held_id(snap, OBS_ID.TIN_ORE) == 0


# Why: both the Range and the Furnace carry `forceapproach=east`, which names the only side that works and rotates with the placement.
# Why: from anywhere else the use-on is silently dropped, so a radius-2 walk is a coin flip.
def use_on_loc_from(stand, item_id, loc_name, done, log):
    """Use a held item on a loc from an exact tile."""
    if done():
        return True
    _w5 = yield from traversal.walk_resilient(stand, radius=0, attempts=4, timeout_ms=300000, log=log)
    if not (_w5):
        log(f'observatory: could not stand on ({stand.x},{stand.z}) to use the {loc_name}')
        return False
    yield from execution.delay_ticks(2)
    loc = locs.query().name(loc_name).within(6).nearest()
    item = ([entry for entry in inventory.items() if entry.id == item_id] or [None])[0]
    if not loc or not item:
        log(f'observatory: no {loc_name} in reach, or nothing to use on it')
        return False
    if not (item.use_on(loc)):
        return False
    _result6 = yield from execution.delay_until(done, 12000)
    return _result6


# Why: an ore used on a furnace runs `smelt_ore_single`, which reads the bar off the ore's `smeltsto` param (1 bar, no quantity panel), and copper and tin each name bronze.
def smelt_bronze_run(log):
    return use_on_loc_from(OBS_TILE.FURNACE, OBS_ID.COPPER_ORE, OBS_LOC_NAME.FURNACE, lambda: inventory.count_by_id(OBS_ID.BRONZE_BAR) > 0, log)


smelt_bronze = Record({'kind': 'custom', 'name': 'smelt a bronze bar', 'run': smelt_bronze_run})


def sand(snap):
    """The `bucket_sand` spawn 25 tiles from the reception, which skips both the bucket and the Yanille pit."""
    _v7 = from_bank(snap, OBS_ID.BUCKET_OF_SAND, OBS_ITEM.BUCKET_OF_SAND, 1)
    return (_v7 if _v7 is not None else Record({
        'kind': 'grab_ground',
        'item': OBS_ITEM.BUCKET_OF_SAND,
        'anchor': OBS_TILE.SAND_SPAWN,
        'wait_if_missing': True,
    }))


def cook_seaweed(log):
    return use_on_loc_from(OBS_TILE.RANGE_STAND, OBS_ID.SEAWEED, OBS_LOC_NAME.RANGE, lambda: inventory.count_by_id(OBS_ID.SODA_ASH) > 0, log)


# Why: nothing sells soda ash or seaweed, and the shore Horror from the Deep walks to is the nearest one off an islet.
# Why: it cooks down on the Ardougne range the furnace leg passes on the way home.
def soda_ash(snap):
    """Seaweed off the shore, then the range that turns it into soda ash."""
    if held_id(snap, OBS_ID.SEAWEED) > 0:
        return Record({'kind': 'custom', 'name': 'cook seaweed into soda ash', 'run': cook_seaweed})
    _v8 = from_bank(snap, OBS_ID.SEAWEED, OBS_ITEM.SEAWEED, 1)
    return (_v8 if _v8 is not None else Record({
        'kind': 'grab_ground',
        'item': OBS_ITEM.SEAWEED,
        'anchor': OBS_TILE.SEAWEED_SPAWN,
        'wait_if_missing': True,
    }))


def smelt_glass_run(log):
    return use_on_loc_from(OBS_TILE.FURNACE, OBS_ID.BUCKET_OF_SAND, OBS_LOC_NAME.FURNACE, lambda: inventory.count_by_id(OBS_ID.MOLTEN_GLASS) > 0, log)


smelt_glass = Record({'kind': 'custom', 'name': 'smelt molten glass', 'run': smelt_glass_run})
