"""Ported from rs2b0t's src/bot/api/ai/quests/defs/eadgar/storeroom.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.items import inventory
from rs2004.quests.defs.eadgar.areas import ER_ITEM, ER_LOC, ER_TILE
from rs2004.quests.exec.prompts import prompt_loc, settle_scene
from rs2004.traversal import traversal

__all__ = ['take_storeroom_key', 'unlock_storeroom', 'take_goutweed', 'retrieve_parrot']


def held_id(id):
    return inventory.count_by_id(id)


def take_storeroom_key(log):
    """Open the kitchen drawers, then search the fake bottom for the Storeroom key."""
    if held_id(ER_ITEM.STOREROOM_KEY.id) > 0:
        return True
    _w1 = yield from traversal.walk_resilient(ER_TILE.KITCHEN_DRAWERS, radius=2, attempts=3, timeout_ms=240000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    shut = locs.query().where(lambda loc: loc.id == ER_LOC.KITCHEN_DRAWERS).action('Open').within(6).nearest()
    if shut:
        if not (shut.interact('Open')):
            return False
        yield from execution.delay_until(lambda: locs.query().where(lambda loc: loc.id == ER_LOC.KITCHEN_DRAWERS_OPEN).within(6).nearest() is not None, 8000)
    _result2 = yield from prompt_loc(Record({
        'name': 'Kitchen Drawers',
        'op': 'Search',
        'near': ER_TILE.KITCHEN_DRAWERS,
        'id': ER_LOC.KITCHEN_DRAWERS_OPEN,
        'within': 6,
        'expect': lambda: held_id(ER_ITEM.STOREROOM_KEY.id) > 0,
    }), log)
    return _result2


# Why: the door reads the key out of the pack, so a spent key is the only client-visible proof the unlock landed; the stage varp is not transmitted.
def unlock_storeroom(log):
    """Unlock the Storeroom Door from the corridor south of it."""
    if held_id(ER_ITEM.STOREROOM_KEY.id) == 0:
        log('no Storeroom key in the pack')
        return False
    _w3 = yield from traversal.walk_resilient(ER_TILE.STOREROOM_DOOR_OUT, radius=1, attempts=3, timeout_ms=240000, log=log)
    if not (_w3):
        return False
    yield from settle_scene()
    _result4 = yield from prompt_loc(Record({
        'name': 'Storeroom Door',
        'op': 'Open',
        'near': ER_TILE.STOREROOM_DOOR_OUT,
        'id': ER_LOC.STOREROOM_DOOR,
        'within': 4,
        'expect': lambda: held_id(ER_ITEM.STOREROOM_KEY.id) == 0,
    }), log)
    return _result4


# Why: 8 guards patrol the crate maze and each knock costs up to 6 hitpoints and a teleport back to the antechamber, so the walk in is expected to fail several times.
def take_goutweed(log):
    """Search the Goutweed Crate, riding out the patrol knockouts."""
    for attempt in range(12):
        if held_id(ER_ITEM.GOUTWEED.id) > 0:
            return True
        got = yield from prompt_loc(Record({
            'name': 'Goutweed Crate',
            'op': 'Search',
            'near': ER_TILE.GOUTWEED_CRATE,
            'id': ER_LOC.GOUTWEED_CRATE,
            'within': 6,
            'expect': lambda: held_id(ER_ITEM.GOUTWEED.id) > 0,
        }), log)
        if got:
            return True
        log(f'knocked back from the goutweed crate (attempt {attempt + 1}/12)')
        yield from execution.delay_ticks(3)
    return False


def retrieve_parrot(log):
    """Take the parrot back out from under the torture rack."""
    return prompt_loc(Record({
        'name': 'Rack',
        'op': 'Search',
        'near': ER_TILE.RACK,
        'id': ER_LOC.RACK,
        'within': 6,
        'expect': lambda: held_id(ER_ITEM.DRUNK_PARROT.id) > 0,
    }), log)
