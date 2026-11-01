"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/pyre.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.entities import locs
from rs2004.items import inventory
from rs2004.quests.defs.mortton.areas import SM_ID, SM_LOC, SM_LOC_ID, SM_TILE
from rs2004.quests.defs.mortton.temple import sacred_oil_doses
from rs2004.quests.exec.prompts import settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['DOSES_PER_PYRE_LOG', 'empty_pyre', 'loaded_pyre', 'bodied_pyre', 'make_pyre_logs', 'stack_pyre', 'lay_remains', 'light_pyre']

PYRE_RADIUS = 10
DOSES_PER_PYRE_LOG = 2


def pyre_of_type(id):
    return locs.query().where(lambda l: l.id == id).within(PYRE_RADIUS).nearest()


def empty_pyre():
    return pyre_of_type(SM_LOC_ID.PYRE_EMPTY)


def loaded_pyre():
    return pyre_of_type(SM_LOC_ID.PYRE_LOGS)


def bodied_pyre():
    return pyre_of_type(SM_LOC_ID.PYRE_BONES)


def make_pyre_logs(log):
    """Pour sacred oil over a log to make a pyre log."""
    if sacred_oil_doses() < DOSES_PER_PYRE_LOG:
        log(f'only {sacred_oil_doses()} dose(s) of sacred oil — a pyre log wants {DOSES_PER_PYRE_LOG}')
        return False
    oil = ([item for item in [([i for i in inventory.items() if i.id == id] or [None])[0] for id in [SM_ID.SACRED_OIL4, SM_ID.SACRED_OIL3, SM_ID.SACRED_OIL2]] if item is not None] or [None])[0]
    logs = ([i for i in inventory.items() if i.id == SM_ID.LOGS] or [None])[0]
    if not oil or not logs:
        log('no sacred oil vial or no logs in the pack')
        return False
    before = inventory.count_by_id(SM_ID.PYRE_LOGS)
    if not (oil.use_on(logs)):
        return False
    _result1 = yield from execution.delay_until(lambda: inventory.count_by_id(SM_ID.PYRE_LOGS) > before, 10000)
    return _result1


def at_pyres(log):
    _v2 = empty_pyre()
    _v3 = (_v2 if _v2 is not None else loaded_pyre())
    if (_v3 if _v3 is not None else bodied_pyre()):
        return True
    _w4 = yield from traversal.walk_resilient(SM_TILE.PYRE, radius=3, attempts=3, timeout_ms=240000, log=log)
    if not (_w4):
        return False
    yield from settle_scene()
    return True


# Why: `%pyre_loc` binds the funeral to the one loc the logs went on, and every later step reads "This funeral pyre is not yours." off any other, so each stage targets the loc type our own pyre is in.
def stack_pyre(log):
    """Stack the pyre logs on a funeral pyre."""
    _v5 = loaded_pyre()
    if (_v5 if _v5 is not None else bodied_pyre()):
        return True
    _w6 = yield from at_pyres(log)
    if not (_w6):
        return False
    _result7 = yield from use_on_loc(SM_ID.PYRE_LOGS, Record({'name': SM_LOC.PYRE, 'near': SM_TILE.PYRE, 'id': SM_LOC_ID.PYRE_EMPTY, 'within': PYRE_RADIUS}), [], lambda: loaded_pyre() is not None, log)
    return _result7


def lay_remains(log):
    """Lay the shade's remains on the stacked logs."""
    if bodied_pyre():
        return True
    _w8 = yield from at_pyres(log)
    if not (_w8):
        return False
    _result9 = yield from use_on_loc(SM_ID.REMAINS, Record({'name': SM_LOC.PYRE, 'near': SM_TILE.PYRE, 'id': SM_LOC_ID.PYRE_LOGS, 'within': PYRE_RADIUS}), [], lambda: bodied_pyre() is not None, log)
    return _result9


def light_pyre(log):
    """Set the cremation alight."""
    if inventory.count_by_id(SM_ID.TINDERBOX) == 0:
        log('no tinderbox in the pack — the pyre cannot be lit')
        return False
    _w10 = yield from at_pyres(log)
    if not (_w10):
        return False
    pyre = bodied_pyre()
    if not pyre:
        log('no loaded funeral pyre in reach')
        return False
    if not (pyre.interact('Light')):
        return False
    # The pyre reverts to its empty type once the reward queue has run.
    burned = yield from execution.delay_until(lambda: bodied_pyre() is None, 90000)
    yield from modals.close_if_open()
    if not burned:
        log('the funeral pyre never caught')
    return burned
