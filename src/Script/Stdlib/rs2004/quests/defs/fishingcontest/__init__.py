"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fishingcontest/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import banked_id, held_id
from rs2004.quests.defs.fishingcontest.areas import FC_ID, in_compound
from rs2004.quests.defs.fishingcontest.contest import claim_spare_trophy, deliver_trophy, fish_at_pipes, hand_over_catch, leave_compound, pay_entry_fee, start_quest, stash_garlic
from rs2004.quests.defs.fishingcontest.journal import FC_STAGE, read_fishing_contest_stage
from rs2004.quests.defs.fishingcontest.supplies import ITEM, source_fee, source_garlic, source_pass, source_rod, source_spade, source_worms, WORM_TARGET
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['decide', 'fishingcontest']

# Why: Outbound crossing opens dialogue that the generic door handler cannot continue.
def outside(snap, step):
    """Any leg that leaves Hemenster has to go through the gate first."""
    if step is None or not in_compound(snap.tile):
        return step
    return Record({'kind': 'custom', 'name': 'leave the competition ground', 'run': leave_compound})


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Fishing Contest journal stage unavailable'})
    if stage == FC_STAGE.NOT_STARTED:
        _v1 = source_garlic(snap)
        _v2 = (_v1 if _v1 is not None else source_spade(snap))
        return (_v2 if _v2 is not None else Record({'kind': 'custom', 'name': 'ask the Mountain Dwarf for the competition pass', 'run': start_quest}))
    elif stage == FC_STAGE.STARTED:
        _v3 = source_pass(snap)
        _v4 = (_v3 if _v3 is not None else source_garlic(snap))
        _v5 = (_v4 if _v4 is not None else source_rod(snap))
        _v6 = (_v5 if _v5 is not None else source_worms(snap, WORM_TARGET))
        _v7 = outside(snap, (_v6 if _v6 is not None else source_fee(snap)))
        return (_v7 if _v7 is not None else Record({'kind': 'custom', 'name': 'pay Bonzo the contest entry fee', 'run': pay_entry_fee}))
    elif stage == FC_STAGE.IN_COMP:
        if held_id(snap, FC_ID.GARLIC) > 0:
            return Record({'kind': 'custom', 'name': 'stash the garlic in the wall pipe', 'run': stash_garlic})
        if held_id(snap, FC_ID.RAW_SARDINE) > 0:
            return Record({'kind': 'custom', 'name': 'hand the sardines to Bonzo and re-enter', 'run': hand_over_catch})
        _v8 = source_pass(snap)
        _v9 = outside(snap, (_v8 if _v8 is not None else source_garlic(snap)))
        return (_v9 if _v9 is not None else Record({'kind': 'wait', 'reason': 'the willow spot cannot win and there is no garlic to move the stranger'}))
    elif stage == FC_STAGE.GARLIC_COMP:
        _v10 = source_pass(snap)
        _v11 = (_v10 if _v10 is not None else source_rod(snap))
        _v12 = outside(snap, (_v11 if _v11 is not None else source_worms(snap, 1)))
        return (_v12 if _v12 is not None else Record({'kind': 'custom', 'name': 'fish the contest beside the pipes', 'run': fish_at_pipes}))
    elif stage == FC_STAGE.WON_COMP:
        if held_id(snap, FC_ID.TROPHY) > 0:
            return Record({'kind': 'custom', 'name': 'take the trophy to the Mountain Dwarf', 'run': deliver_trophy})
        banked = (Record({'kind': 'withdraw', 'items': [{'name': ITEM.TROPHY, 'qty': 1, 'id': FC_ID.TROPHY}]}) if banked_id(snap, FC_ID.TROPHY) > 0 else None)
        _v13 = outside(snap, (banked if banked is not None else source_pass(snap)))
        return (_v13 if _v13 is not None else Record({'kind': 'custom', 'name': 'ask Bonzo for a spare trophy', 'run': claim_spare_trophy}))
    else:
        return Record({'kind': 'wait', 'reason': f'no leg for Fishing Contest stage {stage}'})


fishingcontest = QuestModule(**{
    'record': quest_record('fishingcompo'),
    'bank': 'nearest',
    'food': 8,
    'tools': [
    'fishing pass',
    'garlic',
    'fishing rod',
    'spade',
    'red vine worm',
    'fishing trophy',
    'raw giant carp',
    'coins',
],
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'read_stage': read_fishing_contest_stage,
    'warn_readiness': lambda: 'Fishing Contest walks over White Wolf Mountain — its level 64 and 73 wolves stay aggressive below 146 combat',
    'decide': decide,
})
