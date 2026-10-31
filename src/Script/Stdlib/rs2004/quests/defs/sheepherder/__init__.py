"""Ported from rs2b0t's src/bot/api/ai/quests/defs/sheepherder/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.sheepherder.areas import BANK, BONES_OBJ, FEED, FEED_OBJ, HALGRIVE, JACKET, JACKET_OBJ, ORBON, PROD, PROD_OBJ, SHEEP, TROUSERS, TROUSERS_OBJ
from rs2004.quests.defs.sheepherder.journal import SH_STAGE, read_sheep_herder_progress
from rs2004.quests.defs.sheepherder.pen import fetch_prod, incinerate, pen_and_kill
from rs2004.quests.engine.types import has_flag, held_id
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['decide', 'sheepherder']

SUIT_GP = 100


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


def held(snap, id):
    return held_id(snap, id)


def wearing(snap, id):
    return snap.worn_ids is not None and id in snap.worn_ids


def dressed(snap):
    """Both halves of the suit have to be worn: `prod_sheep` and the gate each read `worn`."""
    for id, name in [[JACKET_OBJ, JACKET], [TROUSERS_OBJ, TROUSERS]]:
        if wearing(snap, id):
            continue
        # Why: the suit is untradeable and has no shop, so a lost half is re-bought from Orbon.
        return (Record({'kind': 'equip', 'item': name}) if held(snap, id) > 0 else Record({'kind': 'talk', 'stop': ORBON}))
    return None


def armed(snap):
    if wearing(snap, PROD_OBJ):
        return None
    return custom(f'fetch the {PROD} from the barn', lambda log: fetch_prod(log))


def next_sheep(snap):
    return ([n for n in SHEEP if not has_flag(snap.progress, f'burnt-{n}')] or [None])[0]


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': HALGRIVE})
    stage = (snap.progress.stage if snap.progress is not None else None)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Sheep Herder journal stage unavailable'})
    if stage == SH_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if stage == SH_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': HALGRIVE})
    if stage == SH_STAGE.NEED_SUIT:
        _v2 = snap.inv.get('coins')
        return (Record({'kind': 'talk', 'stop': ORBON}) if ((_v2 if _v2 is not None else 0)) >= SUIT_GP else Record({'kind': 'withdraw', 'items': [{'name': 'Coins', 'qty': SUIT_GP * 10}], 'bank': BANK}))
    n = next_sheep(snap)
    if n is None:
        return Record({'kind': 'talk', 'stop': HALGRIVE})
    # Why: the incinerator stands inside the enclosure and the gate reads `worn`, so the suit comes before the burn as well as before the herd.
    suit = dressed(snap)
    if suit:
        return suit
    # Why: the remains are already in hand, so the prod and the feed cannot block the burn.
    if held(snap, BONES_OBJ[n]) > 0:
        return custom(f'incinerate the remains of sheep {n}', lambda log: incinerate(n, log))
    prod = armed(snap)
    if prod:
        return prod
    # Why: the feed is untradeable and never consumed, so one is enough, and Halgrive hands out another whenever the pack has none.
    if held(snap, FEED_OBJ) == 0:
        return Record({'kind': 'talk', 'stop': HALGRIVE})
    return custom(f'herd and kill sheep {n}', lambda log: pen_and_kill(n, log))


sheepherder = QuestModule(**{
    'record': quest_record('sheepherder'),
    'bank': BANK,
    'food': 4,
    'tools': ['coins', PROD.lower(), FEED.lower(), JACKET.lower(), TROUSERS.lower(), 'bones'],
    'read_progress': read_sheep_herder_progress,
    'decide': decide,
})
