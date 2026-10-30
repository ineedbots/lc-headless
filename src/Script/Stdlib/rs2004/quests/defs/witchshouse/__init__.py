"""Ported from rs2b0t's src/bot/api/ai/quests/defs/witchshouse/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.strike import prepare_strikes, STRIKE_RUNES
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import held_id
from rs2004.quests.defs.witchshouse.areas import FALADOR_WEST_BANK, BOY, EXPERIMENT_NAMES, SHOP_GP, THESSALIA, WH_NAME, WH_OBJ, WYDIN, in_garden, in_shed
from rs2004.quests.defs.witchshouse.garden import fountain_key, kill_experiment, take_ball, leave_garden
from rs2004.quests.defs.witchshouse.house import diary_wanted, drop_stale_magnet, fetch_diary, fetch_magnet, read_diary, take_door_key, unlock_back_door
from rs2004.quests.defs.witchshouse.journal import WH_STAGE, read_witchs_house_progress
from rs2004.quests.defs.witchshouse.journal import WH_STAGE, parse_witchs_house_journal, read_witchs_house_progress
from rs2004.quests.defs.witchshouse.areas import WH_OBJ, WH_TILE, in_garden, in_shed
from rs2004.quests.defs.witchshouse.house import diary_state, reset_diary_state
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['decide', 'witchshouse']

WH_FOOD = 12


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    _v1 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v1 if _v1 is not None else snap.stage)
    if snap.journal == 'complete' or ((stage if stage is not None else 0)) >= WH_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if stage is None:
        return Record({'kind': 'wait', 'reason': "Witch's House journal stage unavailable"})
    if stage < WH_STAGE.DEFEATED and not in_garden(snap.tile) and not in_shed(snap.tile):
        runes = prepare_strikes(snap, ['door key', 'key', 'magnet', 'cheese', 'ball', 'diary', 'leather gloves'])
        if runes:
            return runes
    if stage == WH_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': BOY})
    if stage >= WH_STAGE.DEFEATED and held_id(snap, WH_OBJ.BALL) > 0:
        if in_garden(snap.tile) or in_shed(snap.tile):
            return custom('carry the ball safely out of the garden', leave_garden)
        return Record({'kind': 'talk', 'stop': BOY})
    # Why: every remaining step is behind the front door, whose `oploc1` reads the key out of the pack.
    if held_id(snap, WH_OBJ.DOOR_KEY) == 0:
        return custom("look under the witch's flower pot for the door key", take_door_key)
    if stage >= WH_STAGE.DEFEATED:
        return custom('take the ball from the shed', take_ball)
    if stage == WH_STAGE.STARTED or stage == WH_STAGE.FOUND_MAGNET:
        gloves = wearing_gloves(snap)
        if not gloves and held_id(snap, WH_OBJ.GLOVES) == 0:
            return Record({'kind': 'withdraw', 'items': [{'name': WH_NAME.GLOVES, 'qty': 1, 'id': WH_OBJ.GLOVES}]})
        if not gloves:
            return Record({'kind': 'equip', 'item': WH_NAME.GLOVES})
        if held_id(snap, WH_OBJ.MAGNET) == 0:
            return custom('search the cellar cupboard for the magnet', fetch_magnet)
        if stage == WH_STAGE.STARTED:
            return custom('drop the magnet the cupboard will not replace', drop_stale_magnet)
        # Why: the cheese is spent luring the mouse, so a bot caught before the magnet lands comes back holding the magnet and nothing to lure with.
        if held_id(snap, WH_OBJ.CHEESE) == 0:
            return Record({'kind': 'buy', 'item': WH_NAME.CHEESE, 'qty': 1, 'shop': WYDIN, 'est_gp': SHOP_GP})
        return custom('lure the mouse and fit the magnet', unlock_back_door)
    if held_id(snap, WH_OBJ.SHED_KEY) > 0:
        return custom('unlock the shed and kill the experiment', kill_experiment)
    # Why: the diary is read before the first garden trip and never while carrying a shed key, since the walk back through the garden is where that key is lost.
    if diary_wanted():
        return (custom("read the witch's diary so a catch cannot relock the back door", read_diary) if held_id(snap, WH_OBJ.DIARY) > 0 else custom("take the witch's diary from the bedroom", fetch_diary))
    return custom('check the garden fountain for the shed key', fountain_key)


def wearing_gloves(snap):
    return WH_OBJ.GLOVES in snap.worn_ids if snap.worn_ids is not None else WH_NAME.GLOVES.lower() in snap.worn


def where(snap):
    if in_shed(snap.tile):
        return 'shed'
    if in_garden(snap.tile):
        return 'garden'
    return (f'{snap.tile.x},{snap.tile.z},L{snap.tile.level}' if snap.tile else 'off-scene')


witchshouse = QuestModule(**{
    'record': quest_record('ball'),
    'resume_at': lambda tile: in_garden(tile) or in_shed(tile),
    'bank': FALADOR_WEST_BANK,
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'food': WH_FOOD,
    'food_ready': lambda snap: ((((snap.progress.stage if snap.progress is not None else None) if (snap.progress.stage if snap.progress is not None else None) is not None else snap.stage) if ((snap.progress.stage if snap.progress is not None else None) if (snap.progress.stage if snap.progress is not None else None) is not None else snap.stage) is not None else 0)) >= WH_STAGE.DEFEATED or prepare_strikes(snap) is None,
    'grind': list(EXPERIMENT_NAMES),
    'tools': ['door key', 'key', 'magnet', 'cheese', 'ball', 'diary', 'leather gloves', 'coins'] + list(STRIKE_RUNES),
    'read_progress': read_witchs_house_progress,
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Trout'], 'eat_below_hp': 0.6}),
    'gather': Record({
    'cheese': lambda _snap, need: (Record({'kind': 'buy', 'item': WH_NAME.CHEESE, 'qty': need, 'shop': WYDIN, 'est_gp': SHOP_GP})),
    'leather gloves': lambda _snap, need: (Record({'kind': 'buy', 'item': WH_NAME.GLOVES, 'qty': need, 'shop': THESSALIA, 'est_gp': SHOP_GP})),
}),
    'observe': lambda snap, step: [f"stage={(((snap.progress.stage if snap.progress is not None else None) if (snap.progress.stage if snap.progress is not None else None) is not None else snap.stage) if ((snap.progress.stage if snap.progress is not None else None) if (snap.progress.stage if snap.progress is not None else None) is not None else snap.stage) is not None else '?')} at={where(snap)}" + f' key={held_id(snap, WH_OBJ.DOOR_KEY)} magnet={held_id(snap, WH_OBJ.MAGNET)}' + f' cheese={held_id(snap, WH_OBJ.CHEESE)} diary={held_id(snap, WH_OBJ.DIARY)}' + f' shedkey={held_id(snap, WH_OBJ.SHED_KEY)} ball={held_id(snap, WH_OBJ.BALL)}' + f" gloves={('worn' if wearing_gloves(snap) else held_id(snap, WH_OBJ.GLOVES))} step={step.kind}"],
    'decide': decide,
})
