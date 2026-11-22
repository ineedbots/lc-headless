"""Recover a lost Regicide spade from the Ardougne ground spawn."""

from rs2004 import execution
from rs2004.clues.tools import SPADE_SPAWNS
from rs2004.entities import ground_items
from rs2004.execution import event_signal
from rs2004.items import inventory
from rs2004.traversal import traversal

__all__ = ['recover_spade']

SPADE_ID = 952
SPADE_NAME = 'Spade'
SPADE_SPAWN = SPADE_SPAWNS[0]
WALK_ATTEMPTS = 2
WALK_TIMEOUT_MS = 60000
TAKE_WAIT_MS = 3000
_recovery_failed = False


def _is_spade(item):
    return item.id == SPADE_ID or (item.name or '').lower() == SPADE_NAME.lower()


def recover_spade(log):
    """Make one bounded attempt at the reachable Ardougne spawn."""
    global _recovery_failed

    if inventory.first(SPADE_NAME) is not None:
        _recovery_failed = False
        return True
    if _recovery_failed:
        log('Ardougne spade recovery was already attempted and failed')
        return False

    _recovery_failed = True

    log(f'no spade in pack or bank; checking Ardougne spawn at ({SPADE_SPAWN.x},{SPADE_SPAWN.z})')
    reached = yield from traversal.walk_resilient(
        SPADE_SPAWN,
        radius=1,
        attempts=WALK_ATTEMPTS,
        timeout_ms=WALK_TIMEOUT_MS,
        log=lambda message: log(f'  {message}'),
    )
    if event_signal.pending():
        _recovery_failed = False
        return False
    if not reached:
        log('could not reach the Ardougne spade spawn')
        return False

    spade = ground_items.query().where(_is_spade).nearest()
    if spade is None:
        log('no spade is available at the Ardougne spawn')
        return False

    if spade.distance() > 1:
        reached = yield from traversal.walk_resilient(
            spade.tile(),
            radius=1,
            attempts=1,
            timeout_ms=WALK_TIMEOUT_MS,
            log=lambda message: log(f'  {message}'),
        )
        if event_signal.pending():
            _recovery_failed = False
            return False
        if not reached:
            log('could not reach the spade on the ground')
            return False

    spade.interact('Take')
    acquired = yield from execution.delay_until(lambda: inventory.first(SPADE_NAME) is not None, TAKE_WAIT_MS)
    if not acquired:
        log('the Ardougne spade was not acquired')
        return False

    log('recovered a spade at Ardougne')
    _recovery_failed = False
    return True


def recovery_failed():
    return _recovery_failed


def reset_recovery():
    global _recovery_failed
    _recovery_failed = False
