"""Ported from rs2b0t's src/bot/api/ai/quests/defs/elementalworkshop/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.defs.elementalworkshop.areas import EW_ITEM, KNIFE_SPAWN, SEERS_BANK, ew_area
from rs2004.quests.defs.elementalworkshop.journal import ELEMENTAL_WORKSHOP_QUEST, EW_FLAG, EW_STAGE, parse_elemental_workshop_journal, read_elemental_workshop_progress
from rs2004.quests.defs.elementalworkshop.supplies import COAL_NEED, EW_FAILED_COMBAT, EW_OFFICIAL_SKILLS, EW_PROBE_COMBAT, EW_PROVEN_COMBAT_FLOOR, EW_RECOMMENDED_COMBAT, EW_TESTED_COMBAT, FOOD_WITHDRAW, best_bank_weapon, best_held_pickaxe, from_bank, has_held_slash_tool, has_pickaxe, has_slash_tool, has_weapon, held, surface_loadout, warn_elemental_workshop_readiness
from rs2004.quests.defs.elementalworkshop.workshop import enter_workshop, fix_bellows, leave_workshop, light_furnace, mine_elemental_ore, read_battered_book, search_bookcase, search_crates_for, slash_book_for_key, smelt_elemental_bar, smith_elemental_shield, start_water_wheel
from rs2004.quests.engine.types import QuestModule, has_flag

__all__ = ['decide', 'elementalworkshop', 'parse_elemental_workshop_journal', 'EW_STAGE', 'EW_FLAG', 'ELEMENTAL_WORKSHOP_QUEST', 'ew_area', 'EW_ITEM', 'SEERS_BANK', 'held', 'has_pickaxe', 'has_held_slash_tool', 'has_slash_tool', 'has_weapon', 'COAL_NEED', 'FOOD_WITHDRAW', 'EW_OFFICIAL_SKILLS', 'EW_PROVEN_COMBAT_FLOOR', 'EW_FAILED_COMBAT', 'EW_PROBE_COMBAT', 'EW_TESTED_COMBAT', 'EW_RECOMMENDED_COMBAT', 'warn_elemental_workshop_readiness', 'surface_loadout']

def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


def need_smelt_materials(snap):
    return held(snap, EW_ITEM.ELEMENTAL_METAL.id) == 0 and held(snap, EW_ITEM.ELEMENTAL_SHIELD.id) == 0


def need_bellows_work(snap):
    return not has_flag(snap.progress, EW_FLAG.BELLOWS)


def need_water_work(snap):
    return not has_flag(snap.progress, EW_FLAG.WATER)


def need_furnace_work(snap):
    return not has_flag(snap.progress, EW_FLAG.FURNACE)


def source_knife(snap):
    # useOn needs a pack item; worn doesn't count (slashBookForKey unequips if needed).
    if held(snap, EW_ITEM.BATTERED_KEY.id) > 0 or has_held_slash_tool(snap):
        return None
    # Bank first (knife or any slash weapon from e.g. bank_f2p / realistic seed), then ground.
    bank_weapon = best_bank_weapon(snap)
    _v1 = from_bank(snap, EW_ITEM.KNIFE, 1)
    _v2 = (_v1 if _v1 is not None else ((from_bank(snap, bank_weapon, 1) if bank_weapon else None)))
    return (_v2 if _v2 is not None else Record({'kind': 'grab_ground', 'item': EW_ITEM.KNIFE.name, 'anchor': KNIFE_SPAWN, 'wait_if_missing': True}))


# Why: the flow runs not started, bookcase, read book, knife, slash for key, surface loadout, enter workshop, water valves and lever, crate supplies, fix bellows, light furnace, mine ore, smelt (air lever and furnace), smith shield.
def decide(snap):
    """Pure decide over journal stage, flags and held items; never reads varps."""
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    _v3 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v3 if _v3 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Elemental Workshop stage unavailable'})
    if stage == EW_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    area = ew_area(snap.tile)
    # Start: book
    if stage == EW_STAGE.NOT_STARTED:
        if held(snap, EW_ITEM.BATTERED_BOOK.id) == 0:
            if area == 'workshop':
                return custom('leave workshop for the bookcase', leave_workshop)
            _v4 = from_bank(snap, EW_ITEM.BATTERED_BOOK, 1)
            return (_v4 if _v4 is not None else custom('search Seers bookcase for the Battered book', search_bookcase))
        return custom('read the Battered book', read_battered_book)
    # Key from book spine
    if held(snap, EW_ITEM.BATTERED_KEY.id) == 0 and stage < EW_STAGE.ENTERED:
        if held(snap, EW_ITEM.BATTERED_BOOK.id) == 0:
            _v5 = from_bank(snap, EW_ITEM.BATTERED_BOOK, 1)
            return (_v5 if _v5 is not None else custom('search Seers bookcase for the Battered book', search_bookcase))
        knife = source_knife(snap)
        if knife:
            return knife
        return custom('slash the Battered book for the key', slash_book_for_key)
    # Once we have the bar or shield, finish at the workbench (or leave if missing tools).
    if held(snap, EW_ITEM.ELEMENTAL_SHIELD.id) > 0:
        # Making the shield completes the quest server-side; wait for journal.
        return Record({'kind': 'wait', 'reason': 'waiting for Elemental Workshop quest complete'})
    if held(snap, EW_ITEM.ELEMENTAL_METAL.id) > 0:
        if area != 'workshop':
            if held(snap, EW_ITEM.BATTERED_BOOK.id) == 0 or held(snap, EW_ITEM.HAMMER.id) == 0:
                load = surface_loadout(snap, False, False)
                if load:
                    return load
            return custom('re-enter the workshop to smith the shield', enter_workshop)
        if held(snap, EW_ITEM.BATTERED_BOOK.id) == 0:
            return custom('leave workshop for the Battered book', leave_workshop)
        if held(snap, EW_ITEM.HAMMER.id) == 0:
            return custom('leave workshop for a Hammer', leave_workshop)
        return custom('smith the Elemental shield', smith_elemental_shield)
    # Surface provisioning before first entry (and when forced out for missing tools / death).
    if area != 'workshop':
        # First open needs the Battered key. After ENTERED, Push works without it
        # (death piles often leave the key in Lumbridge, re-bank/withdraw if held).
        if held(snap, EW_ITEM.BATTERED_KEY.id) == 0:
            bank_key = from_bank(snap, EW_ITEM.BATTERED_KEY, 1)
            if bank_key:
                return bank_key
            if stage < EW_STAGE.ENTERED:
                return Record({'kind': 'wait', 'reason': 'need the Battered key to open the smithy wall'})
        # Before entered, journal has no machinery flags, assume all workshop work remains.
        bellows = stage < EW_STAGE.ENTERED or need_bellows_work(snap)
        smelt = stage < EW_STAGE.ENTERED or need_smelt_materials(snap)
        load = surface_loadout(snap, bellows, smelt)
        if load:
            return load
        if not has_pickaxe(snap) and need_smelt_materials(snap):
            return Record({'kind': 'wait', 'reason': 'need a pickaxe before entering the Elemental Workshop'})
        return custom('enter the Elemental Workshop', enter_workshop)
    # Inside workshop
    if need_water_work(snap):
        return custom('start the water wheel', start_water_wheel)
    if need_bellows_work(snap):
        need_leather = held(snap, EW_ITEM.LEATHER.id) == 0
        need_needle = held(snap, EW_ITEM.NEEDLE.id) == 0
        if need_leather or need_needle:
            return custom('search crates for leather/needle', lambda log: search_crates_for(Record({'bowl': False, 'leather': need_leather, 'needle': need_needle}), log))
        if held(snap, EW_ITEM.THREAD.id) == 0:
            return custom('leave workshop for Thread', leave_workshop)
        return custom('fix the bellows', fix_bellows)
    if need_furnace_work(snap):
        if held(snap, EW_ITEM.STONE_BOWL.id) == 0 and held(snap, EW_ITEM.STONE_BOWL_FULL.id) == 0:
            return custom('search crates for a stone bowl', lambda log: search_crates_for(Record({'bowl': True, 'leather': False, 'needle': False}), log))
        return custom('light the furnace with lava', light_furnace)
    # Mine / smelt
    if held(snap, EW_ITEM.ELEMENTAL_ORE.id) == 0:
        if not has_pickaxe(snap) and not best_held_pickaxe(snap):
            return custom('leave workshop for a pickaxe', leave_workshop)
        return custom('mine Elemental ore from the Earth elemental', mine_elemental_ore)
    if held(snap, EW_ITEM.COAL.id) < COAL_NEED:
        return custom('leave workshop for Coal', leave_workshop)
    return custom('smelt Elemental metal at the furnace', smelt_elemental_bar)


elementalworkshop = QuestModule(**{
    'record': quest_record('elemental_workshop'),
    'bank': SEERS_BANK,
    'owns_inventory': True,
    'tools': ['knife', 'hammer', 'needle', 'thread', 'leather', 'coal', 'battered book', 'battered key'],
    'read_progress': read_elemental_workshop_progress,
    'sustain': Record({'foods': ['Swordfish', 'Lobster', 'Salmon', 'Trout'], 'eat_below_hp': 0.45}),
    'warn_readiness': warn_elemental_workshop_readiness,
    'decide': decide,
})
