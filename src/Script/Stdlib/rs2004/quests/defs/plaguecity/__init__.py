"""Ported from rs2b0t's src/bot/api/ai/quests/defs/plaguecity/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.plaguecity.areas import PC_ITEM, PC_TILE, held, owned, plague_area, worn
from rs2004.quests.defs.plaguecity.east import ask_about_digging, fill_buckets, give_dwellberries, pour_water, pull_the_grill, read_scroll, search_cupboard, start_quest, thank_edmond, tie_rope
from rs2004.quests.defs.plaguecity.journal import PC_STAGE, read_plague_progress
from rs2004.quests.defs.plaguecity.supplies import BUCKET_TARGET, reclaim, scan_bank, source_bucket, source_chocolate_bar, source_dwellberries, source_milk, source_pestle, source_picture, source_rope, source_shopping_float, source_snape_grass, source_spade, withdraw_from
from rs2004.quests.defs.plaguecity.travel import go_east, go_sewer, go_west
from rs2004.quests.defs.plaguecity.west import ask_about_clearance, ask_milli, ask_parents, enter_rehnisons, get_audience, give_hangover_cure, rescue_elena, show_picture

__all__ = ['decide', 'plaguecity']

KEEP_IDS = [PC_ITEM.get(key).id for key in PC_ITEM.keys()]
TIDY_FLOOR = 4


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


TO_EAST = custom('walk back to East Ardougne', go_east)
TO_WEST = custom('cross into West Ardougne', go_west)
TO_SEWER = custom('drop into the Ardougne sewer', go_sewer)


def tidy(snap, area):
    """Bank spillover before a leg that has to pick something up."""
    if area != 'east' or ((snap.free_slots if snap.free_slots is not None else 28)) >= TIDY_FLOOR:
        return None
    return Record({'kind': 'deposit', 'keep': [], 'keep_ids': KEEP_IDS, 'bank': PC_TILE.BANK})


def source_gas_mask(snap):
    if held(snap, PC_ITEM.GAS_MASK) > 0 or worn(snap, PC_ITEM.GAS_MASK):
        return None
    if not snap.bank_known:
        return scan_bank()
    if owned(snap, PC_ITEM.GAS_MASK) > 0:
        return withdraw_from([{'name': PC_ITEM.GAS_MASK.name, 'id': PC_ITEM.GAS_MASK.id, 'qty': 1}])
    return custom("search Alrena's cupboard for the spare gas mask", search_cupboard)


def west_kit(snap):
    """The kit every crossing into West Ardougne needs: a spade for the garden, a mask for the pipe."""
    _v1 = source_gas_mask(snap)
    return (_v1 if _v1 is not None else source_spade(snap))


def in_east(area, step):
    return (step if area == 'east' else TO_EAST)


def in_sewer(snap, area, step):
    if area == 'sewer':
        return step
    if area != 'east':
        return TO_SEWER
    spade = source_spade(snap)
    return (spade if spade is not None else TO_SEWER)


def in_west(snap, area, step):
    if area == 'west':
        return step
    if area != 'east':
        return TO_WEST
    kit = west_kit(snap)
    return (kit if kit is not None else TO_WEST)


# Why: Collect all four buckets before filling them to avoid three extra fountain trips.
def water_leg(snap, area):
    empty = held(snap, PC_ITEM.BUCKET)
    water = held(snap, PC_ITEM.BUCKET_WATER)
    if water > 0 and empty == 0:
        return in_east(area, custom('pour water on the garden soil', pour_water))
    if water + empty >= BUCKET_TARGET:
        return in_east(area, custom('fill buckets at the Ardougne fountain', fill_buckets))
    more = source_bucket(snap, BUCKET_TARGET - water)
    return in_east(area, (more if more is not None else Record({'kind': 'wait', 'reason': 'no bucket for the garden soil'})))


# Why: the cow field, the snape grass spawns, Taverley and Port Sarim are one eastward loop, so every raw ingredient is gathered before the first mix.
def cure_leg(snap, area):
    if held(snap, PC_ITEM.HANGOVER_CURE) > 0:
        return None
    if held(snap, PC_ITEM.CHOCOLATY_MILK) > 0:
        _v2 = source_snape_grass(snap)
        return in_east(area, (_v2 if _v2 is not None else mix(PC_ITEM.SNAPE_GRASS, PC_ITEM.CHOCOLATY_MILK, PC_ITEM.HANGOVER_CURE)))
    if held(snap, PC_ITEM.CHOCOLATE_DUST) > 0:
        _v3 = source_milk(snap)
        return in_east(area, (_v3 if _v3 is not None else mix(PC_ITEM.CHOCOLATE_DUST, PC_ITEM.BUCKET_MILK, PC_ITEM.CHOCOLATY_MILK)))
    _v4 = source_shopping_float(snap)
    _v5 = (_v4 if _v4 is not None else source_milk(snap))
    _v6 = (_v5 if _v5 is not None else source_snape_grass(snap))
    _v7 = (_v6 if _v6 is not None else source_pestle(snap))
    raw = (_v7 if _v7 is not None else source_chocolate_bar(snap))
    return in_east(area, (raw if raw is not None else mix(PC_ITEM.PESTLE, PC_ITEM.CHOCOLATE_BAR, PC_ITEM.CHOCOLATE_DUST)))


def mix(item, target, product):
    return Record({
        'kind': 'use_on',
        'item': item.name,
        'target_kind': 'item',
        'target': target.name,
        'anchor': PC_TILE.BANK,
        'product': product.name,
    })


def stage_step(snap, area, stage):
    if stage == PC_STAGE.NOT_STARTED:
        _v8 = source_shopping_float(snap)
        return in_east(area, (_v8 if _v8 is not None else custom('ask Edmond about his daughter', start_quest)))
    elif stage == PC_STAGE.STARTED:
        _v9 = source_dwellberries(snap)
        return in_east(area, (_v9 if _v9 is not None else custom('give Alrena the dwellberries', give_dwellberries)))
    elif stage == PC_STAGE.GASMASK:
        return in_east(area, custom('ask Edmond about the way into West Ardougne', ask_about_digging))
    elif stage == PC_STAGE.MUD_START:
        return water_leg(snap, area)
    elif stage == PC_STAGE.MUD_SOFT:
        if area != 'east':
            return TO_SEWER
        _v12 = source_spade(snap)
        _v13 = (_v12 if _v12 is not None else source_rope(snap))
        return (_v13 if _v13 is not None else TO_SEWER)
    elif stage == PC_STAGE.TUNNEL:
        rope = source_rope(snap)
        return (in_east(area, rope) if rope else in_sewer(snap, area, custom('tie the rope to the sewer grill', tie_rope)))
    elif stage == PC_STAGE.ROPE_TIED:
        return in_sewer(snap, area, custom('pull the grill off with Edmond', pull_the_grill))
    elif stage == PC_STAGE.PIPE_OPEN:
        picture = source_picture(snap)
        return (in_east(area, picture) if picture else in_west(snap, area, custom("show Jethick Elena's picture", show_picture)))
    elif stage == PC_STAGE.SHOWN_PICTURE:
        book = reclaim(snap, PC_ITEM.TURNIP_BOOK)
        return (in_east(area, book) if book else in_west(snap, area, custom('get into the Rehnison house and ask about Elena', enter_rehnisons)))
    elif stage == PC_STAGE.RETURNED_BOOK:
        return in_west(snap, area, custom('ask the Rehnisons about Elena', ask_parents))
    elif stage == PC_STAGE.SPOKEN_PARENTS:
        return in_west(snap, area, custom('ask Milli what she saw', ask_milli))
    elif stage == PC_STAGE.SPOKEN_MILLI:
        return in_west(snap, area, custom('ask the mourner about the plague house', ask_about_clearance))
    elif stage in [PC_STAGE.NEED_CLEARANCE, PC_STAGE.SPOKEN_CLERK]:
        return in_west(snap, area, custom('get an audience with Bravek', get_audience))
    elif stage == PC_STAGE.SPOKEN_BRAVEK:
        _v10 = cure_leg(snap, area)
        return (_v10 if _v10 is not None else in_west(snap, area, custom('give Bravek the hangover cure', give_hangover_cure)))
    elif stage == PC_STAGE.CURED_BRAVEK:
        warrant = reclaim(snap, PC_ITEM.WARRANT)
        if warrant:
            return in_east(area, warrant)
        return (in_west(snap, area, custom('free Elena from the plague house', rescue_elena)) if held(snap, PC_ITEM.WARRANT) > 0 else in_west(snap, area, custom('ask Bravek for another warrant', give_hangover_cure)))
    elif stage == PC_STAGE.FREED_ELENA:
        return in_east(area, custom('tell Edmond his daughter is safe', thank_edmond))
    else:
        return Record({'kind': 'wait', 'reason': f'Plague City stage {stage} is not implemented'})


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    area = plague_area(snap.tile)
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'player location unavailable'})
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else -1)) >= PC_STAGE.COMPLETE:
        if area != 'east':
            return TO_EAST
        return (custom('read the Ardougne teleport scroll', read_scroll) if held(snap, PC_ITEM.ARDOUGNE_SCROLL) > 0 else Record({'kind': 'done'}))
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Plague City journal stage unavailable'})
    _v11 = tidy(snap, area)
    return (_v11 if _v11 is not None else stage_step(snap, area, snap.stage))


def exit_plague_city(log):
    _w12 = yield from go_east(log)
    if not (_w12):
        return False
    _result13 = yield from read_scroll(log)
    return _result13


plaguecity = QuestModule(**{
    'record': quest_record('elena'),
    'bank': PC_TILE.BANK,
    'owns_inventory': True,
    'read_progress': read_plague_progress,
    'exit': exit_plague_city,
    'decide': decide,
})
