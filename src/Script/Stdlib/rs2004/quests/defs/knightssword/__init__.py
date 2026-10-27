"""Ported from rs2b0t's src/bot/api/ai/quests/defs/knightssword/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.data import QUESTS
from rs2004.quests.defs.knightssword.areas import KS_ID, KS_NAME, KS_STAGE, RELDO, SQUIRE, THURGO
from rs2004.quests.defs.knightssword.dungeon import mine_blurite
from rs2004.quests.defs.knightssword.journal import read_knights_sword_progress
from rs2004.quests.defs.knightssword.portrait import fetch_portrait
from rs2004.quests.defs.knightssword.supplies import iron_bars_at, kit, pickaxe_at, pie, pie_dish
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.engine.types import banked_id, held_id


__all__ = ['decide_at', 'decide', 'knightssword']

def talk(stop):
    return (Record({'kind': 'talk', 'stop': stop}))


def sword_step(snap):
    """`squire_status_report` at stage 6 has one branch per place the sword can be, and only the pack completes the quest."""
    _v1 = (KS_ID.BLURITE_SWORD in (snap.worn_ids or set()))
    if (_v1 if _v1 is not None else False):
        return Record({'kind': 'equip', 'item': KS_NAME.BLURITE_SWORD})
    if held_id(snap, KS_ID.BLURITE_SWORD) > 0:
        return talk(SQUIRE)
    if banked_id(snap, KS_ID.BLURITE_SWORD) > 0:
        return Record({
            'kind': 'withdraw',
            'items': [{'name': KS_NAME.BLURITE_SWORD, 'qty': 1, 'id': KS_ID.BLURITE_SWORD}],
        })
    return None


def materials(snap, mining_level, smithing_level):
    sword = sword_step(snap)
    if sword:
        return sword
    if held_id(snap, KS_ID.IRON_BAR) < 2:
        return iron_bars_at(snap, mining_level, smithing_level)
    if held_id(snap, KS_ID.BLURITE_ORE) == 0:
        # Banked bars skip iron mining, so they do not prove that a pickaxe was acquired.
        pickaxe = pickaxe_at(snap, mining_level)
        if pickaxe is not None:
            return pickaxe
        # Stock up above ground; kit() refuses to send the bot back out of the cave.
        food = None
        for name in ['Lobster', 'Swordfish', 'Tuna']:
            available = (snap.bank or {}).get(name.lower(), 0)
            carried = snap.inv.get(name.lower(), 0)
            if available > 0:
                food = Record({'name': name, 'held': carried, 'low': 2, 'target': min(5, carried + available)})
                break
        _v2 = kit(snap, food)
        return (_v2 if _v2 is not None else Record({'kind': 'custom', 'name': 'mine blurite', 'run': mine_blurite}))
    return talk(THURGO)


def decide_at(snap, mining_level, smithing_level):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v3 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v3 if _v3 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    float_ = kit(snap)
    if float_:
        return float_
    if stage == KS_STAGE.NOT_STARTED:
        return talk(SQUIRE)
    elif stage == KS_STAGE.STARTED:
        # Why: the dish's only non-members source is a ground spawn 13 tiles from the librarian, so it rides this leg.
        # Why: it goes through supplies so both callers agree where a dish comes from.
        if held_id(snap, KS_ID.PIE_DISH) == 0 and banked_id(snap, KS_ID.PIE_DISH) == 0:
            return pie_dish(snap)
        return talk(RELDO)
    elif stage == KS_STAGE.SPOKEN_RELDO:
        return (talk(THURGO) if held_id(snap, KS_ID.REDBERRY_PIE) > 0 else pie(snap))
    elif stage == KS_STAGE.GIVEN_PIE:
        return talk(THURGO)
    elif stage == KS_STAGE.SPOKEN_THURGO:
        return talk(SQUIRE)
    elif stage == KS_STAGE.LOOKING_PORTRAIT:
        return (talk(THURGO) if held_id(snap, KS_ID.PORTRAIT) > 0 else Record({'kind': 'custom', 'name': 'take the portrait', 'run': fetch_portrait}))
    elif stage == KS_STAGE.LOOKING_BLURITE:
        return materials(snap, mining_level, smithing_level)
    else:
        return Record({'kind': 'done'})


def decide(snap):
    return decide_at(snap, skills.level('mining'), skills.level('smithing'))


knightssword = QuestModule(**{
    'record': ([r for r in QUESTS if r.id == 'squire'] or [None])[0],
    'bank': 'nearest',
    'tools': [
    'coins',
    'pickaxe',
    'pie dish',
    'pot of flour',
    'redberries',
    'bucket',
    'pastry dough',
    'pie shell',
    'uncooked berry pie',
    'redberry pie',
    'iron ore',
    'iron bar',
    'blurite ore',
    'portrait',
    'blurite sword',
],
    'owns_inventory': True,
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.6}),
    'read_progress': read_knights_sword_progress,
    'decide': decide,
})
