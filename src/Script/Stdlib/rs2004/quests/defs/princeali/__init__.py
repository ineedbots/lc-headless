"""Ported from rs2b0t's src/bot/api/ai/quests/defs/princeali/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import QUESTS
from rs2004.quests.defs.princeali.areas import HASSAN_REWARD, HASSAN_START, LEELA_STOP, OSMAN_BRIEF, PA_TILE
from rs2004.quests.defs.princeali.disguise import disguise_complete, make_ashes, make_blond_wig, make_paste, source_onions, source_paste_goods, source_pink_skirt, source_shears, source_tinderbox, source_wool
from rs2004.quests.defs.princeali.jailbreak import decide_jailbreak, source_beers, source_ropes
from rs2004.quests.defs.princeali.journal import PRINCE_STAGE, read_prince_progress
from rs2004.quests.defs.princeali.key import collect_key, have_key, make_soft_clay, source_bronze_bar, source_clay, source_pickaxe, source_water, take_key_print
from rs2004.quests.defs.princeali.supplies import PURSE_FLOOR, PURSE_TOP, scan_bank, source_coins
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.exec.primitives import goto_npc, talk_strict


__all__ = ['decide', 'princeali']

# Why: top to bottom this is the route: Al-Kharid, Lumbridge, Varrock, Rimmington and Port Sarim, Draynor, Lady Keli, Osman.
# Why: each leg returns null once it is satisfied, so a resumed run rejoins the tour wherever it left off.
PREP = [
    source_bronze_bar,
    source_water,
    source_tinderbox,
    source_shears,
    source_onions,
    source_wool,
    source_pink_skirt,
    source_pickaxe,
    source_clay,
    source_paste_goods,
    source_beers,
    make_ashes,
    make_blond_wig,
    make_paste,
    source_ropes,
    make_soft_clay,
    take_key_print,
    collect_key,
]


def prep_leg(snap):
    for leg in PREP:
        step = leg(snap)
        if step:
            return step
    return None


def leela_handover(log):
    _w1 = yield from goto_npc(LEELA_STOP, [], log)
    if not (_w1):
        return False
    _result2 = yield from talk_strict(LEELA_STOP.npc, LEELA_STOP.prefer, log)
    return _result2


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else -1)) >= PRINCE_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Prince Ali Rescue journal stage unavailable'})
    if not snap.bank_known:
        return scan_bank()
    # Why: Al-Kharid is reachable only through the 10gp toll gate or the Shantay Pass, and the walker pre-avoids a crossing it cannot pay for.
    # Why: Hassan and Osman are both behind it, so the purse comes before the first step that walks anywhere.
    # Why: completing the quest makes the gate free, hence the stage bound.
    if stage < PRINCE_STAGE.SAVED:
        purse = source_coins(snap, PURSE_FLOOR, PURSE_TOP)
        if purse:
            return purse
    if stage == PRINCE_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': HASSAN_START})
    elif stage == PRINCE_STAGE.STARTED:
        return Record({'kind': 'talk', 'stop': OSMAN_BRIEF})
    elif stage == PRINCE_STAGE.SPOKEN_OSMAN:
        prep = prep_leg(snap)
        if prep:
            return prep
        if not have_key(snap) or not disguise_complete(snap):
            return Record({
                'kind': 'wait',
                'reason': 'every prep leg is satisfied but the disguise or key is not in the pack',
            })
        return Record({'kind': 'custom', 'name': 'show Leela the disguise and collect the key', 'run': leela_handover})
    elif stage in [PRINCE_STAGE.PREP_FINISHED, PRINCE_STAGE.GUARD_DRUNK, PRINCE_STAGE.TIED_KELI]:
        _v3 = prep_leg(snap)
        return (_v3 if _v3 is not None else decide_jailbreak(snap))
    elif stage == PRINCE_STAGE.SAVED:
        return Record({'kind': 'talk', 'stop': HASSAN_REWARD})
    else:
        return Record({'kind': 'wait', 'reason': f'Prince Ali Rescue stage {stage} is not implemented'})


princeali = QuestModule(**{
    'record': ([record for record in QUESTS if record.id == 'prince'] or [None])[0],
    'bank': PA_TILE.DRAYNOR_BANK,
    'owns_inventory': True,
    'read_progress': read_prince_progress,
    'decide': decide,
})
