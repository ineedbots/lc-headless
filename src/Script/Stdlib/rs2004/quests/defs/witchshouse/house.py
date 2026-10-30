"""Ported from rs2b0t's src/bot/api/ai/quests/defs/witchshouse/house.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.traversal import traversal
from rs2004.quests.exec.legs import open_container
from rs2004.quests.exec.prompts import clear_boxes, drive_boxes, prompt_loc, settle_scene
from rs2004.quests.defs.witchshouse.areas import WH_LOC, WH_NPC, WH_OBJ, WH_TILE, in_porch
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['held', 'live_item', 'take_door_key', 'fetch_magnet', 'drop_stale_magnet', 'unlock_back_door', 'diary_state', 'reset_diary_state', 'diary_wanted', 'fetch_diary', 'read_diary']

WALK_MS = 180000
NOTHING_INTERESTING = "/don't find anything interesting/i"
ALREADY_UNLOCKED = 'already unlocked this door'


def held(id):
    return inventory.count_by_id(id)


def live_item(id):
    _v1 = ([item for item in inventory.items() if item.id == id] or [None])[0]
    return (_v1 if _v1 is not None else None)


def take_door_key(log):
    """`~mesbox` announces the key and the `inv_add` lands a tick behind it, so the count is the oracle."""
    if held(WH_OBJ.DOOR_KEY) > 0:
        return True
    took = yield from prompt_loc(Record({
        'name': 'Potted plant',
        'op': 'Look-under',
        'near': WH_TILE.POT,
        'id': WH_LOC.POT,
        'within': 6,
        'expect': lambda: held(WH_OBJ.DOOR_KEY) > 0,
        'expect_ms': 12000,
        'refused': NOTHING_INTERESTING,
    }), log)
    yield from modals.close()
    return took and held(WH_OBJ.DOOR_KEY) > 0


# Why: the cellar gate is a baked door edge, so the walk opens and crosses it, but `_ball_irongate` shocks a bare hand and leaves you on the near side, so the gloves go on first.
def fetch_magnet(log):
    """Search the cellar cupboard behind the electrified gate."""
    if held(WH_OBJ.MAGNET) > 0:
        return True
    _w2 = yield from traversal.walk_resilient(WH_TILE.CUPBOARD, radius=1, attempts=3, timeout_ms=WALK_MS, log=log)
    if not (_w2):
        log('the cellar cupboard stand is unreachable. The iron gate only passes with the gloves worn')
        return False
    yield from settle_scene()
    _w3 = yield from open_container('Cupboard', WH_LOC.CUPBOARD_SHUT, WH_LOC.CUPBOARD_OPEN, WH_TILE.CUPBOARD, log)
    if not (_w3):
        return False
    mark = game_messages.mark()
    found = yield from prompt_loc(Record({
        'name': 'Cupboard',
        'op': 'Search',
        'near': WH_TILE.CUPBOARD,
        'id': WH_LOC.CUPBOARD_OPEN,
        'within': 6,
        'expect': lambda: held(WH_OBJ.MAGNET) > 0,
        'expect_ms': 12000,
        'refused': NOTHING_INTERESTING,
    }), log)
    yield from modals.close()
    if not found and game_messages.saw_since(mark, NOTHING_INTERESTING):
        log('the cupboard is empty because a magnet already exists in the pack or the bank')
    return held(WH_OBJ.MAGNET) > 0


# Why: `magnetcbopen` gives a magnet only when the account owns none, so remove extras before stage 1.
def drop_stale_magnet(log):
    """Drop a magnet that stops the cupboard replacing it."""
    magnet = live_item(WH_OBJ.MAGNET)
    if not magnet:
        return True
    if not (magnet.interact('Drop')):
        log('the stale magnet refused the Drop click')
        return False
    _result4 = yield from execution.delay_until(lambda: held(WH_OBJ.MAGNET) == 0, 6000)
    return _result4


def mouse():
    return npcs.query().where(lambda n: n.id == WH_NPC.MOUSE).within(4).nearest()


# Why: `opheld5,cheese` jumps to the same `ball_cheese` label from anywhere in the porch zone and never reaches the `inv_dropslot` under it.
# Why: that makes Drop a second way in, for when the client does not offer a wall decoration as a use target.
def lure_mouse(log):
    """Spend a cheese to bring the mouse out of its hole."""

    def there():
        return mouse() is not None

    hole = locs.query().where(lambda l: l.id == WH_LOC.MOUSE_HOLE).within(4).nearest()
    cheese = live_item(WH_OBJ.CHEESE)
    if not cheese:
        log('no cheese in the pack to lure the mouse with')
        return False
    _c5 = hole and (cheese.use_on(hole))
    if _c5:
        _w6 = yield from drive_boxes(there, 8000, [], log)
        _c5 = (_w6)
    if _c5:
        yield from clear_boxes()
        return True
    spare = live_item(WH_OBJ.CHEESE)
    if not spare:
        log('the cheese was spent and no mouse came out of the hole')
        return False
    if not (spare.interact('Drop')):
        return False
    came = yield from drive_boxes(there, 8000, [], log)
    yield from clear_boxes()
    return came


def unlock_back_door(log):
    """Lure the mouse and fit the magnet, which is what unlocks the back door."""
    _c7 = not in_porch(game.tile())
    if _c7:
        _w8 = yield from traversal.walk_resilient(WH_TILE.PORCH, radius=0, attempts=3, timeout_ms=WALK_MS, log=log)
        _c7 = not (_w8)
    if _c7:
        log('the back porch is unreachable. The front door needs the door key in the pack')
        return False
    yield from settle_scene()
    _c9 = not mouse()
    if _c9:
        _w10 = yield from lure_mouse(log)
        _c9 = not (_w10)
    if _c9:
        return False
    target = mouse()
    magnet = live_item(WH_OBJ.MAGNET)
    if not target or not magnet:
        log(f'nothing to fit: mouse={target is not None} magnet={magnet is not None}')
        return False
    mark = game_messages.mark()
    if not (magnet.use_on(target)):
        log('the mouse refused the magnet')
        return False
    fitted = yield from drive_boxes(lambda: held(WH_OBJ.MAGNET) == 0, 12000, [], log)
    yield from clear_boxes()
    if fitted:
        return True
    if game_messages.saw_since(mark, ALREADY_UNLOCKED):
        log('the back door was already unlocked')
        return True
    log('the magnet is still in the pack, so the harness is unfitted and the back door still locked')
    return False


# Why: `witch.rs2` rewinds the quest only while the varp sits at 3, and reading the diary moves it to 5.
diary_state = Record({'read': False, 'tries': 0})
MAX_DIARY_TRIES = 3


def reset_diary_state():
    diary_state.read = False
    diary_state.tries = 0


def diary_wanted():
    return not diary_state.read and diary_state.tries < MAX_DIARY_TRIES


def fetch_diary(log):
    if held(WH_OBJ.DIARY) > 0:
        return True
    _w11 = yield from traversal.walk_resilient(WH_TILE.DIARY, radius=1, attempts=3, timeout_ms=WALK_MS, log=log)
    if not (_w11):
        diary_state.tries += 1
        log(f'the upstairs bedroom is unreachable (try {diary_state.tries} of {MAX_DIARY_TRIES})')
        return False
    yield from settle_scene()
    drop = ground_items.query().where(lambda g: g.id == WH_OBJ.DIARY).within(6).nearest()
    if not drop:
        diary_state.tries += 1
        log(f'no diary on the bedroom floor (try {diary_state.tries} of {MAX_DIARY_TRIES}); it respawns in 30 ticks')
        return False
    if not (drop.interact('Take')):
        diary_state.tries += 1
        return False
    _result12 = yield from execution.delay_until(lambda: held(WH_OBJ.DIARY) > 0, 8000)
    return _result12


def read_diary(log):
    """Read the diary; the book modal opening is the only proof the script ran."""
    diary = live_item(WH_OBJ.DIARY)
    if not diary:
        return False
    if not (diary.interact('Read')):
        log('the diary refused the Read click')
        return False
    opened = yield from execution.delay_until(lambda: modals.is_open(), 6000)
    yield from modals.close()
    if not opened:
        diary_state.tries += 1
        log(f'the diary opened no book (try {diary_state.tries} of {MAX_DIARY_TRIES})')
        return False
    diary_state.read = True
    log('diary read, so being caught now costs the shed key and not the back door')
    return True
