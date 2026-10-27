"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ernest/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import QUESTS
from rs2004.quests.defs.ernest.areas import EC_ID, EC_STAGE, EC_TILE, ODDENSTEIN, VERONICA
from rs2004.quests.defs.ernest.basement import basement_region, fetch_oil_can, in_alcove, leave_manor_basement
from rs2004.quests.defs.ernest.items import fetch_pressure_gauge, fetch_rubber_tube, in_closet, leave_closet
from rs2004.quests.defs.ernest.journal import read_ernest_progress
from rs2004.quests.defs.ernest.supplies import kit
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.engine.types import held_id


__all__ = ['decide', 'ernest']

def talk(stop):
    return (Record({'kind': 'talk', 'stop': stop}))


# Why: the tube, oil can and basement are all inside the manor, so only the gauge leg goes outside: one exit and one re-entry.
def parts(snap):
    """The next of tube, oil can, gauge that is still outstanding."""
    if held_id(snap, EC_ID.RUBBER_TUBE) == 0:
        return Record({'kind': 'custom', 'name': 'fetch the rubber tube', 'run': fetch_rubber_tube})
    if held_id(snap, EC_ID.OIL_CAN) == 0:
        return Record({'kind': 'custom', 'name': 'fetch the oil can', 'run': fetch_oil_can})
    if held_id(snap, EC_ID.PRESSURE_GAUGE) == 0:
        return Record({'kind': 'custom', 'name': 'fetch the pressure gauge', 'run': fetch_pressure_gauge})
    return talk(ODDENSTEIN)


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v1 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v1 if _v1 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    # Why: the 3 sealed pockets are only reachable by scripted teleport, and a leg that starts inside one burns its budget failing to walk out.
    # Why: runs ahead of the bank trip, which is itself a walk.
    if in_closet(snap.tile):
        return Record({'kind': 'custom', 'name': 'leave the closet', 'run': leave_closet})
    # Escape only after obtaining the can; `fetchOilCan` controls basement movement until then.
    if held_id(snap, EC_ID.OIL_CAN) > 0 and (in_alcove(snap.tile) or basement_region(snap.tile) != 'outside'):
        return Record({'kind': 'custom', 'name': 'leave the manor basement', 'run': leave_manor_basement})
    supplies = kit(snap)
    if supplies:
        return supplies
    if stage == EC_STAGE.NOT_STARTED:
        return talk(VERONICA)
    elif stage == EC_STAGE.STARTED:
        return talk(ODDENSTEIN)
    elif stage == EC_STAGE.SPOKEN_ODDENSTEIN:
        return parts(snap)
    else:
        return Record({'kind': 'done'})


ernest = QuestModule(**{
    'record': ([r for r in QUESTS if r.id == 'haunted'] or [None])[0],
    'bank': EC_TILE.DRAYNOR_BANK,
    'owns_inventory': True,
    'tools': [
    'spade',
    'poison',
    'fish food',
    'poisoned fish food',
    'key',
    'rubber tube',
    'oil can',
    'pressure gauge',
    'coins',
],
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'read_progress': read_ernest_progress,
    'decide': decide,
})
