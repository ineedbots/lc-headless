"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.data import quest_record
from rs2004.quests.defs.fremenniktrials.areas import BRUNDT, FT_ID, FT_LOC, FT_TILE, MAZE_ROUTE, THORVALD, in_battleground, in_maze, in_puzzle_room, in_seer_east, in_seer_west
from rs2004.quests.defs.fremenniktrials.bard import bard_step
from rs2004.quests.defs.fremenniktrials.hunter import hunter_step
from rs2004.quests.defs.fremenniktrials.journal import FT_STAGE, parse_fremennik_journal, read_fremennik_progress
from rs2004.quests.defs.fremenniktrials.merchant import merchant_step
from rs2004.quests.defs.fremenniktrials.navigator import navigator_step
from rs2004.quests.defs.fremenniktrials.reveller import reveller_step
from rs2004.quests.defs.fremenniktrials.seer import riddle_answer, seer_step
from rs2004.quests.defs.fremenniktrials.warrior import PROVEN_PRAYER, leave_loft_step, on_loft, warrior_step
from rs2004.quests.engine.types import QuestModule, has_flag

__all__ = ['parse_fremennik_journal', 'read_fremennik_progress', 'FT_STAGE', 'riddle_answer', 'FT_ID', 'FT_LOC', 'FT_TILE', 'MAZE_ROUTE', 'decide', 'fremenniktrials']

VOTES_NEEDED = 7


def in_sealed_trial(t):
    """Where a trial is walked with a way out only it knows: Peer's house, Swensen's maze, Koschei's ground, Thorvald's loft."""
    return in_puzzle_room(t) or in_seer_west(t) or in_seer_east(t) or in_maze(t) or in_battleground(t) or on_loft(t)


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    stage = (snap.progress.stage if snap.progress is not None else None)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    # Why: `ownsInventory` skips the engine's provisioning, so nothing else ever opens a booth and a banked shark stays invisible until this read happens.
    # Why: a restart inside a sealed trial has no route to a booth, and the trial's own step is the way out.
    if not snap.bank_known and not in_sealed_trial(snap.tile):
        return Record({'kind': 'scan_bank', 'bank': FT_TILE.SEERS_BANK})
    if stage == FT_STAGE.NOT_STARTED:
        return Record({
            'kind': 'talk',
            'stop': BRUNDT(['Do you have any quests?', 'Yes, I am interested.', 'I want to become a Fremennik!']),
        })
    # Why: the 7th vote comes from the honourable death, which leaves you on a loft the walker has no edge off, so Brundt is unreachable until that ladder is climbed.
    loft = leave_loft_step(snap)
    if loft:
        return loft
    if stage >= VOTES_NEEDED:
        return Record({'kind': 'talk', 'stop': BRUNDT(['Ask about becoming a Fremennik'])})
    # Why: this is the order the map wants: the longhall trials, then the 2 east of town, then the maze, then the trade chain.
    # Why: the seer and the warrior come last because both are walked with an empty pack, and Peer's spell empties it.
    _v1 = reveller_step(snap)
    _v2 = (_v1 if _v1 is not None else bard_step(snap))
    _v3 = (_v2 if _v2 is not None else hunter_step(snap))
    _v4 = (_v3 if _v3 is not None else navigator_step(snap))
    trial = (_v4 if _v4 is not None else merchant_step(snap))
    if trial:
        return trial
    # Why: Peer only offers to bank your equipment while Thorvald's trial is open, and the last 2 trials are walked with nothing.
    if not has_flag(snap.progress, 'warrior-started') and not has_flag(snap.progress, 'warrior-done'):
        return Record({'kind': 'talk', 'stop': THORVALD(['Yes'])})
    _v5 = seer_step(snap)
    _v6 = (_v5 if _v5 is not None else warrior_step(snap))
    return (_v6 if _v6 is not None else Record({'kind': 'wait', 'reason': 'seven votes are in but Brundt has not been told'}))


def readiness():
    gaps = []
    for skill, level in [['woodcutting', 40], ['crafting', 40], ['fletching', 25]]:
        if skills.level(skill) < level:
            gaps.append(f'{skill} {skills.level(skill)}/{level}')
    if len(gaps) > 0:
        return f"The Fremennik Trials needs {', '.join(gaps)}"
    if skills.level('prayer') < PROVEN_PRAYER:
        return f'The Fremennik Trials wants Prayer {PROVEN_PRAYER} — Koschei\'s first three forms kill an unarmed character once Protect from Melee runs dry'
    return 'The Fremennik Trials fights a level 69 Draugen and needs a raw shark — bank one, or the bot buys it from Rufus in Canifis'


fremenniktrials = QuestModule(**{
    'record': quest_record('viking'),
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'bank': FT_TILE.SEERS_BANK,
    'owns_inventory': True,
    'grind': ['The Draugen', 'Koschei the deathless'],
    'tools': ['coins', 'knife', 'axe', 'tinderbox', 'raw shark'],
    'sustain': Record({'foods': ['Lobster', 'Swordfish', 'Tuna'], 'eat_below_hp': 0.5}),
    'read_progress': read_fremennik_progress,
    'resume_at': in_sealed_trial,
    'warn_readiness': readiness,
    'decide': decide,
})
