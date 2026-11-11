"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.fightarena import KIT_KEEP, kit_wanted
from rs2004.quests.defs.fightarena.legs import wear_kit
from rs2004.quests.defs.mortton.areas import SM_ID, SM_NPC, SM_STAGE, SM_TILE
from rs2004.quests.defs.mortton.journal import SM_FLAG, read_mortton_progress
from rs2004.quests.defs.mortton.pyre import lay_remains, light_pyre, DOSES_PER_PYRE_LOG, bodied_pyre, cremate_shade, loaded_pyre, make_pyre_logs
from rs2004.quests.defs.mortton.shades import REMAINS_WANTED, hunt_shade
from rs2004.quests.defs.mortton.supplies import SM_TOOLS, ashes_short, fill_vial, held_id, kit, logs_short, make_ashes, perm_serum_vial_id, recover_pyre_supplies, recover_serum, serums_short
from rs2004.quests.defs.mortton.temple import SANCTITY_TO_SANCTIFY_SERUM, altar_lit, light_altar, repair_temple, sanctify_oil, sanctify_serum, temple_repaired, temple_sanctity
from rs2004.quests.defs.mortton.town import BUILD_SETS, JUNK_IDS, PASTE_PER_SET, RAZMIRE_START_SCRIPT, ULSQUIRE_TEMPLE_SCRIPT, builders_order, drop_down, drop_junk, general_order, handover_and_stock, identify_tarromin, mix_serum, mix_unfinished, read_diary, search_table, sets_that_fit, shop_at_razmire, take_diary, take_vial, visit
from rs2004.quests.engine.types import flag_value

__all__ = ['decide', 'mortton']

SPARE_REMAINS = 2


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


def held(snap, id):
    return held_id(snap, id)


def razmire(script):
    return custom('talk to Razmire', visit(SM_NPC.RAZMIRE, SM_NPC.RAZMIRE_AFFLICTED, SM_TILE.RAZMIRE, script))


def ulsquire(script):
    return custom('talk to Ulsquire', visit(SM_NPC.ULSQUIRE, SM_NPC.ULSQUIRE_AFFLICTED, SM_TILE.ULSQUIRE, script))


def sacred_doses(snap):
    """Doses of sacred oil in the pack; a pyre log wants two."""
    return held(snap, SM_ID.SACRED_OIL4) * 4 + held(snap, SM_ID.SACRED_OIL3) * 3 + held(snap, SM_ID.SACRED_OIL2) * 2 + held(snap, SM_ID.SACRED_OIL1)


def have_oil(snap, made_logs=True):
    """Sacred oil, or the pyre logs it became, or the olive oil it comes from."""
    return (made_logs and held(snap, SM_ID.PYRE_LOGS) > 0) or sacred_doses(snap) >= DOSES_PER_PYRE_LOG or held(snap, SM_ID.OLIVE_OIL4) + held(snap, SM_ID.OLIVE_OIL3) + held(snap, SM_ID.OLIVE_OIL2) > 0


# Why: sanctity is a player varp only this character's building earns, and the shell is world state the shades knock down, so a flame leg can owe material either way.
def needs_temple(snap):
    """True while the flame legs still owe the temple building work."""
    sanctity = flag_value(snap.progress, SM_FLAG.SANCTITY)
    repaired = flag_value(snap.progress, SM_FLAG.REPAIRED)
    return (sanctity if sanctity is not None else 0) < SANCTITY_TO_SANCTIFY_SERUM or (repaired if repaired is not None else 0) < 100


def build_ready(snap):
    """Fresh material for the temple, whether already carried or still in the pool."""
    _v2 = flag_value(snap.progress, SM_FLAG.RESOURCES)
    pool = (_v2 if _v2 is not None else 0)
    carried = min(held(snap, SM_ID.PLANK), held(snap, SM_ID.LIMESTONE_BRICK), (held(snap, SM_ID.SWAMP_PASTE) // 5))
    return carried > 0 or pool > 5


# Why: the shelf, table and 2 vial spawns all sit in Herbi Flax's house and the herb table is a one-shot, so the serum chain runs to completion first.
def serum_leg(snap, stage):
    """The next step toward the serums this quest still owes, or null when it owes none."""
    if stage < SM_STAGE.READ_DIARY or serums_short(snap, stage) == 0:
        return None
    if held(snap, SM_ID.TARROMIN_UNF) > 0:
        return (custom('mix serum 207', mix_serum) if held(snap, SM_ID.ASHES) > 0 else Record({'kind': 'wait', 'reason': 'no ashes for the serum'}))
    if held(snap, SM_ID.TARROMIN) > 0:
        if held(snap, SM_ID.VIAL_WATER) > 0:
            return custom('mix the unfinished potion', mix_unfinished)
        return (custom('fill a vial at the sink', fill_vial) if held(snap, SM_ID.VIAL_EMPTY) > 0 else custom('take an empty vial', take_vial))
    if held(snap, SM_ID.UNID_TARROMIN) > 0:
        return custom('identify the tarromin', identify_tarromin)
    return custom('search the smashed table for herbs', search_table)


def count_of(counts, name):
    count = None if counts is None else counts.get(name.lower())
    return count if count is not None else 0


# Why: 5 shades are killed 150 tiles past the last bank, so the melee kit is drawn on the approach.
def gear_leg(snap):
    """Arm the account from the bank, or null once it is dressed."""
    wanted = kit_wanted(snap)
    if len(wanted) == 0:
        return None
    carried = [name for name in wanted if count_of(snap.inv, name) > 0]
    if len(carried) > 0:
        return custom(f"wear {', '.join(carried)}", lambda log: wear_kit(carried, log))
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    # Nothing in the bank to wear either: fists will have to do.
    banked = [name for name in wanted if count_of(snap.bank, name) > 0]
    return (Record({'kind': 'withdraw', 'items': [({'name': name, 'qty': 1}) for name in banked]}) if len(banked) > 0 else None)


# Why: both counters live behind Razmire's cured face, so anything missing is bought before the leg that needs it; the olive oil waits until the rebuild has spent the 11 slots of plank, brick and paste.
def shop_leg(snap, building, oil, made_logs=True):
    """The next shopping trip at Razmire's counters, or null when the pack is stocked."""
    want_hammer = building and held(snap, SM_ID.HAMMER) == 0
    want_oil = oil and not have_oil(snap, made_logs)
    if want_hammer or want_oil:
        return custom("buy from Razmire's general store", shop_at_razmire(general_order(want_hammer, want_oil)))
    if building and not build_ready(snap):
        sets = sets_that_fit((snap.free_slots if snap.free_slots is not None else 0))
        if sets == 0:
            return Record({'kind': 'wait', 'reason': 'no pack room for building material'})
        return custom('buy temple materials from Razmire', shop_at_razmire(builders_order(sets)))
    return None


# Why: the flame has to be alight before either use-on answers, and sanctifying a vial of serum costs no dose and buys a villager who never reverts.
# Why: the lit altar is `loc_change(templefire_altar, 99)` too, so the oil, which moves the stage, goes in first and the optional serum takes what's left of the flame.
def altar_leg(log):
    """Light the altar, sanctify the oil, and bank a permanent serum against the last conversation."""
    # The shades knock the shell down behind the bot, and only a shell at 100% arms the altar.
    _c3 = temple_repaired() < 100
    if _c3:
        _w4 = yield from repair_temple(log)
        _c3 = not (_w4)
    if _c3:
        return False
    _w5 = yield from light_altar(log)
    if not (_w5):
        return False
    _w6 = yield from sanctify_oil(log)
    if not (_w6):
        return False
    if perm_serum_vial_id() is None and temple_sanctity() >= SANCTITY_TO_SANCTIFY_SERUM:
        if altar_lit() is None:
            yield from light_altar(log)
        yield from sanctify_serum(log)
    return True


def cremate(log):
    laid = yield from lay_remains(log)
    if not laid:
        return laid
    _result = yield from light_pyre(log)
    return _result


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v7 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v7 if _v7 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    if stage >= SM_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    cremating = stage >= SM_STAGE.CREATED_SACRED_OIL and stage < SM_STAGE.LIT_PYRE
    made_logs = stage >= SM_STAGE.CREATED_PYRE_LOGS
    remains_placed = cremating and bodied_pyre() is not None
    logs_placed = remains_placed or (cremating and loaded_pyre() is not None)
    if logs_placed and held(snap, SM_ID.TINDERBOX) > 0 and (remains_placed or held(snap, SM_ID.REMAINS) > 0):
        return custom('cremate the shade', cremate_shade)
    supply_stage = (((SM_STAGE.CREATED_PYRE_LOGS if made_logs else SM_STAGE.CREATED_SACRED_OIL)) if cremating and not logs_placed else stage)
    if cremating:
        recovery = recover_pyre_supplies(snap, made_logs and not logs_placed and held(snap, SM_ID.PYRE_LOGS) == 0, not logs_placed and not have_oil(snap, made_logs), not remains_placed and held(snap, SM_ID.REMAINS) == 0)
        if recovery:
            return recovery
    recovery = recover_serum(snap, supply_stage)
    if recovery:
        return recovery
    supplies = kit(snap, supply_stage)
    if supplies:
        return supplies
    gear = gear_leg(snap)
    if gear:
        return gear
    # Why: the ashes and the pyre log both come from the Varrock spawns, so the burn happens once, before the swamp crossing.
    if ashes_short(snap, supply_stage) > 0 or logs_short(snap, supply_stage) > 0:
        return custom('burn logs for ashes', make_ashes(held(snap, SM_ID.ASHES) + ashes_short(snap, supply_stage), (0 if made_logs and held(snap, SM_ID.PYRE_LOGS) > 0 else 1)))
    if stage == SM_STAGE.NOT_STARTED:
        return (custom("read Herbi Flax's diary", read_diary) if held(snap, SM_ID.DIARY) > 0 else custom("take Herbi Flax's diary", take_diary))
    serum = serum_leg(snap, stage)
    if serum:
        return serum
    # The diary has done its job, and a rotted lobster is a slot the temple load needs.
    if stage >= SM_STAGE.MADE_SERUM and any([held(snap, id) > 0 for id in JUNK_IDS]):
        return custom('drop the diary and the rotten food', drop_junk)
    # Past Ulsquire's study only the pyre wants remains, and a spare covers a failed cremation.
    if stage >= SM_STAGE.SHADES_TO_ULSQUIRE and held(snap, SM_ID.REMAINS) > SPARE_REMAINS:
        return custom('drop the spare remains', lambda log: drop_down([Record({'id': SM_ID.REMAINS, 'keep': SPARE_REMAINS})], log))
    if stage in [SM_STAGE.READ_DIARY, SM_STAGE.MADE_SERUM]:
        return razmire(RAZMIRE_START_SCRIPT)
    elif stage in [SM_STAGE.KILL_SHADES, SM_STAGE.KILLED_1, SM_STAGE.KILLED_2, SM_STAGE.KILLED_3, SM_STAGE.KILLED_4]:
        return custom('hunt a Loar Shade', hunt_shade)
    elif stage == SM_STAGE.KILLED_5:
        if held(snap, SM_ID.REMAINS) < REMAINS_WANTED:
            return custom('hunt a Loar Shade', hunt_shade)
        want_hammer = held(snap, SM_ID.HAMMER) == 0
        # Why: the hammer is one slot and wouldn't fit after 11 slots of material, so it's bought first.
        orders = list((([general_order(True, False)] if want_hammer else []))) + [builders_order(sets_that_fit(((snap.free_slots if snap.free_slots is not None else 0)) - ((1 if want_hammer else 0))))]
        return custom('hand Razmire the remains and stock up', handover_and_stock(orders))
    elif stage == SM_STAGE.SHADES_TO_RAZMIRE:
        shop = shop_leg(snap, True, False)
        return (shop if shop is not None else ulsquire([]))
    elif stage == SM_STAGE.SHADES_TO_ULSQUIRE:
        return ulsquire(ULSQUIRE_TEMPLE_SCRIPT)
    elif stage in [SM_STAGE.ULSQUIRE_TEMPLE, SM_STAGE.REBUILD_TEMPLE]:
        shop = shop_leg(snap, True, False)
        return (shop if shop is not None else custom('rebuild the Flamtaer temple', repair_temple))
    elif stage == SM_STAGE.CAN_LIGHT_ALTAR:
        shop = shop_leg(snap, needs_temple(snap), True)
        return (shop if shop is not None else custom('light the altar and sanctify the oil', altar_leg))
    elif stage in [SM_STAGE.CREATED_SACRED_OIL, SM_STAGE.CREATED_PYRE_LOGS, SM_STAGE.LOGS_ON_PYRE]:
        if not remains_placed and held(snap, SM_ID.REMAINS) == 0:
            return custom('hunt a Loar Shade', hunt_shade)
        if logs_placed or (made_logs and held(snap, SM_ID.PYRE_LOGS) > 0):
            return custom('cremate the shade', cremate_shade)
        if sacred_doses(snap) >= DOSES_PER_PYRE_LOG:
            return custom('soak the logs in sacred oil', make_pyre_logs)
        shop = shop_leg(snap, needs_temple(snap), True, made_logs=made_logs)
        if shop:
            return shop
        return custom('sanctify more oil in the flame', altar_leg)
    elif stage == SM_STAGE.LIT_PYRE:
        return ulsquire([])
    else:
        return Record({'kind': 'wait', 'reason': f'unmapped stage {stage}'})


def warn_readiness():
    return (f"Mort'ton is proven at 70s: {BUILD_SETS} sets of plank, brick and {PASTE_PER_SET} paste rebuild"
            + ' the temple at Crafting 70, and lower Crafting spends more of the pool per wall.')


mortton = QuestModule(**{
    'record': quest_record('mortton'),
    # Varrock for the approach, Canifis for anything Morytania forces a restock of.
    'bank': 'nearest',
    'tools': list(SM_TOOLS) + list(KIT_KEEP),
    'owns_inventory': True,
    'read_progress': read_mortton_progress,
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'warn_readiness': warn_readiness,
    'decide': decide,
})
