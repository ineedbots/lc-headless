"""Ported from rs2b0t's src/bot/api/ai/quests/defs/plaguecity/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.defs.plaguecity.areas import PC_ITEM, PC_TILE, banked, held
from rs2004.quests.defs.plaguecity.east import take_from_house

__all__ = ['AEMAD', 'JATIX', 'WYDIN', 'withdraw_from', 'scan_bank', 'reclaim', 'source_shopping_float', 'buy_item', 'take_spawn', 'source_spade', 'source_picture', 'BUCKET_TARGET', 'source_bucket', 'source_dwellberries', 'source_snape_grass', 'source_rope', 'source_pestle', 'source_chocolate_bar', 'source_milk']

# Why: Shop.open matches the owning NPC's display name, and nobody here is called 'Shop keeper'.
AEMAD = Record({'npc': 'Aemad', 'anchor': PC_TILE.AEMAD})
JATIX = Record({'npc': 'Jatix', 'anchor': PC_TILE.JATIX})
WYDIN = Record({'npc': 'Wydin', 'anchor': PC_TILE.WYDIN})
ROPE_PRICE = 60
PESTLE_PRICE = 40
CHOCOLATE_PRICE = 60
PURSE = 2000


def withdraw_from(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': PC_TILE.BANK})


# Why: one bank inventory serves every booth, and the shopping float is asked for beside the snape grass spawns, 500 tiles from the Ardougne booth this quest banks at.
def withdraw_anywhere(items):
    return Record({'kind': 'withdraw', 'items': items})


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': PC_TILE.BANK})


def from_bank(snap, item, qty):
    if not snap.bank_known:
        return scan_bank()
    stock = banked(snap, item)
    if stock <= 0:
        return None
    return withdraw_from([{'name': item.name, 'id': item.id, 'qty': min(qty - held(snap, item), stock)}])


# Why: Jethick reissues the book and Bravek the warrant only while neither the pack nor the bank holds one, so a banked copy has to come out first.
def reclaim(snap, item):
    """Withdraw a quest-issued item the bank is holding, or null when it is not banked."""
    return (None if held(snap, item) > 0 else from_bank(snap, item, 1))


SHOPPING_NEED = ROPE_PRICE + PESTLE_PRICE + CHOCOLATE_PRICE


# Why: the float is drawn once and spent down, so the trigger is the shopping still to do; a purse topped back to 2000 after every price walks to a bank between shops.
def source_purse(snap, floor, blocking):
    if held(snap, PC_ITEM.COINS) >= floor:
        return None
    if not snap.bank_known:
        return scan_bank()
    available = banked(snap, PC_ITEM.COINS)
    if available <= 0:
        return (Record({'kind': 'wait', 'reason': 'no coins banked for the rope, pestle and chocolate bar'}) if blocking else None)
    return withdraw_anywhere([{'name': PC_ITEM.COINS.name, 'id': PC_ITEM.COINS.id, 'qty': min(PURSE, available)}])


def source_shopping_float(snap):
    return source_purse(snap, SHOPPING_NEED, False)


def buy_item(snap, item, qty, shop, unit_gp):
    """Bank first, then the shop with a purse withdrawn ahead of the trip."""
    if held(snap, item) >= qty:
        return None
    stocked = from_bank(snap, item, qty)
    if stocked:
        return stocked
    missing = qty - held(snap, item)
    gp = missing * unit_gp
    # Why: the shops are a rope in Ardougne, a pestle in Taverley and a chocolate bar in Port Sarim, so the float is drawn once.
    purse = source_purse(snap, gp, True)
    return (purse if purse is not None else Record({'kind': 'buy', 'item': item.name, 'qty': missing, 'shop': shop, 'est_gp': gp}))


# Why: a respawning spawn is worth waiting on, as walking away and back costs more than the respawn timer.
def take_spawn(snap, item, qty, anchor):
    """Bank first, then the ground spawn. Null once the pack already holds enough."""
    if held(snap, item) >= qty:
        return None
    _v1 = from_bank(snap, item, qty)
    return (_v1 if _v1 is not None else Record({'kind': 'grab_ground', 'item': item.name, 'anchor': anchor, 'wait_if_missing': True}))


def from_house_floor(snap, item):
    if held(snap, item) > 0:
        return None
    _v2 = from_bank(snap, item, 1)
    return (_v2 if _v2 is not None else Record({
        'kind': 'custom',
        'name': f'take the {item.name.lower()} from Edmond\'s house',
        'run': lambda log: take_from_house(item, log),
    }))


def source_spade(snap):
    return from_house_floor(snap, PC_ITEM.SPADE)


def source_picture(snap):
    return from_house_floor(snap, PC_ITEM.PICTURE)


# Why: the garden takes 4 pours and hands the bucket back empty each time, so 1 bucket is 4 fountain round trips and 4 buckets is 1.
BUCKET_TARGET = 4


def source_bucket(snap, qty=None):
    if qty is None:
        qty = BUCKET_TARGET
    if held(snap, PC_ITEM.BUCKET) >= qty:
        return None
    _v3 = from_bank(snap, PC_ITEM.BUCKET, qty)
    return (_v3 if _v3 is not None else Record({
        'kind': 'grab_ground',
        'item': PC_ITEM.BUCKET.name,
        'anchor': PC_TILE.BUCKET_SPAWN,
        'wait_if_missing': True,
    }))


def source_dwellberries(snap):
    return take_spawn(snap, PC_ITEM.DWELLBERRIES, 1, PC_TILE.DWELLBERRIES)


def source_snape_grass(snap):
    return take_spawn(snap, PC_ITEM.SNAPE_GRASS, 1, PC_TILE.SNAPE_GRASS)


def source_rope(snap):
    return buy_item(snap, PC_ITEM.ROPE, 1, AEMAD, ROPE_PRICE)


def source_pestle(snap):
    return buy_item(snap, PC_ITEM.PESTLE, 1, JATIX, PESTLE_PRICE)


def source_chocolate_bar(snap):
    return buy_item(snap, PC_ITEM.CHOCOLATE_BAR, 1, WYDIN, CHOCOLATE_PRICE)


def source_milk(snap):
    """Milk a cow in the field north-east of Ardougne; the empty bucket comes first."""
    if held(snap, PC_ITEM.BUCKET_MILK) > 0:
        return None
    _v4 = from_bank(snap, PC_ITEM.BUCKET_MILK, 1)
    _v5 = (_v4 if _v4 is not None else source_bucket(snap, 1))
    return (_v5 if _v5 is not None else Record({
        'kind': 'use_on',
        'item': PC_ITEM.BUCKET.name,
        'target_kind': 'npc',
        'target': 'Cow',
        'anchor': PC_TILE.COW_FIELD,
        'product': PC_ITEM.BUCKET_MILK.name,
    }))
