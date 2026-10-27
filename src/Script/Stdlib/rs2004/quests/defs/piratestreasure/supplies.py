"""Ported from rs2b0t's src/bot/api/ai/quests/defs/piratestreasure/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.piratestreasure.areas import PT_ID, PT_NAME, PT_TILE, THESSALIA_SHOP


__all__ = ['COIN_TARGET', 'COIN_LOW', 'held_id', 'banked_id', 'worn_id', 'kit']

# Why: the crossing costs 30gp each way and Karamja has no bank, so the float is a threshold; topping up to an exact balance puts a booth trip between every purchase.
COIN_TARGET = 2000
COIN_LOW = 300
APRON_GP = 50


def held_id(snap, id):
    _v1 = (snap.inv_ids or {}).get(id)
    return (_v1 if _v1 is not None else 0)


def banked_id(snap, id):
    _v2 = (snap.bank_ids or {}).get(id)
    return (_v2 if _v2 is not None else 0)


def worn_id(snap, id):
    _v3 = (id in (snap.worn_ids or set()))
    return (_v3 if _v3 is not None else False)


# Why: `ownsInventory` marks the quest provisioned before the engine reads `coinFloat`, so it is inert and this is the only place coins are drawn. The quest is free and nothing on it fights back, so it carries no food.
def kit(snap, want_apron, want_spade):
    """Coins and whichever of the apron and spade the caller still needs."""
    need_coins = held_id(snap, PT_ID.COINS) < COIN_LOW
    need_apron = want_apron and held_id(snap, PT_ID.WHITE_APRON) == 0 and not worn_id(snap, PT_ID.WHITE_APRON)
    need_spade = want_spade and held_id(snap, PT_ID.SPADE) == 0
    if not need_coins and not need_apron and not need_spade:
        return None
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    items = []
    _v4 = (snap.bank or {}).get('coins')
    banked_coins = (_v4 if _v4 is not None else 0)
    if need_coins and banked_coins > 0:
        items.append({'name': PT_NAME.COINS, 'qty': min(COIN_TARGET, banked_coins)})
    if need_apron and banked_id(snap, PT_ID.WHITE_APRON) > 0:
        items.append({'name': PT_NAME.WHITE_APRON, 'qty': 1, 'id': PT_ID.WHITE_APRON})
    if need_spade and banked_id(snap, PT_ID.SPADE) > 0:
        items.append({'name': PT_NAME.SPADE, 'qty': 1, 'id': PT_ID.SPADE})
    if len(items) > 0:
        return Record({'kind': 'withdraw', 'items': items})
    if need_apron:
        return Record({'kind': 'buy', 'item': PT_NAME.WHITE_APRON, 'qty': 1, 'shop': THESSALIA_SHOP, 'est_gp': APRON_GP})
    if need_spade:
        return Record({'kind': 'grab_ground', 'item': PT_NAME.SPADE, 'anchor': PT_TILE.SPADE_SPAWN, 'wait_if_missing': True})
    return None
