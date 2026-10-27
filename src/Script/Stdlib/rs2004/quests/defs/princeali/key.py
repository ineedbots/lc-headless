"""Ported from rs2b0t's src/bot/api/ai/quests/defs/princeali/key.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.quests.defs.princeali.areas import KELI_PRINT, LEELA_STOP, OSMAN_FORGE, PA_ITEM, PA_SHOP, PA_TILE
from rs2004.quests.defs.princeali.journal import PRINCE_STAGE
from rs2004.quests.defs.princeali.supplies import banked, buy_item, from_bank, grab_item, has_any_pickaxe, held_item, owned, withdraw_from
from rs2004.quests.defs.princeali.supplies import held
from rs2004.quests.exec.primitives import goto_npc, talk_strict


__all__ = ['have_key', 'source_bronze_bar', 'source_water', 'source_pickaxe', 'source_clay', 'make_soft_clay', 'take_key_print', 'collect_key']

BAR_GP = 40
WATER_GP = 20


def have_key(snap):
    return held(snap, PA_ITEM.PRINCE_KEY.id) > 0


def key_done(snap):
    return owned(snap, PA_ITEM.PRINCE_KEY.id) > 0


# Why: Leela only promotes to stage 30 while the key is in the pack, so from 30 on the key provably existed and prince_keystatus is no longer 0.
# Why: Osman won't forge a second one, so every clay leg past that is dead weight.
def key_issued(snap):
    """True once the key provably existed."""
    return ((snap.stage if snap.stage is not None else 0)) >= PRINCE_STAGE.PREP_FINISHED


def print_done(snap):
    return key_done(snap) or key_issued(snap) or owned(snap, PA_ITEM.KEY_PRINT.id) > 0


def soft_clay_done(snap):
    return print_done(snap) or owned(snap, PA_ITEM.SOFT_CLAY.id) > 0


def source_bronze_bar(snap):
    if key_done(snap) or key_issued(snap):
        return None
    return buy_item(snap, PA_ITEM.BRONZE_BAR, 1, PA_SHOP.SHANTAY, BAR_GP)


def source_water(snap):
    for_clay = (0 if soft_clay_done(snap) else 1)
    for_paste = (0 if owned(snap, PA_ITEM.PASTE.id) > 0 else 1)
    want = for_clay + for_paste
    if want == 0:
        return None
    return buy_item(snap, PA_ITEM.JUG_OF_WATER, want, PA_SHOP.SHANTAY, WATER_GP)


def source_pickaxe(snap):
    if soft_clay_done(snap) or owned(snap, PA_ITEM.CLAY.id) > 0 or has_any_pickaxe(snap):
        return None
    return grab_item(snap, PA_ITEM.PICKAXE, PA_TILE.PICKAXE_SPAWN)


def source_clay(snap):
    if soft_clay_done(snap) or held(snap, PA_ITEM.CLAY.id) > 0:
        return None
    _v1 = from_bank(snap, PA_ITEM.CLAY, 1)
    return (_v1 if _v1 is not None else Record({'kind': 'mine_rock', 'rock': 'Clay', 'item': PA_ITEM.CLAY.name, 'qty': 1, 'anchor': PA_TILE.CLAY_ROCKS}))


def make_soft_clay(snap):
    if soft_clay_done(snap):
        return from_bank(snap, PA_ITEM.SOFT_CLAY, 1)
    if held(snap, PA_ITEM.CLAY.id) == 0 or held(snap, PA_ITEM.JUG_OF_WATER.id) == 0:
        return None
    return Record({
        'kind': 'use_on',
        'item': PA_ITEM.JUG_OF_WATER.name,
        'target_kind': 'item',
        'target': PA_ITEM.CLAY.name,
        'anchor': PA_TILE.CLAY_ROCKS,
        'product': PA_ITEM.SOFT_CLAY.name,
    })


def take_key_print(snap):
    if print_done(snap):
        return (None if key_issued(snap) else from_bank(snap, PA_ITEM.KEY_PRINT, 1))
    if held(snap, PA_ITEM.SOFT_CLAY.id) == 0:
        return None
    return Record({'kind': 'talk', 'stop': KELI_PRINT})


def collect_key(snap):
    if have_key(snap):
        return None
    # Leela's re-issue check reads the bank as well as the pack, so a banked key blocks its own replacement.
    if banked(snap, PA_ITEM.PRINCE_KEY.id) > 0:
        return withdraw_from([{'name': PA_ITEM.PRINCE_KEY.name, 'id': PA_ITEM.PRINCE_KEY.id, 'qty': 1}])
    if key_issued(snap):
        return Record({'kind': 'custom', 'name': 'ask Leela to replace the lost key', 'run': collect_from_leela})
    if held(snap, PA_ITEM.KEY_PRINT.id) == 0 or held(snap, PA_ITEM.BRONZE_BAR.id) == 0:
        return None
    return Record({
        'kind': 'custom',
        'name': 'have Osman forge the key, then collect it from Leela',
        'run': forge_and_collect,
    })


def collect_from_leela(log):
    if held_item(PA_ITEM.PRINCE_KEY.id):
        return True
    _w2 = yield from goto_npc(LEELA_STOP, [], log)
    if not (_w2):
        return False
    yield from talk_strict(LEELA_STOP.npc, LEELA_STOP.prefer, log)
    yield from execution.delay_until(lambda: held_item(PA_ITEM.PRINCE_KEY.id) is not None, 4000)
    return held_item(PA_ITEM.PRINCE_KEY.id) is not None


# Why: Osman forges only while prince_keystatus is 0, and that varp is not transmitted.
# Why: a print still in the pack after the conversation proves the key was already forged, so this goes to Leela either way.
def forge_and_collect(log):
    """Have Osman forge the key, then take it to Leela."""
    if held_item(PA_ITEM.PRINCE_KEY.id):
        return True
    _w3 = yield from goto_npc(OSMAN_FORGE, [], log)
    if _w3:
        yield from talk_strict(OSMAN_FORGE.npc, OSMAN_FORGE.prefer, log)
    if held_item(PA_ITEM.KEY_PRINT.id):
        log('Osman would not take the print — the key is already forged; collecting from Leela')
    _result4 = yield from collect_from_leela(log)
    return _result4
