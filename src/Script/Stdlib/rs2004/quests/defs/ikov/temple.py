"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ikov/temple.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs
from rs2004.game import direct_navigator, game
from rs2004.items import equipment
from rs2004.quests.defs.ikov.areas import GUARDIAN_STOP, IKOV_LOC, IKOV_NAME, IKOV_OBJ, IKOV_TILE, LAVA_BRIDGE_ZONE, WINELDA_STOP, in_guardian_temple, on_winelda_ledge
from rs2004.quests.defs.ikov.dungeon import escape_pocket
from rs2004.quests.exec.primitives import is_underground, talk_strict
from rs2004.quests.exec.prompts import held_id, settle_scene
from rs2004.traversal import traversal

__all__ = ['join_the_guardians', 'leave_the_far_side']

WALK_MS = 300000


def temple_walk(dest, radius, log):
    return traversal.walk_resilient(dest, radius=radius, attempts=3, timeout_ms=WALK_MS, avoid_zones=[LAVA_BRIDGE_ZONE], log=log)


# Why: her teleport lands 5 ticks after the conversation closes, so a leg that acts at once is still on the ledge, where the shiny key is a McGrubor round trip away.
def ensure_across_the_lava(log):
    """Wait out Winelda's ferry, and ask her again if it never came."""

    def on_ledge():
        t = game.tile()
        return t is not None and on_winelda_ledge(t)

    if not on_ledge():
        return True
    _w1 = yield from execution.delay_until(lambda: not on_ledge(), 12000)
    if _w1:
        yield from settle_scene()
        return True
    log('ikov: still on the ledge — asking Winelda for the ferry again')
    _w2 = yield from temple_walk(IKOV_TILE.WINELDA, 2, log)
    if not (_w2):
        return False
    _w3 = yield from talk_strict(WINELDA_STOP.npc, WINELDA_STOP.prefer, log)
    if not (_w3):
        return False
    crossed = yield from execution.delay_until(lambda: not on_ledge(), 15000)
    if crossed:
        yield from settle_scene()
    return crossed


def take_shiny_key(log):
    if held_id(IKOV_OBJ.SHINY_KEY) > 0:
        return True
    _w4 = yield from temple_walk(IKOV_TILE.SHINY_KEY_SPAWN, 1, log)
    if not (_w4):
        return False
    key = ground_items.query().where(lambda g: g.id == IKOV_OBJ.SHINY_KEY).within(8).nearest()
    if not key:
        log(f'ikov: no shiny key at ({IKOV_TILE.SHINY_KEY_SPAWN.x},{IKOV_TILE.SHINY_KEY_SPAWN.z})')
        return False
    if not (key.interact('Take')):
        return False
    _result5 = yield from execution.delay_until(lambda: held_id(IKOV_OBJ.SHINY_KEY) > 0, 8000)
    return _result5


# Why: the wall is a "Wall" with a `Push`, so `derive-doors` never baked it and no route crosses it on its own.
def push_secret_wall(into_temple, log):
    def arrived():
        t = game.tile()
        return t is not None and in_guardian_temple(t) == into_temple

    if arrived():
        return True
    stand = (IKOV_TILE.SECRET_WALL if into_temple else IKOV_TILE.SECRET_WALL_INSIDE)
    through = (IKOV_TILE.SECRET_WALL_INSIDE if into_temple else IKOV_TILE.SECRET_WALL)
    _w6 = yield from temple_walk(stand, 0, log)
    if not (_w6):
        return False
    yield from settle_scene()
    wall = locs.query().where(lambda l: l.id == IKOV_LOC.SECRET_WALL or l.id == IKOV_LOC.SECRET_WALL_OPEN).within(4).nearest()
    if wall and wall.id == IKOV_LOC.SECRET_WALL:
        log(f"ikov: pushing the secret wall {('into' if into_temple else 'out of')} the guardians' temple")
        if not (wall.interact('Push')):
            return False
        # Why: `open_and_close_door2` teleports you through.
        _w7 = yield from execution.delay_until(arrived, 8000)
        if _w7:
            yield from settle_scene()
            return True
    yield from direct_navigator.walk_to(through, 0, 8000)
    if not arrived():
        return False
    yield from settle_scene()
    return True


def shed_lucien_colours(log):
    """Everything the guardians must not see: Lucien's pendant worn, or the staff carried."""
    if equipment.contains(IKOV_NAME.PENDANT_LUCIEN):
        log("ikov: stowing Lucien's pendant before the guardians see it")
        _w8 = yield from equipment.unequip(IKOV_NAME.PENDANT_LUCIEN)
        if not (_w8):
            return False
    if held_id(IKOV_OBJ.STAFF) > 0:
        log('ikov: holding the staff would set every guardian on us — this run does not take it')
        return False
    return True


def join_the_guardians(log):
    """Cross the wall and talk a guardian into the Armadyl pendant."""
    if held_id(IKOV_OBJ.PENDANT_ARMADYL) > 0 or equipment.contains(IKOV_NAME.PENDANT_ARMADYL):
        return True
    _w9 = yield from escape_pocket(log)
    if not (_w9):
        return False
    _w10 = yield from ensure_across_the_lava(log)
    if not (_w10):
        return False
    _w11 = yield from take_shiny_key(log)
    if not (_w11):
        return False
    _w12 = yield from shed_lucien_colours(log)
    if not (_w12):
        return False
    _w13 = yield from push_secret_wall(True, log)
    if not (_w13):
        return False
    _w14 = yield from temple_walk(IKOV_TILE.GUARDIANS, 2, log)
    if not (_w14):
        return False
    yield from settle_scene()
    _w15 = yield from talk_strict(GUARDIAN_STOP.npc, GUARDIAN_STOP.prefer, log)
    if not (_w15):
        return False
    _result16 = yield from execution.delay_until(lambda: held_id(IKOV_OBJ.PENDANT_ARMADYL) > 0 or equipment.contains(IKOV_NAME.PENDANT_ARMADYL), 8000)
    return _result16


def leave_the_far_side(log):
    """The shiny-key door in McGrubor's Wood is the only way off the far side of the lava."""
    here = game.tile()
    if not here:
        return False
    # Why: the leg only runs past Winelda's ferry, so standing on the surface is proof it has already been left.
    if not is_underground(here):
        return True
    _c17 = in_guardian_temple(here)
    if _c17:
        _w18 = yield from push_secret_wall(False, log)
        _c17 = not (_w18)
    if _c17:
        return False
    _w19 = yield from take_shiny_key(log)
    if not (_w19):
        return False
    _w20 = yield from temple_walk(IKOV_TILE.MCGRUBOR_LADDER, 1, log)
    if not (_w20):
        return False
    ladder = locs.query().name('Ladder').action('Climb-up').within(4).nearest()
    if not ladder or not (ladder.interact('Climb-up')):
        log("ikov: no ladder up to McGrubor's Wood")
        return False

    def _fn21():
        t = game.tile()
        return t is not None and t.z < 5000
    out = yield from execution.delay_until(_fn21, 10000)
    if out:
        yield from settle_scene()
    return out
