"""Ported from rs2b0t's src/bot/api/ai/quests/defs/piratestreasure/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import QUESTS
from rs2004.quests.defs.piratestreasure.areas import FRANK, LUTHAS, PT_ID, PT_NAME, PT_STAGE, WYDIN, ZAMBO_SHOP
from rs2004.quests.defs.piratestreasure.journal import read_pirates_treasure_progress
from rs2004.quests.defs.piratestreasure.karamja import on_karamja, ship_crate
from rs2004.quests.defs.piratestreasure.supplies import kit, worn_id
from rs2004.quests.defs.piratestreasure.treasure import collect_rum, dig_treasure, open_chest, read_message
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.engine.types import held_id


__all__ = ['decide', 'piratestreasure']

RUM_GP = 100


def talk(stop):
    return (Record({'kind': 'talk', 'stop': stop}))


def buy_rum():
    return Record({'kind': 'buy', 'item': PT_NAME.RUM, 'qty': 1, 'shop': ZAMBO_SHOP, 'est_gp': RUM_GP})


def ship():
    return Record({'kind': 'custom', 'name': 'ship the crate from the plantation', 'run': ship_crate})


# Why: the apron is bought before the crossing so its Varrock trip rides the Varrock-Draynor-Port Sarim line and isn't a round trip after the rum ships.
APRON_STAGES = set(['need-rum', 'rum-lost', 'rum-shipped', 'store-job'])


def smuggle(snap, flag):
    if flag in ['rum-held-unemployed', 'employed-need-rum']:
        return (talk(LUTHAS) if held_id(snap, PT_ID.RUM) > 0 else buy_rum())
    elif flag in ['rum-held-employed', 'rum-in-crate', 'crate-full']:
        return ship()
    elif flag == 'rum-shipped':
        return talk(WYDIN)
    elif flag == 'store-job':
        if on_karamja(snap.tile):
            return ship()
        return (Record({'kind': 'custom', 'name': 'search the back room for the rum', 'run': collect_rum}) if worn_id(snap, PT_ID.WHITE_APRON) else Record({'kind': 'equip', 'item': PT_NAME.WHITE_APRON}))
    elif flag == 'rum-in-hand':
        return (ship() if on_karamja(snap.tile) else talk(FRANK))
    else:
        return (talk(LUTHAS) if held_id(snap, PT_ID.RUM) > 0 else buy_rum())


def treasure(snap):
    if held_id(snap, PT_ID.PIRATE_MESSAGE) > 0:
        return Record({'kind': 'custom', 'name': 'read the pirate message', 'run': read_message})
    if held_id(snap, PT_ID.CHEST_KEY) > 0:
        return Record({'kind': 'custom', 'name': 'open the Blue Moon chest', 'run': open_chest})
    # Frank re-issues the key to anyone who turns up without one.
    return talk(FRANK)


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v1 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v1 if _v1 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    _v2 = (snap.progress.flags if snap.progress is not None else None)
    flag = (list(_v2 or []) or [None])[0]
    supplies = kit(snap, stage == PT_STAGE.FETCH_RUM and ((flag if flag is not None else 'need-rum') in APRON_STAGES), stage == PT_STAGE.READ_NOTE)
    if supplies:
        return supplies
    if stage == PT_STAGE.NOT_STARTED:
        return talk(FRANK)
    elif stage == PT_STAGE.FETCH_RUM:
        return smuggle(snap, flag)
    elif stage == PT_STAGE.RECEIVED_KEY:
        return treasure(snap)
    elif stage == PT_STAGE.READ_NOTE:
        return Record({'kind': 'custom', 'name': 'dig up the treasure', 'run': dig_treasure})
    else:
        return Record({'kind': 'done'})


piratestreasure = QuestModule(**{
    'record': ([r for r in QUESTS if r.id == 'hunt'] or [None])[0],
    'bank': 'nearest',
    'owns_inventory': True,
    'tools': ['karamjan rum', 'chest key', 'pirate message', 'white apron', 'spade', 'banana', 'coins'],
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'read_progress': read_pirates_treasure_progress,
    'decide': decide,
})
