"""Ported from rs2b0t's src/bot/api/ai/quests/defs/plaguecity/east.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs
from rs2004.items import inventory
from rs2004.quests.defs.plaguecity.areas import PC_ITEM, PC_LOC, PC_NPC, PC_TILE
from rs2004.quests.defs.plaguecity.travel import loc_by_id, walk_to
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.reach import reach

__all__ = ['talk_at', 'start_quest', 'give_dwellberries', 'ask_about_digging', 'pull_the_grill', 'thank_edmond', 'fill_buckets', 'pour_water', 'take_from_house', 'search_cupboard', 'read_scroll', 'tie_rope']

START_PREFER = ["What's happened to her?", 'Can I help find her?']
POURS = 4


def talk_at(npc, near, prefer, log, radius=2):
    _w1 = yield from walk_to(near, radius, log)
    if not (_w1):
        return False
    yield from settle_scene()
    _w2 = yield from reach.npc_dialog(npc, near, log=log)
    if (_w2) != 'done':
        log(f'no dialogue with {npc} near ({near.x},{near.z})')
        return False
    _result3 = yield from talk_strict(npc, prefer, log)
    return _result3


def start_quest(log):
    return talk_at(PC_NPC.EDMOND, PC_TILE.EDMOND, START_PREFER, log)


def give_dwellberries(log):
    return talk_at(PC_NPC.ALRENA, PC_TILE.ALRENA, [], log)


def ask_about_digging(log):
    return talk_at(PC_NPC.EDMOND, PC_TILE.EDMOND, [], log)


def pull_the_grill(log):
    return talk_at(PC_NPC.EDMOND, PC_TILE.SEWER_EDMOND, [], log)


def thank_edmond(log):
    return talk_at(PC_NPC.EDMOND, PC_TILE.EDMOND, ['No problem.'], log)


def fill_buckets(log):
    _w4 = yield from walk_to(PC_TILE.FOUNTAIN, 2, log)
    if not (_w4):
        return False
    yield from settle_scene()
    filled = 0
    while held_id(PC_ITEM.BUCKET.id) > 0 and filled < POURS:
        before = held_id(PC_ITEM.BUCKET_WATER.id)
        fountain = locs.query().name('Fountain').within(8).nearest()
        bucket = ([item for item in inventory.items() if item.id == PC_ITEM.BUCKET.id] or [None])[0]
        if not fountain or not bucket:
            break
        if not (bucket.use_on(fountain)):
            break
        _w5 = yield from execution.delay_until(lambda: held_id(PC_ITEM.BUCKET_WATER.id) > before, 8000)
        if not (_w5):
            break
        filled += 1
    log(f'filled {filled} bucket(s) at the Ardougne fountain')
    return filled > 0


def pour_water(log):
    _w6 = yield from walk_to(PC_TILE.GARDEN, 1, log)
    if not (_w6):
        return False
    yield from settle_scene()
    poured = 0
    while held_id(PC_ITEM.BUCKET_WATER.id) > 0 and poured < POURS:
        before = held_id(PC_ITEM.BUCKET_WATER.id)
        patch = loc_by_id(PC_LOC.MUD_PATCH, None, 6)
        water = ([item for item in inventory.items() if item.id == PC_ITEM.BUCKET_WATER.id] or [None])[0]
        if not patch or not water:
            log('no Mud patch or no Bucket of water in the garden')
            break
        if not (water.use_on(patch)):
            break
        _w7 = yield from drive_until(lambda: held_id(PC_ITEM.BUCKET_WATER.id) < before, [], log, 15000)
        if not (_w7):
            log('the soil took no more water')
            break
        poured += 1
    log(f'poured {poured} bucket(s) onto the garden soil')
    return poured > 0


# Why: both spawns sit behind 2 shut doors, and a plain ground grab clicks Take from the garden, where the server's path search dead-ends and nothing happens.
def take_from_house(item, log):
    if held_id(item.id) > 0:
        return True
    _w8 = yield from walk_to(PC_TILE.HOUSE_FLOOR, 1, log)
    if not (_w8):
        return False
    yield from settle_scene()
    drop = ground_items.query().name(item.name).within(6).nearest()
    if not drop:
        log(f'no {item.name} on the floor of Edmond\'s house')
        return False
    if not (drop.interact('Take')):
        return False
    _result9 = yield from execution.delay_until(lambda: held_id(item.id) > 0, 8000)
    return _result9


# Why: Alrena's cupboard holds a spare mask, the quest's only re-issue for a dropped or destroyed one.
def search_cupboard(log):
    _w10 = yield from walk_to(PC_TILE.CUPBOARD, 1, log)
    if not (_w10):
        return False
    yield from settle_scene()
    open = loc_by_id(PC_LOC.CUPBOARD_OPEN, 'Search', 6)
    if open:
        if not (open.interact('Search')):
            return False
        _result11 = yield from drive_until(lambda: held_id(PC_ITEM.GAS_MASK.id) > 0, [], log, 10000)
        return _result11
    shut = loc_by_id(PC_LOC.CUPBOARD_SHUT, 'Open', 6)
    if not shut or not (shut.interact('Open')):
        log("no cupboard in Alrena's house")
        return False
    _result12 = yield from execution.delay_until(lambda: loc_by_id(PC_LOC.CUPBOARD_OPEN, 'Search', 6) is not None, 6000)
    return _result12


def read_scroll(log):
    scroll = ([item for item in inventory.items() if item.id == PC_ITEM.ARDOUGNE_SCROLL.id] or [None])[0]
    if not scroll:
        return True
    if not (scroll.interact('Read')):
        return False
    learnt = yield from drive_until(lambda: held_id(PC_ITEM.ARDOUGNE_SCROLL.id) == 0, [], log, 10000)
    log(('memorised the Ardougne Teleport scroll' if learnt else 'the magic scroll would not read'))
    return learnt


def tie_rope(log):
    _w13 = yield from walk_to(PC_TILE.SEWER_PIPE, 1, log)
    if not (_w13):
        return False
    yield from settle_scene()
    pipe = loc_by_id(PC_LOC.SEWER_PIPE, None, 8)
    rope = ([item for item in inventory.items() if item.id == PC_ITEM.ROPE.id] or [None])[0]
    if not pipe or not rope:
        log(f"no {('Rope' if pipe else 'Sewer pipe')} for the grill")
        return False
    if not (rope.use_on(pipe)):
        return False
    _result14 = yield from drive_until(lambda: held_id(PC_ITEM.ROPE.id) == 0, [], log, 15000)
    return _result14
