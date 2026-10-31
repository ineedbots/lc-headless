"""Ported from rs2b0t's src/bot/api/ai/quests/defs/deathplateau/nav.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.deathplateau.areas import TILE
from rs2004.quests.exec.primitives import talk_through
from rs2004.traversal import traversal

__all__ = ['in_inn_band', 'descend_to_ground', 'walk_to', 'talk_at', 'THROWER_APPROACH', 'on_secret_path', 'walk_secret_path']

# Why: Burthorpe floor plan, Eohric is castle L1 via "Stairs" at about (2897,3566), Harold is Toad & Chicken L1 via "Staircase" at about (2914,3539), and Tostig, Denulth and Dunstan are on the ground.
# Why: castle L1 and inn L1 are unconnected, so any L1-to-L1 hop between them has to Climb-down, walk the ground, then Climb-up the other building.
# Why: walkResilient can plan that multi-hop only while the stair loc names match the scene.
def in_inn_band(tile):
    """Inn is south of z=3552; castle courtyard and stairs are north."""
    return tile.z < 3552


def stairs_bottom_for(dest):
    return (TILE.INN_STAIRS_BOTTOM if in_inn_band(dest) else TILE.CASTLE_STAIRS_BOTTOM)


def stairs_top_for(dest):
    return (TILE.INN_STAIRS_TOP if in_inn_band(dest) else TILE.CASTLE_STAIRS_TOP)


def climb_one_flight(op, stand, target_level, log):
    here = game.tile()
    if not here:
        return False
    if here.level == target_level:
        return True
    # Approach stand on the current level.
    if stand.distance_to(here) > 2 or here.level != stand.level:
        approach = Tile(stand.x, stand.z, here.level)
        _w1 = yield from traversal.walk_resilient(approach, radius=2, attempts=3, timeout_ms=90000, log=log)
        if not (_w1):
            log(f'could not approach stairs stand ({stand.x},{stand.z},L{here.level})')
    # Castle = "Stairs"; inn = "Staircase". Never grab wall Ladders.
    _v2 = locs.query().name('Stairs', 'Staircase').action(op).within(8).nearest()
    stair = (_v2 if _v2 is not None else locs.query().action(op).where(lambda l: (l.name or '').lower() in ['stair', 'stairs']).within(8).nearest())
    if not stair:
        log(f'no Stairs/Staircase to {op} near ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)},L{(game.tile().level if game.tile() is not None else None)})')
        return False
    log(f"{op} {(stair.name if stair.name is not None else 'stairs')} at {stair.tile()}")
    if not (stair.interact(op)):
        return False

    def _fn4():
        t = game.tile()
        return t is not None and t.level == target_level
    _result3 = yield from execution.delay_until(_fn4, 8000)
    return _result3


def descend_to_ground(log):
    """Drop to ground in the building we currently occupy."""
    for attempt in range(3):
        here = game.tile()
        if not here or here.level == 0:
            return True
        stand = stairs_top_for(here)
        _w5 = yield from climb_one_flight('Climb-down', stand, 0, log)
        if _w5:
            return True
    _v6 = (game.tile().level if game.tile() is not None else None)
    return ((_v6 if _v6 is not None else -1)) == 0


def ascend_to_dest_floor(dest, log):
    """Climb from ground into the building that contains `dest` (level >= 1)."""
    here = game.tile()
    if not here:
        return False
    if here.level == dest.level:
        return True
    if here.level > 0:
        # Wrong building upstairs, go down first.
        _w7 = yield from descend_to_ground(log)
        if not (_w7):
            return False
    bottom = stairs_bottom_for(dest)
    _w8 = yield from traversal.walk_resilient(bottom, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w8):
        log(f'could not reach stairs bottom ({bottom.x},{bottom.z})')
        return False
    _result9 = yield from climb_one_flight('Climb-up', bottom, dest.level, log)
    return _result9


def walk_to(dest, radius, log):
    here0 = game.tile()
    if here0 and here0.level == dest.level and dest.distance_to(here0) <= radius:
        return True
    # Elevated long hops or castle L1 to inn L1: force ground transfer.
    here1 = game.tile()
    if here1 and here1.level > 0:
        cross_buildings = dest.level > 0 and in_inn_band(here1) != in_inn_band(dest)
        long_or_ground = dest.level == 0 or dest.distance_to(here1) > 10 or cross_buildings
        _c10 = long_or_ground
        if _c10:
            _w11 = yield from descend_to_ground(log)
            _c10 = not (_w11)
        if _c10:
            return False
    # Need upper floor of dest building.
    here2 = game.tile()
    if here2 and dest.level > 0 and here2.level != dest.level:
        _w12 = yield from ascend_to_dest_floor(dest, log)
        if not (_w12):
            return False
    now = game.tile()
    if now and now.level == dest.level and dest.distance_to(now) <= radius:
        return True
    # Same-level finish (or walkResilient multi-hop if still elevated).
    _result13 = yield from traversal.walk_resilient(dest, radius=radius, attempts=4, timeout_ms=180000, log=log)
    return _result13


def talk_at(stop, log):
    _w14 = yield from walk_to(stop.anchor, 2, log)
    if not (_w14):
        return False
    here = game.tile()
    if here and here.level != stop.anchor.level:
        _w15 = yield from ascend_to_dest_floor(stop.anchor, log)
        if not (_w15):
            return False
        _w16 = yield from walk_to(stop.anchor, 2, log)
        if not (_w16):
            return False
    _result17 = yield from talk_through(stop.npc, stop.prefer, log)
    return _result17


# Why: the walker indexes its avoid rects, so they're dicts, not Records.
THROWER_APPROACH = [{'min_x': 2848, 'max_x': 2880, 'min_z': 3590, 'max_z': 3608, 'level': 0}]


def on_secret_path(tile):
    return tile is not None and tile.level == 0 and tile.x >= 2810 and tile.x <= 2871 and tile.z >= 3563 and (tile.x < 2848 or tile.z >= 3609)


def walk_secret_path(dest, log):
    _w18 = yield from traversal.walk_to(dest, radius=0, timeout_ms=180000, use_teleport_catalog=False, avoid_zones=THROWER_APPROACH, log=log)
    if not (_w18):
        return False
    here = game.tile()
    return here is not None and here.level == dest.level and dest.distance_to(here) == 0
