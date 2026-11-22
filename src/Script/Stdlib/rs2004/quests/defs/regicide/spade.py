"""Recover a lost Regicide spade from the Ardougne ground spawn."""

from rs2004 import execution
from rs2004.clues.tools import SPADE_SPAWNS as KNOWN_SPADE_SPAWNS
from rs2004.entities import ground_items
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.traversal import traversal

__all__ = ['recover_spade']

SPADE_ID = 952
SPADE_NAME = 'Spade'
SPADE_SPAWN = KNOWN_SPADE_SPAWNS[0]
WALK_ATTEMPTS = 2
WALK_TIMEOUT_MS = 60000
TAKE_WAIT_MS = 3000
_recovery_failed = False


def _is_spade(item):
    return item.id == SPADE_ID or (item.name or '').lower() == SPADE_NAME.lower()


def recover_spade(log):
    """Check each known spade spawn once, starting with the nearest."""
    global _recovery_failed

    if inventory.first(SPADE_NAME) is not None:
        _recovery_failed = False
        return True
    if _recovery_failed:
        log('Ardougne spade recovery was already attempted and failed')
        return False

    _recovery_failed = True

    here = game.tile()
    spawns = sorted(KNOWN_SPADE_SPAWNS, key=lambda tile: tile.distance_to(here)) if here is not None else list(KNOWN_SPADE_SPAWNS)
    log('no spade in pack or bank; checking the nearest known spade spawns')
    for spawn in spawns:
        place = ('Ardougne' if spawn == KNOWN_SPADE_SPAWNS[0] else 'Falador')
        log(f'checking {place} spawn at ({spawn.x},{spawn.z})')
        reached = yield from traversal.walk_resilient(
            spawn,
            radius=1,
            attempts=WALK_ATTEMPTS,
            timeout_ms=WALK_TIMEOUT_MS,
            log=lambda message: log(f'  {message}'),
        )
        if event_signal.pending():
            _recovery_failed = False
            return False
        if not reached:
            log(f'could not reach the {place} spade spawn')
            continue

        spade = ground_items.query().where(_is_spade).nearest()
        if spade is None:
            log(f'no spade is available at the {place} spawn')
            continue

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
                log(f'could not reach the spade at the {place} spawn')
                continue

        spade.interact('Take')
        acquired = yield from execution.delay_until(lambda: inventory.first(SPADE_NAME) is not None, TAKE_WAIT_MS)
        if not acquired:
            log(f'the spade at the {place} spawn was not acquired')
            continue

        log(f'recovered a spade at {place}')
        _recovery_failed = False
        return True

    log('no known spade spawn could provide a spade')
    return False


def recovery_failed():
    return _recovery_failed


def reset_recovery():
    global _recovery_failed
    _recovery_failed = False
