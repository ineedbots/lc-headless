"""Ported from rs2b0t's src/bot/api/ai/quests/defs/murder/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import has_flag
from rs2004.quests.defs.murder.areas import ARHEIN, GUARD_HANDIN, GUARD_START, MURDER_EVIDENCE, MURDER_OBJ, MURDER_TILE, suspect_order
from rs2004.quests.defs.murder.evidence import take_prints, take_thread
from rs2004.quests.defs.murder.journal import POISON_PROVED, read_murder_progress
from rs2004.quests.defs.murder.poison import prove_poison
from rs2004.quests.defs.murder.state import accused, banked, held, held_thread
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['source_pot', 'decide', 'murder']

# Why: Arhein's pot is 1gp and every dusting spends 1 load of flour, so the pack carries enough for the dagger and both thread-matched suspects in one barrel visit.
POT_TARGET = 3
POT_GP = 100


def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


# Why: a barrel, the window and the study floor all refuse while a copy sits in the bank, so anything banked has to come back out first.
def reclaim(snap):
    items = [({'name': obj.name, 'id': obj.id, 'qty': 1}) for obj in [obj for obj in MURDER_EVIDENCE if held(snap, obj.id) == 0 and banked(snap, obj.id) > 0]]
    return (None if len(items) == 0 else Record({'kind': 'withdraw', 'items': items, 'bank': MURDER_TILE.BANK}))


def source_pot(snap):
    """The empty pot the flour barrel fills; the nearest stock is Arhein's in Catherby."""
    if held(snap, MURDER_OBJ.POT) > 0 or held(snap, MURDER_OBJ.POT_FLOUR) > 0:
        return None
    if not snap.bank_known:
        return Record({'kind': 'scan_bank', 'bank': MURDER_TILE.BANK})
    if banked(snap, MURDER_OBJ.POT) > 0:
        return Record({
            'kind': 'withdraw',
            'items': [{'name': 'Pot', 'id': MURDER_OBJ.POT, 'qty': 1}],
            'bank': MURDER_TILE.BANK,
        })
    return Record({'kind': 'buy', 'item': 'Pot', 'qty': POT_TARGET, 'shop': ARHEIN, 'est_gp': POT_GP})


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    progress = snap.progress
    if snap.journal != 'not_started' and progress is None:
        return Record({'kind': 'wait', 'reason': 'Murder Mystery journal stage unavailable'})
    reclaimed = reclaim(snap)
    if reclaimed:
        return reclaimed
    printed = held(snap, MURDER_OBJ.KILLERS_PRINT) > 0
    if not printed:
        pot = source_pot(snap)
        if pot:
            return pot
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': GUARD_START})
    thread = held_thread(snap)
    if thread is None:
        return custom('take the thread from the smashed window', take_thread)
    if not printed:
        order = suspect_order(thread)
        return custom("match the murderer's fingerprints", lambda log: take_prints(order, log))
    if not has_flag(progress, POISON_PROVED):
        named = accused(snap, thread)
        order = ([named] if named else suspect_order(thread))
        return custom('prove the family lied about the poison', lambda log: prove_poison(order, log))
    return Record({'kind': 'talk', 'stop': GUARD_HANDIN})


murder = QuestModule(**{
    'record': quest_record('murder'),
    'bank': MURDER_TILE.BANK,
    'food': 4,
    'tools': ['pot', 'criminals', 'silver', 'flypaper', 'print', 'thread'],
    'read_progress': read_murder_progress,
    'decide': decide,
})
