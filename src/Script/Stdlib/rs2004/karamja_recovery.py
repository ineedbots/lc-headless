"""Earn a stranded traveller's fare: rs2b0t's api/walking/karamjaRecovery.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory

__all__ = ['missing_boat_fare', 'recover_boat_fare']

BOAT_FARE = 30
recovering = False


def on_island(tile):
    return tile.level == 0 and tile.x >= 2700 and tile.x < 3000 and tile.z >= 2880 and tile.z <= 3255


def missing_boat_fare(from_, dest, coins, missing):
    return from_ is not None and on_island(from_) and not on_island(dest) and coins < BOAT_FARE and len(missing) == 1 and missing[0].name.lower() == 'coins' and coins + missing[0].count == BOAT_FARE


def _earn(log):
    from rs2004.quests.defs.piratestreasure.areas import LUTHAS
    from rs2004.quests.defs.piratestreasure import karamja
    from rs2004.quests.exec import primitives
    from rs2004.traversal import traversal

    log("no boat fare: earning 30 coins at Luthas's plantation")
    for attempt in range(2):
        if event_signal.pending():
            return False
        walked = yield from traversal.walk_to(LUTHAS.anchor, radius=2, timeout_ms=120000, log=log)
        if not walked or event_signal.pending():
            return False
        talked = yield from primitives.talk_strict(LUTHAS.npc, LUTHAS.prefer, log)
        if not talked:
            return False
        if inventory.count_by_id(995) >= BOAT_FARE:
            return True
        if attempt == 0:
            if event_signal.pending():
                return False
            filled = yield from karamja.fill_crate(log)
            if not filled:
                return False
    return False


def recover_boat_fare(dest, missing, log):
    """Collect a payment, or fill one crate for it. Use with yield from."""
    global recovering
    if recovering or event_signal.pending() or not missing_boat_fare(game.tile(), dest, inventory.count_by_id(995), missing):
        return False
    if inventory.is_full() and inventory.count_by_id(1963) == 0:
        log('boat fare recovery needs one free inventory slot')
        return False
    recovering = True
    try:
        earned = yield from _earn(log)
    except Exception as error:
        recovering = False
        raise error
    recovering = False
    return earned
