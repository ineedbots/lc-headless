"""Ported from rs2b0t's src/bot/api/ai/quests/defs/scorpcatcher/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.barcrawl.barcrawl_logic import BARCRAWL_CARD, BARCRAWL_GP
from rs2004.quests.defs.scorpcatcher.areas import ANTIPOISON_DOSES, ANTIPOISON_GP, CAGE_ID, CAGE_NAME, EVERY_CAGE, EVERY_SCORPION, SCORPION_LABEL, SC_ITEM, SC_STAGE, SC_TILE, THORMAC, caught_in
from rs2004.quests.defs.scorpcatcher.journal import read_scorpion_progress
from rs2004.quests.defs.scorpcatcher.dungeon import locked_in
from rs2004.quests.defs.scorpcatcher.legs import CATCH_LEG, ask_the_seer
from rs2004.quests.food import FOOD_FLOAT
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['decide', 'warn_readiness', 'scorpcatcher']

def first_cage(counts):
    for id in EVERY_CAGE:
        _v1 = counts.get(id)
        if ((_v1 if _v1 is not None else 0)) > 0:
            return id
    return None


# Why: Thormac replaces a cage only when none exists in inventory or bank, so withdraw banked cages first.
def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': THORMAC})
    held = first_cage(snap.inv_ids)
    if held is None:
        if snap.bank_known != True:
            return Record({'kind': 'scan_bank'})
        banked = first_cage(snap.bank_ids)
        if banked is not None:
            return Record({'kind': 'withdraw', 'items': [{'name': CAGE_NAME, 'qty': 1, 'id': banked}]})
        return Record({'kind': 'talk', 'stop': THORMAC})
    if held == CAGE_ID.FULL:
        return Record({'kind': 'talk', 'stop': THORMAC})
    progress = snap.progress
    if progress is None:
        return Record({'kind': 'wait', 'reason': 'Scorpion Catcher journal stage unavailable'})
    # Why: the seer's first hint is what makes the Taverley wall searchable, and the other 2 scorpions are already where they will be.
    if progress.stage < SC_STAGE.FIRST_HINT:
        return Record({'kind': 'custom', 'name': 'ask the Seer where the scorpions are', 'run': ask_the_seer})
    caught = caught_in(held)
    next_ = ([key for key in EVERY_SCORPION if not (key in caught)] or [None])[0]
    if next_ is None:
        return Record({'kind': 'talk', 'stop': THORMAC})
    return Record({'kind': 'custom', 'name': f'catch the {SCORPION_LABEL[next_]} scorpion', 'run': CATCH_LEG[next_]})


# Why: 31 Prayer is the journal's own gate, but joining the order needs it unboosted and the Jailer, the dragon corridor and Protect from Magic are all live combat the record cannot express.
def warn_readiness():
    prayer = skills.level('prayer')
    if prayer < 37:
        return f'Scorpion Catcher: Prayer {prayer}, 31 opens the monastery, but the blue dragons between the' + ' dusty-key gate and the coffins hit 30 through Protect from Magic at 37 and 50 without it'
    attack = min(skills.level('attack'), skills.level('strength'), skills.level('defence'))
    if attack < 40:
        return f'Scorpion Catcher: melee {attack}, the Jailer is level 47 and has to die for the jail key'
    return None


scorpcatcher = QuestModule(**{
    'record': quest_record('scorpcatcher'),
    'resume_at': locked_in,
    'bank': SC_TILE.BANK,
    'food': FOOD_FLOAT,
    'coin_float': max(1000, BARCRAWL_GP * 2 + ANTIPOISON_GP),
    'tools': [CAGE_NAME, SC_ITEM.DUSTY_KEY, SC_ITEM.JAIL_KEY, BARCRAWL_CARD] + list(ANTIPOISON_DOSES),
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.6}),
    'read_progress': read_scorpion_progress,
    'warn_readiness': warn_readiness,
    'decide': decide,
})
