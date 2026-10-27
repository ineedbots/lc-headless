"""Ported from rs2b0t's src/bot/api/ai/quests/defs/princeali/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.items import inventory
from rs2004.quests.defs.princeali.areas import PA_ITEM


__all__ = ['PURSE_FLOOR', 'PURSE_TOP', 'held', 'banked', 'owned', 'held_item', 'has_any_pickaxe', 'scan_bank', 'withdraw_from', 'from_bank', 'buy_item', 'grab_item', 'source_coins']

PURSE_FLOOR = 150
PURSE_TOP = 1000
PICKAXE_IDS = [1265, 1267, 1269, 1271, 1273, 1275]


def held(snap, id):
    _v1 = (snap.inv_ids or {}).get(id)
    return (_v1 if _v1 is not None else 0)


def banked(snap, id):
    _v2 = (snap.bank_ids or {}).get(id)
    return (_v2 if _v2 is not None else 0)


def owned(snap, id):
    return held(snap, id) + banked(snap, id)


def held_item(id):
    _v3 = ([item for item in inventory.items() if item.id == id] or [None])[0]
    return (_v3 if _v3 is not None else None)


def has_any_pickaxe(snap):
    return any([held(snap, id) > 0 or (((id in (snap.worn_ids or set())) if (id in (snap.worn_ids or set())) is not None else False)) for id in PICKAXE_IDS])


def scan_bank():
    return Record({'kind': 'scan_bank'})


def withdraw_from(items):
    """No `bank`, so openBankLeg uses the nearest branch to wherever the route has reached."""
    return Record({'kind': 'withdraw', 'items': items})


def from_bank(snap, item, qty=1):
    """Pack, then bank, then nothing, for anything the caller makes itself."""
    short = qty - held(snap, item.id)
    if short <= 0:
        return None
    if not snap.bank_known:
        return scan_bank()
    in_bank = banked(snap, item.id)
    return (withdraw_from([{'name': item.name, 'id': item.id, 'qty': min(short, in_bank)}]) if in_bank > 0 else None)


def buy_item(snap, item, qty, shop, unit_gp):
    short = qty - held(snap, item.id)
    if short <= 0:
        return None
    _v4 = from_bank(snap, item, qty)
    return (_v4 if _v4 is not None else Record({'kind': 'buy', 'item': item.name, 'qty': short, 'shop': shop, 'est_gp': short * unit_gp}))


def grab_item(snap, item, anchor):
    if held(snap, item.id) > 0:
        return None
    _v5 = from_bank(snap, item, 1)
    return (_v5 if _v5 is not None else Record({'kind': 'grab_ground', 'item': item.name, 'anchor': anchor, 'wait_if_missing': True}))


def source_coins(snap, floor, top):
    purse = held(snap, PA_ITEM.COINS.id)
    if purse >= floor:
        return None
    if not snap.bank_known:
        return scan_bank()
    available = banked(snap, PA_ITEM.COINS.id)
    if available <= 0:
        return Record({'kind': 'wait', 'reason': 'no coins in the bank for shops, dialogue purchases and the toll gate'})
    return withdraw_from([{'name': PA_ITEM.COINS.name, 'id': PA_ITEM.COINS.id, 'qty': min(top - purse, available)}])
