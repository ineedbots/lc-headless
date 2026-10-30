"""Ported from rs2b0t's src/bot/api/ai/quests/defs/murder/evidence.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items
from rs2004.items import inventory
from rs2004.traversal import traversal
from rs2004.quests.exec.prompts import drive_until, held_id, prompt_loc
from rs2004.quests.defs.murder.areas import MURDER_LOC, MURDER_OBJ, MURDER_TILE
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['take_thread', 'take_prints']

LIFT_MS = 8000
# Why: `Reach.locOp` walks when the loc is out of scene and reports `retry` without clicking, so the first call from elsewhere in the mansion is the approach and the second is the op.
# Why: one leg visits 4 locs, and a step that gives up on the walk restarts the hunt at the first suspect and never gets past the second.
LOC_TRIES = 3


def reach_loc(step, log):
    for i in range(LOC_TRIES):
        _w1 = yield from prompt_loc(step, log)
        if _w1:
            return True
    return False


def live_item(id):
    _v2 = ([item for item in inventory.items() if item.id == id] or [None])[0]
    return (_v2 if _v2 is not None else None)


def take_thread(log):
    return reach_loc(Record({
        'name': 'Smashed window',
        'op': 'Investigate',
        'near': MURDER_TILE.STUDY,
        'id': MURDER_LOC.WINDOW,
        'within': 6,
        'expect': lambda: held_id(MURDER_OBJ.THREAD_RED) + held_id(MURDER_OBJ.THREAD_GREEN) + held_id(MURDER_OBJ.THREAD_BLUE) > 0,
    }), log)


def take_dagger(log):
    if held_id(MURDER_OBJ.DAGGER) > 0 or held_id(MURDER_OBJ.DAGGER_DUST) > 0:
        return True
    _w3 = yield from traversal.walk_resilient(MURDER_TILE.STUDY, radius=1, attempts=3, timeout_ms=90000, log=log)
    if not (_w3):
        return False
    dagger = ground_items.query().where(lambda g: g.id == MURDER_OBJ.DAGGER).within(8).nearest()
    if not dagger:
        log(f'murder: no dagger on the study floor at ({MURDER_TILE.STUDY.x},{MURDER_TILE.STUDY.z})')
        return False
    if not (dagger.interact('Take')):
        return False
    # Why: the Take is answered with a mesbox, so the wait has to drive the box shut before anything else can act.
    _result4 = yield from drive_until(lambda: held_id(MURDER_OBJ.DAGGER) > 0, [], log, LIFT_MS)
    return _result4


def search_barrel(barrel, silver, log):
    return reach_loc(Record({
        'name': barrel.name,
        'op': 'Search',
        'near': barrel.near,
        'id': barrel.id,
        'within': 6,
        'expect': lambda: held_id(silver) > 0,
    }), log)


# Why: the sacks and the flour barrel each hand over 1 at a time and each dusting spends 1 of both, so taking a single sheet is 3 walks per suspect.
PAPER_STOCK = 3


def take_flypaper(log):
    if held_id(MURDER_OBJ.FLYPAPER) > 0:
        return True
    for want in range(1, PAPER_STOCK + 1):
        took = yield from reach_loc(Record({
            'name': 'Sacks',
            'op': 'Investigate',
            'near': MURDER_TILE.SACKS,
            'id': MURDER_LOC.SACKS,
            'within': 6,
            'prefer': ['Yes, it might be useful'],
            'expect': lambda: held_id(MURDER_OBJ.FLYPAPER) >= want,
        }), log)
        if not took:
            break
    return held_id(MURDER_OBJ.FLYPAPER) > 0


def fill_pot(log):
    if held_id(MURDER_OBJ.POT_FLOUR) > 0:
        return True
    empties = held_id(MURDER_OBJ.POT)
    if empties == 0:
        log('murder: no empty pot to take flour in')
        return False
    for want in range(1, empties + 1):
        filled = yield from reach_loc(Record({
            'name': 'Barrel of flour',
            'op': 'Take From',
            'near': MURDER_TILE.FLOUR_BARREL,
            'id': MURDER_LOC.FLOUR_BARREL,
            'within': 6,
            'expect': lambda: held_id(MURDER_OBJ.POT_FLOUR) >= want,
        }), log)
        if not filled:
            break
    return held_id(MURDER_OBJ.POT_FLOUR) > 0


def use_held(item_id, target_id, expect, log):
    item = live_item(item_id)
    target = live_item(target_id)
    if not item or not target:
        log(f'murder: cannot use {item_id} on {target_id} — one of them is not in the pack')
        return False
    if not (item.use_on(target)):
        return False
    _result5 = yield from drive_until(expect, [], log, LIFT_MS)
    return _result5


def flour_onto(clean, dust, log):
    if held_id(dust) > 0:
        return True
    _w6 = yield from fill_pot(log)
    if not (_w6):
        return False
    _result7 = yield from use_held(MURDER_OBJ.POT_FLOUR, clean, lambda: held_id(dust) > 0, log)
    return _result7


def lift_print(dust, print_, log):
    if held_id(print_) > 0:
        return True
    _w8 = yield from take_flypaper(log)
    if not (_w8):
        return False
    _result9 = yield from use_held(MURDER_OBJ.FLYPAPER, dust, lambda: held_id(print_) > 0, log)
    return _result9


# Why: a mismatch destroys the suspect's print only once its mesbox is dismissed, so "the print is gone" is unreadable until the box is driven shut.
def compare(print_, log):
    _result10 = yield from use_held(MURDER_OBJ.UNKNOWN_PRINT, print_, lambda: held_id(MURDER_OBJ.KILLERS_PRINT) > 0 or held_id(print_) == 0, log)
    return _result10


def test_suspect(suspect, log):
    if held_id(suspect.print) == 0:
        _c11 = held_id(suspect.dust) == 0
        if _c11:
            _w12 = yield from search_barrel(suspect.barrel, suspect.silver, log)
            _c11 = not (_w12)
        if _c11:
            return False
        _w13 = yield from flour_onto(suspect.silver, suspect.dust, log)
        if not (_w13):
            return False
        _w14 = yield from lift_print(suspect.dust, suspect.print, log)
        if not (_w14):
            return False
    _result15 = yield from compare(suspect.print, log)
    return _result15


# Why: the loop cursor is local, so a restart re-tests an already cleared suspect (1 pot of flour and 1 sheet of flypaper); no client-visible state could hold a cleared set.
def take_prints(order, log):
    """Lift the murderer's print off the dagger and match it, suspect by suspect."""
    if held_id(MURDER_OBJ.KILLERS_PRINT) > 0:
        return True
    if held_id(MURDER_OBJ.UNKNOWN_PRINT) == 0:
        _w16 = yield from take_dagger(log)
        if not (_w16):
            return False
        _w17 = yield from flour_onto(MURDER_OBJ.DAGGER, MURDER_OBJ.DAGGER_DUST, log)
        if not (_w17):
            return False
        _w18 = yield from lift_print(MURDER_OBJ.DAGGER_DUST, MURDER_OBJ.UNKNOWN_PRINT, log)
        if not (_w18):
            return False
    for suspect in order:
        if held_id(MURDER_OBJ.KILLERS_PRINT) > 0:
            return True
        log(f'murder: taking {suspect.stop.npc}\'s prints')
        _w19 = yield from test_suspect(suspect, log)
        if not (_w19):
            return False
        yield from execution.delay_ticks(1)
    return held_id(MURDER_OBJ.KILLERS_PRINT) > 0
