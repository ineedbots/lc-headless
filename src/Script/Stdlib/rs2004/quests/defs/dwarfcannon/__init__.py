"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dwarfcannon/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.defs.dwarfcannon.areas import CAVE_HOPS, COMMANDER, COMMANDER_INSPECT, FALADOR_WEST_BANK, MC_FOOD_TARGET, MC_OBJ, NULODION
from rs2004.quests.defs.dwarfcannon.journal import MC_FLAG, MC_STAGE, read_dwarf_cannon_progress
from rs2004.quests.defs.dwarfcannon.repair import fetch_remains, fix_railings, in_cave, repair_cannon, rescue_child
from rs2004.quests.engine.types import has_flag, held_id
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['decide', 'dwarfcannon']

def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


def decide(snap):
    _v1 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v1 if _v1 is not None else snap.stage)
    if snap.journal == 'complete' or ((stage if stage is not None else 0)) >= MC_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Dwarf Cannon journal stage unavailable'})
    if stage == MC_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': COMMANDER})
    if stage == MC_STAGE.RAILINGS:
        return (Record({'kind': 'talk', 'stop': COMMANDER}) if has_flag(snap.progress, MC_FLAG.RAILINGS_DONE) else custom('replace the six broken railings', fix_railings))
    if stage == MC_STAGE.GUARD_TOWER:
        return (Record({'kind': 'talk', 'stop': COMMANDER}) if held_id(snap, MC_OBJ.REMAINS.id) > 0 else custom('take the dwarf remains from the watchtower', fetch_remains))
    if stage == MC_STAGE.GOBLIN_CAVE or stage == MC_STAGE.FIND_CHILD:
        return custom("search the goblin cave crate for Gilob's son", lambda log: rescue_child(False, log))
    if stage == MC_STAGE.CHILD_RESCUED:
        return (custom('leave the goblin cave by the mud pile', lambda log: rescue_child(True, log)) if in_cave(snap.tile) else Record({'kind': 'talk', 'stop': COMMANDER}))
    if stage == MC_STAGE.FIX_CANNON:
        # Why: The Commander replaces lost toolkits at stages 6 and 7.
        return (custom('repair the broken multicannon', repair_cannon) if held_id(snap, MC_OBJ.TOOLKIT.id) > 0 else Record({'kind': 'talk', 'stop': COMMANDER}))
    if stage == MC_STAGE.CANNON_FIXED:
        return Record({'kind': 'talk', 'stop': COMMANDER_INSPECT})
    if stage == MC_STAGE.SEE_NULODION:
        return Record({'kind': 'talk', 'stop': NULODION})
    if stage == MC_STAGE.RETURN_NOTES:
        # Why: Nulodion re-issues whichever of the 2 is missing, and the Commander refuses the hand-over without both.
        complete = held_id(snap, MC_OBJ.NOTES.id) > 0 and held_id(snap, MC_OBJ.MOULD.id) > 0
        return Record({'kind': 'talk', 'stop': (COMMANDER if complete else NULODION)})
    return Record({'kind': 'wait', 'reason': f'unrecognized Dwarf Cannon stage {stage}'})


def warn_dwarf_cannon_readiness():
    bits = []
    if skills.level('crafting') < 40 and skills.level('smithing') < 40:
        bits.append('every railing and cannon part is a Crafting/Smithing roll — below 40 in both, expect repeated failures and self-damage')
    if skills.level('hitpoints') < 30:
        bits.append(f"the goblin cave is twenty goblins deep (hp={skills.level('hitpoints')})")
    return (f"Dwarf Cannon: {'; '.join(bits)}" if len(bits) > 0 else None)


# Why: QuestEngine only reads `tools` for the spillover keep list and never provisions it, so a resume mid-quest doesn't bank its own state.
# Why: the quest buys nothing, and a float would walk to the pinned bank on every activation, which from the goblin cave is a route that doesn't exist and costs 90s to prove.
dwarfcannon = QuestModule(**{
    'record': quest_record('mcannon'),
    'bank': FALADOR_WEST_BANK,
    'hops': list(CAVE_HOPS),
    'food': MC_FOOD_TARGET,
    'coin_float': 0,
    'tools': ['coins', 'tool kit', 'dwarf remains', "nulodion's notes", 'ammo mould', 'railing'],
    'read_progress': read_dwarf_cannon_progress,
    'sustain': Record({'foods': ['Lobster', 'Trout', 'Bread'], 'eat_below_hp': 0.6}),
    'warn_readiness': warn_dwarf_cannon_readiness,
    'decide': decide,
})
