"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/guild.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.quests.defs.legends.areas import LEGENDS_QUEST, LQ_ID, LQ_LOC, LQ_LOC_ID, LQ_NPC, LQ_TILE
from rs2004.quests.defs.legends.config import legends_config
from rs2004.quests.defs.legends.scene import drive_to_end, drive_until, held_id, loc_near, modal_text, prompt_loc, said_any, settle_scene
from rs2004.reach import reach
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['inside_guild', 'in_main_hall', 'enter_guild', 'start_quest', 'replace_map', 'take_machete', 'hand_in_totem', 'enter_main_hall', 'take_training']

def inside_guild():
    """Inside the guild wall: the gate sits on z=3349 and everything past it is the compound."""
    here = game.tile()
    return here is not None and here.level == 0 and here.z >= 3350 and here.x >= 2716 and here.x <= 2740 and here.z <= 3390


def in_main_hall():
    """Inside the main hall, behind the Legends Guild doors."""
    here = game.tile()
    return here is not None and here.level == 0 and here.x >= 2722 and here.x <= 2733 and here.z >= 3374 and here.z <= 3390


# Why: At stage 0, Open starts the guard dialogue instead of crossing the gate.
# Why: the guard's "Yes, I'd like to talk to Grand Vizier Erkle" branch opens the gate and teleports you through, the only way in before the quest starts.
GUARD_PREFER = [
    "Yes, I'd like to talk to Grand Vizier Erkle",
    'Can I go on the quest?',
    'What is this place?',
    'Which quests do I need to complete?',
]
# Why: Failed eligibility can end without an entry option, so detect the closed gate instead of retrying the guard indefinitely.
GUARD_REFUSED = ['complete more quests', 'quest point']
# Why: `legends_guard_start` only has a conversation before the quest starts; from stage 1 on he nods you past and says nothing, so `Reach.npcDialog` would wait out its budget on a chat that never comes.
# Why: from then on the gate is the way in: `open_legends_gate` looks for a guard within 14 tiles, has him nod, and swings the doors for anyone past `legends_not_started`.
GUILD_GATE_Z = 3349


def past_guild_gate():
    here = game.tile()
    return here is not None and here.level == 0 and here.x >= 2722 and here.x <= 2733 and here.z > GUILD_GATE_Z


def walk_through_gate(log):
    """Open the guild gate, which needs no conversation once the quest has begun."""
    for id in [LQ_LOC_ID.GUILD_GATE_L, LQ_LOC_ID.GUILD_GATE_R]:
        opened = yield from prompt_loc(Record({
            'name': LQ_LOC.GUILD_GATE,
            'op': 'Open',
            'near': LQ_TILE.GUARD,
            'within': 6,
            'id': id,
            'expect': past_guild_gate,
            'expect_ms': 12000,
        }), log)
        if opened:
            yield from settle_scene()
            return True
    log('the Legends Guild gate would not open')
    return False


def enter_guild(log):
    """Talk the patrolling guard into opening the gate."""
    if inside_guild() or past_guild_gate():
        return True
    _w1 = yield from traversal.walk_resilient(LQ_TILE.GUARD, radius=3, attempts=3, timeout_ms=180000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    if quests.status(LEGENDS_QUEST) != 'not_started':
        _result2 = yield from walk_through_gate(log)
        return _result2
    # Why: the guard patrols, so the leash-limited `gotoNpc` loses him; `Reach` searches the scene and lets the server chase.
    status = yield from reach.npc_dialog(LQ_NPC.GUARD, LQ_TILE.GUARD, log=log)
    if status != 'done':
        log('the Legends guard never opened a dialogue')
        return False
    # Why: the gate opens inside the conversation and teleports us through, so the goal is the tile.
    # Why: the refusal is caught while the chat is still up, since it's gone from `modalText` once the conversation closes.
    refused = ['']

    def inside_or_refused():
        if refused[0] == '' and said_any(modal_text(), GUARD_REFUSED):
            refused[0] = modal_text()
        return inside_guild()
    entered = yield from drive_until(inside_or_refused, GUARD_PREFER, log, 60000)
    if not entered:
        said = refused[0][0:200]
        log('the guard conversation ended with the gate still shut' if said == '' else f'the Legends guard refused entry — {said}')
    return entered


START_PREFER = ['Yes, it sounds great!', "Yes actually, what's involved?", 'Who are you?']


def start_quest(log):
    """Radimus hands over the Kharazi notes, which is what starts the quest."""
    if held_id(LQ_ID.MAP) > 0 or held_id(LQ_ID.MAP_COMPLETE) > 0:
        return True
    _w4 = yield from enter_guild(log)
    if not (_w4):
        return False
    _w5 = yield from traversal.walk_resilient(LQ_TILE.RADIMUS_STUDY, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w5):
        return False
    yield from settle_scene()
    status = yield from reach.npc_dialog(LQ_NPC.RADIMUS, LQ_TILE.RADIMUS_STUDY, log=log)
    if status != 'done':
        log('Radimus Erkle never opened a dialogue')
        return False
    _result6 = yield from drive_until(lambda: held_id(LQ_ID.MAP) > 0, START_PREFER, log, 60000)
    return _result6


# Why: `radimus_erkle_midquest` only offers the lost-map topic when neither map is held, and it charges 30 coins for the copy.
LOST_MAP_PREFER = ['Terrible, I lost my map of the Kharazi Jungle.', "Yes, I'll pay for it."]


def replace_map(log):
    """Buy a replacement map from Radimus, for a run that died holding the old one."""
    if held_id(LQ_ID.MAP) > 0 or held_id(LQ_ID.MAP_COMPLETE) > 0:
        return True
    _w7 = yield from enter_guild(log)
    if not (_w7):
        return False
    _w8 = yield from traversal.walk_resilient(LQ_TILE.RADIMUS_STUDY, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w8):
        return False
    yield from settle_scene()
    status = yield from reach.npc_dialog(LQ_NPC.RADIMUS, LQ_TILE.RADIMUS_STUDY, log=log)
    if status != 'done':
        log('Radimus Erkle never opened a dialogue for the replacement map')
        return False
    _result9 = yield from drive_until(lambda: held_id(LQ_ID.MAP) > 0, LOST_MAP_PREFER, log, 60000)
    return _result9


# Why: the cupboard is a shut loc that becomes an open one, and only the open half carries Search.
# Why: the Search branch returns silently unless Radimus is within 5 tiles, so it's only ever run from his study.
def take_machete(log):
    """Take the free machete out of Radimus' cupboard."""
    if held_id(LQ_ID.MACHETE) > 0:
        return True
    _w10 = yield from enter_guild(log)
    if not (_w10):
        return False
    _w11 = yield from traversal.walk_resilient(LQ_TILE.CUPBOARD, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w11):
        return False
    yield from settle_scene()
    if not loc_near(LQ_LOC.CUPBOARD_OPEN, 'Search', 6):
        shut = loc_near(LQ_LOC.CUPBOARD, 'Open', 6)
        if shut and (shut.interact('Open')):
            yield from execution.delay_until(lambda: loc_near(LQ_LOC.CUPBOARD_OPEN, 'Search', 6) is not None, 8000)
    _result12 = yield from prompt_loc(Record({
        'name': LQ_LOC.CUPBOARD_OPEN,
        'op': 'Search',
        'near': LQ_TILE.CUPBOARD,
        'id': LQ_LOC_ID.CUPBOARD_OPEN,
        'expect': lambda: held_id(LQ_ID.MACHETE) > 0,
    }), log)
    return _result12


HAND_IN_PREFER = ['Yes', 'Ok']


# Why: he takes the gilded totem and the finished map together, and refuses either alone.
def hand_in_totem(log):
    """Hand the gilded totem and the completed map to Radimus."""
    _w13 = yield from enter_guild(log)
    if not (_w13):
        return False
    _w14 = yield from traversal.walk_resilient(LQ_TILE.RADIMUS_STUDY, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w14):
        return False
    yield from settle_scene()
    status = yield from reach.npc_dialog(LQ_NPC.RADIMUS, LQ_TILE.RADIMUS_STUDY, log=log)
    if status != 'done':
        log('Radimus Erkle never opened a dialogue for the hand-in')
        return False
    _result15 = yield from drive_until(lambda: held_id(LQ_ID.GILDED_TOTEM) == 0, HAND_IN_PREFER, log, 60000)
    return _result15


def enter_main_hall(log):
    """The main hall doors refuse everyone below stage 50 and open freely above it."""
    if in_main_hall():
        return True
    _w16 = yield from enter_guild(log)
    if not (_w16):
        return False
    ok = yield from prompt_loc(Record({'name': LQ_LOC.GUILD_DOOR, 'op': 'Open', 'near': LQ_TILE.GUILD_DOORS, 'expect': in_main_hall}), log)
    if ok:
        yield from settle_scene()
    return ok


# Why: one conversation walks all 4 sessions, each choice re-offers the menu until the 4th, which queues the completion.
# Why: the 4 menus are `p_choice4` pages of 3 skills and a link to the next, so reaching a skill off page 1 means taking the link until its page is up.
# Why: every page carries one link, so listing all 4 costs nothing and the chosen skill coming first stops the walk when it arrives.
def training_prefer():
    """Say yes, then page to the chosen skill and take it."""
    return [
        "Yes, I'll train now.",
        f'* {legends_config.reward} *',
        '--- Go to Skill Menu 1 ----',
        '--- Go to Skill Menu 2 ----',
        '--- Go to Skill Menu 3 ----',
        '--- Go to Skill Menu 4 ----',
    ]


def take_training(log):
    """Take Radimus' 4 training sessions, which completes the quest."""
    _w17 = yield from enter_main_hall(log)
    if not (_w17):
        return False
    _w18 = yield from traversal.walk_resilient(LQ_TILE.RADIMUS_HALL, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w18):
        return False
    yield from settle_scene()
    status = yield from reach.npc_dialog(LQ_NPC.RADIMUS, LQ_TILE.RADIMUS_HALL, log=log)
    if status != 'done':
        log('Radimus Erkle never opened a dialogue in the main hall')
        return False
    # Why: live, the conversation shut after the first session on every run, with 3 still owed, and a wait on the quest completing then sat out its whole budget with nothing open. Driven to its end, the engine's next attempt talks to him again at once.
    yield from drive_to_end(training_prefer(), log, 120000)
    done = yield from execution.delay_until(lambda: quests.status(LEGENDS_QUEST) == 'complete', 3000)
    return done
