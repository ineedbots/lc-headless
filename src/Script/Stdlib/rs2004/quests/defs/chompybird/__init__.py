"""Ported from rs2b0t's src/bot/api/ai/quests/defs/chompybird/index.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.items import equipment, inventory
from rs2004.quests.data import quest_record
from rs2004.quests.defs.chompybird.areas import ANY_BELLOWS, CB_ID, CB_NAME, CB_NPC, CB_STAGE, CB_TILE
from rs2004.quests.defs.chompybird.arrows import arrow_step, feathers_needed, walk_to
from rs2004.quests.defs.chompybird.cook import ask_kids, cook_chompy, cook_state, seasoning_step
from rs2004.quests.defs.chompybird.dialogue import talk_boxes
from rs2004.quests.defs.chompybird.hunt import catch_toad, chest_state, hunt_chompy, open_chest, watch_rantz_shoot
from rs2004.quests.defs.chompybird.journal import read_chompy_progress
from rs2004.quests.defs.chompybird.supplies import banked_id, feathers_step, held_id, loadout_step, scan_bank, tool_step, tools_held, withdraw
from rs2004.quests.defs.fightarena import kit_wanted
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.fightarena.legs import wear_kit
from rs2004.quests.exec.prompts import settle_scene

__all__ = ['decide', 'chompybird']

def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


TOADIES = 'How do we make the chompys come?'
STABBERS = ["Ok, I'll make you some 'stabbers'.", "Ok, I'll make the 'stabbers' for you."]
THANKS = 'Ok, thanks.'


def has_bellows(snap):
    return any([held_id(snap, id) > 0 for id in ANY_BELLOWS])


def bank_has_bellows(snap):
    return ([id for id in ANY_BELLOWS if banked_id(snap, id) > 0] or [None])[0]


# Why: 3 in the pack runs dry with the bird alive, and the quiver has no count on the wire, so a quivered stack is trusted and the pack has to reach this floor.
HUNT_ARROWS = 6


def has_arrows(snap):
    return held_id(snap, CB_ID.ARROW) >= HUNT_ARROWS or (snap.worn_ids is not None and CB_ID.ARROW in snap.worn_ids)


def has_bow(snap):
    return held_id(snap, CB_ID.BOW) > 0 or (snap.worn_ids is not None and CB_ID.BOW in snap.worn_ids)


# Why: the bait clearing is 15 tiles from Rantz, outside the range the npc list holds him in, so a talk from there finds nobody and fails at once.
def talk_rantz(drive, log):
    """Walk to Rantz and complete the dialogue for the current stage."""
    if drive.expect is not None and drive.expect():
        return True
    _w2 = yield from walk_to(CB_TILE.RANTZ, 3, log)
    if not (_w2):
        return False
    yield from settle_scene()
    _result3 = yield from talk_boxes(CB_NPC.RANTZ, drive, log)
    return _result3


def start_quest(log):
    return talk_rantz(Record({'prefer': STABBERS, 'ms': 60000}), log)


# Why: The handoff opens a repeating five-choice menu; select the stage-15 option once.
def give_arrows(log):
    before = inventory.count_by_id(CB_ID.ARROW)
    yield from talk_rantz(Record({'prefer': [TOADIES] + list(STABBERS) + [THANKS], 'once': [TOADIES], 'ms': 90000}), log)
    if inventory.count_by_id(CB_ID.ARROW) > before - 6:
        log('Rantz did not take the six ogre arrows')
        return False
    return True


def ask_toadies(log):
    return talk_rantz(Record({'prefer': [TOADIES, THANKS], 'once': [TOADIES], 'ms': 60000}), log)


def show_toad(log):
    return talk_rantz(Record({'prefer': [THANKS], 'ms': 60000}), log)


# Why: at 40 Rantz lends the bow through a 2-page choice and at 45 with no bow he sells a replacement first; one preference list covers both, and the bow in hand is the only proof either landed.
def get_bow(log):
    return talk_rantz(Record({
        'expect': lambda: inventory.count_by_id(CB_ID.BOW) > 0 or equipment.contains(CB_NAME.BOW),
        'prefer': ["Yes, I'll buy the bow.", 'Come on, let me have a go', "I'm actually quite strong"],
        'ms': 90000,
    }), log)


def show_chompy(log):
    return talk_rantz(Record({'prefer': [THANKS], 'ms': 60000}), log)


def hand_over(log):
    return talk_rantz(Record({'expect': lambda: inventory.count_by_id(CB_ID.SEASONED_CHOMPY) == 0, 'prefer': [THANKS], 'ms': 90000}), log)


def kit_step(snap):
    """The best melee kit the account owns, for the wolves that carry the arrow tips."""
    wanted = kit_wanted(snap)
    if len(wanted) == 0:
        return None
    carried = [name for name in wanted if (snap.inv.get(name.lower()) or 0) > 0]
    if len(carried) > 0:
        return custom(f"wear {', '.join(carried)}", lambda log: wear_kit(carried, log))
    if not snap.bank_known:
        return scan_bank()
    return withdraw([{'name': name, 'qty': 1} for name in wanted])


# Why: the chest is 100 tiles from the quest and the bank is 400, so the chest goes first and its refusal is what pays for the booth trip.
def bellows_step(snap):
    """The rock off the ogre chest, or the pair the account already banked."""
    if has_bellows(snap):
        return None
    if not chest_state.refused:
        return custom('take the ogre bellows from the chest', open_chest)
    if not snap.bank_known:
        return scan_bank()
    banked = bank_has_bellows(snap)
    if banked is not None:
        return withdraw([{'name': 'Ogre bellows', 'qty': 1, 'id': banked}])
    return Record({'kind': 'wait', 'reason': 'no ogre bellows in the chest or the bank'})


def fletch_leg(snap):
    """Feathers, shafts and tips, with an axe in the pack and the melee kit on before the wolves."""
    # Why: an achey tree with no axe in the pack answers nothing at all, no refusal and no message.
    loadout = loadout_step(snap)
    if loadout:
        return loadout
    feathers = feathers_step(snap, feathers_needed(snap))
    if feathers:
        return feathers
    next_ = arrow_step(snap)
    if not next_:
        return None
    if next_.kind == 'custom' and ('wolf' in next_.name):
        kit = kit_step(snap)
        return kit if kit is not None else next_
    return next_


# Why: Bugs answers the sale with a doubleobjbox, which suspends his script on a main modal no chat driver can see.
def buy_tools(log):
    """Buy the knife and chisel from Bugs for 10 coins."""
    _w4 = yield from walk_to(CB_TILE.BUGS, 4, log)
    if not (_w4):
        return False
    _result5 = yield from talk_boxes(CB_NPC.BUGS, Record({
        'expect': lambda: inventory.count_by_id(CB_ID.KNIFE) > 0 and inventory.count_by_id(CB_ID.CHISEL) > 0,
        'prefer': ["Ok, I'll give you 10 bright pretties.", THANKS],
        'ms': 60000,
    }), log)
    return _result5


def arrow_leg(snap):
    """Everything the 6 ogre arrows need: tools, coin, feathers, shafts and tips."""
    # Why: the wolves are 300 tiles past the bank, so the kit comes off the same booth trip as the coins.
    kit = kit_step(snap)
    if kit:
        return kit
    loadout = loadout_step(snap)
    if loadout:
        return loadout
    if not tools_held(snap):
        # Why: Bugs sells the pair for 10 coins inside the cave, which is the only tool counter this quest walks past.
        _v6 = tool_step(snap)
        return (_v6 if _v6 is not None else custom('buy the knife and chisel from Bugs', buy_tools))
    _v7 = fletch_leg(snap)
    return (_v7 if _v7 is not None else custom('hand Rantz the six ogre arrows', give_arrows))


def shooting_leg(snap):
    """The bow, the arrows and the bellows, whichever is still missing before a shot."""
    if not has_bow(snap):
        return custom('borrow the ogre bow from Rantz', get_bow)
    if not has_arrows(snap):
        if not tools_held(snap):
            # Why: Bugs stops selling once the arrows are handed over, so past that point the tools have to already exist.
            _v8 = tool_step(snap)
            return (_v8 if _v8 is not None else Record({'kind': 'wait', 'reason': 'no knife or chisel to fletch more ogre arrows with'}))
        fletch = fletch_leg(snap)
        if fletch:
            return fletch
    return bellows_step(snap)


def cook_leg(snap):
    """Ask the children, carry all 6 seasonings, then roast."""
    if not cook_state.kids_asked:
        return custom('ask Bugs and Fycie what they want', ask_kids)
    seasoning = seasoning_step(snap)
    if seasoning:
        return seasoning
    if held_id(snap, CB_ID.RAW_CHOMPY) == 0:
        _v9 = shooting_leg(snap)
        return (_v9 if _v9 is not None else custom('shoot and pluck a chompy bird', hunt_chompy))
    return custom('roast the chompy on the ogre spit', cook_chompy)


def decide(snap):
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    _v10 = (snap.progress.stage if snap.progress is not None else None)
    stage = (_v10 if _v10 is not None else snap.stage)
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest stage not readable'})
    if stage == CB_STAGE.NOT_STARTED:
        # Why: the kit, the axe and the feathers all come from the Lumbridge side of the map, so fetch them before the walk to the Feldip Hills.
        _v11 = kit_step(snap)
        _v12 = (_v11 if _v11 is not None else loadout_step(snap))
        _v13 = (_v12 if _v12 is not None else feathers_step(snap, feathers_needed(snap)))
        return (_v13 if _v13 is not None else custom("agree to make Rantz his 'stabbers'", start_quest))
    if stage == CB_STAGE.STARTED:
        return arrow_leg(snap)
    # Why: past the loan Rantz sells the replacement bow for 500-550 coins and answers an empty purse with "come back when you have", which no oracle here can tell from a dropped click; the axe is left out since only the arrow leg needs one.
    provisions = loadout_step(snap, False)
    if provisions:
        return provisions
    if stage == CB_STAGE.GIVEN_ARROWS and held_id(snap, CB_ID.TOAD) == 0:
        return custom('ask Rantz how to make the chompys come', ask_toadies)
    if stage < CB_STAGE.SHOWN_TOAD:
        if held_id(snap, CB_ID.TOAD) > 0:
            return custom('show Rantz the bloated toad', show_toad)
        _v14 = bellows_step(snap)
        return (_v14 if _v14 is not None else custom('inflate a swamp toad', catch_toad))
    if stage < CB_STAGE.RANTZ_MISSED:
        _v15 = bellows_step(snap)
        return (_v15 if _v15 is not None else custom('bait the clearing and watch Rantz shoot', watch_rantz_shoot))
    if stage < CB_STAGE.KILLED_CHOMPY:
        _v16 = shooting_leg(snap)
        return (_v16 if _v16 is not None else custom('shoot and pluck a chompy bird', hunt_chompy))
    if stage == CB_STAGE.KILLED_CHOMPY:
        if held_id(snap, CB_ID.RAW_CHOMPY) == 0:
            _v17 = shooting_leg(snap)
            return (_v17 if _v17 is not None else custom('shoot and pluck a chompy bird', hunt_chompy))
        return custom('show Rantz the raw chompy', show_chompy)
    if stage == CB_STAGE.TOLD_TO_COOK:
        return cook_leg(snap)
    # Why: the spit accepts a second chompy at stage 60, so a burnt or dropped one is recoverable.
    if held_id(snap, CB_ID.SEASONED_CHOMPY) == 0:
        return cook_leg(snap)
    return custom('hand Rantz the seasoned chompy', hand_over)


def warn_readiness():
    gaps = []
    if skills.level('crafting') < 5:
        gaps.append('Crafting 5 (the chisel refuses wolf bones below it)')
    if skills.level('attack') < 20 or skills.level('strength') < 20:
        gaps.append('a melee kit and about 40 combat (the arrow tips come off level-64 wolves)')
    return (f"untested below {' and '.join(gaps)}" if len(gaps) > 0 else None)


chompybird = QuestModule(**{
    'record': quest_record('chompybird'),
    'bank': CB_TILE.YANILLE_BANK,
    'owns_inventory': True,
    'read_progress': read_chompy_progress,
    'warn_readiness': warn_readiness,
    'decide': decide,
})
