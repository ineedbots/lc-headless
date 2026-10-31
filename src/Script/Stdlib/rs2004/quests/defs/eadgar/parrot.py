"""Ported from rs2b0t's src/bot/api/ai/quests/defs/eadgar/parrot.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.items import inventory
from rs2004.quests.defs.eadgar.areas import ER_ITEM, ER_LOC, ER_TILE, PETE_FEED, PETE_WHEN, banked, held
from rs2004.quests.defs.eadgar.supplies import HECKEL, held_liquor, scan_bank, source_knife, source_liquor, withdraw
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import drive_until, use_on_loc
from rs2004.traversal import traversal

__all__ = ['source_parrot']

PINEAPPLE_PRICE = 5


def inv_by_id(id):
    return ([item for item in inventory.items() if item.id == id] or [None])[0]


# Why: the knife opens a two-object chat; "Slice the pineapple." yields 4 rings and only "Dice the pineapple." makes the chunks the parrot wants.
def dice_pineapple(log):
    """Cut an uncut pineapple into chunks."""
    if inventory.count_by_id(ER_ITEM.PINEAPPLE_CHUNKS.id) > 0:
        return True
    # Why: this runs the tick after Heckel Funch's counter shuts, and a use-on issued into the closing shop interface is swallowed.
    yield from modals.close_if_open()
    yield from execution.delay_ticks(1)
    knife = inv_by_id(ER_ITEM.KNIFE.id)
    fruit = inv_by_id(ER_ITEM.PINEAPPLE.id)
    if not knife or not fruit:
        log('dice: no Knife or no Pineapple in the pack')
        return False
    if not (knife.use_on(fruit)):
        return False
    _result1 = yield from drive_until(lambda: inventory.count_by_id(ER_ITEM.PINEAPPLE_CHUNKS.id) > 0, ['Dice the'], log)
    return _result1


def source_pineapple_chunks(snap):
    """Bank, then the knife, then Heckel Funch's counter. Null once chunks are in the pack."""
    if held(snap, ER_ITEM.PINEAPPLE_CHUNKS) > 0:
        return None
    if not snap.bank_known:
        return scan_bank(snap)
    if banked(snap, ER_ITEM.PINEAPPLE_CHUNKS) > 0:
        return withdraw(snap, [{'name': ER_ITEM.PINEAPPLE_CHUNKS.name, 'id': ER_ITEM.PINEAPPLE_CHUNKS.id, 'qty': 1}])
    if held(snap, ER_ITEM.PINEAPPLE) > 0:
        _v2 = source_knife(snap)
        return (_v2 if _v2 is not None else Record({'kind': 'custom', 'name': 'dice the pineapple', 'run': dice_pineapple}))
    if banked(snap, ER_ITEM.PINEAPPLE) > 0:
        return withdraw(snap, [{'name': ER_ITEM.PINEAPPLE.name, 'id': ER_ITEM.PINEAPPLE.id, 'qty': 1}])
    # One trip: Heckel Funch stocks the knife as well as the fruit and the vodka.
    _v3 = source_knife(snap)
    return (_v3 if _v3 is not None else Record({'kind': 'buy', 'item': ER_ITEM.PINEAPPLE.name, 'qty': 1, 'shop': HECKEL, 'est_gp': PINEAPPLE_PRICE}))


# Why: `make_alco_chunks` is gated on both of Parroty Pete's varbits and neither is visible to the client, so both lines are re-asked every pass; 2 dialogues and never a wrong guess.
def catch_parrot(log):
    """Dip the chunks, bait the hatch, pocket the parrot."""
    if inventory.count_by_id(ER_ITEM.DRUNK_PARROT.id) > 0:
        return True
    if inventory.count_by_id(ER_ITEM.ALCO_CHUNKS.id) == 0:
        _w4 = yield from traversal.walk_resilient(ER_TILE.PETE, radius=4, attempts=3, timeout_ms=180000, log=log)
        if not (_w4):
            return False
        for stop in [PETE_WHEN, PETE_FEED]:
            _w5 = yield from talk_strict(stop.npc, stop.prefer, log)
            if not (_w5):
                log(f'Parroty Pete would not answer "{stop.prefer[0]}"')
                return False
            yield from execution.delay_ticks(2)
        chunks = inv_by_id(ER_ITEM.PINEAPPLE_CHUNKS.id)
        liquor = ([item for item in inventory.items() if (item.name or '').lower() in ['vodka', 'gin', 'brandy', 'whisky']] or [None])[0]
        if not chunks or not liquor:
            log('no Pineapple chunks or no liquor in the pack')
            return False
        if not (chunks.use_on(liquor)):
            return False
        _w6 = yield from execution.delay_until(lambda: inventory.count_by_id(ER_ITEM.ALCO_CHUNKS.id) > 0, 8000)
        if not (_w6):
            log('the chunks did not soak — Pete has not said both of his lines yet')
            return False
    _result7 = yield from use_on_loc(ER_ITEM.ALCO_CHUNKS.id, Record({'name': 'Aviary Hatch', 'near': ER_TILE.AVIARY_HATCH, 'id': ER_LOC.AVIARY_HATCH}), [], lambda: inventory.count_by_id(ER_ITEM.DRUNK_PARROT.id) > 0, log)
    return _result7


def source_parrot(snap):
    """Everything between an empty pack and a Drunk parrot. Null once one is carried."""
    if held(snap, ER_ITEM.DRUNK_PARROT) > 0:
        return None
    if not snap.bank_known:
        return scan_bank(snap)
    # Why: the aviary refuses a second parrot while one is banked, so a banked one has to come out.
    if banked(snap, ER_ITEM.DRUNK_PARROT) > 0:
        return withdraw(snap, [{'name': ER_ITEM.DRUNK_PARROT.name, 'id': ER_ITEM.DRUNK_PARROT.id, 'qty': 1}])
    _v8 = source_pineapple_chunks(snap)
    _v9 = (_v8 if _v8 is not None else source_liquor(snap))
    if _v9 is not None:
        return _v9
    liquor = held_liquor(snap)
    bait = liquor if liquor is not None else ER_ITEM.VODKA
    return Record({'kind': 'custom', 'name': f'catch a parrot with {bait.name.lower()} chunks', 'run': catch_parrot})
