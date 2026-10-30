"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tribaltotem.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.messages import game_messages
from rs2004.tabs import quests
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.prompts import drive_until, held_id, prompt_loc, settle_scene, use_on_loc
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record
import _core

__all__ = ['TOTEM_STAGE', 'LABEL_OBJ', 'TOTEM_OBJ', 'in_mansion', 'COMBINATION', 'parse_tribal_totem_journal', 'decide', 'tribaltotem']

QUEST = 'Tribal Totem'
TOTEM_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 1, 'CRATE_MARKED': 2, 'CRATE_DELIVERED': 3, 'TELEPORTED': 4, 'COMPLETE': 5})
LABEL_OBJ = 1858
TOTEM_OBJ = 1857
# Why: the depot has 5 locs called "Crate" and the mansion a 6th once the parcel lands, so every lookup is by id.
HORN_CRATE = 2707
TELEPORT_CRATE = 2708
COMBO_DOOR = 2705
TRAP_STAIRS = 2711
CHEST_SHUT = 2709
CHEST_OPEN = 2710
KANGAI = Record({
    'npc': 'Kangai Mau',
    'anchor': Tile(2791, 3182, 0),
    'leash': 6,
    'prefer': ['Ok, I will get it back.', "I'm in search of adventure!"],
})
CROMPERTY = Record({
    'npc': 'Wizard Cromperty',
    'anchor': Tile(2681, 3325, 0),
    'leash': 8,
    'prefer': ['So what have you invented?', 'Can I be teleported please?', 'Yes, that sounds good. Teleport me!'],
})
RPDT = Record({
    'npc': 'RPDT employee',
    'anchor': Tile(2644, 3272, 0),
    'leash': 8,
    'prefer': ['So, when are you going to deliver this crate?'],
})
# Why: the crates are walking distance from the Ardougne bank, so only the mansion leg needs Cromperty's block; it lands here before delivery.
DEPOT_STAND = Tile(2649, 3271, 0)
COMBO_STAND = Tile(2635, 3323, 0)
STAIRS_STAND = Tile(2631, 3325, 0)
CHEST_STAND = Tile(2638, 3323, 1)
QUEST_BANK = Tile(2655, 3283, 0)
# Why: the mansion is sealed, the inner door only opens outward and the way in is Cromperty's block, so a resume outside gets teleported back.
MANSION_BOXES = [
    Record({'level': 0, 'x0': 2627, 'x1': 2643, 'z0': 3322, 'z1': 3325}),
    Record({'level': 0, 'x0': 2627, 'x1': 2628, 'z0': 3320, 'z1': 3321}),
    Record({'level': 0, 'x0': 2631, 'x1': 2633, 'z0': 3320, 'z1': 3321}),
    Record({'level': 0, 'x0': 2637, 'x1': 2639, 'z0': 3320, 'z1': 3321}),
    Record({'level': 1, 'x0': 2630, 'x1': 2640, 'z0': 3318, 'z1': 3325}),
]


def in_mansion(tile):
    if not tile:
        return False
    return any([tile.level == b.level and tile.x >= b.x0 and tile.x <= b.x1 and tile.z >= b.z0 and tile.z <= b.z1 for b in MANSION_BOXES])


# Why: the packer numbers a root's components from root + 1, so `tribal_door2:com_N` is `716 + 1 + N`.
DOOR_UI = 716


def com(index):
    return DOOR_UI + 1 + index


DIAL_TEXT = [com(43), com(44), com(45), com(46)]
DIAL_DOWN = [com(47), com(49), com(51), com(53)]
DIAL_UP = [com(48), com(50), com(52), com(54)]
CONFIRM = com(57)
COMBINATION = 'KURT'
LETTERS = 26
CORRECT = 'combination seems correct'
TRAP_FOUND = 'trap in these stairs'


def parse_tribal_totem_journal(lines):
    text = normalize(lines)
    if ('quest complete!' in text):
        return QuestProgress(TOTEM_STAGE.COMPLETE, set(['combo']))
    # Why: every stage from here down repeats the ones above, so test the newest sentence first.
    if ('teleported myself inside' in text):
        flags = set()
        if ('i worked out the combination for the door' in text):
            flags.add('combo')
        return QuestProgress(TOTEM_STAGE.TELEPORTED, flags)
    if ('get wizard cromperty to teleport me inside' in text):
        return QuestProgress(TOTEM_STAGE.CRATE_DELIVERED, set())
    if ('deliver the crate now' in text):
        return QuestProgress(TOTEM_STAGE.CRATE_MARKED, set())
    if ('lord handelmorts mansion' in text):
        return QuestProgress(TOTEM_STAGE.STARTED, set())
    if ('i can start this quest by speaking to' in text):
        return QuestProgress(TOTEM_STAGE.NOT_STARTED, set())
    return None


def read_tribal_totem_progress():
    status = quests.status(QUEST)
    if status == 'complete':
        return QuestProgress(TOTEM_STAGE.COMPLETE, set(['combo']))
    if status == 'not_started':
        return QuestProgress(TOTEM_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(QUEST)
    progress = parse_tribal_totem_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress


def loc_by_id(id, within=6):
    return locs.query().where(lambda l: l.id == id).within(within).nearest()


def take_label(log):
    if held_id(LABEL_OBJ) > 0:
        return True
    log('tribaltotem: peeling the address label off the mansion crate')
    _result2 = yield from prompt_loc(Record({
        'name': 'Crate',
        'op': 'Investigate',
        'id': HORN_CRATE,
        'near': DEPOT_STAND,
        'within': 8,
        'expect': lambda: held_id(LABEL_OBJ) > 0,
    }), log)
    return _result2


def mark_crate(log):
    log("tribaltotem: covering the Wizards' Tower label with the mansion one")
    _result3 = yield from use_on_loc(LABEL_OBJ, Record({'name': 'Crate', 'near': DEPOT_STAND, 'id': TELEPORT_CRATE, 'within': 8}), [], lambda: held_id(LABEL_OBJ) == 0, log)
    return _result3


def dial_letter(index):
    text = reader.component_text(DIAL_TEXT[index])
    if text is None:
        return None
    cleaned = text.strip().upper()
    if not cleaned:
        return None
    letter = cleaned[0]
    return (letter if letter >= 'A' and letter <= 'Z' else None)


# Why: the arrows step 1 letter per click and the interface echoes the server's value, so read the dial after every click or a dropped click shifts every letter after it.
def set_dial(index, target, log):
    for clicks in range(LETTERS + 1):
        current = dial_letter(index)
        if current is None:
            log(f'tribaltotem: dial {index + 1} is not readable — the lock interface closed')
            return False
        if current == target:
            return True
        forward = (ord(target[0]) - ord(current[0]) + LETTERS) % LETTERS
        button = (DIAL_UP[index] if forward * 2 <= LETTERS else DIAL_DOWN[index])
        if not _core.click_component(button):
            return False
        _w4 = yield from execution.delay_until(lambda: dial_letter(index) != current, 3000)
        if not (_w4):
            log(f'tribaltotem: dial {index + 1} did not move off {current}')
            return False
    return dial_letter(index) == target


def solve_combination(log):
    opened = yield from prompt_loc(Record({
        'name': 'Door',
        'op': 'Open',
        'id': COMBO_DOOR,
        'near': COMBO_STAND,
        'within': 6,
        'expect': lambda: modals.main() == DOOR_UI,
        'expect_ms': 8000,
    }), log)
    if not opened:
        log('tribaltotem: the security door never raised its lock')
        return False
    for dial in range(len(COMBINATION)):
        _w5 = yield from set_dial(dial, COMBINATION[dial], log)
        if not (_w5):
            yield from modals.close_if_open()
            return False
    log(f'tribaltotem: entering {COMBINATION} on the security door')
    mark = game_messages.mark()
    if not _core.click_component(CONFIRM):
        yield from modals.close_if_open()
        return False
    # Why: `com_57` runs `if_close` before it tests the word, so the modal goes either way and only the message says which.
    accepted = yield from drive_until(lambda: game_messages.saw_since(mark, CORRECT), [], log, 8000)
    if not accepted:
        log('tribaltotem: the security door refused the combination')
        yield from modals.close_if_open()
    return accepted


# Why: `[oploc2,totemtrapstairs]` re-shows its box whether or not the trap is noted, so this is safe to repeat and no client-visible bit can skip it.
def disarm_trap(log):
    state = {'found': False}

    def noted():
        if not state['found'] and any([TRAP_FOUND in t.lower() for t in list(chat_dialog.texts()) + list(reader.main_modal_texts())]):
            state['found'] = True
        return state['found']

    log('tribaltotem: searching the stairs for the trap')
    _result6 = yield from prompt_loc(Record({
        'name': 'Stairs',
        'op': 'Investigate',
        'id': TRAP_STAIRS,
        'near': STAIRS_STAND,
        'within': 8,
        'expect': noted,
        'expect_ms': 15000,
    }), log)
    return _result6


def climb_stairs(log):
    def upstairs():
        t = game.tile()
        return t is not None and t.level == 1

    log('tribaltotem: climbing the disarmed stairs')
    climbed = yield from prompt_loc(Record({
        'name': 'Stairs',
        'op': 'Climb-up',
        'id': TRAP_STAIRS,
        'near': STAIRS_STAND,
        'within': 8,
        'expect': upstairs,
        'expect_ms': 15000,
    }), log)
    if climbed:
        yield from settle_scene()
    return climbed


def empty_chest(log):
    if loc_by_id(CHEST_OPEN, 8) is None:
        # Why: the shut chest and the open chest are 2 locs, and the shut one lingers for a tick after the Open lands.
        opened = yield from prompt_loc(Record({
            'name': 'Chest',
            'op': 'Open',
            'id': CHEST_SHUT,
            'near': CHEST_STAND,
            'within': 8,
            'expect': lambda: loc_by_id(CHEST_OPEN, 8) is not None,
            'expect_ms': 8000,
        }), log)
        if not opened:
            return False
    log('tribaltotem: searching the chest for the totem')
    _result7 = yield from prompt_loc(Record({
        'name': 'Chest',
        'op': 'Search',
        'id': CHEST_OPEN,
        'near': CHEST_STAND,
        'within': 8,
        'expect': lambda: held_id(TOTEM_OBJ) > 0,
        'expect_ms': 12000,
    }), log)
    return _result7


def take_totem(log):
    if held_id(TOTEM_OBJ) > 0:
        return True
    here = game.tile()
    if not here:
        return False
    # Why: the undisarmed stairs drop you into the Ardougne sewers for 20% of your hitpoints, so the climb is driven by hand.
    if here.level == 0:
        _w8 = yield from disarm_trap(log)
        if not (_w8):
            return False
        _w9 = yield from climb_stairs(log)
        if not (_w9):
            return False
    _result10 = yield from empty_chest(log)
    return _result10


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': KANGAI})
    progress = snap.progress
    if progress is None:
        return Record({'kind': 'wait', 'reason': 'Tribal Totem journal stage unavailable'})
    # Why: the chest refuses a second totem while one is in the pack or bank, so holding it means the quest is over bar the walk.
    _v11 = (snap.inv_ids or {}).get(TOTEM_OBJ)
    if ((_v11 if _v11 is not None else 0)) > 0:
        return Record({'kind': 'talk', 'stop': KANGAI})
    if progress.stage == TOTEM_STAGE.STARTED:
        _v12 = (snap.inv_ids or {}).get(LABEL_OBJ)
        return (Record({'kind': 'custom', 'name': "relabel the crate bound for the Wizards' Tower", 'run': mark_crate}) if ((_v12 if _v12 is not None else 0)) > 0 else Record({'kind': 'custom', 'name': 'take the address label off the mansion crate', 'run': take_label}))
    elif progress.stage == TOTEM_STAGE.CRATE_MARKED:
        return Record({'kind': 'talk', 'stop': RPDT})
    elif progress.stage == TOTEM_STAGE.CRATE_DELIVERED:
        return Record({'kind': 'talk', 'stop': CROMPERTY})
    elif progress.stage == TOTEM_STAGE.TELEPORTED:
        if not in_mansion(snap.tile):
            return Record({'kind': 'talk', 'stop': CROMPERTY})
        return (Record({'kind': 'custom', 'name': 'take the totem from the mansion chest', 'run': take_totem}) if has_flag(progress, 'combo') else Record({'kind': 'custom', 'name': 'work out the security door combination', 'run': solve_combination}))
    else:
        return Record({'kind': 'wait', 'reason': f'Tribal Totem stage {progress.stage} is not implemented'})


tribaltotem = QuestModule(**{
    'record': quest_record('totem'),
    'resume_at': in_mansion,
    'bank': QUEST_BANK,
    'tools': ['address label', 'totem', 'coins'],
    'read_progress': read_tribal_totem_progress,
    'warn_readiness': lambda: 'Tribal Totem was proven at 70 across the board; the mansion guard dogs are level 44 and hunt cowardly, so they leave a grown account alone and nothing here is fought',
    'decide': decide,
})
