"""Ported from rs2b0t's src/bot/api/ai/quests/defs/observatory/dungeon.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.observatory.areas import OBS_ID, OBS_LOC, OBS_LOC_NAME, OBS_QUEST, OBS_TILE
from rs2004.quests.defs.trollstronghold.combat import attackable, fight
from rs2004.quests.exec.primitives import is_underground
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['in_dome', 'in_keep', 'descend', 'fetch_keep_key', 'enter_keep', 'fetch_lens_mould', 'use_telescope']

def walk(to, log, radius=0):
    return traversal.walk_resilient(to, radius=radius, attempts=3, timeout_ms=180000, log=log)


def loc_by_id(id, within=6):
    return locs.query().where(lambda l: l.id == id).within(within).nearest()


# Why: the dome is a walled pocket of the surface; nothing walks into it and its own ladder only goes down.
def in_dome(t):
    return t.level == 0 and t.x >= 2430 and t.x <= 2450 and t.z >= 3150 and t.z <= 3170


def in_keep(t):
    """True while standing south of the keep gate, the 4 tiles the sack sits in."""
    return is_underground(t) and t.x >= 2386 and t.x <= 2392 and t.z >= 9450 and t.z <= 9457


# Why: `obs_dungeonladderdown` is a `p_telejump` behind 2 lines of the assistant's goblin warning, so the derived graph marks the edge "behind a runtime guard" and disables it.
# Why: the climb has to drive that dialogue, so it's the module's leg; `hopLadder` only clicks and waits, and the wait outlives the conversation.
def descend(log):
    """Climb the reception ladder into the cavern, answering the assistant on the way."""
    here = game.tile()
    if here and is_underground(here):
        return True
    _w1 = yield from walk(OBS_TILE.RECEPTION_LADDER, log, 1)
    if not (_w1):
        return False
    ladder = loc_by_id(OBS_LOC.RECEPTION_LADDER, 4)
    if not ladder:
        log(f'observatory: no cavern ladder at ({OBS_TILE.RECEPTION_LADDER.x},{OBS_TILE.RECEPTION_LADDER.z})')
        return False
    log('observatory: climbing down into the goblin cavern')
    if not (ladder.interact('Climb-down')):
        return False

    def _fn2():
        t = game.tile()
        return t is not None and is_underground(t)
    down = yield from drive_until(_fn2, [], log, 20000)
    if down:
        yield from settle_scene()
    return down


def ascend_to_reception(log):
    """Climb out of the cavern the way the baked graph does, so the surface legs start above ground."""
    here = game.tile()
    if here and not is_underground(here):
        return True
    _result3 = yield from walk(OBS_TILE.PROFESSOR, log, 2)
    return _result3


# Why: `loc_2197` is the only one of the cavern's 8 chests with a key; 6 of the others are `shutdungeonchest`, whose Search spawns a poisonous spider, so nothing here is looked up by name.
# Why: it is `forceapproach=north` placed at angle 2, which rotates the legal side to the south.
def fetch_keep_key(log):
    """Open and search the keep-key chest."""
    if held_id(OBS_ID.KEEP_KEY) > 0:
        return True
    _w4 = yield from descend(log)
    if not (_w4):
        return False
    _w5 = yield from walk(OBS_TILE.KEY_CHEST_STAND, log, 0)
    if not (_w5):
        return False
    yield from settle_scene()
    shut = loc_by_id(OBS_LOC.KEY_CHEST_SHUT, 4)
    if shut:
        log('observatory: opening the keep-key chest')
        if not (shut.interact('Open')):
            return False
        yield from execution.delay_until(lambda: loc_by_id(OBS_LOC.KEY_CHEST_OPEN, 4) is not None, 6000)
    open = loc_by_id(OBS_LOC.KEY_CHEST_OPEN, 4)
    if not open:
        log(f'observatory: no keep-key chest at ({OBS_TILE.KEY_CHEST_STAND.x},{OBS_TILE.KEY_CHEST_STAND.z})')
        return False
    if not (open.interact('Search')):
        return False
    _result6 = yield from drive_until(lambda: held_id(OBS_ID.KEEP_KEY) > 0, [], log, 12000)
    return _result6


def gate():
    return locs.query().where(lambda l: l.id == OBS_LOC.GATE_RIGHT or l.id == OBS_LOC.GATE_LEFT).within(4).nearest()


# Why: opening the gate runs `~npc_retaliate(0)` on any goblin guard within 8 tiles, and it then follows the leg into the keep and interrupts the search.
# Why: it spawns beside the north stand, and an NPC standing on a tile makes it unwalkable for the client's own path search.
def clear_guard(log):
    """Clear the guard off the gate before touching it."""
    guard = attackable('Goblin guard', 10)
    if not guard:
        return True
    log('observatory: killing the goblin guard on the keep gate')
    _result7 = yield from fight(Record({
        'what': 'Goblin guard',
        'target': lambda: attackable('Goblin guard', 10),
        'won': lambda: attackable('Goblin guard', 10) is None,
        'protect': 'melee',
        'guard': 300,
    }), log)
    return _result7


# Why: `@open_keep_gate` teleports you 1 tile across the gate and re-adds the loc 3 ticks later, so the crossing is checked by tile.
# Why: from the north it refuses with "The gate is locked." until the key sets `%itkeepgatelock`; from the south it always opens.
def enter_keep(log):
    """Cross the keep gate southwards. False when it is still locked and the pack holds no key."""
    here = game.tile()
    if here and in_keep(here):
        return True
    _w8 = yield from walk(OBS_TILE.GATE_NORTH, log, 0)
    if not (_w8):
        return False
    yield from settle_scene()
    yield from clear_guard(log)
    shut = gate()
    if not shut:
        log(f'observatory: no keep gate at ({OBS_TILE.GATE_NORTH.x},{OBS_TILE.GATE_NORTH.z})')
        return False
    key = ([item for item in inventory.items() if item.id == OBS_ID.KEEP_KEY] or [None])[0]
    if key:
        log('observatory: unlocking the keep gate with the keep key')
        if not (key.use_on(shut)):
            return False
    else:
        log('observatory: trying the keep gate without a key')
        if not (shut.interact('Open')):
            return False

    def _fn9():
        t = game.tile()
        return t is not None and in_keep(t)
    crossed = yield from drive_until(_fn9, [], log, 8000)
    # Why: "The gate is locked." is a chat line the click doesn't report, so the tile is the only test of whether the key is needed.
    if not crossed and not key:
        log('observatory: the keep gate is locked — fetching the keep key')
        yield from fetch_keep_key(log)
    return crossed


def leave_keep(log):
    """Cross back out; from inside, the gate opens for anyone."""
    here = game.tile()
    if here and not in_keep(here):
        return True
    _w10 = yield from walk(OBS_TILE.GATE_SOUTH, log, 0)
    if not (_w10):
        return False
    shut = gate()
    if not shut or not (shut.interact('Open')):
        log('observatory: cannot leave the keep — no gate in reach')
        return False

    def _fn12():
        t = game.tile()
        return t is not None and not in_keep(t)
    _result11 = yield from drive_until(_fn12, [], log, 10000)
    return _result11


def fetch_lens_mould(log):
    """Fetch the lens mould from the sack the goblins hid it under, and get back out."""
    if held_id(OBS_ID.LENS_MOULD) == 0:
        _w13 = yield from descend(log)
        if not (_w13):
            return False
        _w14 = yield from enter_keep(log)
        if not (_w14):
            return False
        _w15 = yield from walk(OBS_TILE.SACK_STAND, log, 0)
        if not (_w15):
            return False
        yield from settle_scene()
        sack = loc_by_id(OBS_LOC.SACK, 4)
        if not sack:
            log(f'observatory: no sack at ({OBS_TILE.SACK_STAND.x},{OBS_TILE.SACK_STAND.z})')
            return False
        log('observatory: searching the sack for the lens mould')
        if not (sack.interact('Search')):
            return False
        _w16 = yield from drive_until(lambda: held_id(OBS_ID.LENS_MOULD) > 0, [], log, 12000)
        if not (_w16):
            return False
    _w17 = yield from leave_keep(log)
    if not (_w17):
        return False
    _result18 = yield from ascend_to_reception(log)
    return _result18


# Why: the dome's telescope only answers while `observatory_professor2` is within 7 tiles of the player, and his copy stands 3 tiles from it.
# Why: `if_openmain(telescope)` puts the star chart on main and queues the conversation a tick later, so the chat options arrive under an open main modal.
def use_telescope(log):
    """Climb into the dome, look through the telescope, and take the constellation."""
    start = game.tile()
    if not start or not in_dome(start):
        _w19 = yield from descend(log)
        if not (_w19):
            return False
        _w20 = yield from walk(OBS_TILE.DOME_LADDER_FOOT, log, 0)
        if not (_w20):
            return False
        yield from settle_scene()
        ladder = locs.query().name(OBS_LOC_NAME.LADDER).action('Climb-up').within(4).nearest()
        if not ladder:
            log(f'observatory: no dome ladder at ({OBS_TILE.DOME_LADDER_FOOT.x},{OBS_TILE.DOME_LADDER_FOOT.z})')
            return False
        log('observatory: climbing into the observatory dome')
        if not (ladder.interact('Climb-up')):
            return False

        def _fn21():
            t = game.tile()
            return t is not None and in_dome(t)
        _w22 = yield from execution.delay_until(_fn21, 10000)
        if not (_w22):
            return False
        yield from settle_scene()
    _w23 = yield from walk(OBS_TILE.TELESCOPE_STAND, log, 1)
    if not (_w23):
        return False
    yield from settle_scene()
    telescope = loc_by_id(OBS_LOC.TELESCOPE, 6)
    if not telescope:
        log(f'observatory: no telescope at ({OBS_TILE.TELESCOPE_STAND.x},{OBS_TILE.TELESCOPE_STAND.z})')
        return False
    log('observatory: looking through the telescope')
    if not (telescope.interact('Use')):
        return False
    # Why: the professor's "Well done, well done!!" is a chat that has to be driven before `if_openmain(telescope)` puts the star chart up.
    yield from drive_until(lambda: modals.is_open(), [], log, 20000)
    # Why: `canAccess()` is `!delayed && !containsModalInterface()` and the constellation conversation is an engine queue, so it can't run while the chart is up.
    if modals.is_open():
        log('observatory: closing the star chart so the constellation conversation can run')
        yield from modals.close()
    _result24 = yield from drive_until(lambda: quests.status(OBS_QUEST) == 'complete', ['I can see a constellation.'], log, 90000)
    return _result24
