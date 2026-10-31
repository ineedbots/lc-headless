"""Ported from rs2b0t's src/bot/api/ai/quests/defs/plaguecity/west.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.game import direct_navigator, game
from rs2004.items import inventory
from rs2004.quests.defs.plaguecity.areas import PC_ITEM, PC_LOC, PC_NPC, PC_TILE
from rs2004.quests.defs.plaguecity.east import talk_at
from rs2004.quests.defs.plaguecity.travel import area, go_cellar, go_upstairs, loc_by_id, walk_to
from rs2004.quests.exec.prompts import drive_choice, held_id, settle_scene

__all__ = ['show_picture', 'ask_parents', 'enter_rehnisons', 'ask_milli', 'ask_about_clearance', 'give_hangover_cure', 'get_audience', 'rescue_elena']

JETHICK_PREFER = ["I'm looking for a woman from East Ardougne."]
MOURNER_PREFER = ['I fear not a mere plague.', 'How do I get clearance?']
CLERK_PREFER = ['I need permission to enter a plague house.', 'This is urgent though!']
BRAVEK_RECIPE_PREFER = ['This is really important though!', 'Do you know what is in the cure?']
BRAVEK_WARRANT_PREFER = ["They won't listen to me!"]


def answer_prompt(prefer, log):
    _w1 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w1):
        return True
    answered = yield from drive_choice(prefer, log)
    yield from execution.delay_ticks(2)
    return answered


def open_door(id, near, prefer, log):
    _w2 = yield from walk_to(near, 1, log)
    if not (_w2):
        return False
    yield from settle_scene()
    door = loc_by_id(id, 'Open', 6)
    if not door:
        log(f'no shut door {id} near ({near.x},{near.z}) — already open')
        return True
    if not (door.interact('Open')):
        return False
    _result3 = yield from answer_prompt(prefer, log)
    return _result3


def show_picture(log):
    return talk_at(PC_NPC.JETHICK, PC_TILE.JETHICK, JETHICK_PREFER, log)


def return_book(log):
    _w4 = yield from open_door(PC_LOC.REHNISON_DOOR, PC_TILE.REHNISON_DOOR, [], log)
    if not (_w4):
        return False
    _result5 = yield from execution.delay_until(lambda: held_id(PC_ITEM.TURNIP_BOOK.id) == 0, 10000)
    return _result5


def ask_parents(log):
    return talk_at(PC_NPC.TED, PC_TILE.REHNISON_TED, [], log)


# Why: the journal renders stages 20 and 21 identically, so one leg covers the book hand-over and the question after it.
# Why: a shut Rehnison door is the only state where the family refuses to talk, so that sends this back to Jethick.
def enter_rehnisons(log):
    _c6 = held_id(PC_ITEM.TURNIP_BOOK.id) > 0
    if _c6:
        _w7 = yield from return_book(log)
        _c6 = not (_w7)
    if _c6:
        return False
    _w8 = yield from ask_parents(log)
    if _w8:
        return True
    log('the Rehnisons would not talk — asking Jethick for another book')
    _result9 = yield from show_picture(log)
    return _result9


def ask_milli(log):
    _w10 = yield from go_upstairs(log)
    if not (_w10):
        return False
    _result11 = yield from talk_at(PC_NPC.MILLI, PC_TILE.MILLI, [], log)
    return _result11


# Why: doors.rs2 gates every branch of this door on `npc_find(coord, mournertwb, 14, 0)`, and with no mourner in range the op returns with no message, door state or dialogue.
MOURNER_EARSHOT = 14


def knock_plague_door(prefer, log):
    _w12 = yield from walk_to(PC_TILE.PLAGUE_DOOR, 0, log)
    if not (_w12):
        return False
    yield from settle_scene()

    def _fn13():
        mourner = npcs.query().name(PC_NPC.MOURNER).nearest()
        return mourner is not None and mourner.distance() <= MOURNER_EARSHOT
    heard = yield from execution.delay_until(_fn13, 30000)
    if not heard:
        log(f'no {PC_NPC.MOURNER} within {MOURNER_EARSHOT} tiles of the plague house door — the op does nothing without one')
        return False
    door = loc_by_id(PC_LOC.PLAGUE_DOOR, 'Open', 6)
    if not door:
        return True
    if not (door.interact('Open')):
        return False
    _result14 = yield from answer_prompt(prefer, log)
    return _result14


def ask_about_clearance(log):
    return knock_plague_door(MOURNER_PREFER, log)


# Why: the clerk only calls Bravek in while you're within 7 tiles, and Bravek has no wanderrange, so he drifts the default 5 tiles around his desk.
CLERK_LEASH = 7


def ask_clerk(log):
    _w15 = yield from walk_to(PC_TILE.CLERK, 1, log)
    if not (_w15):
        return False

    def _fn16():
        bravek = npcs.query().name(PC_NPC.BRAVEK).nearest()
        return bravek is not None and bravek.distance() <= CLERK_LEASH
    near = yield from execution.delay_until(_fn16, 30000)
    if not near:
        here = game.tile()
        bravek = npcs.query().name(PC_NPC.BRAVEK).nearest()
        _v17 = (bravek.distance() if bravek is not None else None)
        log(f"Bravek is {(_v17 if _v17 is not None else '?')} tiles from ({(here.x if here is not None else None)},{(here.z if here is not None else None)}) — too far for the clerk to call him in")
        return False
    _result18 = yield from talk_at(PC_NPC.CLERK, PC_TILE.CLERK, CLERK_PREFER, log, 1)
    return _result18


def in_bravek_room():
    here = game.tile()
    return here is not None and here.level == 0 and here.x >= 2530 and here.x <= 2539 and here.z >= 3312 and here.z <= 3316


# Why: his door reverts 2 ticks after it lets anyone through, so walking back to the stand from inside would shut it and reopen it every leg.
# Why: it also refuses everyone until the clerk calls him in, and the walker would spend minutes retrying the crossing.
def reach_bravek(log):
    if in_bravek_room():
        return True
    _w19 = yield from open_door(PC_LOC.BRAVEK_DOOR, PC_TILE.BRAVEK_DOOR, [], log)
    if not (_w19):
        return False
    if in_bravek_room():
        return True
    log('Bravek is still busy — the clerk has not called him in yet')
    return False


def ask_bravek_for_recipe(log):
    _w20 = yield from reach_bravek(log)
    if not (_w20):
        return False
    _result21 = yield from talk_at(PC_NPC.BRAVEK, PC_TILE.BRAVEK, BRAVEK_RECIPE_PREFER, log)
    return _result21


def give_hangover_cure(log):
    _w22 = yield from reach_bravek(log)
    if not (_w22):
        return False
    _result23 = yield from talk_at(PC_NPC.BRAVEK, PC_TILE.BRAVEK, BRAVEK_WARRANT_PREFER, log)
    return _result23


# Why: stages 24 and 25 render the same journal line, and the clerk's stage-25 answer is a single harmless line, so one leg covers both.
def get_audience(log):
    _w24 = yield from ask_clerk(log)
    if not (_w24):
        return False
    _result25 = yield from ask_bravek_for_recipe(log)
    return _result25


# Why: the door opens for a warrant holder mid-conversation, so the last tile is a scene step the baked pathfinder never sees.
def enter_plague_house(log):
    _w26 = yield from knock_plague_door([], log)
    if not (_w26):
        return False
    yield from direct_navigator.walk_to(PC_TILE.PLAGUE_DOOR_INSIDE, 0, 6000)
    if inside_plague_house():
        return True
    log('the mourner did not turn their back — the plague house door stayed shut')
    return False


# Why: the house's north wall steps back a tile east of the door, so a flat box either claims the doorstep as inside or the east strip as outside.
def inside_plague_house():
    here = game.tile()
    if here is None or here.level != 0 or here.x < 2532 or here.x > 2541:
        return False
    return here.z >= 3268 and here.z <= ((3272 if here.x >= 2535 else 3271))


def rescue_elena(log):
    _c27 = area() != 'cellar' and not inside_plague_house()
    if _c27:
        _w28 = yield from enter_plague_house(log)
        _c27 = not (_w28)
    if _c27:
        return False
    _c29 = area() != 'cellar' and held_id(PC_ITEM.ELENA_KEY.id) == 0
    if _c29:
        _w30 = yield from search_barrel(log)
        _c29 = not (_w30)
    if _c29:
        return False
    _result31 = yield from free_elena(log)
    return _result31


def search_barrel(log):
    _w32 = yield from walk_to(PC_TILE.BARREL, 1, log)
    if not (_w32):
        return False
    yield from settle_scene()
    barrel = loc_by_id(PC_LOC.BARREL, 'Search', 6)
    if not barrel or not (barrel.interact('Search')):
        log('no Barrel offering Search on the plague house floor')
        return False
    _result33 = yield from execution.delay_until(lambda: held_id(PC_ITEM.ELENA_KEY.id) > 0, 10000)
    return _result33


def free_elena(log):
    _w34 = yield from go_cellar(log)
    if not (_w34):
        return False
    _w35 = yield from walk_to(PC_TILE.ELENA_GATE, 1, log)
    if not (_w35):
        return False
    yield from settle_scene()
    gate = loc_by_id(PC_LOC.ELENA_GATE, 'Open', 6)
    if gate:
        key = ([item for item in inventory.items() if item.id == PC_ITEM.ELENA_KEY.id] or [None])[0]
        if not key:
            log("no key for Elena's cell door")
            return False
        if not (key.use_on(gate)):
            return False
        yield from answer_prompt([], log)
    _result36 = yield from talk_at(PC_NPC.ELENA, PC_TILE.ELENA, [], log)
    return _result36
