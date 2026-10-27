"""Ported from rs2b0t's src/bot/api/ai/quests/defs/princeali/disguise.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, npcs
from rs2004.quests.defs.princeali.areas import AGGIE_PASTE, NED_WIG, PA_ITEM, PA_LOC, PA_NPC, PA_SHOP, PA_TILE
from rs2004.quests.defs.princeali.supplies import buy_item, from_bank, grab_item, held_item, owned
from rs2004.quests.defs.princeali.supplies import held
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.quests.exec.wool import gather_wool
from rs2004.traversal import traversal


__all__ = ['disguise_complete', 'source_tinderbox', 'source_shears', 'source_onions', 'source_wool', 'source_pink_skirt', 'source_paste_goods', 'make_ashes', 'make_blond_wig', 'make_paste']

WOOL_SITES = Record({
    'pen': PA_TILE.SHEEP_PEN,
    'wheel_stand': PA_TILE.SPIN_STAND,
    'shears_spawn': PA_TILE.SHEARS_SPAWN,
    'spin_label': 'spin wool at Lumbridge',
})
BALLS_FOR_WIG = 3
ONIONS_FOR_DYE = 2
TINDERBOX_GP = 10
SHEARS_GP = 10
SKIRT_GP = 20
REDBERRIES_GP = 20
FLOUR_GP = 30


def have_wig(snap):
    return owned(snap, PA_ITEM.BLOND_WIG.id) > 0 or owned(snap, PA_ITEM.PLAIN_WIG.id) > 0


def have_dye(snap):
    return owned(snap, PA_ITEM.BLOND_WIG.id) > 0 or owned(snap, PA_ITEM.YELLOW_DYE.id) > 0


def have_paste(snap):
    return owned(snap, PA_ITEM.PASTE.id) > 0


def disguise_complete(snap):
    """The prince consumes all 3 from the pack, so a banked piece doesn't count."""
    return held(snap, PA_ITEM.BLOND_WIG.id) > 0 and held(snap, PA_ITEM.PINK_SKIRT.id) > 0 and held(snap, PA_ITEM.PASTE.id) > 0


def source_tinderbox(snap):
    if have_paste(snap) or owned(snap, PA_ITEM.ASHES.id) > 0:
        return None
    return buy_item(snap, PA_ITEM.TINDERBOX, 1, PA_SHOP.LUMBRIDGE, TINDERBOX_GP)


def source_shears(snap):
    if have_wig(snap) or owned(snap, PA_ITEM.BALL_OF_WOOL.id) >= BALLS_FOR_WIG:
        return None
    return buy_item(snap, PA_ITEM.SHEARS, 1, PA_SHOP.LUMBRIDGE, SHEARS_GP)


def source_onions(snap):
    if have_dye(snap) or held(snap, PA_ITEM.ONION.id) >= ONIONS_FOR_DYE:
        return None
    _v1 = from_bank(snap, PA_ITEM.ONION, ONIONS_FOR_DYE)
    return (_v1 if _v1 is not None else Record({
        'kind': 'pick_loc',
        'loc': PA_LOC.ONION,
        'op': 'Pick',
        'item': PA_ITEM.ONION.name,
        'anchor': PA_TILE.ONION_PATCH,
    }))


def source_wool(snap):
    if have_wig(snap) or held(snap, PA_ITEM.BALL_OF_WOOL.id) >= BALLS_FOR_WIG:
        return None
    banked = from_bank(snap, PA_ITEM.BALL_OF_WOOL, BALLS_FOR_WIG)
    if banked:
        return banked
    # gatherWool reads the name map; this quest reads ids everywhere else.
    shears = ([['shears', 1]] if held(snap, PA_ITEM.SHEARS.id) > 0 else [])
    wool_snap = snap.with_fields({'inv': {name: count for name, count in [['wool', held(snap, PA_ITEM.WOOL.id)]] + shears}})
    return gather_wool(wool_snap, BALLS_FOR_WIG - held(snap, PA_ITEM.BALL_OF_WOOL.id), WOOL_SITES)


def source_pink_skirt(snap):
    return buy_item(snap, PA_ITEM.PINK_SKIRT, 1, PA_SHOP.THESSALIA, SKIRT_GP)


def source_paste_goods(snap):
    if have_paste(snap):
        return None
    _v3 = buy_item(snap, PA_ITEM.REDBERRIES, 1, PA_SHOP.WYDIN, REDBERRIES_GP)
    return (_v3 if _v3 is not None else buy_item(snap, PA_ITEM.POT_OF_FLOUR, 1, PA_SHOP.WYDIN, FLOUR_GP))


def make_ashes(snap):
    if have_paste(snap) or owned(snap, PA_ITEM.ASHES.id) > 0 or held(snap, PA_ITEM.TINDERBOX.id) == 0:
        return None
    _v4 = grab_item(snap, PA_ITEM.LOGS, PA_TILE.LOGS_SPAWN)
    return (_v4 if _v4 is not None else Record({'kind': 'custom', 'name': 'burn the logs for ashes', 'run': burn_logs}))


def make_blond_wig(snap):
    if owned(snap, PA_ITEM.BLOND_WIG.id) > 0:
        return from_bank(snap, PA_ITEM.BLOND_WIG, 1)
    if held(snap, PA_ITEM.YELLOW_DYE.id) == 0:
        if held(snap, PA_ITEM.ONION.id) < ONIONS_FOR_DYE:
            return None
        return Record({'kind': 'custom', 'name': 'have Aggie make yellow dye', 'run': make_yellow_dye})
    if held(snap, PA_ITEM.PLAIN_WIG.id) == 0:
        if held(snap, PA_ITEM.BALL_OF_WOOL.id) < BALLS_FOR_WIG:
            return None
        return Record({'kind': 'talk', 'stop': NED_WIG})
    return Record({'kind': 'custom', 'name': 'dye the wig blond', 'run': dye_wig})


def make_paste(snap):
    if have_paste(snap):
        return from_bank(snap, PA_ITEM.PASTE, 1)
    missing = [
        (PA_ITEM.REDBERRIES.name if held(snap, PA_ITEM.REDBERRIES.id) == 0 else None),
        (PA_ITEM.POT_OF_FLOUR.name if held(snap, PA_ITEM.POT_OF_FLOUR.id) == 0 else None),
        (PA_ITEM.ASHES.name if held(snap, PA_ITEM.ASHES.id) == 0 else None),
        (PA_ITEM.JUG_OF_WATER.name if held(snap, PA_ITEM.JUG_OF_WATER.id) == 0 else None),
    ]
    absent = [name for name in missing if name is not None]
    if len(absent) > 0:
        return Record({'kind': 'wait', 'reason': f"paste needs {', '.join(absent)}"})
    return Record({'kind': 'talk', 'stop': AGGIE_PASTE})


def use_held_on_npc(item_id, npc_name, near, expect, log):
    """Item-on-NPC is an opnpcu, so this walks then uses; `Reach.npcDialog` would open a conversation first."""
    if expect():
        return True
    _w5 = yield from traversal.walk_resilient(near, radius=3, attempts=3, timeout_ms=120000, log=log)
    if not (_w5):
        return False
    yield from settle_scene()
    npc = npcs.query().name(npc_name).within(10).nearest()
    item = held_item(item_id)
    if not npc or not item:
        log(f'useHeldOnNpc: no \'{npc_name}\' or no item {item_id} in the pack')
        return False
    if not (item.use_on(npc)):
        return False
    _result6 = yield from drive_until(expect, [], log)
    return _result6


def burn_logs(log):
    if held_item(PA_ITEM.ASHES.id):
        return True
    tinder = held_item(PA_ITEM.TINDERBOX.id)
    logs = held_item(PA_ITEM.LOGS.id)
    if not tinder or not logs:
        log('burnLogs: no tinderbox or no logs')
        return False
    # Bank tiles (and an open bank) refuse firemaking, walk outside first (#278).
    if bank.is_open():
        yield from bank.close()
    log(f'burnLogs: lighting outside near {PA_TILE.LOGS_SPAWN.x},{PA_TILE.LOGS_SPAWN.z}')
    _w7 = yield from traversal.walk_resilient(PA_TILE.LOGS_SPAWN, radius=2, attempts=3, timeout_ms=90000, log=log)
    if not (_w7):
        log('burnLogs: could not reach an outdoor fire tile')
        return False
    yield from settle_scene()
    if not (tinder.use_on(logs)):
        return False

    def ashes_near():
        return ground_items.query().name(PA_ITEM.ASHES.name).within(3).nearest() is not None

    _w8 = yield from execution.delay_until(ashes_near, 150000)
    if not (_w8):
        log('burnLogs: the fire never left any ashes')
        return False
    ash = ground_items.query().name(PA_ITEM.ASHES.name).within(3).nearest()
    if not ash or not (ash.interact('Take')):
        return False
    _result9 = yield from execution.delay_until(lambda: held_item(PA_ITEM.ASHES.id) is not None, 5000)
    return _result9


def make_yellow_dye(log):
    return use_held_on_npc(PA_ITEM.ONION.id, PA_NPC.AGGIE, PA_TILE.AGGIE, lambda: held_item(PA_ITEM.YELLOW_DYE.id) is not None, log)


def dye_wig(log):
    if held_item(PA_ITEM.BLOND_WIG.id):
        return True
    dye = held_item(PA_ITEM.YELLOW_DYE.id)
    wig = held_item(PA_ITEM.PLAIN_WIG.id)
    if not dye or not wig:
        log('dyeWig: no yellow dye or no plain wig')
        return False
    if not (dye.use_on(wig)):
        return False
    _result10 = yield from execution.delay_until(lambda: held_item(PA_ITEM.BLOND_WIG.id) is not None, 8000)
    return _result10
