"""Ported from rs2b0t's src/bot/api/ai/quests/defs/murder/state.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.murder.areas import MURDER_OBJ, suspect_order
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['held', 'banked', 'owned', 'held_thread', 'accused']

def held(snap, id):
    _v1 = (snap.inv_ids or {}).get(id)
    return (_v1 if _v1 is not None else 0)


# Why: Preserve unknown bank state instead of treating an unread bank as empty.
def banked(snap, id):
    return ((((snap.bank_ids or {}).get(id) if (snap.bank_ids or {}).get(id) is not None else 0)) if snap.bank_known else 0)


def owned(snap, id):
    return held(snap, id) + banked(snap, id)


THREADS = [MURDER_OBJ.THREAD_GREEN, MURDER_OBJ.THREAD_RED, MURDER_OBJ.THREAD_BLUE]


def held_thread(snap):
    """The thread in the pack, or null when the window still has to be searched."""
    _v2 = ([id for id in THREADS if held(snap, id) > 0] or [None])[0]
    return (_v2 if _v2 is not None else None)


# Why: the print hunt walks the suspects in one fixed order and stops at the match, so every keepsake taken belongs to a suspect at or before the murderer, and the last one held is the murderer.
# Why: this survives a restart; a counter of who has been cleared doesn't.
def accused(snap, thread):
    """Who the matched print convicts, or null while the keepsakes cannot say."""
    if held(snap, MURDER_OBJ.KILLERS_PRINT) == 0:
        return None
    order = suspect_order(thread)
    for i in range(len(order) - 1, 0 - 1, -1):
        if held(snap, order[i].silver) > 0:
            return order[i]
    return None
