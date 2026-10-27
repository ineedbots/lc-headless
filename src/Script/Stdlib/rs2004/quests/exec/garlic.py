"""Ported from rs2b0t's src/bot/api/ai/quests/exec/garlic.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.traversal import traversal

__all__ = ['GARLIC', 'MORGAN_STAIRS_TOP', 'take_garlic']

GARLIC = 'Garlic'
MORGAN_STAIRS_BOTTOM = Tile(3099, 3266, 0)
MORGAN_STAIRS_TOP = Tile(3100, 3266, 1)
GARLIC_CUPBOARD = Tile(3096, 3268, 1)
CUPBOARD_SHUT = 2612
CUPBOARD_OPEN = 2613


def climb_morgan_stairs(log):
    _w1 = yield from traversal.walk_resilient(MORGAN_STAIRS_BOTTOM, radius=2, attempts=3, timeout_ms=90000, log=log)
    if not (_w1):
        return False
    stairs = locs.query().name('Staircase').action('Climb-up').within(6).nearest()
    if not stairs or not (stairs.interact('Climb-up')):
        log("Morgan's Staircase did not offer Climb-up")
        return False
    yield from execution.delay_until(lambda: (game.tile().level if game.tile() is not None else None) == 1, 8000)
    return False


# Why: the cupboard restocks, so the leg is repeatable and a second clove is one more Search.
def take_garlic(log):
    """Take one clove from Morgan's cupboard. False until the clove is in the pack, the climb and the Open each cost a pass."""
    if inventory.contains(GARLIC):
        return True
    if (game.tile().level if game.tile() is not None else None) != 1:
        _result2 = yield from climb_morgan_stairs(log)
        return _result2
    _w3 = yield from traversal.walk_resilient(GARLIC_CUPBOARD, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w3):
        return False
    shut = locs.query().where(lambda loc: loc.id == CUPBOARD_SHUT).action('Open').within(6).nearest()
    if shut:
        shut.interact('Open')
        yield from execution.delay_ticks(2)
        return False
    open = locs.query().where(lambda loc: loc.id == CUPBOARD_OPEN).action('Search').within(6).nearest()
    if not open:
        log("Morgan's garlic Cupboard is neither open nor searchable")
        return False
    before = inventory.count(GARLIC)
    if not (open.interact('Search')):
        return False
    _result4 = yield from execution.delay_until(lambda: inventory.count(GARLIC) > before, 8000)
    return _result4
