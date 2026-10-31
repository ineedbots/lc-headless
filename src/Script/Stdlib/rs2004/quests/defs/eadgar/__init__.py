"""Ported from rs2b0t's src/bot/api/ai/quests/defs/eadgar/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.eadgar.areas import BURNTMEAT_TALK, EADGAR_TALK, ER_ITEM, SANFEW_FINISH, SANFEW_START, TEGID_ROBE, banked, committed, eadgar_zone, held
from rs2004.quests.defs.eadgar.journal import EADGAR_FLAG, EADGAR_QUEST, EADGAR_STAGE, SCARECROW_NEED, parse_eadgar_journal, read_eadgar_progress
from rs2004.quests.defs.eadgar.parrot import source_parrot
from rs2004.quests.defs.eadgar.storeroom import retrieve_parrot, take_goutweed, take_storeroom_key, unlock_storeroom
from rs2004.quests.defs.eadgar.supplies import SCARECROW_FOOD_TARGET, food_names, prepare, scan_bank, source_axe, source_chickens, source_grain, source_logs, withdraw
from rs2004.quests.defs.eadgar.travel import guarded, guarded_talk
from rs2004.quests.defs.eadgar.trollheim import free_eadgar, hide_parrot, source_troll_potion
from rs2004.quests.defs.trollstronghold.journal import TROLL_QUEST
from rs2004.quests.engine.types import flag_value, has_flag
from rs2004.tabs import quests

__all__ = ['EADGAR_FLAG', 'EADGAR_QUEST', 'EADGAR_STAGE', 'parse_eadgar_journal', 'read_eadgar_progress', 'eadgar_zone', 'committed', 'decide', 'eadgar']

HERBLORE_REQ = 31


def scarecrow_need(snap, stage):
    """What the scarecrow still wants, read from the journal at stage 70 and assumed complete before it."""
    if stage != EADGAR_STAGE.NEEDS_ITEMS:
        return Record({'logs': SCARECROW_NEED.logs, 'chickens': SCARECROW_NEED.chickens, 'grain': SCARECROW_NEED.grain})
    _v1 = flag_value(snap.progress, EADGAR_FLAG.NEED_CHICKENS)
    _v2 = flag_value(snap.progress, EADGAR_FLAG.NEED_GRAIN)
    return Record({
        'logs': (1 if has_flag(snap.progress, EADGAR_FLAG.NEED_LOGS) else 0),
        'chickens': (_v1 if _v1 is not None else 0),
        'grain': (_v2 if _v2 is not None else 0),
    })


# Why: the food float only shrinks while the grain and chickens are still filling the pack; holding it down for the rest of stage 70 sends you up the thrower gauntlet on 4 lobsters, which killed 3 runs.
def scarecrow_slots(snap, stage):
    """Pack slots the scarecrow still has to fill."""
    need = scarecrow_need(snap, stage)
    return need.logs + need.chickens + need.grain


SCARECROW_SLOT_SLACK = 4


def source_scarecrow(snap, stage):
    """Fetch whatever the scarecrow is still short of. Null once the pack can satisfy the turn-in."""
    need = scarecrow_need(snap, stage)
    _v3 = ((source_logs(snap, need.logs) if need.logs > 0 else None))
    _v4 = (_v3 if _v3 is not None else ((source_chickens(snap, need.chickens) if need.chickens > 0 else None)))
    return (_v4 if _v4 is not None else ((source_grain(snap, need.grain) if need.grain > 0 else None)))


# Why: Tegid only parts with a robe at stage 70 when neither the pack nor the bank holds one, so a banked robe has to come out first.
def source_robe(snap):
    if not has_flag(snap.progress, EADGAR_FLAG.NEED_CLOTHES) or held(snap, ER_ITEM.DIRTY_ROBE) > 0:
        return None
    if not snap.bank_known:
        return scan_bank(snap)
    if banked(snap, ER_ITEM.DIRTY_ROBE) > 0:
        return withdraw(snap, [{'name': ER_ITEM.DIRTY_ROBE.name, 'id': ER_ITEM.DIRTY_ROBE.id, 'qty': 1}])
    return Record({'kind': 'talk', 'stop': TEGID_ROBE})


def parrot_in_hand(snap):
    """The parrot Eadgar wants back in hand before it can be hidden."""
    if held(snap, ER_ITEM.DRUNK_PARROT) > 0:
        return None
    if not snap.bank_known:
        return scan_bank(snap)
    if banked(snap, ER_ITEM.DRUNK_PARROT) > 0:
        return withdraw(snap, [{'name': ER_ITEM.DRUNK_PARROT.name, 'id': ER_ITEM.DRUNK_PARROT.id, 'qty': 1}])
    # Eadgar replaces the item when neither inventory nor bank has one.
    return Record({'kind': 'talk', 'stop': EADGAR_TALK})


# Why: Burntmeat consumes only the carried dummy, and Eadgar supplies replacements.
def fake_man_in_hand(snap):
    if held(snap, ER_ITEM.FAKE_MAN) > 0:
        return None
    if not snap.bank_known:
        return scan_bank(snap)
    if banked(snap, ER_ITEM.FAKE_MAN) > 0:
        return withdraw(snap, [{'name': ER_ITEM.FAKE_MAN.name, 'id': ER_ITEM.FAKE_MAN.id, 'qty': 1}])
    return Record({'kind': 'talk', 'stop': EADGAR_TALK})


def source_storeroom_key(snap):
    if held(snap, ER_ITEM.STOREROOM_KEY) > 0:
        return None
    if snap.bank_known and banked(snap, ER_ITEM.STOREROOM_KEY) > 0:
        return withdraw(snap, [{'name': ER_ITEM.STOREROOM_KEY.name, 'id': ER_ITEM.STOREROOM_KEY.id, 'qty': 1}])
    return guarded('search the kitchen drawers for the storeroom key', take_storeroom_key)


def decide(snap):
    _v5 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v5 if _v5 is not None else snap.stage)
    if snap.journal == 'complete' or ((stage if stage is not None else 0)) >= EADGAR_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if stage is None:
        return Record({'kind': 'wait', 'reason': "Eadgar's Ruse journal stage unavailable"})
    if stage == EADGAR_STAGE.NOT_STARTED and quests.status(TROLL_QUEST) != 'complete':
        return Record({'kind': 'wait', 'reason': "Troll Stronghold must be complete before Eadgar's Ruse"})
    zone = eadgar_zone(snap.tile)

    def prep(food_want=None):
        return prepare(snap, zone, food_want)

    # Why: every Eadgar leg walks into a cave he is only standing in once his cell has been opened.
    if not has_flag(snap.progress, EADGAR_FLAG.EADGAR_FREED):
        _v6 = prep()
        return (_v6 if _v6 is not None else guarded('free Mad Eadgar from the troll prison', free_eadgar))
    if stage == EADGAR_STAGE.NOT_STARTED:
        _v7 = prep()
        return (_v7 if _v7 is not None else Record({'kind': 'talk', 'stop': SANFEW_START}))
    elif stage == EADGAR_STAGE.STARTED:
        _v8 = prep()
        return (_v8 if _v8 is not None else guarded_talk(EADGAR_TALK))
    elif stage == EADGAR_STAGE.SPOKE_EADGAR:
        _v9 = prep()
        return (_v9 if _v9 is not None else guarded_talk(BURNTMEAT_TALK))
    elif stage in [EADGAR_STAGE.SPOKE_BURNTMEAT_FIRST, EADGAR_STAGE.SPOKE_BURNTMEAT]:
        _v10 = prep()
        return (_v10 if _v10 is not None else guarded_talk(EADGAR_TALK))
    elif stage == EADGAR_STAGE.NEEDS_PARROT:
        _v11 = prep()
        _v12 = (_v11 if _v11 is not None else source_axe(snap))
        _v13 = (_v12 if _v12 is not None else source_parrot(snap))
        return (_v13 if _v13 is not None else guarded_talk(EADGAR_TALK))
    elif stage == EADGAR_STAGE.EXPLAINED_PLAN:
        _v14 = prep()
        _v15 = (_v14 if _v14 is not None else parrot_in_hand(snap))
        return (_v15 if _v15 is not None else guarded('hide the parrot under the prison rack', hide_parrot))
    elif stage in [EADGAR_STAGE.HID_PARROT, EADGAR_STAGE.NEEDS_ITEMS]:
        _v16 = prep((SCARECROW_FOOD_TARGET if scarecrow_slots(snap, stage) > SCARECROW_SLOT_SLACK else None))
        _v17 = (_v16 if _v16 is not None else ((source_robe(snap) if stage == EADGAR_STAGE.NEEDS_ITEMS else None)))
        _v18 = (_v17 if _v17 is not None else source_scarecrow(snap, stage))
        return (_v18 if _v18 is not None else guarded_talk(EADGAR_TALK))
    elif stage == EADGAR_STAGE.NEEDS_POTION:
        _v19 = prep()
        _v20 = (_v19 if _v19 is not None else source_troll_potion(snap))
        return (_v20 if _v20 is not None else guarded_talk(EADGAR_TALK))
    elif stage == EADGAR_STAGE.NEEDS_PARROT_BACK:
        _v21 = prep()
        return (_v21 if _v21 is not None else guarded('fetch the parrot back from under the rack', retrieve_parrot))
    elif stage == EADGAR_STAGE.GOT_PARROT_BACK:
        _v22 = prep()
        return (_v22 if _v22 is not None else guarded_talk(EADGAR_TALK))
    elif stage == EADGAR_STAGE.GOT_FAKE_MAN:
        _v23 = prep()
        _v24 = (_v23 if _v23 is not None else fake_man_in_hand(snap))
        return (_v24 if _v24 is not None else guarded_talk(BURNTMEAT_TALK))
    elif stage == EADGAR_STAGE.GOT_BURNT_MEAT:
        _v25 = prep()
        _v26 = (_v25 if _v25 is not None else source_storeroom_key(snap))
        return (_v26 if _v26 is not None else guarded('unlock the troll storeroom', unlock_storeroom))
    elif stage == EADGAR_STAGE.UNLOCKED_STOREROOM:
        if held(snap, ER_ITEM.GOUTWEED) > 0:
            return Record({'kind': 'talk', 'stop': SANFEW_FINISH})
        # Why: Sanfew reads the goutweed out of the pack, so a banked one still finishes the quest.
        if snap.bank_known and banked(snap, ER_ITEM.GOUTWEED) > 0:
            return withdraw(snap, [{'name': ER_ITEM.GOUTWEED.name, 'id': ER_ITEM.GOUTWEED.id, 'qty': 1}])
        _v27 = prep()
        return (_v27 if _v27 is not None else guarded('take goutweed from the storeroom crate', take_goutweed))
    else:
        return Record({'kind': 'wait', 'reason': f'unrecognized Eadgar\'s Ruse stage {stage}'})


def warn_eadgar_readiness():
    bits = []
    if skills.level('herblore') < HERBLORE_REQ:
        bits.append(f'Herblore {HERBLORE_REQ} is required — Sanfew will not hand out the quest below it')
    if skills.level('agility') < 15:
        bits.append('Agility 15 is required for the Trollheim climbing rocks')
    if skills.level('thieving') < 30:
        bits.append('Thieving 30 is what steals Cell key 2 if Mad Eadgar still needs freeing')
    combat = min(skills.level('attack'), skills.level('strength'), skills.level('defence'))
    if combat < 40 or skills.level('hitpoints') < 40:
        bits.append(f"combat looks light for the troll pass (att/str/def≈{combat}, hp={skills.level('hitpoints')})")
    return (f"Eadgar's Ruse: {'; '.join(bits)}" if len(bits) > 0 else None)


def observe(snap, step):
    _v28 = (snap.progress.stage if snap.progress is not None else None)
    _v29 = (_v28 if _v28 is not None else snap.stage)
    need = scarecrow_need(snap, (_v29 if _v29 is not None else -1))
    _v30 = (snap.progress.flags if snap.progress is not None else None)
    return [
        f"zone={eadgar_zone(snap.tile)} flags=[{', '.join(list(((_v30 if _v30 is not None else []))))}]",
        f'scarecrow still wants logs={need.logs} chickens={need.chickens} grain={need.grain}',
        f'step={step.kind}',
    ]


eadgar = QuestModule(**{
    'record': quest_record('eadgar'),
    'bank': 'nearest',
    'grind': ['Chicken'],
    'tools': [ER_ITEM.get(key).name.lower() for key in ER_ITEM.keys()] + [name.lower() for name in food_names()],
    'owns_inventory': True,
    'read_progress': read_eadgar_progress,
    'sustain': Record({'foods': food_names(), 'eat_below_hp': 0.7}),
    'warn_readiness': warn_eadgar_readiness,
    'observe': observe,
    'decide': decide,
})
