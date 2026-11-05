"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/vials.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record
from bots.account_leveler.travel import leveler_travel_zones

from rs2004.geometry import Tile

__all__ = ['VIAL_FOUNTAIN', 'fill_supply_vials']

VIAL_FOUNTAIN = Tile(2949, 3381, 0)


def fill_supply_vials(count, log):
    if count < 1 or count > 28:
        return False
    _w1 = yield from traversal.walk_resilient(VIAL_FOUNTAIN, radius=3, timeout_ms=120000, avoid_zones=leveler_travel_zones(), log=log)
    if not (_w1):
        return False
    for i in range(count):
        fountain = locs.query().name('Fountain').within(6).nearest()
        vial = ([item for item in inventory.items() if item.id == 229 and not item.noted] or [None])[0]
        if not fountain or not vial:
            return False
        water = inventory.count_by_id(227)
        empty = inventory.count_by_id(229)
        if not (vial.use_on(fountain)):
            return False
        _w2 = yield from execution.delay_until(lambda: inventory.count_by_id(227) > water and inventory.count_by_id(229) < empty, 4000)
        if not (_w2):
            return False
        yield from execution.delay_ticks(1)
    return True
