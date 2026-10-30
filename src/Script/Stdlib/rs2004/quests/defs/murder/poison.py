"""Ported from rs2b0t's src/bot/api/ai/quests/defs/murder/poison.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.traversal import traversal
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.primitives import goto_npc, talk_through
from rs2004.quests.exec.prompts import drive_choice, settle_scene
from rs2004.quests.defs.murder.areas import SALESMAN
from rs2004.quests.defs.murder.journal import POISON_PROVED, read_murder_progress
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['prove_poison']

BOX_MS = 6000


# Why: the anchor walk is a hint; everyone here drifts 5 tiles off spawn, and `Reach` finds and chases whoever is in the scene when the walk falls short.
def ask(stop, log):
    yield from goto_npc(stop, [], log)
    _result1 = yield from talk_through(stop.npc, stop.prefer, log)
    return _result1


# Why: The loc emits a game message before the poison interview and a mesbox afterward; no item confirms progress.
def investigate(loc, log):
    _w2 = yield from traversal.walk_resilient(loc.near, radius=1, attempts=3, timeout_ms=90000, log=log)
    if not (_w2):
        return False
    yield from settle_scene()
    target = locs.query().where(lambda l: l.id == loc.id).action('Investigate').within(6).nearest()
    if not target:
        log(f'murder: no {loc.name} at ({loc.near.x},{loc.near.z})')
        return False
    if not (target.interact('Investigate')):
        return False
    yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), BOX_MS)
    _result3 = yield from drive_choice([], log)
    return _result3


def proved():
    _w4 = yield from read_murder_progress()
    return has_flag(_w4, POISON_PROVED)


# Why: only the murderer's own answer moves the quest on, and asking anyone else is a no-op, so the sweep is safe to repeat from any point.
def prove_poison(order, log):
    """The salesman names the family, the suspect explains the purchase, and their loc gives the lie away."""
    _w5 = yield from ask(SALESMAN, log)
    if not (_w5):
        return False
    for suspect in order:
        log(f'murder: asking {suspect.stop.npc} about the poison')
        yield from ask(suspect.stop, log)
        yield from investigate(suspect.poison, log)
        _w6 = yield from proved()
        if _w6:
            return True
    return False
