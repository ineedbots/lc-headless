"""Ported from rs2b0t's src/bot/api/ai/quests/defs/treegnome/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.treegnome.areas import LOGS_WANTED, TG_ITEM, TG_NPC, TG_TILE, held, in_stronghold
from rs2004.quests.defs.treegnome.combat import kill_the_warlord
from rs2004.quests.defs.treegnome.journal import TG_STAGE, read_tree_gnome_progress
from rs2004.quests.defs.treegnome.stronghold import fire_ballista, leave_stronghold, take_the_orb
from rs2004.quests.defs.treegnome.supplies import arm_for_the_warlord, chop_logs, scan_bank, source_axe, top_up_food
from rs2004.quests.exec.primitives import NpcStop
from rs2004.quests.food import FOOD_FLOAT
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['decide', 'treegnome']

BOLREN = NpcStop(TG_NPC.BOLREN, TG_TILE.BOLREN, 8, [
    'Can I help at all?',
    'I would be glad to help.',
    'I will find the warlord and bring back the orbs.',
    'Yes please.',
])
MONTAI = NpcStop(TG_NPC.MONTAI, TG_TILE.MONTAI, 8, ["Ok, I'll gather some wood.", "I'll try my best."])


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


LEAVE = custom('walk out of the Khazard stronghold', leave_stronghold)
TAKE_ORB = custom("search the Khazard chest for the gnomes' orb", take_the_orb)
KILL_WARLORD = custom('kill the Khazard warlord for the last two orbs', kill_the_warlord)


def logs_leg(snap):
    if held(snap, TG_ITEM.LOGS) >= LOGS_WANTED:
        return Record({'kind': 'talk', 'stop': MONTAI})
    _v1 = source_axe(snap)
    return (_v1 if _v1 is not None else custom(f'chop {LOGS_WANTED} logs on the battlefield', chop_logs))


CEREMONY_RANGE = 12


# Why: the chest and the warlord both refuse while a copy sits in the bank, so a banked orb has to come back out.
# Why: Bolren deletes the orbs a tick before the queue that finishes the quest, so an empty pack at his feet is that gap.
def reclaim(snap, item, earn):
    if held(snap, item) > 0:
        return Record({'kind': 'talk', 'stop': BOLREN})
    if snap.tile and TG_TILE.BOLREN.distance_to(snap.tile) <= CEREMONY_RANGE:
        return Record({'kind': 'wait', 'reason': 'King Bolren is running the ceremony'})
    if snap.bank_known != True:
        return scan_bank()
    _v2 = snap.bank_ids.get(item.id)
    return (Record({
        'kind': 'withdraw',
        'items': [{'name': item.name, 'qty': 1, 'id': item.id}],
        'bank': TG_TILE.BANK,
    }) if ((_v2 if _v2 is not None else 0)) > 0 else earn)


def stage_step(snap, stage):
    if stage == TG_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': BOLREN})
    elif stage in [TG_STAGE.STARTED, TG_STAGE.GAVE_LOGS]:
        return Record({'kind': 'talk', 'stop': MONTAI})
    elif stage == TG_STAGE.SPOKEN_MONTAI:
        return logs_leg(snap)
    elif stage == TG_STAGE.FINDING_TRACKERS:
        return custom('fire the gnome ballista at the stronghold', fire_ballista)
    elif stage == TG_STAGE.BALLISTA_FIRED:
        return TAKE_ORB
    elif stage == TG_STAGE.RETRIEVED_ORB:
        return reclaim(snap, TG_ITEM.ORB, TAKE_ORB)
    elif stage == TG_STAGE.RETURNED_FIRST_ORB:
        _v3 = top_up_food(snap)
        return (_v3 if _v3 is not None else KILL_WARLORD)
    elif stage == TG_STAGE.DEFEATED_WARLORD:
        return reclaim(snap, TG_ITEM.ORBS, KILL_WARLORD)
    else:
        return Record({'kind': 'wait', 'reason': f'Tree Gnome Village stage {stage} is not implemented'})


def chest_business(snap, stage):
    """The chest is the only errand the stronghold pocket can run; everything else walks out first."""
    if stage == TG_STAGE.BALLISTA_FIRED:
        return True
    # Why: the chest refuses while a copy sits in the bank, so a banked orb means walk out.
    return stage == TG_STAGE.RETRIEVED_ORB and held(snap, TG_ITEM.ORB) == 0 and ((snap.bank_ids.get(TG_ITEM.ORB.id) if snap.bank_ids.get(TG_ITEM.ORB.id) is not None else 0)) == 0


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v4 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v4 if _v4 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'Tree Gnome Village journal stage unavailable'})
    if in_stronghold(snap.tile):
        return (TAKE_ORB if chest_business(snap, stage) else LEAVE)
    # Why: the kit comes out on the opening bank trip; arming at the first fight walks the battlefield back to Ardougne for it.
    _v5 = arm_for_the_warlord(snap)
    return (_v5 if _v5 is not None else stage_step(snap, stage))


def warn_readiness():
    """Proven floor 70 melee in rune with Protect from Melee; 50 is the next probe."""
    return 'Tree Gnome Village ends on a level 112 warlord with 170 hitpoints — 70 melee in rune took him without a hit landing.'


treegnome = QuestModule(**{
    'record': quest_record('tree'),
    'bank': TG_TILE.BANK,
    'food': FOOD_FLOAT,
    'tools': ['logs', 'axe', 'orb of protection', 'gnome amulet'],
    'read_progress': read_tree_gnome_progress,
    'exit': leave_stronghold,
    'warn_readiness': warn_readiness,
    'decide': decide,
})
