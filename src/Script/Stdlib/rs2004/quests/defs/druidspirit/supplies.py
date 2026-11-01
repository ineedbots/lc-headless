"""Ported from rs2b0t's src/bot/api/ai/quests/defs/druidspirit/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.game import skills
from rs2004.items import inventory
from rs2004.quests.defs.druidspirit.areas import BOB, DOMMIK, NS_ID, NS_LOC, NS_NAME, NS_TILE, URHNEY
from rs2004.quests.defs.knightssword.supplies import pickaxe_at
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal

__all__ = ['NS_TOOLS', 'SILVER_MINING', 'SILVER_SMITHING', 'held_id', 'banked_id', 'amulet', 'sickle_step']

NS_TOOLS = [
    'ghostspeak amulet',
    'mirror',
    'journal',
    'druidic spell',
    'a used spell',
    'mort myre fungi',
    'mort myre stem',
    'mort myre pear',
    'silver sickle',
    'silver sickle(b)',
    'druid pouch',
    'sickle mould',
    'silver ore',
    'silver bar',
    'coins',
    'bronze pickaxe',
    'iron pickaxe',
    'steel pickaxe',
    'mithril pickaxe',
    'adamant pickaxe',
    'rune pickaxe',
]


SILVER_MINING = 20
SILVER_SMITHING = 20


def held_id(snap, id):
    count = None if snap.inv_ids is None else snap.inv_ids.get(id)
    return count if count is not None else 0


def banked_id(snap, id):
    count = None if snap.bank_ids is None else snap.bank_ids.get(id)
    return count if count is not None else 0


scan_bank = Record({'kind': 'scan_bank'})


def withdraw(name, id, qty=1):
    return (Record({'kind': 'withdraw', 'items': [{'name': name, 'qty': qty, 'id': id}]}))


def amulet(snap):
    """Every word with either spirit needs the amulet worn."""
    if snap.worn_ids is not None and NS_ID.GHOSTSPEAK in snap.worn_ids:
        return None
    if held_id(snap, NS_ID.GHOSTSPEAK) > 0:
        return Record({'kind': 'equip', 'item': NS_NAME.GHOSTSPEAK})
    if not snap.bank_known:
        return scan_bank
    if banked_id(snap, NS_ID.GHOSTSPEAK) > 0:
        return withdraw(NS_NAME.GHOSTSPEAK, NS_ID.GHOSTSPEAK)
    # Why: Urhney replaces a lost amulet, so this does not require user intervention.
    return Record({'kind': 'talk', 'stop': URHNEY})


def at_furnace(log, open, product, expect):
    """Walk to the furnace and complete the resulting make menu."""
    if expect():
        return True
    _w1 = yield from traversal.walk_resilient(NS_TILE.FURNACE, radius=2, attempts=4, timeout_ms=300000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    # Why: the furnace is 2 locs and only one carries `op2=Smelt`, so prefer that half; the other is only a use-on target.
    _v2 = locs.query().name(NS_LOC.FURNACE).action('Smelt').within(8).nearest()
    furnace = (_v2 if _v2 is not None else locs.query().name(NS_LOC.FURNACE).within(8).nearest())
    if not furnace:
        log('no Furnace in reach of the Al Kharid stand')
        return False
    _w3 = yield from open(furnace)
    if not (_w3):
        log('the Al Kharid furnace did not answer')
        return False
    _w4 = yield from execution.delay_until(lambda: chat_dialog.is_make_menu(), 8000)
    if not (_w4):
        log('the make menu never opened')
        return False
    _w5 = yield from chat_dialog.make_x(product, 1)
    if not (_w5):
        log(f"no '{product}' in the menu: [{', '.join(chat_dialog.make_products())}]")
        return False
    _result6 = yield from execution.delay_until(expect, 30000)
    return _result6


def open_smelt(furnace):
    if False:
        yield
    return furnace.interact('Smelt')


def smelt_silver(log):
    _result7 = yield from at_furnace(log, open_smelt, 'Silver', lambda: inventory.count_by_id(NS_ID.SILVER_BAR) > 0)
    return _result7


def use_bar_on(furnace):
    bar = ([i for i in inventory.items() if i.id == NS_ID.SILVER_BAR] or [None])[0]
    if False:
        yield
    return bar.use_on(furnace) if bar else False


# Why: the `Smelt` op only opens the ore-to-bar menu; silver craft is an `oplocu`, so the bar is used on the furnace.
# Why: casting the sickle is a members-only option and this world is members everywhere (`Environment.node.members`), so the Al Kharid furnace serves.
# Why: The Silver sickle option appears only while the mould is held.
def cast_sickle(log):
    _result8 = yield from at_furnace(log, use_bar_on, NS_NAME.SICKLE, lambda: inventory.count_by_id(NS_ID.SICKLE) > 0)
    return _result8


# Why: the shared helper's last resort is the bronze pickaxe ground spawn at Rimmington, 360 tiles the wrong side of Al Kharid.
# Why: Bob stocks 5 of them 70 tiles from the mine, and this quest carries coin for the mould anyway.
def pickaxe(snap, mining_level):
    """A pickaxe, bank first, then Bob's counter in Lumbridge."""
    step = pickaxe_at(snap, mining_level)
    if not step or step.kind != 'grab_ground':
        return step
    return Record({'kind': 'buy', 'item': 'Bronze pickaxe', 'qty': 1, 'shop': BOB, 'est_gp': 500})


def sickle_step(snap, mining_level=None, smithing_level=None):
    """Bank first, then Al Kharid: mould, ore, bar, cast. Null once a sickle is in hand."""
    if held_id(snap, NS_ID.SICKLE_BLESSED) > 0 or held_id(snap, NS_ID.SICKLE) > 0:
        return None
    if not snap.bank_known:
        return scan_bank
    if banked_id(snap, NS_ID.SICKLE_BLESSED) > 0:
        return withdraw(NS_NAME.SICKLE_BLESSED, NS_ID.SICKLE_BLESSED)
    if banked_id(snap, NS_ID.SICKLE) > 0:
        return withdraw(NS_NAME.SICKLE, NS_ID.SICKLE)
    if held_id(snap, NS_ID.MOULD) == 0:
        if banked_id(snap, NS_ID.MOULD) > 0:
            return withdraw(NS_NAME.MOULD, NS_ID.MOULD)
        # Why: `buy` funds itself from the bank when the pack is short, so this quest carries no standing coin float.
        return Record({'kind': 'buy', 'item': NS_NAME.MOULD, 'qty': 1, 'shop': DOMMIK, 'est_gp': 200})
    if held_id(snap, NS_ID.SILVER_BAR) > 0:
        return Record({'kind': 'custom', 'name': 'cast the silver sickle', 'run': cast_sickle})
    if banked_id(snap, NS_ID.SILVER_BAR) > 0:
        return withdraw(NS_NAME.SILVER_BAR, NS_ID.SILVER_BAR)
    # Why: below a skill's level the server refuses in a message box, which no step reads, so the smelt or the mine
    # would fail silently until the quest parked; and ore that can't be smelted isn't worth mining. This departs
    # from rs2b0t.
    smithing = smithing_level if smithing_level is not None else skills.level('smithing')
    if smithing < SILVER_SMITHING:
        return Record({'kind': 'wait', 'reason': f'a silver bar needs Smithing {SILVER_SMITHING} (have {smithing}); bank a silver bar or a sickle'})
    if held_id(snap, NS_ID.SILVER_ORE) > 0:
        return Record({'kind': 'custom', 'name': 'smelt a silver bar', 'run': smelt_silver})
    if banked_id(snap, NS_ID.SILVER_ORE) > 0:
        return withdraw(NS_NAME.SILVER_ORE, NS_ID.SILVER_ORE)
    level = mining_level if mining_level is not None else skills.level('mining')
    if level < SILVER_MINING:
        return Record({'kind': 'wait', 'reason': f'silver ore needs Mining {SILVER_MINING} (have {level}); bank a silver bar or a sickle'})
    # Why: Mining without a pickaxe fails silently, so source one first.
    _v10 = pickaxe(snap, level)
    return (_v10 if _v10 is not None else Record({
        'kind': 'mine_rock',
        'rock': 'Silver',
        'item': NS_NAME.SILVER_ORE,
        'qty': 1,
        'anchor': NS_TILE.SILVER_ROCKS,
    }))
