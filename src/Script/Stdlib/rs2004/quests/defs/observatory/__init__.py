"""Ported from rs2b0t's src/bot/api/ai/quests/defs/observatory/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.defs.observatory.areas import OBSERVATORY_TOOLS, OBS_ID, OBS_ITEM, OBS_STAGE, OBS_TILE, PLANKS_NEEDED, PROFESSOR
from rs2004.quests.defs.observatory.dungeon import fetch_lens_mould, use_telescope
from rs2004.quests.defs.observatory.journal import read_observatory_stage
from rs2004.quests.defs.observatory.supplies import from_bank, held_id, ore, ore_short, planks, sand, smelt_bronze, smelt_glass, soda_ash
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['decide', 'warn_observatory_readiness', 'observatory']

talk_professor = Record({'kind': 'talk', 'stop': PROFESSOR})
fetch_mould = Record({'kind': 'custom', 'name': 'fetch the lens mould', 'run': fetch_lens_mould})
HANDBACK_SLOT = 1


# Why: the professor only accepts the item his current stage names, so hand-overs can't be batched but the errands can, and each opens as soon as its stage is in reach.
# Why: the order below follows the map: sand by the reception, the pickaxe and seam south-east, the planks and seaweed north, then one furnace visit for both bars on the way home.
# Why: ordering by quest walks the map 3 times, since the planks and the seaweed are 200 tiles apart and everything else is south of both.
def supply(snap, need_planks, need_bar, need_glass, need_mould):
    """The next errand this loop owes, or null when the pack is ready for the professor."""
    glass_short = need_glass and held_id(snap, OBS_ID.MOLTEN_GLASS) == 0
    bar_short = need_bar and held_id(snap, OBS_ID.BRONZE_BAR) == 0
    planks_short = need_planks and held_id(snap, OBS_ID.PLANK) < PLANKS_NEEDED
    mould_short = need_mould and held_id(snap, OBS_ID.LENS_MOULD) == 0
    # A finished item in the bank is worth more than every rung that would rebuild it.
    if glass_short:
        banked = from_bank(snap, OBS_ID.MOLTEN_GLASS, OBS_ITEM.MOLTEN_GLASS, 1)
        if banked:
            return banked
    if bar_short:
        banked = from_bank(snap, OBS_ID.BRONZE_BAR, OBS_ITEM.BRONZE_BAR, 1)
        if banked:
            return banked
    if mould_short:
        banked = from_bank(snap, OBS_ID.LENS_MOULD, OBS_ITEM.LENS_MOULD, 1)
        if banked:
            return banked
    if glass_short and held_id(snap, OBS_ID.BUCKET_OF_SAND) == 0 and held_id(snap, OBS_ID.SODA_ASH) == 0:
        return sand(snap)
    if bar_short and ore_short(snap):
        return ore(snap)
    if planks_short:
        return planks(snap)
    if glass_short and held_id(snap, OBS_ID.SODA_ASH) == 0:
        return soda_ash(snap)
    if glass_short:
        return (sand(snap) if held_id(snap, OBS_ID.BUCKET_OF_SAND) == 0 else smelt_glass)
    if bar_short:
        return smelt_bronze
    if mould_short:
        return fetch_mould
    return None


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return talk_professor
    stage = snap.stage
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Observatory Quest journal stage unavailable'})
    if stage >= OBS_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if stage == OBS_STAGE.SENT_TELESCOPE:
        return Record({'kind': 'custom', 'name': 'look through the telescope', 'run': use_telescope})
    if stage == OBS_STAGE.GIVEN_MOULD:
        if held_id(snap, OBS_ID.LENS) > 0:
            return talk_professor
        # Why: `professor_glass` removes the glass and `professor_mould` immediately returns it, so it should be present at stage 5.
        rebuild = supply(snap, False, False, True, True)
        if rebuild:
            return rebuild
        return Record({
            'kind': 'use_on',
            'item': OBS_ITEM.LENS_MOULD,
            'target_kind': 'item',
            'target': OBS_ITEM.MOLTEN_GLASS,
            'anchor': OBS_TILE.PROFESSOR,
            'product': OBS_ITEM.LENS,
        })
    errand = supply(snap, stage <= OBS_STAGE.STARTED, stage <= OBS_STAGE.GIVEN_PLANKS, stage <= OBS_STAGE.GIVEN_BRONZE, stage <= OBS_STAGE.GIVEN_GLASS)
    if errand:
        return errand
    if stage == OBS_STAGE.GIVEN_GLASS and snap.free_slots is not None and snap.free_slots < HANDBACK_SLOT:
        return Record({'kind': 'deposit', 'keep': list(OBSERVATORY_TOOLS)})
    return talk_professor


# Why: the server gates nothing here, `craft_telescope_disc` has no level check, but the quest is listed at Crafting 10 and an account short of it is short of the rest of the trip too.
OBS_PROVEN_SKILLS = {'crafting': 10, 'mining': 1, 'smithing': 1, 'cooking': 1}


def warn_observatory_readiness():
    short = [f'{s} {skills.level(s)}/{OBS_PROVEN_SKILLS[s]}' for s in OBS_PROVEN_SKILLS.keys() if skills.level(s) < OBS_PROVEN_SKILLS[s]]
    if len(short) == 0:
        return None
    return f"below the proven profile ({', '.join(short)}); headed PASS at 70s across the board. " + 'The goblin guard on the keep gate is level 42 and turns on the bot the moment the gate moves.'


observatory = QuestModule(**{
    'record': quest_record('itgronigen'),
    'bank': OBS_TILE.BANK,
    'food': 8,
    'tools': list(OBSERVATORY_TOOLS),
    'read_stage': read_observatory_stage,
    'warn_readiness': warn_observatory_readiness,
    'decide': decide,
})
