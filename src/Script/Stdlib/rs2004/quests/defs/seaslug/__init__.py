"""Ported from rs2b0t's src/bot/api/ai/quests/defs/seaslug/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.karamja_recovery import on_island
from rs2004.quests.data import QUESTS
from rs2004.quests.defs.seaslug.areas import BAILEY, CAROLINE, HOLGART_LAND, KHAZARD_SHOP, SS_ITEM, SS_OBJ, SS_TILE, on_island, on_platform
from rs2004.quests.defs.seaslug.journal import SS_STAGE, read_sea_slug_progress
from rs2004.quests.defs.seaslug.legs import call_kennith, climb_to, find_kent, open_panel_and_call, rotate_crane, rub_sticks, sail_to
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['source_paste', 'torch_step', 'decide', 'seaslug']

PASTE_GP = 1000


def held(snap, id):
    _v1 = (snap.inv_ids or {}).get(id)
    return (_v1 if _v1 is not None else 0)


def sail_step():
    return Record({'kind': 'custom', 'name': 'sail to the fishing platform', 'run': lambda log: sail_to('platform', log)})


def source_paste(snap):
    if held(snap, SS_OBJ.SWAMP_PASTE) > 0:
        return None
    if snap.bank_known != True:
        return Record({'kind': 'scan_bank'})
    _v2 = (snap.bank or {}).get(SS_ITEM.SWAMP_PASTE.lower())
    if ((_v2 if _v2 is not None else 0)) > 0:
        return Record({'kind': 'withdraw', 'items': [{'name': SS_ITEM.SWAMP_PASTE, 'qty': 1}]})
    return Record({'kind': 'buy', 'item': SS_ITEM.SWAMP_PASTE, 'qty': 1, 'shop': KHAZARD_SHOP, 'est_gp': PASTE_GP})


def torch_step(snap):
    if not on_platform(snap.tile):
        return sail_step()
    if snap.tile and snap.tile.level != 0:
        return Record({'kind': 'custom', 'name': 'climb down to the lower deck', 'run': lambda log: climb_to(0, log)})
    if held(snap, SS_OBJ.TORCH_LIT) + held(snap, SS_OBJ.TORCH_UNLIT) == 0:
        if snap.stage == SS_STAGE.NEED_KENNITH_PATH:
            return Record({'kind': 'wait', 'reason': 'no torch, and Bailey has no stage-10 line to hand one over'})
        return Record({'kind': 'talk', 'stop': BAILEY})
    if held(snap, SS_OBJ.DRY_STICKS) > 0:
        return Record({'kind': 'custom', 'name': 'rub the dry sticks together', 'run': rub_sticks})
    if held(snap, SS_OBJ.DAMP_STICKS) == 0:
        return Record({
            'kind': 'grab_ground',
            'item': SS_ITEM.DAMP_STICKS,
            'anchor': SS_TILE.DAMP_STICKS_SPAWN,
            'wait_if_missing': True,
        })
    if held(snap, SS_OBJ.BROKEN_GLASS) == 0:
        return Record({
            'kind': 'grab_ground',
            'item': SS_ITEM.BROKEN_GLASS,
            'anchor': SS_TILE.BROKEN_GLASS_SPAWN,
            'wait_if_missing': True,
        })
    return Record({
        'kind': 'use_on',
        'item': SS_ITEM.BROKEN_GLASS,
        'target_kind': 'item',
        'target': SS_ITEM.DAMP_STICKS,
        'anchor': SS_TILE.BROKEN_GLASS_SPAWN,
        'product': SS_ITEM.DRY_STICKS,
    })


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': CAROLINE})
    progress = snap.progress
    if progress is None:
        return Record({'kind': 'wait', 'reason': 'Sea Slug journal stage unavailable'})
    stage = progress.stage
    if stage == SS_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': CAROLINE})
    if stage == SS_STAGE.STARTED:
        return Record({'kind': 'talk', 'stop': HOLGART_LAND})
    if stage == SS_STAGE.SPOKEN_HOLGART:
        _v3 = source_paste(snap)
        return (_v3 if _v3 is not None else Record({'kind': 'talk', 'stop': HOLGART_LAND}))
    if stage == SS_STAGE.BOAT_REPAIRED:
        return Record({'kind': 'custom', 'name': 'call to Kennith behind the crates', 'run': call_kennith})
    if stage == SS_STAGE.SPOKEN_KENNITH or stage == SS_STAGE.SAILED_KENT:
        return Record({'kind': 'custom', 'name': 'find Kent on the island', 'run': find_kent})
    lit_torch = held(snap, SS_OBJ.TORCH_LIT) > 0
    if stage == SS_STAGE.SPOKEN_KENT or (stage <= SS_STAGE.NEED_KENNITH_PATH and stage >= SS_STAGE.LIT_TORCH and not lit_torch):
        return torch_step(snap)
    if stage == SS_STAGE.LIT_TORCH:
        return Record({'kind': 'custom', 'name': 'show Kennith the lit torch', 'run': call_kennith})
    if stage == SS_STAGE.KENNITH_NEED_ESCAPE or stage == SS_STAGE.PANEL_OPENED:
        return Record({'kind': 'custom', 'name': 'kick the panel open and call Kennith through', 'run': open_panel_and_call})
    if stage == SS_STAGE.NEED_KENNITH_PATH:
        return Record({'kind': 'custom', 'name': 'swing the crane over to Kennith', 'run': rotate_crane})
    if stage == SS_STAGE.SAVED_KENNITH:
        if on_platform(snap.tile) or on_island(snap.tile):
            return Record({
                'kind': 'custom',
                'name': 'sail back to the Ardougne shore',
                'run': lambda log: sail_to('mainland', log),
            })
        return Record({'kind': 'talk', 'stop': CAROLINE})
    return Record({'kind': 'wait', 'reason': f'unhandled Sea Slug stage {stage}'})


seaslug = QuestModule(**{
    'record': quest_record('seaslug'),
    'resume_at': lambda tile: on_platform(tile) or on_island(tile),
    'bank': SS_TILE.BANK,
    'tools': ['torch', 'damp sticks', 'dry sticks', 'broken glass', 'swamp paste', 'coins'],
    'read_progress': read_sea_slug_progress,
    'decide': decide,
})
