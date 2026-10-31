"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, BIO_TILE, banked, held, owned

__all__ = ['HANDBACK_SLOTS', 'FOOD_CARRY', 'FOOD', 'scan_bank', 'withdraw', 'reclaim', 'source_coins', 'source_food', 'tidy', 'owns_all']

HANDBACK_SLOTS = 6
FOOD_CARRY = 5
FOOD = Record({'id': 379, 'name': 'Lobster'})
KEEP_IDS = [BIO_ITEM.get(key).id for key in BIO_ITEM.keys()] + [FOOD.id]


def scan_bank():
    return Record({'kind': 'scan_bank'})


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items})


# Why: the cupboard, the crate and the chemist all gate their re-issue on `obj_gettotal`, which counts the bank, so a banked copy has to come out.
def reclaim(snap, item, qty=1):
    """Withdraw a quest item the bank is holding, or null when it is not banked."""
    if held(snap, item) >= qty:
        return None
    if not snap.bank_known:
        return scan_bank()
    stock = banked(snap, item)
    if stock <= 0:
        return None
    return withdraw([{'name': item.name, 'id': item.id, 'qty': min(qty - held(snap, item), stock)}])


# Why: the float is drawn beside the Ardougne booth on the distraction leg, so the walk from Rimmington to Thessalia is one leg with no bank detour.
# Why: a draw is much larger than the trigger, or the 60 coins spent on the way to the chemist put the purse back under the threshold and buy a second bank trip.
PURSE = 1000


def source_coins(snap, floor, blocking=True):
    """Coins for Thessalia. `blocking` waits when the bank has none; otherwise it lets the leg run on."""
    if held(snap, BIO_ITEM.COINS) >= floor:
        return None
    if not snap.bank_known:
        return scan_bank()
    available = banked(snap, BIO_ITEM.COINS)
    if available <= 0:
        return (Record({'kind': 'wait', 'reason': 'no coins banked for the priest gown'}) if blocking else None)
    return withdraw([{'name': BIO_ITEM.COINS.name, 'id': BIO_ITEM.COINS.id, 'qty': min(PURSE, available)}])


def source_food(snap):
    """A few lobsters for the mourner, when the bank has them. Never blocks."""
    if held(snap, FOOD) > 0 or not snap.bank_known or banked(snap, FOOD) <= 0:
        return None
    return withdraw([{'name': FOOD.name, 'id': FOOD.id, 'qty': min(FOOD_CARRY, banked(snap, FOOD))}])


def tidy(snap, floor):
    """Bank everything this quest does not need, so Elena's hand-back has somewhere to land."""
    if ((snap.free_slots if snap.free_slots is not None else 28)) >= floor:
        return None
    return Record({'kind': 'deposit', 'keep': [], 'keep_ids': KEEP_IDS, 'bank': BIO_TILE.ARDOUGNE_BANK})


def owns_all(snap, items):
    return all([owned(snap, item) > 0 for item in items])
