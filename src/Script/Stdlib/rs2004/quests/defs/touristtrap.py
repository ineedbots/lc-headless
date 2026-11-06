"""Ported from rs2b0t's src/bot/api/ai/quests/defs/touristtrap.ts (MIT, see thirdparty/rs2b0t)."""

import _core
import math
from rs2004 import execution
from rs2004.bank import bank, banking
from rs2004.catalogs.combat import food_forms
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.navigation import reachability
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.exec.fund_coins import earn_quest_coins_step
from rs2004.quests.food import quest_food
from rs2004.quests.journal_text import normalize_journal as journal_text
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['TOURIST_TRAP_STAGE', 'parse_tourist_trap_journal', 'tourist_trap_area', 'strict_tourist_trap_choice', 'waterskin_doses', 'forge_bar_wasted_since', 'run_surface_rescue_checkpoint', 'observe_tourist_trap', 'decide', 'touristtrap']

# Why: the journal collapses the hidden transport stages 19..26 and reward choices 27..29, so the world and inventory probes below resolve those ranges.
# Stages the client can see.
TOURIST_TRAP_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'APPROACHED_CAPTAIN': 3,
    'KILLED_CAPTAIN': 4,
    'ENTERED_CAMP': 5,
    'SPOKEN_SLAVE': 6,
    'FREED_SLAVE': 7,
    'TRADED_CLOTHES': 8,
    'ENTERED_MINE': 9,
    'FINDING_PINEAPPLE': 10,
    'BEDABIN_KEY': 11,
    'RETRIEVED_PLANS': 12,
    'SHOWN_PLANS': 13,
    'MADE_DART_TIP': 14,
    'FINISHED_DART': 15,
    'LEARNED_DARTS': 16,
    'GIVEN_PINEAPPLE': 17,
    'USED_MINE_CART': 18,
    'RESCUE': 19,
    'REWARD': 27,
    'COMPLETE': 30,
})


def parse_tourist_trap_journal(lines):
    text = journal_text(lines)
    # The journal is cumulative, so test the newest milestone first.
    if ('quest complete!' in text):
        return TOURIST_TRAP_STAGE.COMPLETE
    if ('talk to irena' in text) and ('for my reward' in text):
        return TOURIST_TRAP_STAGE.REWARD
    if ('get ana' in text) and ('her barrel' in text) and ('out of this mine camp' in text):
        return TOURIST_TRAP_STAGE.RESCUE
    if ('find some way of getting ana out' in text):
        return TOURIST_TRAP_STAGE.USED_MINE_CART
    if ('i am sure ana is down here' in text):
        return TOURIST_TRAP_STAGE.GIVEN_PINEAPPLE
    if ('now i have a pineapple' in text) or (('misplaced it' in text) and ('another one' in text)):
        return TOURIST_TRAP_STAGE.LEARNED_DARTS
    if ('made a prototype dart' in text):
        return TOURIST_TRAP_STAGE.FINISHED_DART
    if ('made the prototype dart tip' in text):
        return TOURIST_TRAP_STAGE.MADE_DART_TIP
    if ('if i make him a' in text) and ('prototype' in text):
        return TOURIST_TRAP_STAGE.SHOWN_PLANS
    if ('captain siad' in text) and ('stolen the plans' in text):
        return TOURIST_TRAP_STAGE.RETRIEVED_PLANS
    if ('if i can steal the' in text) and ('plans' in text):
        return TOURIST_TRAP_STAGE.BEDABIN_KEY
    if ("get the mine guard a 'tenti' pineapple" in text):
        return TOURIST_TRAP_STAGE.FINDING_PINEAPPLE
    if ('head deeper into the mine' in text):
        return TOURIST_TRAP_STAGE.ENTERED_MINE
    if ('head into the mine' in text) and ('look for ana' in text):
        return TOURIST_TRAP_STAGE.TRADED_CLOTHES
    if ('trade my desert robes' in text):
        return TOURIST_TRAP_STAGE.FREED_SLAVE
    if ('undo the locks on the slave' in text):
        return TOURIST_TRAP_STAGE.SPOKEN_SLAVE
    if ('look around this desert mining camp' in text):
        return TOURIST_TRAP_STAGE.ENTERED_CAMP
    if ('inside a desert mining camp' in text):
        return TOURIST_TRAP_STAGE.KILLED_CAPTAIN
    if ('feeling ana must be around here' in text):
        return TOURIST_TRAP_STAGE.APPROACHED_CAPTAIN
    if ('head into the desert' in text) and ('search for ana' in text):
        return TOURIST_TRAP_STAGE.STARTED
    if ('start this quest by speaking to irena' in text):
        return TOURIST_TRAP_STAGE.NOT_STARTED
    return None


def read_tourist_trap_stage():
    # The 2004 journal calls it "Tourist Trap"; some quest-list revisions add "The".
    names = ['The Tourist Trap', 'Tourist Trap']
    statuses = [(Record({'name': name, 'status': quests.status(name)})) for name in names]
    if any([entry.status == 'complete' for entry in statuses]):
        return TOURIST_TRAP_STAGE.COMPLETE
    if any([entry.status == 'not_started' for entry in statuses]):
        return TOURIST_TRAP_STAGE.NOT_STARTED
    active = ([entry for entry in statuses if entry.status == 'in_progress'] or [None])[0]
    if not active:
        return None
    lines = yield from quests.journal(active.name)
    stage = parse_tourist_trap_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage


def tourist_trap_area(tile):
    if not tile:
        return 'unknown'
    # The cells sit inside the camp/mine rectangles, so test them first.
    in_surface_cell = tile.level == 0 and tile.x >= 3284 and tile.x <= 3286 and tile.z >= 3032 and tile.z <= 3036
    escape_tiles = set(['3283,3032', '3282,3037', '3279,3038', '3277,3039', '3275,3040'])
    on_surface_escape_rocks = tile.level == 0 and (f'{tile.x},{tile.z}' in escape_tiles)
    if in_surface_cell or on_surface_escape_rocks:
        return 'surfaceJail'
    if tile.x >= 3274 and tile.x <= 3306 and tile.z >= 3011 and tile.z <= 3043:
        return ('campUpper' if tile.level == 1 else 'campSurface')
    if tile.level == 0 and tile.x >= 3264 and tile.x <= 3327 and tile.z >= 9408 and tile.z <= 9471:
        # Order checked against every walkable tile in m51_147; the cave wall, punishment gate and cart each split adjacent coordinates.
        if tile.x <= 3282:
            return 'mineEntrance'
        if tile.x >= 3285 and tile.x <= 3292 and tile.z >= 9429 and tile.z <= 9452:
            return 'undergroundJail'
        if tile.x >= 3315 or tile.z >= 9428:
            return 'mineDeep'
        return 'mineLower'
    if tile.level == 0 and tile.x >= 3167 and tile.x <= 3176 and tile.z >= 3046 and tile.z <= 3052:
        return 'bedabinTent'
    if tile.level == 0 and tile.x >= 3150 and tile.x <= 3200 and tile.z >= 2990 and tile.z <= 3070:
        return 'bedabin'
    if tile.level == 0 and tile.x >= 3300 and tile.x <= 3314 and tile.z >= 3109 and tile.z <= 3116:
        return 'irena'
    if tile.level == 0 and tile.x >= 3288 and tile.x <= 3320 and tile.z >= 3117 and tile.z <= 3140:
        return 'shantayNorth'
    if tile.level == 0 and tile.z < 3117:
        return 'desert'
    if tile.level == 0:
        return 'mainland'
    return 'unknown'


DRAYNOR_BANK = Tile(3093, 3243, 0)
BOB_AXES = Record({'npc': 'Bob', 'anchor': Tile(3232, 3203, 0)})
KEBAB_SELLER = Tile(3272, 3182, 0)
SHANTAY_SHOP = Record({'npc': 'Shantay', 'anchor': Tile(3304, 3123, 0)})
SHANTAY_PASS = Tile(3302, 3116, 0)
SHANTAY_NORTH_APPROACH = Tile(3302, 3118, 0)
SHANTAY_SOUTH_APPROACH = Tile(3302, 3114, 0)
IRENA = Tile(3303, 3113, 0)
CAPTAIN = Tile(3270, 3029, 0)
CAMP_GATE = Tile(3273, 3029, 0)
SLAVE = Tile(3302, 3016, 0)
MINE_ENTRANCE = Tile(3301, 3036, 0)
# Source reverse-cave landing on the guards' west-mine component. (3279,9420) looks right but is a sealed collision component.
CAVE_GUARD = Tile(3278, 9415, 0)
CAVE_GUARD_POST = {'min_x': 3274, 'max_x': 3284, 'min_z': 9413, 'max_z': 9423}
AL_SHABIM = Tile(3171, 3025, 0)
# Why: interior tent tiles like (3169,3046) are a sealed collision component (walks from Shantay or Irena stop "unreachable", best about 135), so stand 1 south of the door and Walk-through.
BEDABIN_TENT_APPROACH = Tile(3169, 3045, 0)
EXPERIMENTAL_ANVIL = Tile(3171, 3048, 0)
CAMP_LADDER = Tile(3290, 3036, 0)
SIAD_BOOKCASE = Tile(3284, 3032, 1)
SIAD_DESK = Tile(3290, 3033, 1)
SIAD_CHEST = Tile(3292, 3033, 1)
LOWER_BARREL = Tile(3303, 9415, 0)
LOWER_CART = Tile(3303, 9417, 0)
DEEP_CART = Tile(3318, 9430, 0)
ROWDY_SLAVE = Tile(3288, 9446, 0)
ANA_TILE = Tile(3302, 9466, 0)
LIFT_BUCKET = Tile(3292, 9423, 0)
CAVE_OUTER_LANDING = Tile(3278, 9415, 0)
CAVE_INNER_LANDING = Tile(3286, 9415, 0)
MINE_EXIT_DOOR = Tile(3278, 9426, 0)
MINE_EXIT_INSIDE_STAND = Tile(3278, 9427, 0)
# The winch loc's origin (3279,3017) is occupied collision, so approach from the open south-east tile.
SURFACE_WINCH_APPROACH = Tile(3280, 3018, 0)
# 3 tiles from the quest's upper barrel at (3278,3017) only; the decorative full barrel stays outside locAt's filter.
SURFACE_BARREL_APPROACH = Tile(3281, 3017, 0)
# The cart's origin (3287,3023) is inside its 2x3 footprint; the west edge keeps the driver at (3287,3022) within the dialogue leash.
SURFACE_CART_APPROACH = Tile(3286, 3023, 0)
SURFACE_JAIL = Tile(3285, 3034, 0)
# Why: the cell wall carries a window on each face, (3283,3032) outside and this one inside, both within reach of the
# jail anchor, and only the inside one can be reached from the cell. This departs from rs2b0t.
CELL_WINDOW = Tile(3284, 3032, 0)
UNDERGROUND_JAIL = Tile(3288, 9437, 0)
NPC = Record({
    'ANA': 822,
    'SLAVE': 825,
    'ESCAPED_SLAVE': 826,
    'ROWDY_SLAVE': 827,
    'CAPTAIN': 830,
    'SIAD': 831,
    'AL_SHABIM': 832,
    'BEDABIN_GUARD': 834,
    'IRENA': 835,
    'SHANTAY': 836,
    'MINE_CART_DRIVER': 841,
})
LOC = Record({
    'SHANTAY_PASS': 4031,
    'CAMP_GATE': [2673, 2674],
    'SURFACE_MINE_DOOR': [2675, 2676],
    'LADDER_UP': 1747,
    'LADDER_DOWN': 1746,
    'BOOKCASE': 2678,
    'SIAD_DESK': 2679,
    'CHEST': 2677,
    'ANVIL': 2672,
    'BEDABIN_TENT_DOOR': 2700,
    'UNDERGROUND_MINE_DOOR': [2690, 2691],
    'MINE_CAVE': [2698, 2699],
    'EMPTY_BARREL': 2681,
    'MINE_CART': 2684,
    'LIFT_BUCKET': 2668,
    'SURFACE_WINCH': 2667,
    'FULL_BARREL': 2680,
    'SURFACE_CART': 2682,
    'WINDOW': 2683,
    'PUNISHMENT_GATE': [2685, 2686],
    'PUNISHMENT_ROCK': 2704,
})
PUNISHMENT_ROCK_ID = 1855
ITEM = Record({
    'COINS': 'Coins',
    'PICKAXE': 'Bronze pickaxe',
    'KEBAB': 'Kebab',
    'DESERT_SHIRT': 'Desert shirt',
    'DESERT_ROBE': 'Desert robe',
    'DESERT_BOOTS': 'Desert boots',
    'SLAVE_SHIRT': "Slaves' shirt",
    'SLAVE_ROBE': 'Slave robe',
    'SLAVE_BOOTS': 'Slave boots',
    'WATERSKIN': 'Waterskin(4)',
    'BAR': 'Bronze bar',
    'FEATHER': 'Feather',
    'HAMMER': 'Hammer',
    'PASS': 'Shantay pass',
    'DISCLAIMER': 'Shantay disclaimer',
    'METAL_KEY': 'Metal key',
    'CELL_KEY': 'Cell door key',
    'BEDABIN_KEY': 'Bedobin key',
    'PLANS': 'Technical plans',
    'DART_TIP': 'Prototype dart tip',
    'DART': 'Prototype dart',
    'PINEAPPLE': 'Tenti pineapple',
    'BARREL': 'Barrel',
    'ANA_BARREL': 'Ana in a barrel',
})
DESERT_OUTFIT = [ITEM.DESERT_SHIRT, ITEM.DESERT_ROBE, ITEM.DESERT_BOOTS]
SLAVE_OUTFIT = [ITEM.SLAVE_SHIRT, ITEM.SLAVE_ROBE, ITEM.SLAVE_BOOTS]
SLAVE_OUTFIT_DROP_IDS = [1844, 1845, 1846]
WATERSKINS = ['Waterskin(4)', 'Waterskin(3)', 'Waterskin(2)', 'Waterskin(1)', 'Waterskin(0)']
FOOD_ENTRY_TARGET = 16
FOOD_ENTRY_FLOOR = 12
FOOD_RESTOCK_FLOOR = 4
WATER_ENTRY_DOSES = 16
WATER_ENTRY_FLOOR = 12
WATER_RESTOCK_FLOOR = 8
RESCUE_COIN_FLOOR = 100
RESCUE_COIN_TARGET = 200
IRENA_START = [
    "What's the matter?",
    'Is there a reward if I get her back?',
    "Okay Irena, calm down. I'll get your daughter back for you.",
]
CAPTAIN_DUEL = [
    'Wow! A real captain!',
    "I'd love to work for a tough guy like you!",
    "Can't I do something for a strong Captain like you?",
    "Sorry Sir, I don't think I can do that.",
    "It's a funny captain who can't fight his own battles!",
]
SLAVE_INTRO = [
    "I've just arrived.",
    'Oh yes, that sounds interesting.',
    "What's that then?",
    'I can try to undo them for you.',
]
SLAVE_LOCK = ["It's funny you should say that...", "Yeah, okay, let's give it a go.", "Yeah I'll give it another go."]
SLAVE_TRADE = ["It's funny you should say that...", "Yes, I'll trade."]
CAVE_GUARD_DIALOG = [
    "I'd like to mine in a different area.",
    "Yes sir, you're quite right sir.",
    'Yes sir, we understand each other perfectly.',
]
AL_PINEAPPLE = ['I am looking for a pineapple.', "Yes, I'm interested."]
SIAD_DISTRACTION = [
    'I wanted to have a chat?',
    'You seem to have a lot of books!',
    "So, you're interested in sailing?",
    'I could tell by the cut of your jib.',
]
AL_PLANS = ["Yes, I'm very interested.", "Yes, I'm kind of curious."]
ANVIL_DIALOG = ["Yes, I'd like to try."]
LIFT_GUARD_DIALOG = ['Yes please.', 'I said you were very gregarious!']
DRIVER_DIALOG = [
    'Nice cart.',
    "One wagon wheel says to the other, 'I'll see you around'.",
    "'One good turn deserves another'",
    'Fired... no, shot perhaps!',
    'In for a penny in for a pound.',
    "Well, you see, it's like this...",
    "There's ten gold in it for you if you leave now - no questions asked.",
    'A hundred it is!',
]
DRIVER_NO_COIN_DIALOG = list(DRIVER_DIALOG[0:6]) + ['Prison riot in ten minutes, get your cart out of here!', "You can't leave me here, I'll get killed!"]


def normalize_choice(text):
    return ' '.join(text.split()).lower()


def strict_tourist_trap_choice(options, prefer):
    allowed = set([normalize_choice(_x) for _x in prefer])
    _v1 = ([option for option in options if (normalize_choice(option) in allowed)] or [None])[0]
    return (_v1 if _v1 is not None else None)


def drive_strict_dialog(prefer, log, until=None):
    """Strict quest-local dialogue driver; it never guesses when a menu changes."""
    reached_until = False
    for i in range(140):
        if event_signal.pending():
            return False
        if (until() if until is not None else None):
            reached_until = True
        if chat_dialog.can_continue():
            _w2 = yield from chat_dialog.continue_()
            if not (_w2):
                return False
            yield from execution.delay_ticks(1)
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            selected = strict_tourist_trap_choice(options, prefer)
            if not selected:
                log(f"Tourist Trap dialogue stopped: unrecognized options [{' | '.join(options)}]")
                return False
            _w3 = yield from chat_dialog.choose_option(selected)
            if not (_w3):
                return False
            yield from execution.delay_ticks(1)
            continue
        if not chat_dialog.is_open():
            if not until or reached_until:
                return True
            # Some source conversations close the modal for a few ticks mid-flow; the until predicate tells that gap from completion.
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_ticks(1)
    log('Tourist Trap dialogue exceeded its bounded step count')
    return False


def drain_interaction_dialog(prefer, log, until=None):
    started = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue() or (until() if until is not None else None) == True, (8000 if len(prefer) > 0 or until else 1500))
    if not started:
        yield from execution.delay_ticks(2)
        return (until() if until else len(prefer) == 0)
    if not chat_dialog.is_open() and not chat_dialog.can_continue():
        return (until() if until is not None else None) == True
    _result4 = yield from drive_strict_dialog(prefer, log, until)
    return _result4


def dialog_matches(pattern):
    """Whether any open dialogue text passes pattern, a predicate over the text."""
    return any([pattern(text) for text in chat_dialog.texts()])


def any_phrase(*phrases):
    """A case-insensitive test for any of phrases, for rs2b0t's /a|b/i."""
    wanted = [phrase.lower() for phrase in phrases]

    def test(text):
        lowered = text.lower()
        return any([phrase in lowered for phrase in wanted])
    return test


def talk_action(actions_list):
    _v5 = ([action for action in actions_list if (action.lower().startswith('talk'))] or [None])[0]
    return (_v5 if _v5 is not None else None)


def walk(anchor, radius, log):
    here = game.tile()
    if here and here.level == anchor.level and anchor.distance_to(here) <= radius:
        return True
    _result6 = yield from traversal.walk_resilient(anchor, radius=radius, attempts=4, timeout_ms=180000, log=log)
    return _result6


def talk_strict(npc_id, anchor, prefer, log, leash=8, until=None):
    npc_ids = ([npc_id] if ((isinstance(npc_id, int) or isinstance(npc_id, float)) and not isinstance(npc_id, bool)) else npc_id)
    if not chat_dialog.is_open():
        _w7 = yield from walk(anchor, min(3, leash), log)
        if not (_w7):
            return False
        npc = npcs.query().where(lambda candidate: (candidate.id in npc_ids) and talk_action(candidate.actions()) is not None).within(leash).nearest()
        if not npc:
            log(f"no Tourist Trap NPC [{','.join([str(i) for i in npc_ids])}] available near ({anchor.x},{anchor.z})")
            return False
        if not (npc.interact(talk_action(npc.actions()))):
            return False
        _w8 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
        if not (_w8):
            return False
    _result9 = yield from drive_strict_dialog(prefer, log, until)
    return _result9


def loc_at(ids, op, anchor, radius=8):
    return locs.query().where(lambda loc: (loc.id in ids) and loc.tile().distance_to(anchor) <= 3).action(op).within(radius).nearest()


def interact_loc(ids, op, anchor, log, prefer=None, until=None):
    if prefer is None:
        prefer = []
    _w10 = yield from walk(anchor, 3, log)
    if not (_w10):
        return False
    # The walk may take a transport edge on the way, so check the postcondition before looking for a loc that's now in the previous scene.
    if (until() if until is not None else None):
        return True
    loc = loc_at(ids, op, anchor, 10)
    if not loc:
        log(f"no Tourist Trap loc [{','.join([str(i) for i in ids])}] offering '{op}' near ({anchor.x},{anchor.z})")
        return False
    if not (loc.interact(op)):
        return False
    _result11 = yield from drain_interaction_dialog(prefer, log, until)
    return _result11


def use_item_on_loc(item_name, ids, anchor, log, prefer=None, until=None):
    if prefer is None:
        prefer = []
    _w12 = yield from walk(anchor, 3, log)
    if not (_w12):
        return False
    item = inventory.first(item_name)
    loc = locs.query().where(lambda candidate: (candidate.id in ids) and candidate.tile().distance_to(anchor) <= 3).within(10).nearest()
    if not item or not loc:
        log(f"cannot use '{item_name}' on Tourist Trap loc [{','.join([str(i) for i in ids])}]")
        return False
    if not (item.use_on(loc)):
        return False
    _result13 = yield from drain_interaction_dialog(prefer, log, until)
    return _result13


def use_item_on_npc(item_name, npc_id, anchor, log, prefer=None, until=None):
    if prefer is None:
        prefer = []
    _w14 = yield from walk(anchor, 4, log)
    if not (_w14):
        return False
    item = inventory.first(item_name)
    npc = npcs.query().where(lambda candidate: candidate.id == npc_id).within(10).nearest()
    if not item or not npc:
        return False
    if not (item.use_on(npc)):
        return False
    _result15 = yield from drain_interaction_dialog(prefer, log, until)
    return _result15


def lower(name):
    return name.lower()


def held_count(snap, name):
    return (snap.inv.get(lower(name)) if snap.inv.get(lower(name)) is not None else 0)


def held(snap, name):
    return held_count(snap, name) > 0


def worn(snap, name):
    return (lower(name) in snap.worn)


def owned_now(snap, name):
    return held_count(snap, name) + ((1 if worn(snap, name) else 0))


def banked(snap, name):
    return ((snap.bank.get(lower(name)) if snap.bank is not None else None) if (snap.bank.get(lower(name)) if snap.bank is not None else None) is not None else 0)


def waterskin_containers(snap):
    return sum([held_count(snap, name) for name in WATERSKINS])


def waterskin_doses(snap):
    doses = 0
    for index in range(4):
        doses += held_count(snap, WATERSKINS[index]) * (4 - index)
    return doses


def configured_food_name():
    name = (quest_food.name.strip() if quest_food.name is not None else None)
    return (name if name else None)


def configured_food_forms():
    name = configured_food_name()
    return (food_forms(name) if name else [])


def configured_food_count(snap):
    return sum([held_count(snap, name) for name in configured_food_forms()])


def banked_configured_food_count(snap):
    return sum([banked(snap, name) for name in configured_food_forms()])


def has_outfit(snap, outfit):
    return all([owned_now(snap, item) > 0 for item in outfit])


def outfit_copies(snap, outfit):
    return min([owned_now(snap, item) for item in outfit])


def bank_step(items):
    # Nearest bank; mid-desert recovery shouldn't walk from Al Kharid to Draynor.
    return Record({'kind': 'withdraw', 'items': items})


def scan_bank():
    return Record({'kind': 'scan_bank'})


def preparation_keep():
    return [lower(_x) for _x in [ITEM.COINS, ITEM.PICKAXE, ITEM.KEBAB] + list(configured_food_forms()) + list(DESERT_OUTFIT) + list(SLAVE_OUTFIT) + list(WATERSKINS) + [ITEM.BAR, ITEM.FEATHER, ITEM.HAMMER, ITEM.PASS, ITEM.DISCLAIMER, ITEM.METAL_KEY, ITEM.BEDABIN_KEY, ITEM.PLANS, ITEM.DART_TIP, ITEM.DART, ITEM.PINEAPPLE, ITEM.BARREL, ITEM.ANA_BARREL]]


def rescue_keep():
    return [lower(_x) for _x in [ITEM.COINS, ITEM.PICKAXE, ITEM.KEBAB] + list(configured_food_forms()) + list(DESERT_OUTFIT) + list(SLAVE_OUTFIT) + list(WATERSKINS) + [ITEM.PASS, ITEM.DISCLAIMER, ITEM.METAL_KEY, ITEM.PINEAPPLE, ITEM.BARREL, ITEM.ANA_BARREL]]


def has_preparation_spillover(snap):
    keep = preparation_keep()
    return any([not (name in keep) for name in list(list(snap.inv.keys()))])


def make_preparation_space(snap, slots):
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    if has_preparation_spillover(snap):
        return Record({'kind': 'deposit', 'keep': preparation_keep(), 'exact_keep': True})
    return Record({
        'kind': 'wait',
        'reason': f"need {slots} free inventory slot{('' if slots == 1 else 's')} for the Tourist Trap loadout",
    })


def make_rescue_space(snap, slots):
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    keep = rescue_keep()
    if any([not (name in keep) for name in list(list(snap.inv.keys()))]):
        return Record({'kind': 'deposit', 'keep': keep, 'exact_keep': True})
    return Record({
        'kind': 'wait',
        'reason': f"need {slots} free inventory slot{('' if slots == 1 else 's')} for Tourist Trap survival supplies",
    })


SHANTAY_TARGETS = [
    Record({'name': ITEM.DESERT_SHIRT, 'qty': 1, 'shop': SHANTAY_SHOP, 'est_gp': 45}),
    Record({'name': ITEM.DESERT_ROBE, 'qty': 1, 'shop': SHANTAY_SHOP, 'est_gp': 45}),
    Record({'name': ITEM.DESERT_BOOTS, 'qty': 1, 'shop': SHANTAY_SHOP, 'est_gp': 25}),
    Record({'name': ITEM.WATERSKIN, 'qty': 4, 'shop': SHANTAY_SHOP, 'est_gp': 35}),
    Record({'name': ITEM.PASS, 'qty': 1, 'shop': SHANTAY_SHOP, 'est_gp': 6}),
    Record({'name': ITEM.BAR, 'qty': 3, 'shop': SHANTAY_SHOP, 'est_gp': 8}),
    Record({'name': ITEM.FEATHER, 'qty': 10, 'shop': SHANTAY_SHOP, 'est_gp': 2}),
    Record({'name': ITEM.HAMMER, 'qty': 1, 'shop': SHANTAY_SHOP, 'est_gp': 13}),
]
INITIAL_SHANTAY_TARGETS = [target for target in SHANTAY_TARGETS if target.name != ITEM.BAR and target.name != ITEM.FEATHER and target.name != ITEM.HAMMER]


def withdraw_banked_shortage(snap, name, target):
    missing = target - owned_now(snap, name)
    available = banked(snap, name)
    if missing <= 0 or available <= 0:
        return None
    qty = min(missing, available)
    stackable = name == ITEM.COINS or name == ITEM.FEATHER or name == ITEM.PASS
    slots = (1 if stackable and held_count(snap, name) == 0 else (0 if stackable else qty))
    _v17 = make_preparation_space(snap, slots)
    return (_v17 if _v17 is not None else bank_step([{'name': name, 'qty': qty}]))


def buy_kebabs(target, log):
    if event_signal.pending():
        return False
    _w18 = yield from walk(KEBAB_SELLER, 2, log)
    if not (_w18):
        return False
    while inventory.count(ITEM.KEBAB) < target:
        if event_signal.pending():
            return False
        if inventory.count(ITEM.COINS) < 1 or inventory.is_full():
            return False
        before = inventory.count(ITEM.KEBAB)
        # The Kebab seller has no shop interface, only this dialogue.
        seller = npcs.query().name('Kebab seller').within(8).nearest()
        if not seller:
            return False
        op = talk_action(seller.actions())
        if not op or not (seller.interact(op)):
            return False
        _w19 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
        if not (_w19):
            return False
        _w20 = yield from drive_strict_dialog(['Yes please.'], log)
        if not (_w20):
            return False
        if event_signal.pending():
            return False
        _w21 = yield from execution.delay_until(lambda: inventory.count(ITEM.KEBAB) > before, 5000)
        if not (_w21):
            return False
    return True


def configured_food_withdrawal(snap, minimum, target, space):
    name = configured_food_name()
    if not name:
        return None
    carried = configured_food_count(snap)
    if carried >= minimum:
        return None
    if not snap.bank_known:
        return scan_bank()
    banked_food = banked_configured_food_count(snap)
    if carried + banked_food < target:
        return Record({
            'kind': 'wait',
            'reason': f'configured Tourist Trap food \'{name}\' unavailable: need {target}, carried {carried}, banked {banked_food}',
        })
    missing = target - carried
    items = []
    for form in configured_food_forms():
        qty = min(missing, banked(snap, form))
        if qty <= 0:
            continue
        items.append({'name': (name if form == name.lower() else form), 'qty': qty})
        missing -= qty
        if missing == 0:
            break
    _v22 = space(snap, target - carried)
    return (_v22 if _v22 is not None else bank_step(items))


def preparation_acquisition_step(snap):
    if not snap.bank_known:
        return scan_bank()
    if has_preparation_spillover(snap):
        return Record({'kind': 'deposit', 'keep': preparation_keep(), 'exact_keep': True})
    already_south = (tourist_trap_area(snap.tile) in ['irena', 'desert', 'bedabin'])
    # One funding step covers every purchase and the driver's bribe.
    if not already_south and held_count(snap, ITEM.COINS) < 1000:
        coins = withdraw_banked_shortage(snap, ITEM.COINS, 1000)
        if coins:
            return coins
        return earn_quest_coins_step(1000, 'Tourist Trap')
    if owned_now(snap, ITEM.PICKAXE) < 1:
        bank_pick = withdraw_banked_shortage(snap, ITEM.PICKAXE, 1)
        if bank_pick:
            return bank_pick
        space = make_preparation_space(snap, 1)
        return (space if space is not None else Record({'kind': 'buy', 'item': ITEM.PICKAXE, 'qty': 1, 'shop': BOB_AXES, 'est_gp': 2}))
    selected_food = configured_food_name()
    if selected_food:
        food = configured_food_withdrawal(snap, FOOD_ENTRY_TARGET, FOOD_ENTRY_TARGET, make_preparation_space)
        if food:
            return food
    else:
        ration = source_kebabs(snap, FOOD_ENTRY_TARGET)
        if ration:
            return ration
    for target in INITIAL_SHANTAY_TARGETS:
        # Crossing south consumes the pass; buying another from the desert would route you back north and the quest would never start.
        if target.name == ITEM.PASS and already_south:
            continue
        if target.name == ITEM.WATERSKIN:
            water = source_water_doses(snap, WATER_ENTRY_DOSES, WATER_ENTRY_DOSES, make_preparation_space)
            if water:
                return water
            continue
        bank_item = withdraw_banked_shortage(snap, target.name, target.qty)
        if bank_item:
            return bank_item
        missing = target.qty - owned_now(snap, target.name)
        if missing <= 0:
            continue
        stackable = target.name == ITEM.FEATHER or target.name == ITEM.PASS
        slots = (1 if stackable and held_count(snap, target.name) == 0 else (0 if stackable else missing))
        space = make_preparation_space(snap, slots)
        if space:
            return space
        return Record({
            'kind': 'buy',
            'item': target.name,
            'qty': missing,
            'shop': target.shop,
            'est_gp': target.est_gp * missing,
        })
    return None


def preparation_step(snap):
    acquisition = preparation_acquisition_step(snap)
    if not acquisition:
        return None
    north = route_north(snap)
    return north if north is not None else acquisition


def ensure_equipment(required, allowed, log):
    # Equip first: a same-slot swap is atomic and needs no spare pack slot for the old garment.
    for item in required:
        _c23 = not equipment.contains(item)
        if _c23:
            _w24 = yield from equipment.equip(item)
            _c23 = not (_w24)
        if _c23:
            log(f'could not equip required Tourist Trap item \'{item}\'')
            return False
    permitted = set([lower(_x) for _x in allowed])
    for item in equipment.items():
        _c25 = item.name and not (lower(item.name) in permitted)
        if _c25:
            _w26 = yield from equipment.unequip(item.name)
            _c25 = not (_w26)
        if _c25:
            log(f'could not safely remove \'{item.name}\' inside the mining camp')
            return False
    return all([equipment.contains(item) for item in required])


def wear_desert_loadout(log):
    _result27 = yield from ensure_equipment(list(DESERT_OUTFIT) + [ITEM.PICKAXE], list(DESERT_OUTFIT) + [ITEM.PICKAXE], log)
    return _result27


def wear_desert_outfit_for_space(log):
    _result28 = yield from ensure_equipment(DESERT_OUTFIT, list(DESERT_OUTFIT) + [ITEM.PICKAXE], log)
    return _result28


def wear_slave_loadout(log):
    # A pickaxe is the one weapon the camp equipment search allows.
    _result29 = yield from ensure_equipment(list(SLAVE_OUTFIT) + [ITEM.PICKAXE], list(SLAVE_OUTFIT) + [ITEM.PICKAXE], log)
    return _result29


def wear_slave_disguise_only(log):
    _result30 = yield from ensure_equipment(SLAVE_OUTFIT, list(SLAVE_OUTFIT) + [ITEM.PICKAXE], log)
    return _result30


def wait_out_combat(timeout_ms):
    deadline = _core.step_time() + timeout_ms
    while game.in_combat() and _core.step_time() < deadline:
        yield from sustain.run()
        if event_signal.pending():
            return False
        yield from execution.delay_ticks(1)
    return not game.in_combat()


def cross_shantay_pass(log):
    # Why: the pass loc sits south of its own closed collision barrier, so walk to the near side first and then send Go-through.
    _w31 = yield from walk(SHANTAY_NORTH_APPROACH, 1, log)
    if not (_w31):
        return False
    pass_ = loc_at([LOC.SHANTAY_PASS], 'Go-through', SHANTAY_PASS, 6)
    if not pass_ or not (pass_.interact('Go-through')):
        return False
    _w32 = yield from drain_interaction_dialog(["Yeah, that poster doesn't scare me!"], log)
    if not (_w32):
        return False

    def _fn34():
        tile = game.tile()
        return tile is not None and tile.z < 3117
    _result33 = yield from execution.delay_until(_fn34, 10000)
    return _result33


def cross_shantay_pass_north(log):
    _w35 = yield from walk(SHANTAY_SOUTH_APPROACH, 1, log)
    if not (_w35):
        return False
    pass_ = loc_at([LOC.SHANTAY_PASS], 'Go-through', SHANTAY_PASS, 6)
    if not pass_ or not (pass_.interact('Go-through')):
        return False
    _w36 = yield from drain_interaction_dialog([], log)
    if not (_w36):
        return False

    def _fn38():
        tile = game.tile()
        return tile is not None and tile.z >= 3117
    _result37 = yield from execution.delay_until(_fn38, 10000)
    return _result37


def start_with_irena(log):
    _result39 = yield from talk_strict(NPC.IRENA, IRENA, IRENA_START, log)
    return _result39


def challenge_captain(log):
    _result40 = yield from talk_strict(NPC.CAPTAIN, CAPTAIN, CAPTAIN_DUEL, log, 10)
    return _result40


def provoke_and_defeat_captain(log):
    # Stage 3 can resume after a restart before combat; the captain refuses a cold Attack and guards may join, so replay the taunt.
    _c41 = not game.in_combat()
    if _c41:
        _w42 = yield from challenge_captain(log)
        _c41 = not (_w42)
    if _c41:
        return False
    yield from execution.delay_until(lambda: game.in_combat(), 5000)
    if game.in_combat():
        yield from wait_out_combat(180000)
        _result43 = yield from execution.delay_until(lambda: inventory.contains(ITEM.METAL_KEY), 8000)
        return _result43
    log('the Mercenary Captain did not enter the guaranteed duel; retrying the strict provocation')
    return False


def enter_camp(log):
    _w44 = yield from interact_loc(LOC.CAMP_GATE, 'Open', CAMP_GATE, log)
    if not (_w44):
        return False

    def _fn46():
        area = tourist_trap_area(game.tile())
        return area == 'campSurface' or area == 'campUpper'
    _result45 = yield from execution.delay_until(_fn46, 10000)
    return _result45


def leave_camp(log):
    # Why: the outer gate only rejects slave clothing, so swap to the full desert outfit if it survived and otherwise strip the slave disguise before leaving.
    has_full_desert_outfit = all([equipment.contains(item) or inventory.contains(item) for item in DESERT_OUTFIT])
    required = DESERT_OUTFIT if has_full_desert_outfit else []
    safely_dressed = yield from ensure_equipment(required, list(DESERT_OUTFIT) + [ITEM.PICKAXE], log)
    if not safely_dressed:
        return False
    _w50 = yield from interact_loc(LOC.CAMP_GATE, 'Open', CAMP_GATE, log, [], lambda: tourist_trap_area(game.tile()) == 'desert')
    if not (_w50):
        return False
    _result51 = yield from execution.delay_until(lambda: tourist_trap_area(game.tile()) == 'desert', 10000)
    return _result51


def enter_mine(log):
    # The doors need only the 3 slave garments. A lost pickaxe shouldn't block rescue recovery; the punishment cell spawns its own.
    _w52 = yield from wear_slave_disguise_only(log)
    if not (_w52):
        return False
    _w53 = yield from interact_loc(LOC.SURFACE_MINE_DOOR, 'Open', MINE_ENTRANCE, log)
    if not (_w53):
        return False

    def _fn55():
        area = tourist_trap_area(game.tile())
        return area == 'mineEntrance'
    _result54 = yield from execution.delay_until(_fn55, 12000)
    return _result54


def leave_mine(log):
    _w56 = yield from wear_slave_disguise_only(log)
    if not (_w56):
        return False
    _c57 = tourist_trap_area(game.tile()) == 'mineLower'
    if _c57:
        _w58 = yield from cross_mine_cave(False, log)
        _c57 = not (_w58)
    if _c57:
        return False
    if tourist_trap_area(game.tile()) != 'mineEntrance':
        return False
    # The loc origin is across the closed door; targeting it makes the walker take the door transport and then chase a stale underground tile from the surface.
    _w59 = yield from walk(MINE_EXIT_INSIDE_STAND, 0, log)
    if not (_w59):
        log('could not reach the inside stand for the underground mine exit')
        return False
    door = loc_at(LOC.UNDERGROUND_MINE_DOOR, 'Open', MINE_EXIT_DOOR, 4)
    if not door:
        log('underground mine exit did not expose its Open action from the inside stand')
        return False
    _c60 = not (door.interact('Open'))
    if not _c60:
        _w61 = yield from drain_interaction_dialog([], log)
        _c60 = not (_w61)
    if _c60:
        return False
    _result62 = yield from execution.delay_until(lambda: tourist_trap_area(game.tile()) == 'campSurface', 12000)
    return _result62


def climb_camp_ladder(up, log):
    id = (LOC.LADDER_UP if up else LOC.LADDER_DOWN)
    op = ('Climb-up' if up else 'Climb-down')
    anchor = Tile(CAMP_LADDER.x, CAMP_LADDER.z, (0 if up else 1))
    _w63 = yield from interact_loc([id], op, anchor, log)
    if not (_w63):
        return False
    _result64 = yield from execution.delay_until(lambda: (game.tile().level if game.tile() is not None else None) == ((1 if up else 0)), 8000)
    return _result64


def slave_unlock_and_trade(log):
    # Success, retry and the trade are one bounded interaction, so a random lockpick result can't leave a choice menu open between ticks.
    _result65 = yield from talk_strict([NPC.SLAVE, NPC.ESCAPED_SLAVE], SLAVE, list(SLAVE_INTRO) + list(SLAVE_LOCK) + list(SLAVE_TRADE), log, 10)
    return _result65


def replace_lost_slave_outfit(log):
    if live_has_slave_outfit():
        return True
    _w66 = yield from wear_desert_loadout(log)
    if not (_w66):
        return False
    _w67 = yield from walk(SLAVE, 3, log)
    if not (_w67):
        return False
    slave = npcs.query().where(lambda candidate: (candidate.id == NPC.SLAVE or candidate.id == NPC.ESCAPED_SLAVE) and talk_action(candidate.actions()) is not None).within_of(SLAVE, 6).nearest()
    if not slave:
        log(f'slave-outfit recovery: no male slave 825/826 near ({SLAVE.x},{SLAVE.z})')
        return False
    tile = slave.tile()
    log(f'slave-outfit recovery: talking to npc={slave.id} at ({tile.x},{tile.z}); ' + f"missing={'|'.join([item for item in SLAVE_OUTFIT if not inventory.contains(item) and not equipment.contains(item)])}")
    if not (slave.interact(talk_action(slave.actions()))):
        return False
    _w68 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w68):
        log('slave-outfit recovery: male-slave dialogue did not open')
        return False
    _w69 = yield from drive_strict_dialog(["Yes, I'll trade."], log)
    if not (_w69):
        return False
    _w70 = yield from execution.delay_until(live_has_slave_outfit, 5000)
    if _w70:
        log('slave-outfit recovery: received the complete shirt, robe, and boots')
        return True
    log('slave-outfit recovery: dialogue ended without a complete outfit; ' + f"missing={'|'.join([item for item in SLAVE_OUTFIT if not inventory.contains(item) and not equipment.contains(item)])}")
    return False


def ask_cave_guard(log):
    guard = npcs.query().where(lambda npc: (npc.id == 828 or npc.id == 829) and talk_action(npc.actions()) is not None).inside(CAVE_GUARD_POST).nearest()
    if not guard:
        _w71 = yield from walk(CAVE_GUARD, 4, log)
        if not (_w71):
            return False
        return False
    if not (guard.interact(talk_action(guard.actions()))):
        return False
    _w72 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not (_w72):
        return False
    _result73 = yield from drive_strict_dialog(CAVE_GUARD_DIALOG, log)
    return _result73


def give_pineapple(log):
    _w74 = yield from walk(CAVE_GUARD, 4, log)
    if not (_w74):
        return False
    guard = npcs.query().where(lambda npc: npc.id == 828 or npc.id == 829).inside(CAVE_GUARD_POST).nearest()
    pineapple = inventory.first(ITEM.PINEAPPLE)
    if not guard or not pineapple or not (pineapple.use_on(guard)):
        return False
    _result75 = yield from drain_interaction_dialog([], log)
    return _result75


def cross_mine_cave(to_inner_mine, log):
    # Approach from the source landing tile; the cave loc tiles are wall-separated collision slivers and can't be walked to.
    anchor = (CAVE_OUTER_LANDING if to_inner_mine else CAVE_INNER_LANDING)
    landing = (CAVE_INNER_LANDING if to_inner_mine else CAVE_OUTER_LANDING)

    def at_landing():
        tile = game.tile()
        return tile is not None and tile.level == landing.level and landing.distance_to(tile) <= 1

    for attempt in range(1, 3 + 1):
        if event_signal.pending():
            return False
        _w77 = yield from interact_loc(LOC.MINE_CAVE, 'Walk through', anchor, log, [], at_landing)
        _c76 = _w77
        if _c76:
            _w78 = yield from execution.delay_until(at_landing, 10000)
            _c76 = _w78
        if _c76:
            return True
        if attempt < 3:
            log(f'mine cave transit attempt {attempt}/3 was interrupted before the exact landing; retrying')
            yield from sustain.run()
            yield from execution.delay_ticks(1)
    # The mine regions overlap the approach tiles, so only the source landing proves the delayed transport ran.
    log(f'mine cave transit did not reach ({landing.x},{landing.z}) after 3 attempts')
    return False


def search_cell_window(log):
    window = locs.query().where(lambda loc: loc.id == LOC.WINDOW and loc.tile().x == CELL_WINDOW.x and loc.tile().z == CELL_WINDOW.z).action('Search').within(8).nearest()
    if not window:
        log(f'no cell window offering Search at ({CELL_WINDOW.x},{CELL_WINDOW.z})')
        return False
    if not window.interact('Search'):
        return False
    bent = yield from drain_interaction_dialog(["Yes, I'll bend the bar.", "Yes, I'll bend the bar again."], log)
    return bent


def escape_surface_jail(log):
    start = game.tile()
    still_in_cell = start is not None and start.x >= 3284 and start.x <= 3286 and start.z >= 3032 and start.z <= 3036
    if still_in_cell:
        bent = yield from search_cell_window(log)
        if not bent:
            return False
    for attempt in range(16):
        tile = game.tile()
        if tile and tile.x < 3274:
            return True
        if not tile:
            return False
        rock = locs.query().where(lambda loc: (loc.id in [2694, 2695, 2696]) and loc.tile().x < tile.x).action('Climb-to').within(12).nearest()
        if rock:
            if not (rock.interact('Climb-to')):
                return False
            preference = (["Yes, I'll give it a try."] if rock.id == 2694 else [])
            _w81 = yield from drain_interaction_dialog(preference, log)
            if not (_w81):
                return False
            yield from execution.delay_ticks(1)
            continue
        # The 4th, westernmost rock is a one-way Climb down.
        descent = locs.query().where(lambda loc: loc.id == 2697 and loc.tile().x < tile.x).action('Climb down').within(12).nearest()
        if not descent or not (descent.interact('Climb down')):
            log('no next outbound surface-jail rock is reachable')
            return False
        _w82 = yield from drain_interaction_dialog([], log)
        if not (_w82):
            return False
        yield from execution.delay_ticks(1)
    return game.tile() is not None and game.tile().x < 3274


JAIL_DROP_ORDER = [ITEM.KEBAB, 'Waterskin(0)', 'Waterskin(1)', 'Waterskin(2)', 'Waterskin(3)', 'Waterskin(4)', ITEM.HAMMER, ITEM.BAR, ITEM.FEATHER, ITEM.PASS] + list(DESERT_OUTFIT)


def drop_punishment_junk_until(slots, log):
    for name in JAIL_DROP_ORDER:
        while inventory.free() < slots:
            item = inventory.first(name)
            if not item:
                break
            before_free = inventory.free()
            if not (item.interact('Drop')):
                return False
            _w83 = yield from execution.delay_until(lambda: inventory.free() > before_free, 3000)
            if not (_w83):
                return False
        if inventory.free() >= slots:
            return True
    log(f'cannot safely free {slots} punishment-mine inventory slots')
    return False


def punishment_rock_count():
    # Common Rock (968) shares the display name but the gate only takes thpunishrock (1855), so count by id.
    return sum([item.count for item in [item for item in inventory.items() if item.id == PUNISHMENT_ROCK_ID]])


def live_has_slave_outfit():
    return all([inventory.contains(item) or equipment.contains(item) for item in SLAVE_OUTFIT])


def slave_outfit_drop(drop_id):
    return ground_items.query().where(lambda item: item.id == drop_id).within(30).nearest()


def recover_slave_outfit_from_rowdy(log):
    if live_has_slave_outfit():
        return True
    # Why: the live Rowdy-slave death script checks the backpack only, so every surviving worn piece goes into the pack first or its shirt, robe, boots sequence repeats a piece.
    required_slots = len([item for item in SLAVE_OUTFIT if not inventory.contains(item)])
    _c84 = inventory.free() < required_slots
    if _c84:
        _w85 = yield from drop_punishment_junk_until(required_slots, log)
        _c84 = not (_w85)
    if _c84:
        return False
    for item in SLAVE_OUTFIT:
        _c86 = equipment.contains(item)
        if _c86:
            _w87 = yield from equipment.unequip(item)
            _c86 = not (_w87)
        if _c86:
            log(f'could not move \'{item}\' into the backpack for Rowdy-slave recovery')
            return False
    game.set_combat_style('strength')
    for index in range(len(SLAVE_OUTFIT)):
        name = SLAVE_OUTFIT[index]
        drop_id = SLAVE_OUTFIT_DROP_IDS[index]
        for attempt in range(16):
            if not (not inventory.contains(name)):
                break
            drop = slave_outfit_drop(drop_id)
            if drop:
                if not (drop.interact('Take')):
                    return False
                _w88 = yield from execution.delay_until(lambda: inventory.contains(name), 8000)
                if not (_w88):
                    return False
                break
            if game.in_combat():
                yield from wait_out_combat(120000)
                continue
            _w89 = yield from walk(ROWDY_SLAVE, 6, log)
            if not (_w89):
                return False
            rowdy = npcs.query().where(lambda npc: npc.id == NPC.ROWDY_SLAVE and not npc.in_combat and not npc.targets_another_player()).action('Attack').within(18).nearest()
            if not rowdy:
                yield from execution.delay_ticks(2)
                continue
            log(f'defeating the Rowdy slave for \'{name}\'')
            if not (rowdy.interact('Attack')):
                return False
            yield from execution.delay_until(lambda: slave_outfit_drop(drop_id) is not None or game.in_combat() or not rowdy.valid(), 5000)
            yield from wait_out_combat(120000)
        if not inventory.contains(name):
            log(f'Rowdy-slave recovery did not produce \'{name}\'')
            return False
    return True


def free_punishment_rock_slots(log):
    rock_slots = max(0, 15 - punishment_rock_count())
    if not equipment.contains(ITEM.PICKAXE) and not inventory.contains(ITEM.PICKAXE):
        _c90 = inventory.free() < 1
        if _c90:
            _w91 = yield from drop_punishment_junk_until(1, log)
            _c90 = not (_w91)
        if _c90:
            return False
        spawn = ground_items.query().name(ITEM.PICKAXE).within(20).nearest()
        if not spawn or not (spawn.interact('Take')):
            log('no Bronze pickaxe held or available from the punishment-mine spawn')
            return False
        _w92 = yield from execution.delay_until(lambda: inventory.contains(ITEM.PICKAXE), 8000)
        if not (_w92):
            return False
    _c93 = not equipment.contains(ITEM.PICKAXE)
    if _c93:
        _w94 = yield from equipment.equip(ITEM.PICKAXE)
        _c93 = not (_w94)
    if _c93:
        log('could not wield the punishment-mine Bronze pickaxe')
        return False
    _c95 = inventory.free() >= rock_slots
    if _c95:
        return _c95
    _result96 = yield from drop_punishment_junk_until(rock_slots, log)
    return _result96


def escape_underground_jail(log):
    _c97 = not live_has_slave_outfit()
    if _c97:
        _w98 = yield from recover_slave_outfit_from_rowdy(log)
        _c97 = not (_w98)
    if _c97:
        return False
    if not equipment.contains(ITEM.PICKAXE) or (punishment_rock_count() < 15 and inventory.free() < 15 - punishment_rock_count()):
        _w99 = yield from free_punishment_rock_slots(log)
        if not (_w99):
            return False
    while punishment_rock_count() < 15:
        before = punishment_rock_count()
        # Why: identical punishment rocks stand across the closed gate and a distance-only query clicks those forever once the near veins are gone, so stay on a reachable rock and wait for respawns.
        rock = locs.query().where(lambda loc: loc.id == LOC.PUNISHMENT_ROCK and reachability.can_reach(loc.tile(), adjacent_ok=True)).action('Mine').within(20).nearest()
        if not rock:
            _w100 = yield from walk(UNDERGROUND_JAIL, 5, log)
            if not (_w100):
                return False
            yield from execution.delay_ticks(2)
            continue
        if not (rock.interact('Mine')):
            return False
        _w101 = yield from execution.delay_until(lambda: punishment_rock_count() > before, 20000)
        if not (_w101):
            return False
    gate = locs.query().where(lambda loc: (loc.id in (LOC.PUNISHMENT_GATE))).action('Open').within(20).nearest()
    if not gate or not (gate.interact('Open')):
        return False
    _w102 = yield from drain_interaction_dialog([], log)
    if not (_w102):
        return False
    _result103 = yield from execution.delay_until(lambda: tourist_trap_area(game.tile()) != 'undergroundJail', 10000)
    return _result103


def ask_al_for_pineapple_deal(log):
    _result104 = yield from talk_strict(NPC.AL_SHABIM, AL_SHABIM, AL_PINEAPPLE, log, 10, lambda: inventory.contains(ITEM.BEDABIN_KEY))
    return _result104


def ask_al_for_lost_key(log):
    _result105 = yield from talk_strict(NPC.AL_SHABIM, AL_SHABIM, ["I've lost the key!"], log, 10, lambda: inventory.contains(ITEM.BEDABIN_KEY))
    return _result105


def ask_al_for_lost_key_and_plans(log):
    _result106 = yield from talk_strict(NPC.AL_SHABIM, AL_SHABIM, ["I've lost the key and the plans!"], log, 10, lambda: inventory.contains(ITEM.BEDABIN_KEY))
    return _result106


def ask_al_for_lost_plans_and_tip(log):
    # At stage 14 this is still the menu label; the plans/tips wording only appears in the player chat after picking it.
    _result107 = yield from talk_strict(NPC.AL_SHABIM, AL_SHABIM, ["I've lost the key and the plans!"], log, 10, lambda: inventory.contains(ITEM.BEDABIN_KEY))
    return _result107


def recover_pineapple_from_al(log):
    _result108 = yield from talk_strict(NPC.AL_SHABIM, AL_SHABIM, ['I am looking for a pineapple.'], log, 10, lambda: inventory.contains(ITEM.PINEAPPLE))
    return _result108


def steal_technical_plans(log):
    if inventory.contains(ITEM.PLANS):
        return True
    _c109 = (game.tile().level if game.tile() is not None else None) != 1
    if _c109:
        _w110 = yield from climb_camp_ladder(True, log)
        _c109 = not (_w110)
    if _c109:
        return False
    _w111 = yield from interact_loc([LOC.BOOKCASE], 'Search', SIAD_BOOKCASE, log)
    if not (_w111):
        return False
    _w112 = yield from talk_strict(NPC.SIAD, Tile(3291, 3032, 1), SIAD_DISTRACTION, log, 8)
    if not (_w112):
        return False
    # The next chest attempt consumes the distraction, so approach from the north and stay out of Siad's line of sight.
    north_of_chest = Tile(3292, 3034, 1)
    _w113 = yield from walk(north_of_chest, 0, log)
    if not (_w113):
        return False
    chest = loc_at([LOC.CHEST], 'Open', SIAD_CHEST, 5)
    if not chest or not (chest.interact('Open')):
        return False
    _w114 = yield from drain_interaction_dialog([], log)
    if not (_w114):
        return False
    _result115 = yield from execution.delay_until(lambda: inventory.contains(ITEM.PLANS), 8000)
    return _result115


def recover_mining_camp_keys(log):
    if inventory.contains(ITEM.METAL_KEY):
        return True
    _c116 = (game.tile().level if game.tile() is not None else None) != 1
    if _c116:
        _w117 = yield from climb_camp_ladder(True, log)
        _c116 = not (_w117)
    if _c116:
        return False
    _w118 = yield from interact_loc([LOC.SIAD_DESK], 'Search', SIAD_DESK, log)
    if not (_w118):
        return False
    _result119 = yield from execution.delay_until(lambda: inventory.contains(ITEM.METAL_KEY), 8000)
    return _result119


def show_plans_to_al(log):
    _w120 = yield from walk(AL_SHABIM, 4, log)
    if not (_w120):
        return False
    plans = inventory.first(ITEM.PLANS)
    al = npcs.query().where(lambda npc: npc.id == NPC.AL_SHABIM).within(10).nearest()
    if not plans or not al or not (plans.use_on(al)):
        return False
    _result121 = yield from drain_interaction_dialog(AL_PLANS, log)
    return _result121


def enter_prototype_tent(log):
    _w122 = yield from walk(BEDABIN_TENT_APPROACH, 3, log)
    if not (_w122):
        log('could not reach the Bedabin experimental tent approach (3169,3045)')
        return False
    guard = npcs.query().where(lambda npc: npc.id == NPC.BEDABIN_GUARD).within(8).nearest()
    plans = inventory.first(ITEM.PLANS)
    if not guard or not plans or not (plans.use_on(guard)):
        log('could not show the technical plans to the Bedabin guard at the tent')
        return False
    _w123 = yield from drain_interaction_dialog([], log)
    if not (_w123):
        return False
    _result124 = yield from execution.delay_until(lambda: tourist_trap_area(game.tile()) == 'bedabinTent', 8000)
    return _result124


def exit_prototype_tent(log):
    if tourist_trap_area(game.tile()) != 'bedabinTent':
        return True
    _w125 = yield from interact_loc([LOC.BEDABIN_TENT_DOOR], 'Walk-through', BEDABIN_TENT_APPROACH, log)
    if not (_w125):
        return False
    _result126 = yield from execution.delay_until(lambda: tourist_trap_area(game.tile()) == 'bedabin', 8000)
    return _result126


def forge_bar_wasted_since(mark):
    return game_messages.saw_since(mark, any_phrase('waste the bronze bar', 'unlucky accident'))


def forge_prototype_tip(log):
    if inventory.contains(ITEM.DART_TIP):
        return True
    if tourist_trap_area(game.tile()) != 'bedabinTent':
        _w127 = yield from enter_prototype_tent(log)
        if not (_w127):
            return False
    _w128 = yield from walk(EXPERIMENTAL_ANVIL, 3, log)
    if not (_w128):
        return False
    bar = inventory.first(ITEM.BAR)
    anvil = locs.query().where(lambda loc: loc.id == LOC.ANVIL).within(8).nearest()
    if not bar or not anvil:
        return False
    # An earlier unlucky line is still in the chatbox; only a message after this bar goes in counts as wasted.
    forge_mark = game_messages.mark()
    if not (bar.use_on(anvil)):
        return False
    _w129 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue() or inventory.contains(ITEM.DART_TIP), 8000)
    if not (_w129):
        return False
    # The source consumes the bar before the success roll, so keep driving the anvil dialogue until the tip exists or the waste line fires.
    forged = yield from drive_strict_dialog(ANVIL_DIALOG, log, lambda: inventory.contains(ITEM.DART_TIP) or forge_bar_wasted_since(forge_mark))
    if inventory.contains(ITEM.DART_TIP):
        return True
    if forge_bar_wasted_since(forge_mark):
        log('forge failed: bronze bar wasted without a dart tip')
        return False
    return forged


def fletch_prototype_dart(log):
    feathers = inventory.first(ITEM.FEATHER)
    tip = inventory.first(ITEM.DART_TIP)
    if not feathers or not tip or inventory.count(ITEM.FEATHER) < 10:
        return False
    if not (feathers.use_on(tip)):
        return False
    _w130 = yield from drain_interaction_dialog([], log)
    if not (_w130):
        return False
    # A failed attempt eats the feathers with no dart, so only the dart proves success; the next pass can buy 10 more.
    _result131 = yield from execution.delay_until(lambda: inventory.contains(ITEM.DART), 12000)
    return _result131


def give_prototype_to_al(log):
    _w132 = yield from exit_prototype_tent(log)
    if not (_w132):
        return False
    _w133 = yield from walk(AL_SHABIM, 4, log)
    if not (_w133):
        return False
    dart = inventory.first(ITEM.DART)
    al = npcs.query().where(lambda npc: npc.id == NPC.AL_SHABIM).within(10).nearest()
    if not dart or not al or not (dart.use_on(al)):
        return False
    _w134 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue() or inventory.contains(ITEM.PINEAPPLE), 8000)
    if not (_w134):
        return False
    _result135 = yield from drive_strict_dialog([], log, lambda: inventory.contains(ITEM.PINEAPPLE))
    return _result135


def return_from_deep_mine(log):
    _w136 = yield from interact_loc([LOC.MINE_CART], 'Search', DEEP_CART, log, ['Yes, of course.'])
    if not (_w136):
        return False
    _result137 = yield from execution.delay_until(lambda: tourist_trap_area(game.tile()) == 'mineLower', 10000)
    return _result137


def return_to_punishment_mine_for_outfit(log):
    area = tourist_trap_area(game.tile())
    if area == 'mineDeep':
        # The cart refuses you while carrying Ana, so send her barrel first; the collapsed-stage probe picks her up later.
        if inventory.contains(ITEM.ANA_BARREL):
            _w138 = yield from use_item_on_loc(ITEM.ANA_BARREL, [LOC.MINE_CART], DEEP_CART, log)
            if not (_w138):
                return False
            _w139 = yield from execution.delay_until(lambda: not inventory.contains(ITEM.ANA_BARREL), 8000)
            if not (_w139):
                return False
        _w140 = yield from return_from_deep_mine(log)
        if not (_w140):
            return False
        area = tourist_trap_area(game.tile())
    if area == 'mineLower' and inventory.contains(ITEM.ANA_BARREL):
        # Why: a guard capture deletes Ana's barrel without setting a recovery transport bit, so she goes on the lift first and the collapsed-stage probe fetches her once the disguise is back.
        _w141 = yield from use_item_on_loc(ITEM.ANA_BARREL, [LOC.LIFT_BUCKET], LIFT_BUCKET, log, LIFT_GUARD_DIALOG)
        if not (_w141):
            return False
        _w142 = yield from execution.delay_until(lambda: not inventory.contains(ITEM.ANA_BARREL), 8000)
        if not (_w142):
            return False
    if area != 'mineLower' and area != 'mineEntrance':
        return False
    # Approaching the guarded cave without the full worn disguise triggers the search/capture and puts you beside the Rowdy slave.
    anchor = (Tile(3286, 9415, 0) if area == 'mineLower' else Tile(3281, 9415, 0))
    _w143 = yield from interact_loc(LOC.MINE_CAVE, 'Walk through', anchor, log)
    if not (_w143):
        return False

    # Before the pineapple milestone the search sends you to the surface cell; from stage 17 it's the underground punishment mine.
    def _fn145():
        destination = tourist_trap_area(game.tile())
        return destination == 'surfaceJail' or destination == 'undergroundJail'
    _result144 = yield from execution.delay_until(_fn145, 15000)
    return _result144


def safe_recovery_route(area):
    if area == 'bedabinTent':
        return Record({'kind': 'custom', 'name': 'leave the prototype tent for item recovery', 'run': exit_prototype_tent})
    if area == 'campUpper':
        return Record({
            'kind': 'custom',
            'name': 'climb down before item recovery',
            'run': lambda log: climb_camp_ladder(False, log),
        })
    if area == 'campSurface':
        return Record({'kind': 'custom', 'name': 'leave the camp safely for item recovery', 'run': leave_camp})
    if area == 'mineEntrance' or area == 'mineLower':
        return Record({'kind': 'custom', 'name': 'leave the mine for item recovery', 'run': leave_mine})
    if area == 'mineDeep':
        return Record({
            'kind': 'custom',
            'name': 'ride back to the lower mine for item recovery',
            'run': return_from_deep_mine,
        })
    return None


# Why: the prototype's bar, feathers and hammer are sourced one at a time into a full pack, so leaving them out banked
# each one the next needed room for, and the bar went in and out of the bank for ever. This departs from rs2b0t.
def critical_slot_keep():
    # Kebabs are the rations only when no food is configured; otherwise they're the first thing to bank.
    rations = [] if configured_food_name() else [ITEM.KEBAB]
    return [lower(_x) for _x in [ITEM.COINS, ITEM.PICKAXE] + rations + list(configured_food_forms()) + list(WATERSKINS) + list(DESERT_OUTFIT) + list(SLAVE_OUTFIT) + [ITEM.BAR, ITEM.FEATHER, ITEM.HAMMER, ITEM.PASS, ITEM.METAL_KEY, ITEM.BEDABIN_KEY, ITEM.PLANS, ITEM.DART_TIP, ITEM.DART, ITEM.PINEAPPLE, ITEM.BARREL, ITEM.ANA_BARREL]]


def bank_food_down_to(count, log):
    """Bank configured food one at a time until count are carried."""
    opened = yield from banking.open(log=log)
    if not opened:
        return False
    for form in configured_food_forms():
        while inventory.count(form) > 0 and inventory_food_count() > count:
            before = inventory.count(form)
            if not bank.deposit(form):
                return False
            moved = yield from execution.delay_until(lambda: inventory.count(form) < before, 3000)
            if not moved:
                return False
    yield from bank.close()
    return inventory_food_count() <= count


def inventory_food_count():
    return sum([inventory.count(form) for form in configured_food_forms()])


def make_critical_item_space(snap, slots=1):
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if route:
        return route
    north = route_north(snap)
    if north:
        return north
    keep = critical_slot_keep()
    if not any([not (name in keep) for name in list(list(snap.inv.keys()))]):
        # Why: the entry food, both outfits and the waterskins fill the pack, so the room comes out of the food above
        # the floor that would draw it straight back. This departs from rs2b0t.
        carried = configured_food_count(snap)
        if configured_food_name() and carried > FOOD_ENTRY_FLOOR:
            target = carried - min(slots, carried - FOOD_ENTRY_FLOOR)
            return custom(f'bank food down to {target} for a quest item', lambda log: bank_food_down_to(target, log))
        return Record({
            'kind': 'wait',
            'reason': f"need {slots} safe inventory slot{('' if slots == 1 else 's')} for a Tourist Trap quest item",
        })
    return Record({'kind': 'deposit', 'keep': keep, 'exact_keep': True})


def recover_critical(snap, name, reacquire):
    if held(snap, name):
        return None
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if route:
        return route
    space = make_critical_item_space(snap)
    if space:
        return space
    if not snap.bank_known or banked(snap, name) > 0:
        north = route_north(snap)
        if north:
            return north
    if not snap.bank_known:
        return scan_bank()
    if banked(snap, name) > 0:
        space = make_preparation_space(snap, 1)
        return (space if space is not None else bank_step([{'name': name, 'qty': 1}]))
    return reacquire


def source_consumable(snap, name, target):
    if held_count(snap, name) >= target:
        return None
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if route:
        return route
    north = route_north(snap)
    if north:
        return north
    if not snap.bank_known:
        return scan_bank()
    missing = target - held_count(snap, name)
    stackable = name == ITEM.FEATHER
    needs_slot = not stackable or held_count(snap, name) == 0
    required_slots = (((1 if stackable else missing)) if needs_slot else 0)
    if missing > 0 and required_slots > 0 and ((snap.free_slots if snap.free_slots is not None else required_slots)) < required_slots:
        space = make_critical_item_space(snap, required_slots)
        if space:
            return space
    withdrawal = withdraw_banked_shortage(snap, name, target)
    if withdrawal:
        return withdrawal
    shop_target = ([item for item in SHANTAY_TARGETS if item.name == name] or [None])[0]
    if not shop_target:
        return Record({'kind': 'wait', 'reason': f'cannot naturally replace \'{name}\''})
    purchase_cost = shop_target.est_gp * missing
    coins = source_coins(snap, purchase_cost, f'replace {name}')
    if coins:
        return coins
    slots = (1 if stackable and held_count(snap, name) == 0 else (0 if stackable else missing))
    space = make_preparation_space(snap, slots)
    return (space if space is not None else Record({'kind': 'buy', 'item': name, 'qty': missing, 'shop': SHANTAY_SHOP, 'est_gp': purchase_cost}))


def free_one_rescue_slot(log):
    if inventory.free() >= 1:
        return True
    # From stage 17 the prototype is done, so these are surplus. Never drop a key, disguise, rescue barrel, coins or the pickaxe.
    for name in ['Waterskin(0)', ITEM.HAMMER, ITEM.BAR, ITEM.FEATHER, ITEM.PASS, ITEM.KEBAB]:
        item = inventory.first(name)
        if not item:
            continue
        before = inventory.free()
        if not (item.interact('Drop')):
            return False
        _w146 = yield from execution.delay_until(lambda: inventory.free() > before, 3000)
        if _w146:
            return True
    log('no safe expendable item can be dropped for the rescue barrel checkpoint')
    return False


def search_lower_barrel(take_ordinary, log):
    if inventory.free() < 1 and not inventory.contains(ITEM.BARREL) and not inventory.contains(ITEM.ANA_BARREL):
        _w147 = yield from free_one_rescue_slot(log)
        if not (_w147):
            return False
    preference = (['Yeah, cool!'] if take_ordinary else ['No thanks.'])
    mark = game_messages.mark()

    def completed():
        if take_ordinary:
            return inventory.contains(ITEM.BARREL) or inventory.contains(ITEM.ANA_BARREL)
        return inventory.contains(ITEM.ANA_BARREL) or game_messages.saw_since(mark, 'decide not to take the barrel')

    _w148 = yield from interact_loc([LOC.EMPTY_BARREL], 'Search', LOWER_BARREL, log, preference, completed)
    if not (_w148) or not completed():
        observed = ' | '.join([message.text for message in game_messages.since(mark)])
        log(f'lower barrel interaction ended without its authoritative result; observed=[{observed}]')
        return False
    return True


def search_surface_barrel(log):
    _w149 = yield from walk(SURFACE_BARREL_APPROACH, 3, log)
    if not (_w149):
        return False
    barrel = loc_at([LOC.FULL_BARREL], 'Search', SURFACE_BARREL_APPROACH, 10)
    if not barrel:
        log('lift checkpoint: exact top barrel did not expose its Search action')
        return False
    if not (barrel.interact('Search')):
        log('lift checkpoint: exact top barrel Search action was not dispatched')
        return False
    ana_response = yield from execution.delay_until(lambda: inventory.contains(ITEM.ANA_BARREL) or chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if not ana_response:
        # The source sends no message when this barrel has no Ana bit.
        log('lift checkpoint: top barrel contained no Ana response')
        return False
    if chat_dialog.is_open() or chat_dialog.can_continue():
        _w150 = yield from drive_strict_dialog([], log, lambda: inventory.contains(ITEM.ANA_BARREL))
        if not (_w150):
            log('lift checkpoint: top barrel Ana dialogue did not reach the inventory award')
            return False
    recovered = yield from execution.delay_until(lambda: inventory.contains(ITEM.ANA_BARREL), 3000)
    if not recovered:
        log('lift checkpoint: top barrel dialogue ended without returning Ana')
    return recovered


def ride_mine_cart(anchor, log):
    yield from sustain.run()
    if event_signal.pending():
        return False
    from_lower = anchor.distance_to(LOWER_CART) <= 1
    origin = ('lower mine' if from_lower else 'deep mine')
    destination = ('deep mine' if from_lower else 'lower mine')
    log(f"mine-cart attempt: {origin} -> {destination}; Agility={skills.level('agility')}")
    _w151 = yield from interact_loc([LOC.MINE_CART], 'Search', anchor, log, ['Yes, of course.'])
    if not (_w151):
        log(f'mine-cart interaction did not complete at the {origin}')
        return False
    arrived = yield from execution.delay_until(lambda: tourist_trap_area(game.tile()) == (('mineDeep' if from_lower else 'mineLower')), 12000)
    if arrived:
        log(f'mine-cart transit reached the {destination}')
        return True
    area = tourist_trap_area(game.tile())
    if area == (('mineLower' if from_lower else 'mineDeep')):
        yield from sustain.run()
        log(f'mine-cart Agility roll failed at the {origin}; upkeep applied before retry')
    else:
        log(f'mine-cart transit unresolved; current area={area}')
    return False


def catch_ana_in_barrel(log):
    if inventory.contains(ITEM.ANA_BARREL):
        return True
    # Re-catching Ana with stale transport bits adds 2 delayed messages before the catch; her final complaint means every gap was driven.
    caught = any_phrase('manage to squeeze Ana into the barrel', 'I djont fit in dis bawwel')
    completed = yield from use_item_on_npc(ITEM.BARREL, NPC.ANA, ANA_TILE, log, [], lambda: dialog_matches(caught))
    return completed and inventory.contains(ITEM.ANA_BARREL)


def reach_and_catch_ana(log):
    area = tourist_trap_area(game.tile())
    log(f"deep-mine recapture: starting area={area}; empty barrel={('yes' if inventory.contains(ITEM.BARREL) else 'no')}; Ana barrel={('yes' if inventory.contains(ITEM.ANA_BARREL) else 'no')}")
    if area == 'campSurface':
        _w152 = yield from enter_mine(log)
        if not (_w152):
            return False
        area = tourist_trap_area(game.tile())
    if area == 'mineEntrance':
        _w153 = yield from cross_mine_cave(True, log)
        if not (_w153):
            return False
        area = tourist_trap_area(game.tile())
    if area == 'mineDeep' and not inventory.contains(ITEM.BARREL):
        _w154 = yield from ride_mine_cart(DEEP_CART, log)
        if not (_w154):
            return False
        area = tourist_trap_area(game.tile())
    if area == 'mineLower':
        _c155 = not inventory.contains(ITEM.BARREL)
        if _c155:
            _w156 = yield from search_lower_barrel(True, log)
            _c155 = not (_w156)
        if _c155:
            return False
        if inventory.contains(ITEM.ANA_BARREL):
            log('deep-mine recapture: recovered Ana directly from the lower transport barrel')
            return True
        _w157 = yield from ride_mine_cart(LOWER_CART, log)
        if not (_w157):
            return False
        area = tourist_trap_area(game.tile())
    if area != 'mineDeep':
        log(f'deep-mine recapture did not reach Ana; current area={area}')
        return False
    caught = yield from catch_ana_in_barrel(log)
    log(('deep-mine recapture: Ana secured in the barrel' if caught else 'deep-mine recapture: using the empty barrel on Ana did not complete'))
    return caught


def deep_to_lower_checkpoint(log):
    if inventory.contains(ITEM.ANA_BARREL):
        _w158 = yield from use_item_on_loc(ITEM.ANA_BARREL, [LOC.MINE_CART], DEEP_CART, log)
        if not (_w158):
            return False
        _w159 = yield from execution.delay_until(lambda: not inventory.contains(ITEM.ANA_BARREL), 8000)
        if not (_w159):
            return False
    _w160 = yield from ride_mine_cart(DEEP_CART, log)
    if not (_w160):
        return False
    _w161 = yield from search_lower_barrel(False, log)
    if not (_w161):
        return False
    # At hidden stage 20 this barrel returns Ana (stage 21). If it offers an ordinary barrel, No changes nothing and proves Ana is already on the lift.
    return inventory.contains(ITEM.ANA_BARREL) or tourist_trap_area(game.tile()) == 'mineLower'


def retrieve_from_surface_lift(log):
    if tourist_trap_area(game.tile()) == 'mineLower':
        if inventory.contains(ITEM.ANA_BARREL):
            log('lift checkpoint: placing Ana on the underground lift')
            _w162 = yield from use_item_on_loc(ITEM.ANA_BARREL, [LOC.LIFT_BUCKET], LIFT_BUCKET, log, LIFT_GUARD_DIALOG, lambda: not inventory.contains(ITEM.ANA_BARREL))
            if not (_w162):
                log('lift checkpoint: underground lift interaction did not complete')
                return False
            _w163 = yield from execution.delay_until(lambda: not inventory.contains(ITEM.ANA_BARREL), 8000)
            if not (_w163):
                log('lift checkpoint: Ana remained in the backpack after the lift interaction')
                return False
        _w164 = yield from leave_mine(log)
        if not (_w164):
            log('lift checkpoint: could not reach the surface machinery')
            return False
    area = tourist_trap_area(game.tile())
    if area != 'campSurface':
        log(f'lift checkpoint: surface probe unavailable from area={area}')
        return False
    log('lift checkpoint: probing the surface winch and top barrel')
    empty_winch_followup = 'heavy barrel filled with stone comes to the surface'
    ana_winch_followup = any_phrase('barrel coming to the surface', 'get me out of here')
    winch_mark = game_messages.mark()
    _w165 = yield from interact_loc([LOC.SURFACE_WINCH], 'Use', SURFACE_WINCH_APPROACH, log)
    if not (_w165):
        log('lift checkpoint: surface winch interaction could not be dispatched')
        return False
    # After the same server delay an empty lift gives a game message and an Ana lift gives a multi-page modal.
    followed_up = yield from execution.delay_until(lambda: game_messages.saw_since(winch_mark, empty_winch_followup) or dialog_matches(ana_winch_followup), 8000)
    if not followed_up:
        observed = ' | '.join([message.text for message in game_messages.since(winch_mark)])
        log(f"lift checkpoint: surface winch follow-up timed out; messages=[{observed}] modal=[{' | '.join(chat_dialog.texts())}]")
        return False
    if chat_dialog.is_open() or chat_dialog.can_continue():
        _w166 = yield from drive_strict_dialog([], log, lambda: dialog_matches(ana_winch_followup))
        if not (_w166):
            return False
    _c167 = inventory.free() < 1
    if _c167:
        _w168 = yield from free_one_rescue_slot(log)
        _c167 = not (_w168)
    if _c167:
        return False
    recovered = yield from search_surface_barrel(log)
    log(('lift checkpoint: recovered Ana from the top barrel' if recovered else 'lift checkpoint: top barrel did not contain Ana'))
    return recovered


def bribe_driver_and_escape(log):
    if inventory.contains(ITEM.ANA_BARREL):
        log('surface cart: placing Ana in the cart')
        _w169 = yield from use_item_on_loc(ITEM.ANA_BARREL, [LOC.SURFACE_CART], SURFACE_CART_APPROACH, log)
        if not (_w169):
            log('surface cart: placing Ana in the cart did not complete')
            return False
        _w170 = yield from execution.delay_until(lambda: not inventory.contains(ITEM.ANA_BARREL), 8000)
        if not (_w170):
            log('surface cart: Ana remained in the backpack after the cart interaction')
            return False
    # A reload can land after paying the driver but before boarding, so Search first; with the ready bit set it boards for free.
    _w171 = yield from interact_loc([LOC.SURFACE_CART], 'Search', SURFACE_CART_APPROACH, log, ["Yes, I'll get on."])
    if _w171:
        # Boarding closes its choice modal for p_delay(1) before teleporting with Ana; wait for that so a driver click can't cancel the ride.
        escaped = yield from execution.delay_until(lambda: tourist_trap_area(game.tile()) == 'desert' and inventory.contains(ITEM.ANA_BARREL), 8000)
        if escaped:
            log('surface cart: ready-state boarding reached the desert with Ana')
            return True
    log('surface cart: ready-state boarding was not available')
    # With the coins banked after a restart use the prison-riot appeal; a clean run pays the 100-coin bribe.
    coins_sufficient = inventory.count(ITEM.COINS) >= 100
    coins_before = inventory.count(ITEM.COINS)
    dialog = (DRIVER_DIALOG if coins_sufficient else DRIVER_NO_COIN_DIALOG)
    log(f"surface cart: starting driver dialogue; coins>=100={('yes' if coins_sufficient else 'no')}")
    _w172 = yield from talk_strict(NPC.MINE_CART_DRIVER, SURFACE_CART_APPROACH, dialog, log, 8)
    if not (_w172):
        log('surface cart: driver dialogue did not complete')
        return False
    if coins_sufficient and inventory.count(ITEM.COINS) != coins_before - 100:
        log(f'surface cart: driver dialogue ended without the 100-Coin bribe ({coins_before}→{inventory.count(ITEM.COINS)})')
        return False
    yield from execution.delay_ticks(1)
    _w173 = yield from interact_loc([LOC.SURFACE_CART], 'Search', SURFACE_CART_APPROACH, log, ["Yes, I'll get on."])
    if not (_w173):
        log('surface cart: boarding interaction did not complete')
        return False

    def _fn174():
        area = tourist_trap_area(game.tile())
        return area == 'desert' and inventory.contains(ITEM.ANA_BARREL)
    escaped = yield from execution.delay_until(_fn174, 15000)
    log(('surface cart: driver sequence reached the desert with Ana' if escaped else 'surface cart: boarding did not reach the desert with Ana'))
    return escaped


def lower_rescue_checkpoint(log):
    # A failed lower-cart Agility roll leaves this state. Retry beside the cart; the lift/surface route would throw away a ready barrel and loop for minutes.
    if inventory.contains(ITEM.BARREL):
        log('lower checkpoint: empty barrel ready after a failed cart roll; retrying the cart in place')
        _result175 = yield from ride_mine_cart(LOWER_CART, log)
        return _result175
    if not inventory.contains(ITEM.ANA_BARREL):
        _w176 = yield from search_lower_barrel(False, log)
        if not (_w176):
            return False
        if inventory.contains(ITEM.ANA_BARREL):
            return True
    # An ordinary-barrel probe with no item means hidden stage 22.
    _result177 = yield from retrieve_from_surface_lift(log)
    return _result177


def run_surface_rescue_checkpoint(operations, log):
    yield from operations.maintain_survival()
    if event_signal.pending():
        return False
    if not operations.has_ana_barrel():
        # Safe at hidden stages 22, 23 and 25: the winch is harmless to repeat and the top barrel only yields Ana with its transport bit set.
        _w178 = yield from operations.retrieve_lift(log)
        if _w178:
            return True
        yield from operations.maintain_survival()
        if event_signal.pending():
            return False
    # Hidden stage 25 has Ana on this cart, so retry the full driver sequence before treating every transport bit as clear.
    for attempt in range(1, 3 + 1):
        yield from operations.maintain_survival()
        if event_signal.pending():
            return False
        log(f'surface cart attempt {attempt}/3')
        _w179 = yield from operations.escape_by_cart(log)
        if _w179:
            return True
        yield from operations.maintain_survival()
        if event_signal.pending():
            return False
        if attempt < 3:
            yield from operations.wait_between_attempts()
            if event_signal.pending():
                return False
    # A transient cart/driver failure shouldn't send you back underground while holding Ana; leave the state and retry next pass.
    if operations.has_ana_barrel():
        log('surface cart unresolved while carrying Ana; retrying this checkpoint in place')
        return False
    # Cleared bits or lost barrel: take the lower barrel and catch original Ana, which clears every transport bit server-side.
    yield from operations.maintain_survival()
    if event_signal.pending():
        return False
    log('surface lift/cart state is clear; starting the canonical deep-mine replay')
    recaptured = yield from operations.recapture_ana(log)
    if not recaptured:
        log(f'deep-mine recapture did not complete; current area={operations.current_area()}')
    return recaptured


def surface_rescue_checkpoint(log):
    slave_outfit_ready = all([inventory.contains(item) or equipment.contains(item) for item in SLAVE_OUTFIT])
    log(f"rescue checkpoint: area={tourist_trap_area(game.tile())}; empty barrel={('yes' if inventory.contains(ITEM.BARREL) else 'no')}; " + f"Ana barrel={('yes' if inventory.contains(ITEM.ANA_BARREL) else 'no')}; slave outfit={('ready' if slave_outfit_ready else 'missing')}; " + f"free slots={inventory.free()}; coins>=100={('yes' if inventory.count(ITEM.COINS) >= 100 else 'no')}")
    _result180 = yield from run_surface_rescue_checkpoint(Record({
        'has_ana_barrel': lambda: inventory.contains(ITEM.ANA_BARREL),
        'retrieve_lift': retrieve_from_surface_lift,
        'escape_by_cart': bribe_driver_and_escape,
        'recapture_ana': reach_and_catch_ana,
        'current_area': lambda: tourist_trap_area(game.tile()),
        'maintain_survival': lambda: sustain.run(),
        'wait_between_attempts': lambda: execution.delay_ticks(1),
    }), log)
    return _result180


def return_ana_to_irena(log):
    # Returning Ana runs straight into both reward menus with no dialogue boundary, so allow the skill choice here too.
    _w181 = yield from talk_strict(NPC.IRENA, IRENA, ['Agility.'], log)
    if not (_w181):
        return False
    _result182 = yield from execution.delay_until(lambda: not inventory.contains(ITEM.ANA_BARREL), 8000)
    return _result182


def claim_reward(log):
    # The same skill can be picked at both menus; the driver picks it twice and drains the quest-complete dialogue.
    _result183 = yield from talk_strict(NPC.IRENA, IRENA, ['Agility.'], log)
    return _result183


def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


def route_north(snap):
    area = tourist_trap_area(snap.tile)
    if area != 'desert' and area != 'irena' and area != 'bedabin':
        return None
    return custom('cross the Shantay Pass north for supplies', cross_shantay_pass_north)


def source_water_doses(snap, minimum, target, make_space):
    doses = waterskin_doses(snap)
    if doses >= minimum:
        return None
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if route:
        return route
    north = route_north(snap)
    if north:
        return north
    if not snap.bank_known:
        return scan_bank()
    partial_names = [lower(_x) for _x in WATERSKINS[1:]]
    if any([(name in partial_names) for name in list(list(snap.inv.keys()))]):
        keep = [name for name in rescue_keep() if not (name in partial_names)]
        return Record({'kind': 'deposit', 'keep': keep, 'exact_keep': True})
    missing_containers = math.ceil((target - doses) / 4)
    banked_full = banked(snap, ITEM.WATERSKIN)
    if banked_full > 0:
        qty = min(missing_containers, banked_full)
        _v184 = make_space(snap, qty)
        return (_v184 if _v184 is not None else bank_step([{'name': ITEM.WATERSKIN, 'qty': qty}]))
    purchase_cost = 35 * missing_containers
    coins = source_coins(snap, purchase_cost, 'replace Tourist Trap waterskins')
    if coins:
        return coins
    space = make_space(snap, missing_containers)
    if space:
        return space
    return Record({
        'kind': 'buy',
        'item': ITEM.WATERSKIN,
        'qty': missing_containers,
        'shop': SHANTAY_SHOP,
        'est_gp': purchase_cost,
    })


def source_configured_survival_food(snap):
    area = tourist_trap_area(snap.tile)
    minimum = (FOOD_ENTRY_FLOOR if area == 'mainland' or area == 'shantayNorth' else FOOD_RESTOCK_FLOOR)
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if configured_food_count(snap) < minimum and route:
        return route
    north = route_north(snap)
    if configured_food_count(snap) < minimum and north:
        return north
    return configured_food_withdrawal(snap, minimum, FOOD_ENTRY_TARGET, make_rescue_space)


def source_coins(snap, target, purpose):
    if held_count(snap, ITEM.COINS) >= target:
        return None
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if route:
        return route
    north = route_north(snap)
    if north:
        return north
    if not snap.bank_known:
        return scan_bank()
    missing = target - held_count(snap, ITEM.COINS)
    available = banked(snap, ITEM.COINS)
    if available > 0:
        return bank_step([{'name': ITEM.COINS, 'qty': min(missing, available, 40)}])
    return earn_quest_coins_step(target, purpose)


def source_rescue_coins(snap):
    if held_count(snap, ITEM.COINS) >= RESCUE_COIN_FLOOR:
        return None
    return source_coins(snap, RESCUE_COIN_TARGET, 'Tourist Trap rescue')


def survival_step(snap):
    if held(snap, ITEM.ANA_BARREL):
        return None
    if configured_food_name():
        food = source_configured_survival_food(snap)
        if food:
            return food
    else:
        area = tourist_trap_area(snap.tile)
        minimum = (FOOD_ENTRY_FLOOR if area == 'mainland' or area == 'shantayNorth' else FOOD_RESTOCK_FLOOR)
        ration = (source_kebabs(snap, FOOD_ENTRY_TARGET) if held_count(snap, ITEM.KEBAB) < minimum else None)
        if ration:
            return ration
    area = tourist_trap_area(snap.tile)
    minimum = (WATER_ENTRY_FLOOR if area == 'mainland' or area == 'shantayNorth' else WATER_RESTOCK_FLOOR)
    return source_water_doses(snap, minimum, WATER_ENTRY_DOSES, make_rescue_space)


def route_south(snap):
    area = tourist_trap_area(snap.tile)
    if area != 'mainland' and area != 'shantayNorth':
        return None
    skins = source_water_doses(snap, WATER_ENTRY_FLOOR, WATER_ENTRY_DOSES, make_rescue_space)
    if skins:
        return skins
    if not held(snap, ITEM.PASS):
        if not snap.bank_known:
            return scan_bank()
        # Why: the pass lands in a pack the prototype's materials have filled, and the shop refuses it there. This
        # departs from rs2b0t.
        space = make_critical_item_space(snap, 1)
        if space:
            return space
        if banked(snap, ITEM.PASS) > 0:
            return bank_step([{'name': ITEM.PASS, 'qty': 1}])
        coins = source_coins(snap, 6, 'replace a Shantay pass')
        if coins:
            return coins
        return Record({'kind': 'buy', 'item': ITEM.PASS, 'qty': 1, 'shop': SHANTAY_SHOP, 'est_gp': 6})
    return custom('cross the Shantay Pass', cross_shantay_pass)


def source_desert_outfit_copies(snap, target):
    if outfit_copies(snap, DESERT_OUTFIT) >= target:
        return None
    area = tourist_trap_area(snap.tile)
    route = safe_recovery_route(area)
    if route:
        return route
    north = route_north(snap)
    if north:
        return north
    if not snap.bank_known:
        return scan_bank()
    for name in DESERT_OUTFIT:
        missing = target - owned_now(snap, name)
        if missing <= 0:
            continue
        available_slots = (snap.free_slots if snap.free_slots is not None else missing)
        if available_slots == 0:
            can_wear_first_copy = target > 1 and outfit_copies(snap, DESERT_OUTFIT) >= 1 and not all([worn(snap, item) for item in DESERT_OUTFIT])
            if can_wear_first_copy:
                return custom('wear the first desert outfit to free recovery slots', wear_desert_outfit_for_space)
            space = make_critical_item_space(snap, 1)
            if space:
                return space
        qty = min(missing, max(1, available_slots))
        if banked(snap, name) > 0:
            withdraw_qty = min(qty, banked(snap, name))
            space = make_preparation_space(snap, withdraw_qty)
            return (space if space is not None else bank_step([{'name': name, 'qty': withdraw_qty}]))
        price = ([item for item in SHANTAY_TARGETS if item.name == name] or [None])[0].est_gp
        purchase_cost = price * qty
        coins = source_coins(snap, purchase_cost, f'replace {name}')
        if coins:
            return coins
        space = make_preparation_space(snap, qty)
        return (space if space is not None else Record({'kind': 'buy', 'item': name, 'qty': qty, 'shop': SHANTAY_SHOP, 'est_gp': purchase_cost}))
    return None


def source_pickaxe(snap):
    if owned_now(snap, ITEM.PICKAXE) > 0:
        return None
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if route:
        return route
    north = route_north(snap)
    if north:
        return north
    if not snap.bank_known:
        return scan_bank()
    if snap.free_slots == 0:
        space = make_critical_item_space(snap)
        if space:
            return space
    if banked(snap, ITEM.PICKAXE) > 0:
        space = make_preparation_space(snap, 1)
        return (space if space is not None else bank_step([{'name': ITEM.PICKAXE, 'qty': 1}]))
    coins = source_coins(snap, 2, 'replace the Tourist Trap pickaxe')
    if coins:
        return coins
    space = make_preparation_space(snap, 1)
    return (space if space is not None else Record({'kind': 'buy', 'item': ITEM.PICKAXE, 'qty': 1, 'shop': BOB_AXES, 'est_gp': 2}))


def ensure_desert_exterior_loadout(snap):
    outfit = source_desert_outfit_copies(snap, 1)
    if outfit:
        return outfit
    pickaxe = source_pickaxe(snap)
    if pickaxe:
        return pickaxe
    south = route_south(snap)
    if south:
        return south
    if not all([worn(snap, item) for item in DESERT_OUTFIT]) or not worn(snap, ITEM.PICKAXE):
        return custom('wear the camp-safe desert loadout', wear_desert_loadout)
    return None


def source_kebabs(snap, target=8):
    """Blank configured food means Kebabs."""
    if held_count(snap, ITEM.KEBAB) >= target:
        return None
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if route:
        return route
    north = route_north(snap)
    if north:
        return north
    if not snap.bank_known:
        return scan_bank()
    bank_food = withdraw_banked_shortage(snap, ITEM.KEBAB, target)
    if bank_food:
        return bank_food
    missing = target - held_count(snap, ITEM.KEBAB)
    coins = source_coins(snap, missing, 'buy Tourist Trap quest rations')
    if coins:
        return coins
    space = make_preparation_space(snap, missing)
    return (space if space is not None else Record({'kind': 'custom', 'name': f'buy {missing} Kebabs', 'run': lambda log: buy_kebabs(target, log)}))


def ensure_camp_surface(snap):
    area = tourist_trap_area(snap.tile)
    if area == 'campSurface':
        return None
    if area == 'campUpper':
        return custom('climb down to the mining camp', lambda log: climb_camp_ladder(False, log))
    if area == 'mineEntrance' or area == 'mineLower':
        return custom('leave the underground mine', leave_mine)
    if area == 'mineDeep':
        return custom('ride back to the lower mine', return_from_deep_mine)
    if not held(snap, ITEM.METAL_KEY):
        if not snap.bank_known or banked(snap, ITEM.METAL_KEY) > 0:
            north = route_north(snap)
            if north:
                return north
        if not snap.bank_known:
            return scan_bank()
        if banked(snap, ITEM.METAL_KEY) > 0:
            space = make_critical_item_space(snap)
            return (space if space is not None else bank_step([{'name': ITEM.METAL_KEY, 'qty': 1}]))
    loadout = ensure_desert_exterior_loadout(snap)
    if loadout:
        return loadout
    if not held(snap, ITEM.METAL_KEY):
        return custom('replace the mining-camp Metal key', provoke_and_defeat_captain)
    return custom('unlock the desert mining camp', enter_camp)


def ensure_mine_entrance(snap):
    area = tourist_trap_area(snap.tile)
    if (area == 'mineEntrance' or area == 'mineLower') and has_outfit(snap, SLAVE_OUTFIT) and not all([worn(snap, item) for item in SLAVE_OUTFIT]):
        return custom('wear the slave disguise', wear_slave_disguise_only)
    if area == 'mineEntrance':
        return None
    if area == 'mineLower':
        return custom('cross back to the cave guards', lambda log: cross_mine_cave(False, log))
    if area == 'mineDeep':
        return custom('ride back to the lower mine', return_from_deep_mine)
    pickaxe = source_pickaxe(snap)
    if pickaxe:
        return pickaxe
    if not has_outfit(snap, SLAVE_OUTFIT):
        # The late re-trade swaps worn desert pieces in place, so 1 set is enough and leaves room for rescue supplies.
        desert = source_desert_outfit_copies(snap, 1)
        if desert:
            return desert
    camp = ensure_camp_surface(snap)
    if camp:
        return camp
    if not has_outfit(snap, SLAVE_OUTFIT):
        return custom('replace the slave disguise', replace_lost_slave_outfit)
    if not all([worn(snap, item) for item in SLAVE_OUTFIT]) or not worn(snap, ITEM.PICKAXE):
        return custom('wear the slave disguise', wear_slave_loadout)
    return custom('open the slave-only mine doors', enter_mine)


def ensure_mine_lower(snap):
    area = tourist_trap_area(snap.tile)
    if area == 'mineLower':
        return None
    if area == 'mineDeep':
        return custom('ride back to the lower mine', return_from_deep_mine)
    if area == 'mineEntrance':
        if has_outfit(snap, SLAVE_OUTFIT) and not all([worn(snap, item) for item in SLAVE_OUTFIT]):
            return custom('wear the slave disguise', wear_slave_disguise_only)
        return custom('walk through the guarded mine cave', lambda log: cross_mine_cave(True, log))
    return ensure_mine_entrance(snap)


def plans_recovery_step(snap):
    if held(snap, ITEM.PLANS):
        return None
    area = tourist_trap_area(snap.tile)
    item_space = make_critical_item_space(snap)
    if item_space:
        return item_space
    if not snap.bank_known or banked(snap, ITEM.PLANS) > 0:
        route = safe_recovery_route(area)
        if route:
            return route
        north = route_north(snap)
        if north:
            return north
        if not snap.bank_known:
            return scan_bank()
        space = make_preparation_space(snap, 1)
        return (space if space is not None else bank_step([{'name': ITEM.PLANS, 'qty': 1}]))
    if (area == 'campSurface' or area == 'campUpper') and held(snap, ITEM.BEDABIN_KEY):
        return custom('distract Captain Siad and recover the plans', steal_technical_plans)
    if area == 'mineEntrance' or area == 'mineLower' or area == 'mineDeep':
        return safe_recovery_route(area)
    if not held(snap, ITEM.BEDABIN_KEY):
        route = safe_recovery_route(area)
        if route:
            return route
        if banked(snap, ITEM.BEDABIN_KEY) > 0:
            north = route_north(snap)
            if north:
                return north
            space = make_preparation_space(snap, 1)
            return (space if space is not None else bank_step([{'name': ITEM.BEDABIN_KEY, 'qty': 1}]))
        south = route_south(snap)
        lost = (ask_al_for_lost_plans_and_tip if snap.stage == TOURIST_TRAP_STAGE.MADE_DART_TIP else ask_al_for_lost_key_and_plans)
        return (south if south is not None else custom('ask Al Shabim to replace the plans key', lost))
    camp = ensure_camp_surface(snap)
    if camp:
        return camp
    return custom('distract Captain Siad and recover the plans', steal_technical_plans)


def remake_prototype_step(snap, need_dart):
    if need_dart and held(snap, ITEM.DART):
        return None
    if not held(snap, ITEM.DART_TIP):
        if not snap.bank_known:
            route = safe_recovery_route(tourist_trap_area(snap.tile))
            if route:
                return route
            north = route_north(snap)
            return (north if north is not None else scan_bank())
        banked_product = (ITEM.DART if need_dart and banked(snap, ITEM.DART) > 0 else (ITEM.DART_TIP if banked(snap, ITEM.DART_TIP) > 0 else None))
        if banked_product:
            route = safe_recovery_route(tourist_trap_area(snap.tile))
            if route:
                return route
            north = route_north(snap)
            if north:
                return north
            space = make_critical_item_space(snap)
            return (space if space is not None else bank_step([{'name': banked_product, 'qty': 1}]))
    if held(snap, ITEM.DART_TIP):
        feathers = source_consumable(snap, ITEM.FEATHER, 10)
        return (feathers if feathers is not None else custom('attach feathers to the prototype dart tip', fletch_prototype_dart))
    plans = plans_recovery_step(snap)
    if plans:
        return plans
    hammer = source_consumable(snap, ITEM.HAMMER, 1)
    if hammer:
        return hammer
    bars = source_consumable(snap, ITEM.BAR, 1)
    if bars:
        return bars
    route = safe_recovery_route(tourist_trap_area(snap.tile))
    if route:
        return route
    south = route_south(snap)
    if south:
        return south
    return custom('forge the prototype dart tip', forge_prototype_tip)


def step_label(step):
    if step.kind == 'talk':
        return f'talk {step.stop.npc}'
    elif step.kind == 'buy':
        return f'buy {step.qty}× {step.item} @ {step.shop.npc}'
    elif step.kind == 'withdraw':
        rows = [f"{i['name']}×{i['qty']}" for i in step.items]
        return f"withdraw {','.join(rows)}"
    elif step.kind == 'deposit':
        return f"deposit keep={'|'.join(step.keep)}"
    elif step.kind == 'custom':
        return step.name
    elif step.kind == 'wait':
        return f'wait:{step.reason}'
    elif step.kind == 'equip':
        return f'equip {step.item}'
    elif step.kind == 'scan_bank':
        return 'scan_bank'
    elif step.kind == 'done':
        return 'done'
    else:
        return step.kind


def observe_tourist_trap(snap, step):
    """Dense context for stuck runs; the engine logs it via observe and operators paste it into agents."""
    area = tourist_trap_area(snap.tile)
    # Why: pocketpy reads a replacement field that opens with a bracket straight after another as a call on it.
    tile = '(no tile)'
    if snap.tile:
        level = f',L{snap.tile.level}' if snap.tile.level else ''
        tile = f'({snap.tile.x},{snap.tile.z}' + level + ')'
    water = waterskin_doses(snap)
    containers = waterskin_containers(snap)
    food = configured_food_name()
    desert_worn = len([n for n in DESERT_OUTFIT if worn(snap, n)])
    slave_owned = len([n for n in SLAVE_OUTFIT if owned_now(snap, n) > 0])
    lines = [
        f"tt: stage={(snap.stage if snap.stage is not None else '?')} journal={snap.journal} area={area} tile={tile} free={(snap.free_slots if snap.free_slots is not None else '?')} bankKnown={snap.bank_known == True}",
        f"tt: water={water} doses across {containers} skins food={(food if food is not None else '(disabled)')}:{configured_food_count(snap)} " + f'pass={held_count(snap, ITEM.PASS)} coins={held_count(snap, ITEM.COINS)} ' + f'pick={owned_now(snap, ITEM.PICKAXE)} metalKey={held_count(snap, ITEM.METAL_KEY)} ' + f'bedabinKey={held_count(snap, ITEM.BEDABIN_KEY)} pineapple={held_count(snap, ITEM.PINEAPPLE)} ' + f'anaBarrel={held_count(snap, ITEM.ANA_BARREL)} barrel={held_count(snap, ITEM.BARREL)}',
        f'tt: desertWorn={desert_worn}/{len(DESERT_OUTFIT)} slaveOwned={slave_owned}/{len(SLAVE_OUTFIT)} ' + f'kebabs={held_count(snap, ITEM.KEBAB)} plans={held_count(snap, ITEM.PLANS)} ' + f'dartTip={held_count(snap, ITEM.DART_TIP)} dart={held_count(snap, ITEM.DART)}',
        f'tt: decide→ {step_label(step)}',
    ]
    if (area == 'desert' or area == 'irena' or area == 'bedabin') and water < WATER_RESTOCK_FLOOR:
        lines.append(f'tt: WARN only {water} waterskin doses in the desert — below {WATER_RESTOCK_FLOOR}-dose safety floor')
    if step.kind == 'wait' and step.reason == 'death':
        lines.append('tt: death dump — next loop re-provisions (ownsInventory) then re-decides from journal')
    return lines


def decide(snap):
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else 0)) >= TOURIST_TRAP_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Tourist Trap journal stage unavailable'})
    stage = snap.stage
    area = tourist_trap_area(snap.tile)
    # Capture, lockpick, equipment search and guard dialogue can all jail you at any stage, so location wins over stage.
    if area == 'surfaceJail':
        return custom('escape the surface jail through the rocks', escape_surface_jail)
    if area == 'undergroundJail':
        return custom('mine 15 punishment rocks and escape', escape_underground_jail)
    if stage >= TOURIST_TRAP_STAGE.TRADED_CLOTHES and (area == 'mineEntrance' or area == 'mineLower' or area == 'mineDeep') and not has_outfit(snap, SLAVE_OUTFIT):
        # The supply route can't leave this component without the disguise it wants to replace, so recover the outfit here first.
        return custom('return to the punishment mine to recover the slave disguise', return_to_punishment_mine_for_outfit)
    if stage >= TOURIST_TRAP_STAGE.STARTED and stage <= TOURIST_TRAP_STAGE.REWARD and (stage < TOURIST_TRAP_STAGE.REWARD or (stage == TOURIST_TRAP_STAGE.REWARD and (area == 'mainland' or area == 'shantayNorth'))):
        survival = survival_step(snap)
        if survival:
            return survival
    if stage >= TOURIST_TRAP_STAGE.ENTERED_CAMP and (stage != TOURIST_TRAP_STAGE.RESCUE or (not held(snap, ITEM.ANA_BARREL) and not has_outfit(snap, SLAVE_OUTFIT))) and (area == 'campSurface' or area == 'campUpper') and not held(snap, ITEM.METAL_KEY):
        # The desk gives a cell key then the Metal key, so a restart with neither needs 2 free slots.
        slots = (1 if held(snap, ITEM.CELL_KEY) else 2)
        if ((snap.free_slots if snap.free_slots is not None else slots)) < slots:
            return custom('free a slot for mining-camp key recovery', free_one_rescue_slot)
        return custom("recover the mining-camp keys from Captain Siad's desk", recover_mining_camp_keys)
    if stage == TOURIST_TRAP_STAGE.NOT_STARTED:
        prep = preparation_step(snap)
        if prep:
            return prep
        if not all([worn(snap, item) for item in DESERT_OUTFIT]) or not worn(snap, ITEM.PICKAXE):
            return custom('wear the desert quest loadout', wear_desert_loadout)
        south = route_south(snap)
        return (south if south is not None else custom('start Tourist Trap with Irena', start_with_irena))
    if stage == TOURIST_TRAP_STAGE.STARTED:
        loadout = ensure_desert_exterior_loadout(snap)
        if loadout:
            return loadout
        return custom('provoke the Mercenary Captain', challenge_captain)
    if stage == TOURIST_TRAP_STAGE.APPROACHED_CAPTAIN:
        loadout = ensure_desert_exterior_loadout(snap)
        if loadout:
            return loadout
        return custom('provoke and defeat the Mercenary Captain', provoke_and_defeat_captain)
    if stage == TOURIST_TRAP_STAGE.KILLED_CAPTAIN:
        if not held(snap, ITEM.METAL_KEY):
            if not snap.bank_known or banked(snap, ITEM.METAL_KEY) > 0:
                north = route_north(snap)
                if north:
                    return north
            if not snap.bank_known:
                return scan_bank()
            if banked(snap, ITEM.METAL_KEY) > 0:
                space = make_critical_item_space(snap)
                return (space if space is not None else bank_step([{'name': ITEM.METAL_KEY, 'qty': 1}]))
            loadout = ensure_desert_exterior_loadout(snap)
            if loadout:
                return loadout
            if snap.free_slots == 0:
                return custom("free one slot for the captain's Metal key", free_one_rescue_slot)
            return custom('provoke and defeat the respawned Mercenary Captain', provoke_and_defeat_captain)
        camp = ensure_camp_surface(snap)
        return (camp if camp is not None else custom('unlock the desert mining camp', enter_camp))
    if stage == TOURIST_TRAP_STAGE.ENTERED_CAMP or stage == TOURIST_TRAP_STAGE.SPOKEN_SLAVE or stage == TOURIST_TRAP_STAGE.FREED_SLAVE:
        outfit = source_desert_outfit_copies(snap, 2)
        if outfit:
            return outfit
        camp = ensure_camp_surface(snap)
        return (camp if camp is not None else custom('free the slave and trade the spare desert outfit', slave_unlock_and_trade))
    if stage == TOURIST_TRAP_STAGE.TRADED_CLOTHES:
        mine = ensure_mine_entrance(snap)
        return (mine if mine is not None else custom('open the slave-only mine doors', enter_mine))
    if stage == TOURIST_TRAP_STAGE.ENTERED_MINE:
        mine = ensure_mine_entrance(snap)
        return (mine if mine is not None else custom('learn the cave guard wants a Tenti pineapple', ask_cave_guard))
    if stage == TOURIST_TRAP_STAGE.FINDING_PINEAPPLE:
        route = safe_recovery_route(area)
        if route:
            return route
        item_space = make_critical_item_space(snap)
        if item_space:
            return item_space
        south = route_south(snap)
        return (south if south is not None else custom("accept Al Shabim's pineapple deal", ask_al_for_pineapple_deal))
    if stage == TOURIST_TRAP_STAGE.BEDABIN_KEY:
        if not held(snap, ITEM.BEDABIN_KEY) and snap.bank_known and banked(snap, ITEM.BEDABIN_KEY) == 0:
            item_space = make_critical_item_space(snap)
            if item_space:
                return item_space
            south = route_south(snap)
            if south:
                return south
        key = recover_critical(snap, ITEM.BEDABIN_KEY, custom('ask Al Shabim for a replacement key', ask_al_for_lost_key))
        if key:
            return key
        camp = ensure_camp_surface(snap)
        return (camp if camp is not None else custom('distract Captain Siad and steal the plans', steal_technical_plans))
    if stage == TOURIST_TRAP_STAGE.RETRIEVED_PLANS:
        plans = plans_recovery_step(snap)
        if plans:
            return plans
        bar = source_consumable(snap, ITEM.BAR, 1)
        if bar:
            return bar
        feathers = source_consumable(snap, ITEM.FEATHER, 10)
        if feathers:
            return feathers
        hammer = source_consumable(snap, ITEM.HAMMER, 1)
        if hammer:
            return hammer
        route = safe_recovery_route(area)
        if route:
            return route
        south = route_south(snap)
        return (south if south is not None else custom('show the technical plans to Al Shabim', show_plans_to_al))
    if stage == TOURIST_TRAP_STAGE.SHOWN_PLANS:
        remake = remake_prototype_step(snap, False)
        return (remake if remake is not None else custom('forge the prototype dart tip', forge_prototype_tip))
    if stage == TOURIST_TRAP_STAGE.MADE_DART_TIP:
        remake = remake_prototype_step(snap, True)
        return (remake if remake is not None else custom('attach feathers to the prototype dart tip', fletch_prototype_dart))
    if stage == TOURIST_TRAP_STAGE.FINISHED_DART:
        remake = remake_prototype_step(snap, True)
        if remake:
            return remake
        south = route_south(snap)
        return (south if south is not None else custom('give the prototype dart to Al Shabim', give_prototype_to_al))
    if stage == TOURIST_TRAP_STAGE.LEARNED_DARTS:
        if not held(snap, ITEM.PINEAPPLE) and snap.bank_known and banked(snap, ITEM.PINEAPPLE) == 0:
            item_space = make_critical_item_space(snap)
            if item_space:
                return item_space
            south = route_south(snap)
            if south:
                return south
        pineapple = recover_critical(snap, ITEM.PINEAPPLE, custom('replace the Tenti pineapple at Al Shabim', recover_pineapple_from_al))
        if pineapple:
            return pineapple
        mine = ensure_mine_entrance(snap)
        return (mine if mine is not None else custom('give the cave guard his Tenti pineapple', give_pineapple))
    if stage == TOURIST_TRAP_STAGE.GIVEN_PINEAPPLE:
        mine = ensure_mine_lower(snap)
        if mine:
            return mine
        if snap.free_slots == 0 and not held(snap, ITEM.BARREL):
            return custom('free one slot for the rescue barrel', free_one_rescue_slot)
        if not held(snap, ITEM.BARREL):
            return custom('take an empty mining barrel', lambda log: search_lower_barrel(True, log))
        return custom('ride the mine cart and catch Ana in the barrel', reach_and_catch_ana)
    if stage == TOURIST_TRAP_STAGE.USED_MINE_CART:
        if area == 'mineLower':
            if snap.free_slots == 0 and not held(snap, ITEM.BARREL):
                return custom('free one slot for the rescue barrel', free_one_rescue_slot)
            if not held(snap, ITEM.BARREL):
                return custom('take an empty mining barrel', lambda log: search_lower_barrel(True, log))
            return custom('ride back to Ana with the empty barrel', lambda log: ride_mine_cart(LOWER_CART, log))
        if area == 'mineDeep':
            return (custom('put Ana safely in the barrel', catch_ana_in_barrel) if held(snap, ITEM.BARREL) else custom('return to the lower mine for an empty barrel', return_from_deep_mine))
        mine = ensure_mine_lower(snap)
        return (mine if mine is not None else custom('return to the deep mine', reach_and_catch_ana))
    if stage == TOURIST_TRAP_STAGE.RESCUE:
        if not held(snap, ITEM.ANA_BARREL) and not has_outfit(snap, SLAVE_OUTFIT):
            recovery = ensure_mine_entrance(snap)
            if recovery:
                return recovery
        if not held(snap, ITEM.ANA_BARREL) and area != 'mineDeep' and area != 'mineLower' and area != 'mineEntrance':
            coins = source_rescue_coins(snap)
            if coins:
                return coins
        if area == 'mineDeep':
            if held(snap, ITEM.BARREL):
                # Catching Ana clears every stale transport bit first, so it resets the rescue at any hidden stage.
                return custom('reset the rescue state by catching original Ana', catch_ana_in_barrel)
            return custom('move Ana through the deep-to-lower cart checkpoint', deep_to_lower_checkpoint)
        if area == 'mineLower':
            if held(snap, ITEM.ANA_BARREL):
                return custom('lift Ana and retrieve her at the surface checkpoint', retrieve_from_surface_lift)
            if held(snap, ITEM.BARREL):
                return custom('retry the lower mine cart with the empty barrel', lambda log: ride_mine_cart(LOWER_CART, log))
            if snap.free_slots == 0:
                return custom('free one slot for the lower barrel probe', free_one_rescue_slot)
            return custom('resolve the lower barrel/lift checkpoint', lower_rescue_checkpoint)
        if area == 'mineEntrance':
            return custom('leave the mine to resolve the surface checkpoint', leave_mine)
        if area == 'campSurface':
            return custom('resolve the surface winch/cart checkpoint', surface_rescue_checkpoint)
        if area == 'campUpper':
            return custom('climb down to the surface rescue machinery', lambda log: climb_camp_ladder(False, log))
        if (area == 'desert' or area == 'irena') and held(snap, ITEM.ANA_BARREL):
            return custom('return Ana to Irena', return_ana_to_irena)
        if area == 'desert' or area == 'irena' or area == 'bedabin':
            camp = ensure_camp_surface(snap)
            return (camp if camp is not None else custom("return to the mining camp to resume Ana's rescue", enter_camp))
        south = route_south(snap)
        return (south if south is not None else Record({'kind': 'wait', 'reason': 'locating the visible Ana rescue checkpoint'}))
    if stage == TOURIST_TRAP_STAGE.REWARD:
        south = route_south(snap)
        return (south if south is not None else custom('claim both Tourist Trap skill rewards', claim_reward))
    return Record({'kind': 'wait', 'reason': f'unrecognized Tourist Trap journal stage {stage}'})


# Why: the cells, the walled camp, the guarded mine and the experimental tent are left only by the quest's own legs, so a
# queue that moves on from inside one walks the next quest at a locked door. This departs from rs2b0t.
SEALED_AREAS = ['surfaceJail', 'undergroundJail', 'campSurface', 'campUpper', 'mineEntrance', 'mineLower', 'mineDeep', 'bedabinTent']


def in_sealed_area(tile):
    return tourist_trap_area(tile) in SEALED_AREAS


touristtrap = QuestModule(**{
    'record': quest_record('desertrescue'),
    'bank': DRAYNOR_BANK,
    'grind': ['Mercenary Captain'],
    'tools': ['bronze pickaxe'],
    'owns_inventory': True,
    'sustain': Record({'foods': [ITEM.KEBAB], 'eat_below_hp': 0.5}),
    'read_stage': read_tourist_trap_stage,
    'observe': observe_tourist_trap,
    'resume_at': in_sealed_area,
    'decide': decide,
})
