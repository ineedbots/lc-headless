"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/pyre.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.game import skills
from rs2004.execution import event_signal
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


active_pyre = None


def owned_pyre():
    global active_pyre
    if not active_pyre or _core.step_time() >= active_pyre.expires:
        active_pyre = None
        return None
    tile = active_pyre.tile
    pyre = locs.query().where(lambda loc: loc.tile().equals(tile) and (loc.id == SM_LOC_ID.PYRE_LOGS or loc.id == SM_LOC_ID.PYRE_BONES)).within(PYRE_RADIUS).nearest()
    if not pyre:
        active_pyre = None
    return pyre


def loaded_pyre():
    pyre = owned_pyre()
    return (pyre if (pyre.id if pyre is not None else None) == SM_LOC_ID.PYRE_LOGS else None)


def bodied_pyre():
    pyre = owned_pyre()
    return (pyre if (pyre.id if pyre is not None else None) == SM_LOC_ID.PYRE_BONES else None)


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


def stack_pyre(log):
    global active_pyre
    if owned_pyre():
        return True
    _w5 = yield from at_pyres(log)
    if not (_w5):
        return False
    pyre = empty_pyre()
    logs = ([item for item in inventory.items() if item.id == SM_ID.PYRE_LOGS] or [None])[0]
    if not pyre or not logs:
        log('need an empty funeral pyre and replacement pyre logs')
        return False
    before = inventory.count_by_id(SM_ID.PYRE_LOGS)
    if not (logs.use_on(pyre)):
        return False
    tile = pyre.tile()
    def landed():
        expected_tile = tile
        found = locs.query().where(lambda loc: loc.id == SM_LOC_ID.PYRE_LOGS and loc.tile().equals(expected_tile)).nearest()
        return inventory.count_by_id(SM_ID.PYRE_LOGS) < before and found is not None
    stacked = yield from execution.delay_until(landed, 8000)
    active_pyre = (Record({'tile': pyre.tile(), 'expires': _core.step_time() + 29400}) if stacked else None)
    return stacked


def lay_remains(log):
    global active_pyre
    if bodied_pyre():
        return True
    pyre = loaded_pyre()
    remains = ([item for item in inventory.items() if item.id == SM_ID.REMAINS] or [None])[0]
    if not pyre or not remains:
        log('need our stacked funeral pyre and Loar remains')
        return False
    before = inventory.count_by_id(SM_ID.REMAINS)
    if not (remains.use_on(pyre)):
        return False
    active_pyre = Record({'tile': pyre.tile(), 'expires': _core.step_time() + 29400})
    _result6 = yield from execution.delay_until(lambda: inventory.count_by_id(SM_ID.REMAINS) < before and bodied_pyre() is not None, 8000)
    return _result6


def light_pyre(log):
    global active_pyre
    pyre = bodied_pyre()
    if not pyre or inventory.count_by_id(SM_ID.TINDERBOX) == 0:
        log('need our funeral pyre with remains and a tinderbox')
        return False
    before = skills.xp('firemaking')
    if not (pyre.interact('Light')):
        return False
    burned = yield from execution.delay_until(lambda: skills.xp('firemaking') > before, 35000)
    yield from modals.close_if_open()
    if burned:
        active_pyre = None
    else:
        log('no cremation experience received; rechecking the pyre and supplies')
    return burned


def cremate_shade(log):
    if event_signal.pending():
        return False
    if inventory.count_by_id(SM_ID.TINDERBOX) == 0 or (not bodied_pyre() and inventory.count_by_id(SM_ID.REMAINS) == 0):
        log('prepare a tinderbox and Loar remains before starting the funeral')
        return False
    _w9 = yield from stack_pyre(log)
    _c8 = (_w9) and not event_signal.pending()
    if _c8:
        _w10 = yield from lay_remains(log)
        _c8 = (_w10)
    _c7 = _c8 and not event_signal.pending()
    if not (_c7):
        return _c7
    _result11 = yield from light_pyre(log)
    return _result11
