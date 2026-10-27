"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dragonslayer/index.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.quests.journal_text import normalize_journal
from rs2004 import execution
from rs2004.quests.engine.types import QuestModule
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.quests.engine.types import banked_id, has_flag, held_id
from rs2004.quests.data import QUESTS
from rs2004.quests.food import quest_food
from rs2004.quests.prayer import PRAYER_POTION
from rs2004.quests.weapons import best_held, best_banked, MELEE_WEAPONS
from rs2004.quests.armour import armour_choice
from rs2004.quests.exec.primitives import goto_npc, open_dialogue, talk_through
from rs2004.quests.defs.dragonslayer.areas import DS_ID, DS_ITEM, DS_LOC, DS_NPC, SHIP_PRICE, SHIP_REPAIR, WORMBRAIN_PRICE
from rs2004.quests.defs.dragonslayer.journal import DRAGON_STAGE, describe_journal, read_dragon_progress
from rs2004.quests.defs.dragonslayer.maze import MazeRun, held_by_id, in_maze, leave_maze, loot_chest, maze_scene_loaded
from rs2004.quests.defs.dragonslayer.supplies import SUPPLY_GATHERS, SUPPLY_TOOLS, in_plank_graveyard, smith_nails
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.traversal import traversal
from rs2004.tabs import quests
import _core

__all__ = ['OZIACH_GOALS', 'decide', 'dragonslayer']

GUILDMASTER = Record({
    'npc': 'Guild master',
    'anchor': DS_NPC.GUILDMASTER,
    'leash': 8,
    'prefer': ['Do you know where I could get a Rune Plate mail body?'],
})
OZIACH = Record({'npc': 'Oziach', 'anchor': DS_NPC.OZIACH, 'leash': 6, 'prefer': []})
DUKE = Record({
    'npc': 'Duke Horacio',
    'anchor': DS_NPC.DUKE,
    'leash': 6,
    'prefer': ["I seek a shield that will protect me from the dragon's breath."],
})
ORACLE = Record({
    'npc': 'Oracle',
    'anchor': DS_NPC.ORACLE,
    'leash': 6,
    'prefer': ['I seek a piece of the map to the island of Crandor.'],
})
KLARENSE = Record({
    'npc': 'Klarense',
    'anchor': DS_NPC.KLARENSE,
    'leash': 6,
    'prefer': ["I don't suppose I could buy it?", 'Yep, sounds good.'],
})
NED_HIRE = Record({
    'npc': 'Ned',
    'anchor': DS_NPC.NED,
    'leash': 6,
    'prefer': [
    "You're a sailor? Could you take me to the island of Crandor?",
    'So are you going to take me to Crandor Island now then?',
],
})
NED_ABOARD = Record({'npc': 'Ned', 'anchor': DS_NPC.NED_ABOARD, 'leash': 8, 'prefer': ['Yep lets go!']})
ORACLE_DOOR_ITEMS = [DS_ID.MIND_BOMB, DS_ID.UNFIRED_BOWL, DS_ID.LOBSTER_POT, DS_ID.SILK]
# Why: oziach.rs2 lines 100/107/124/131/138 each move the quest on: the rune-plate chain sets %dragonquest = spoken_to_oziach, the first piece hands over melzarkey, the second sets %dragon_oracle, the third %dragon_goblin, the shield %dragon_shield.
# Why: none of those varps are client-readable and the journal can't be read with a dialogue open, so goals are judged on what he says, which is distinct per branch.
# Why: tracking clicked options looped, since his menus re-offer answered questions and the first and second map piece swap places.
OZIACH_OPENING = [
    'Can you sell me some Rune plate mail?',
    "The guildmaster of the Champions' Guild told me.",
    'So how am I meant to prove that?',
    'A dragon, that sounds like fun!',
    'And will I need anything to defeat this dragon?',
]
FIND_DRAGON = 'So where can I find this dragon?'
FAREWELL = "Ok I'll try and get everything together."
OZIACH_GOALS = [
    Record({'ask': 'Where is the first piece of the map?', 'heard': "melzar's maze"}),
    Record({'ask': 'Where is the second piece of the map?', 'heard': 'oracle on the ice mountain'}),
    Record({'ask': 'Where is the third piece of the map?', 'heard': 'goblins from the goblin village'}),
    Record({'ask': 'Where can I get an antidragon shield?', 'heard': 'duke of lumbridge castle'}),
]


def flatten(lines):
    return normalize_journal(lines)


def option_for(options, want):
    return ([o for o in options if (want.lower() in o.lower())] or [None])[0]


def talk_oziach(log):
    """Drives Oziach until every goal has been answered, then leaves."""
    _w1 = yield from goto_npc(OZIACH, [], log)
    if not (_w1):
        return False
    _w2 = yield from open_dialogue(OZIACH.npc, log)
    if not (_w2):
        return False
    answered = set()
    for i in range(200):
        if event_signal.pending():
            return False
        options = chat_dialog.options()
        if len(options) == 0 and chat_dialog.is_open():
            said = flatten(chat_dialog.texts())
            for goal in OZIACH_GOALS:
                if (goal.heard in said) and not (goal.ask in answered):
                    answered.add(goal.ask)
                    log(f'Oziach answered: {goal.ask}')
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if len(options) > 0:
            outstanding = [g for g in OZIACH_GOALS if not (g.ask in answered)]
            _v3 = ([o for o in [option_for(options, o) for o in OZIACH_OPENING] if o is not None] or [None])[0]
            _v4 = (_v3 if _v3 is not None else ([o for o in [option_for(options, g.ask) for g in outstanding] if o is not None] or [None])[0])
            _v5 = (_v4 if _v4 is not None else ((option_for(options, FIND_DRAGON) if len(outstanding) > 0 else None)))
            pick = (_v5 if _v5 is not None else option_for(options, FAREWELL))
            if not pick:
                log(f"nothing useful in [{' | '.join(options)}]")
                return False
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            continue
        if not chat_dialog.is_open():
            break
        yield from execution.delay_ticks(1)
    # decide() re-runs this step until the journal agrees, so a partial pass costs one more conversation.
    return len(answered) == len(OZIACH_GOALS)


def walk(to, log, radius=2):
    route = traversal.walk_resilient(to, radius=radius, attempts=3, timeout_ms=180000, log=log)
    while True:
        try:
            waiting = next(route)
        except StopIteration as result:
            return result.value
        yield waiting
        if event_signal.pending():
            return False
        yield from sustain.run()


maze = MazeRun()


def buy_map_from_wormbrain(log):
    """Wormbrain is caged: the talk is an ap-op, taken from outside through the bars."""
    if held_by_id(DS_ID.MAP_WORMBRAIN):
        return True
    if inventory.count('Coins') < WORMBRAIN_PRICE:
        log(f'Wormbrain wants {WORMBRAIN_PRICE} coins and the pack is short')
        return False
    _w6 = yield from walk(DS_NPC.WORMBRAIN_STAND, log, 1)
    if not (_w6):
        return False
    # gotoNpc would try to stand next to him; the bars block that, and the server answers the click from 3 tiles out on line of sight.
    ok = yield from talk_through('Wormbrain', [
        "I believe you've got a piece of map that I need.",
        'I suppose I could pay you for the map piece',
        'Alright then, 10,000 it is.',
    ], log)
    if not ok:
        return False
    _result7 = yield from execution.delay_until(lambda: held_by_id(DS_ID.MAP_WORMBRAIN), 6000)
    return _result7


def open_oracle_magic_door(log, want_east):
    """Open the magic door (both ways). Stand west to enter, east to leave (#379)."""
    _w8 = yield from maze_scene_loaded()
    if not (_w8):
        return False
    stand = (DS_LOC.ORACLE_DOOR_STAND if want_east else Tile(3051, 9840, 0))
    # Enter from west stand; leave from east of the door tile.
    leave_stand = Tile(3052, 9840, 0)
    _w9 = yield from walk((stand if want_east else leave_stand), log, 0)
    if not (_w9):
        return False

    def _fn10(l):
        t = l.tile()
        return t.x == DS_LOC.ORACLE_DOOR.x and t.z == DS_LOC.ORACLE_DOOR.z
    door = locs.query().name('Door').where(_fn10).first()
    if not door:
        log('the magic door is not in the scene yet')
        return False
    log(('opening the magic door with the four charms' if want_east else 'opening the magic door to leave the oracle chest room'))
    if not (door.interact('Open')):
        return False

    def _fn12():
        t = game.tile()
        if not t or t.z < 9800:
            return False
        return (t.x >= 3051 if want_east else t.x < 3051)
    _result11 = yield from execution.delay_until(_fn12, 8000)
    return _result11


def in_oracle_chest_room(t):
    return not not t and t.level == 0 and t.x >= 3051 and t.x <= 3060 and t.z >= 9836 and t.z <= 9845


def oracle_chest(log):
    """The Oracle's door eats a mind bomb, unfired bowl, lobster pot and silk."""
    here = game.tile()
    past_door = in_oracle_chest_room(here)
    # #379: after the piece is looted, the room has no nav edge out, open the
    # door west and only then return true so coinsShort/bank can run.
    if held_by_id(DS_ID.MAP_ORACLE):
        if past_door:
            log('map piece in hand — leaving the oracle chest room')
            _result13 = yield from open_oracle_magic_door(log, False)
            return _result13
        return True
    if not past_door:
        _w14 = yield from walk(DS_LOC.ORACLE_DOOR_STAND, log, 0)
        if not (_w14):
            return False
        # Once you've been through, the door opens for nothing, so try it even with a charm missing.
        if not all([inventory.count_by_id(id) > 0 for id in ORACLE_DOOR_ITEMS]):
            log('not carrying all four charms — the door may already be open to me')
        _result15 = yield from open_oracle_magic_door(log, True)
        return _result15
    _w17 = yield from walk(DS_LOC.ORACLE_CHEST_STAND, log, 1)
    _c16 = not (_w17)
    if not _c16:
        _w18 = yield from maze_scene_loaded()
        _c16 = not (_w18)
    if _c16:
        return False
    _w19 = yield from loot_chest(DS_ID.MAP_ORACLE, log)
    if not (_w19):
        return False
    # Walk out now so the next decide (coins / Wormbrain) isn't planned from inside a sealed room.
    log('looted oracle map piece — leaving through the magic door')
    _result20 = yield from open_oracle_magic_door(log, False)
    return _result20


def combine_map(log):
    first = ([i for i in inventory.items() if i.id == DS_ID.MAP_MELZAR] or [None])[0]
    second = ([i for i in inventory.items() if i.id == DS_ID.MAP_WORMBRAIN] or [None])[0]
    if not first or not second:
        return False
    log('joining the three map pieces')
    if not (first.use_on(second)):
        return False
    _result21 = yield from execution.delay_until(lambda: held_by_id(DS_ID.MAP), 8000)
    return _result21


def in_ship_hold(t):
    return not not t and t.x >= 3040 and t.x <= 3055 and t.z >= 9630 and t.z <= 9650


# Why: gangplank and ladder are scripted teleports off the nav graph, and the gangplank only reaches the deck, so boarding falls through to the ladder.
def go_below_decks(log, boarded=False):
    """Board the ship and drop into the hold."""
    here = game.tile()
    if in_ship_hold(here):
        return True
    if on_deck(here):
        ladder = locs.query().name('Ladder').action('Climb-down').within(6).nearest()
        if not ladder:
            log('no ladder down on deck yet')
            return False
        log('climbing down into the hold')
        if not (ladder.interact('Climb-down')):
            return False
        _result22 = yield from execution.delay_until(lambda: in_ship_hold(game.tile()), 8000)
        return _result22
    if boarded:
        return False
    _w24 = yield from walk(DS_LOC.GANGPLANK_STAND, log, 0)
    _c23 = not (_w24)
    if not _c23:
        _w25 = yield from maze_scene_loaded()
        _c23 = not (_w25)
    if _c23:
        return False
    plank = locs.query().name('Gangplank').action('Cross').within(5).nearest()
    if not plank:
        log('no gangplank beside the dock')
        return False
    log('boarding the Lady Lumbridge')
    if not (plank.interact('Cross')):
        return False
    _w26 = yield from execution.delay_until(lambda: on_deck(game.tile()), 8000)
    if not (_w26):
        return False
    yield from maze_scene_loaded()
    _result27 = yield from go_below_decks(log, True)
    return _result27


def repair_ship(log):
    """Three planks, four nails each, driven in with a hammer."""
    _w28 = yield from go_below_decks(log)
    if not (_w28):
        return False
    yield from maze_scene_loaded()

    def find_hole():
        return locs.query().name('Hole').within(8).nearest()

    # Why: locs read blank for about a tick after the teleport into the hold, and nothing on the ship is walkable, so wait the snapshot out.
    hole = find_hole()
    if not hole:
        yield from execution.delay_ticks(2)
        hole = find_hole()
    plank = ([i for i in inventory.items() if i.id == DS_ID.PLANK] or [None])[0]
    if not hole:
        log('no hole in the hold yet')
        return False
    if not plank:
        log('out of planks with the hull still open')
        return False
    before = inventory.count_by_id(DS_ID.PLANK)
    log('patching a hole in the hull')
    if not (plank.use_on(hole)):
        return False
    _result29 = yield from execution.delay_until(lambda: inventory.count_by_id(DS_ID.PLANK) < before, 10000)
    return _result29


def board_for_crandor(log):
    """Ned waits on the top deck once he has the map; the hold ladder now goes there."""
    here = game.tile()
    if here and here.level >= 3:
        return True
    _result30 = yield from go_below_decks(log)
    return _result30


def on_deck(t):
    return not not t and t.level >= 1 and t.x >= 3044 and t.x <= 3052 and t.z >= 3204 and t.z <= 3212


def aboard(t):
    return on_deck(t) or in_ship_hold(t)


def leave_ship(log):
    """Every leg that starts ashore walks off first; the gangplank and ladders are scripted teleports off the nav graph."""
    here = game.tile()
    if not aboard(here):
        return True
    if in_ship_hold(here):
        ladder = locs.query().name('Ladder').action('Climb-up').within(6).nearest()
        if not ladder:
            log('no ladder up out of the hold')
            return False
        log('climbing out of the hold')
        if not (ladder.interact('Climb-up')):
            return False
        _result31 = yield from execution.delay_until(lambda: on_deck(game.tile()), 8000)
        return _result31
    plank = locs.query().name('Gangplank').action('Cross').within(6).nearest()
    if not plank:
        log('no gangplank off the deck')
        return False
    log('going ashore')
    if not (plank.interact('Cross')):
        return False
    _result32 = yield from execution.delay_until(lambda: not aboard(game.tile()), 8000)
    return _result32


def in_elvarg_lair(t):
    return not not t and t.x >= 2847 and t.x <= 2863 and t.z >= 9628 and t.z <= 9646


def in_crandor_dungeon(t):
    return not not t and t.x >= 2810 and t.x <= 2880 and t.z >= 9600 and t.z <= 9670


def on_crandor_surface(t):
    return not not t and t.x >= 2810 and t.x <= 2880 and t.z >= 3225 and t.z <= 3300


def on_crandor(t):
    return in_crandor_dungeon(t) or on_crandor_surface(t)


shortcut_opened = False


# Why: one loc on the Crandor row serves both directions, matched by tile since every other wall down here is called "Wall" too.
def open_wall(log):
    """Click the secret wall, from whichever side the bot is standing on."""
    at = DS_LOC.CRANDOR_SECRET_DOOR

    def _fn33(l):
        t = l.tile()
        return t.x == at.x and t.z == at.z and t.level == at.level
    leaf = locs.query().name('Wall').action('Open').where(_fn33).first()
    if not leaf:
        log('the secret wall is not in the scene')
        return False
    # Arrival upkeep can drink a potion; give that action its tick before sending Open.
    yield from execution.delay_ticks(1)
    return leaf.interact('Open')



# Why: $entering is false from this row, so the server teleports you onto the wall's own tile.
def cross_secret_wall(log):
    """Cross back into Crandor from the Karamja side."""
    _w35 = yield from walk(DS_LOC.SECRET_WALL_KARAMJA_STAND, log, 0)
    _c34 = not (_w35)
    if not _c34:
        _w36 = yield from maze_scene_loaded()
        _c34 = not (_w36)
    if _c34:
        return False
    log('back through the secret wall into Crandor')
    _w37 = yield from open_wall(log)
    if not (_w37):
        return False
    _w38 = yield from execution.delay_until(lambda: in_crandor_dungeon(game.tile()), 8000)
    if _w38:
        return True
    # From this side it answers "nothing interesting happens" until %dragon_wall is set, and only the Crandor side can set it.
    log('the wall will not open from Karamja — it was never opened from Crandor, and there is no other way back in')
    return False


# Why: the rock opening, pot hole and wall are scripted teleports off the nav graph, so each leg is one walk plus one interaction.
def descend_crandor(log):
    """Every way into Crandor's dungeon, by where the bot is standing."""
    here = game.tile()
    if not here:
        return False
    if in_crandor_dungeon(here):
        return True
    if on_crandor_surface(here):
        _w40 = yield from walk(DS_LOC.CRANDOR_ROCK, log, 1)
        _c39 = not (_w40)
        if not _c39:
            _w41 = yield from maze_scene_loaded()
            _c39 = not (_w41)
        if _c39:
            return False
        opening = locs.query().name('Rock opening').action('Climb-down').within(5).nearest()
        if not opening:
            log('no rock opening in reach')
            return False
        log('climbing down into Crandor')
        if not (opening.interact('Climb-down')):
            return False
        _w42 = yield from execution.delay_until(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 0)) >= 9000, 8000)
        if not (_w42):
            return False
        _result43 = yield from maze_scene_loaded()
        return _result43
    # Why: from anywhere else, including the Lumbridge respawn, the ship has crash-landed, so the wall is the only way in; the volcano pot hole and rope are on the nav graph.
    _result44 = yield from cross_secret_wall(log)
    return _result44


# Why: a death against Elvarg with the wall still shut strands the quest, since the ship crash-lands and the island has no boat.
# Why: the wall spawns angle 3 (m44_150.jm2), so check_axis_locactive reads "entering" as z == 9600, the Crandor row; from Karamja it answers "nothing interesting happens" until %dragon_wall is set.
# Why: opening it teleports you through, so coming back is half of this leg.
def unlock_shortcut(log):
    global shortcut_opened
    """Open the Karamja wall from the Crandor side and come straight back."""
    wall = DS_LOC.CRANDOR_SECRET_DOOR
    here = game.tile()
    # Already through: walking back proves the shortcut is open, and it's the same walk a death makes later.
    if here and here.z >= 9000 and not in_crandor_dungeon(here):
        shortcut_opened = yield from cross_secret_wall(log)
        return shortcut_opened
    _w45 = yield from descend_crandor(log)
    if not (_w45):
        return False
    _w47 = yield from walk(wall, log, 0)
    _c46 = not (_w47)
    if not _c46:
        _w48 = yield from maze_scene_loaded()
        _c46 = not (_w48)
    if _c46:
        return False
    log('opening the secret wall so there is a way back in')
    _w49 = yield from open_wall(log)
    if not (_w49):
        return False
    # Landing on the Karamja row proves %dragon_wall took. The next pass walks back in.
    yield from execution.delay_until(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < wall.z, 8000)
    return False


def reach_elvarg(log):
    """The lair gate is locked until the ship has sailed and isn't on the nav graph."""
    if in_elvarg_lair(game.tile()):
        return True
    _w50 = yield from descend_crandor(log)
    if not (_w50):
        return False
    _w52 = yield from walk(DS_LOC.ELVARG_GATE_STAND, log, 0)
    _c51 = not (_w52)
    if not _c51:
        _w53 = yield from maze_scene_loaded()
        _c51 = not (_w53)
    if _c51:
        return False
    gate = locs.query().name('Gate').action('Open').within(4).nearest()
    if not gate:
        log('no gate into the lair in reach')
        return False
    log('opening the lair gate')
    if not (gate.interact('Open')):
        return False
    _result54 = yield from execution.delay_until(lambda: in_elvarg_lair(game.tile()), 8000)
    return _result54


def kill_elvarg(log):
    # Her breath maxes 70 without the shield and 10 with it worn.
    if not equipment.contains(DS_ITEM.SHIELD):
        if not inventory.contains(DS_ITEM.SHIELD):
            log('no anti-dragonbreath shield — she will burn straight through')
            return False
        log('wearing the shield before going in')
        yield from equipment.equip(DS_ITEM.SHIELD)
        return False
    _w55 = yield from reach_elvarg(log)
    if not (_w55):
        return False
    elvarg = npcs.query().name('Elvarg').action('Attack').within(16).nearest()
    if not elvarg:
        log('no Elvarg in the lair yet')
        yield from execution.delay_ticks(3)
        return False
    log('attacking Elvarg')
    if not (elvarg.interact('Attack')):
        return False
    # Keep the journal closed during the fight: opening it between swings stops our attack.
    deadline = _core.step_time() + 90000
    attacked_at = game.tick()
    while _core.step_time() < deadline:
        if event_signal.pending():
            return False
        if quests.status('Dragon Slayer') == 'complete':
            return True
        before_upkeep = game.tick()
        yield from sustain.run()
        if not elvarg.valid():
            break
        now = game.tick()
        if now == before_upkeep and now - attacked_at >= 8:
            elvarg.interact('Attack')
            attacked_at = now
        yield from execution.delay_ticks(1)
    return quests.status('Dragon Slayer') == 'complete'


# Why: Crandor has no bank and no boat after the kill, so the wall is the way home.
# Why: both gate leaves are angle 0, so check_axis_locactive reads the lair's own column as "entering" and the lock only guards the way in.
def leave_crandor(log):
    """Get off the island once Elvarg is dead."""
    here = game.tile()
    if not here or not on_crandor(here):
        return True
    if in_elvarg_lair(here):
        _w57 = yield from walk(DS_LOC.ELVARG_GATE_INSIDE, log, 0)
        _c56 = not (_w57)
        if not _c56:
            _w58 = yield from maze_scene_loaded()
            _c56 = not (_w58)
        if _c56:
            return False
        gate = locs.query().name('Gate').action('Open').within(4).nearest()
        if not gate:
            log('no gate out of the lair')
            return False
        log('letting myself out of the lair')
        if not (gate.interact('Open')):
            return False
        _result59 = yield from execution.delay_until(lambda: not in_elvarg_lair(game.tile()), 8000)
        return _result59
    if on_crandor_surface(here):
        _result60 = yield from descend_crandor(log)
        return _result60
    _w62 = yield from walk(DS_LOC.CRANDOR_SECRET_DOOR, log, 0)
    _c61 = not (_w62)
    if not _c61:
        _w63 = yield from maze_scene_loaded()
        _c61 = not (_w63)
    if _c61:
        return False
    log('leaving Crandor through the secret wall')
    _w64 = yield from open_wall(log)
    if not (_w64):
        return False
    _result65 = yield from execution.delay_until(lambda: not on_crandor(game.tile()), 8000)
    return _result65


def custom(name, run):
    return (Record({'kind': 'custom', 'name': name, 'run': run}))


def where(snap, id):
    """Where an item is, for logs that have to explain a decision."""
    _v66 = (snap.inv_ids or {}).get(id)
    if ((_v66 if _v66 is not None else 0)) > 0:
        return 'carried'
    if (id in (snap.worn_ids or set())):
        return 'worn'
    _v67 = (snap.bank_ids or {}).get(id)
    if ((_v67 if _v67 is not None else 0)) > 0:
        return 'banked'
    return 'nowhere'


def anywhere(snap, id):
    """Inventory, worn or bank. The quest is resumable from any of the three."""
    _v68 = (snap.inv_ids or {}).get(id)
    return ((_v68 if _v68 is not None else 0)) > 0 or (((snap.bank_ids or {}).get(id) if (snap.bank_ids or {}).get(id) is not None else 0)) > 0 or (((id in (snap.worn_ids or set())) if (id in (snap.worn_ids or set())) is not None else False))


MAP_PIECES = [DS_ID.MAP_MELZAR, DS_ID.MAP_WORMBRAIN, DS_ID.MAP_ORACLE]


# Why: Wormbrain's 10k and Klarense's 2k must be in the pack before the dialogue opens; fetching them per leg lets the record ask for a single coin.
def coins_short(snap, price):
    """A step that fetches the coins one leg is about to spend, or null."""
    _v69 = snap.inv.get('coins')
    held = (_v69 if _v69 is not None else 0)
    if held >= price:
        return None
    return Record({'kind': 'withdraw', 'items': [{'name': 'Coins', 'qty': price + 1000 - held}]})


def banked_pieces(snap):
    """A piece left in the bank reads to the journal as never found; fetch it back."""
    want = [id for id in list(MAP_PIECES) + [DS_ID.MAP] if (((snap.bank_ids or {}).get(id) if (snap.bank_ids or {}).get(id) is not None else 0)) > 0 and (((snap.inv_ids or {}).get(id) if (snap.inv_ids or {}).get(id) is not None else 0)) == 0]
    return [({'name': (DS_ITEM.MAP if id == DS_ID.MAP else DS_ITEM.MAP_PART), 'qty': 1, 'id': id}) for id in want]


# Why: Elvarg is level 83 with no bank on the island, and by now the shield is worn and the shopping spent, so the pack has the slots.
ELVARG_FOOD = 18
MAZE_FOOD = 12
KARAMJA_FARE = 100


# Why: Crandor is one-way, so anything not aboard when the ship sails is out of reach; killElvarg can only report a missing shield.
def gear_up(snap):
    """The last preparation done ashore, or null when the pack is ready."""
    melee = combat_gear(snap)
    if melee:
        return melee
    if not (DS_ID.SHIELD in (snap.worn_ids or set())):
        _v70 = (snap.inv_ids or {}).get(DS_ID.SHIELD)
        if ((_v70 if _v70 is not None else 0)) > 0:
            return Record({'kind': 'equip', 'item': DS_ITEM.SHIELD})
        _v71 = (snap.bank_ids or {}).get(DS_ID.SHIELD)
        if ((_v71 if _v71 is not None else 0)) > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': DS_ITEM.SHIELD, 'qty': 1, 'id': DS_ID.SHIELD}]})
        return Record({'kind': 'talk', 'stop': DUKE})
    potions = combat_potions(snap)
    if potions:
        return potions
    # Why: the shield is worn so its slot is free for food, and the 3-fish float is sized for walking between banks, which Crandor has none of.
    food = quest_food.name
    if food:
        _v72 = snap.inv.get(food.lower())
        _v73 = (snap.bank or {}).get(food.lower())
        want = min(ELVARG_FOOD - ((_v72 if _v72 is not None else 0)), (_v73 if _v73 is not None else 0))
        if want > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': food, 'qty': want}]})
    return None


def combat_potions(snap):
    held = snap.inv.get(PRAYER_POTION.lower(), 0)
    banked = (snap.bank or {}).get(PRAYER_POTION.lower(), 0)
    draw = min(2 - held, banked)
    if draw > 0:
        return Record({'kind': 'withdraw', 'items': [{'name': PRAYER_POTION, 'qty': draw}]})
    return None


def combat_gear(snap, bank_allowed=True):
    """Re-equip held gear, then recover banked gear after a death before entering a bankless fight."""
    weapon = best_held(snap)
    banked = best_banked(snap) if bank_allowed else None
    if banked is not None and (weapon is None or MELEE_WEAPONS.index(banked) < MELEE_WEAPONS.index(weapon)):
        return Record({'kind': 'withdraw', 'items': [{'name': banked.name, 'qty': 1, 'id': banked.id}]})
    if weapon is not None:
        if weapon.id not in (snap.worn_ids or set()):
            return Record({'kind': 'equip', 'item': weapon.name})
    for slot in ['torso', 'legs', 'hat']:
        piece = armour_choice(snap, slot)
        if piece is None or piece.id in (snap.worn_ids or set()):
            continue
        if held_id(snap, piece.id) > 0:
            return Record({'kind': 'equip', 'item': piece.name})
        if bank_allowed:
            return Record({'kind': 'withdraw', 'items': [{'name': piece.name, 'qty': 1, 'id': piece.id}]})
    return None


def bought(id, name, qty=1):
    return (Record({
        'id': id,
        'name': name,
        'qty': qty,
        'source': lambda snap, need: SUPPLY_GATHERS.get(name.lower())(snap, need),
    }))


# Why: the door eats all four on the first pass, so they are stocked only while her piece is still to come.
ORACLE_CHARMS = [
    bought(DS_ID.LOBSTER_POT, DS_ITEM.LOBSTER_POT),
    bought(DS_ID.MIND_BOMB, DS_ITEM.MIND_BOMB),
    bought(DS_ID.UNFIRED_BOWL, DS_ITEM.UNFIRED_BOWL),
    bought(DS_ID.SILK, DS_ITEM.SILK),
]


# Why: the engine's own provisioning walks record.items on every session start and after every death, so anything the quest eats is stocked here, bank first, at the leg that eats it.
def stock(snap, wants):
    """The step that brings the pack one item closer to `wants`, or null once it holds them all."""

    short = []
    for want in wants:
        need = want.qty - held_id(snap, want.id)
        if need > 0:
            short.append(Record({'id': want.id, 'name': want.name, 'qty': want.qty, 'source': want.source, 'need': need}))
    if len(short) == 0:
        return None
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    banked = [({'name': w.name, 'qty': min(w.need, banked_id(snap, w.id)), 'id': w.id}) for w in [w for w in short if banked_id(snap, w.id) > 0]]
    if len(banked) > 0:
        return Record({'kind': 'withdraw', 'items': banked})
    return short[0].source(snap, short[0].need)


def hull_errand(snap):
    """The next thing the hull needs that the pack lacks, or null once hammer, nails and planks are all aboard."""
    # Why: a hole takes one plank and four nails together, as lady_lumbridge.rs2 inv_dels both, so what is owed is four nails per plank still to be placed and never the twelve the hull costs.
    # Why: measured against the total, the first patched hole reads as eight missing nails and the bot walks back to the Dwarven Mine with the hull still open.
    # Why: the pack is the ruler and the bank is not, once a plank is carried it is one hole's worth of work, and a spare left in the bank must not inflate the count back to a full hull.
    planks_held = held_id(snap, DS_ID.PLANK)
    planks_wanted = (planks_held if planks_held > 0 else SHIP_REPAIR.planks)

    def _fn78(s, need):
        if skills.effective('smithing') < 34:
            return Record({
            'kind': 'wait',
            'reason': 'Smithing 34 is required to make nails; train Smithing or obtain and bank Nails',
        })
        _v79 = s.inv.get('steel bar')
        if ((_v79 if _v79 is not None else 0)) == 0:
            bars = math.ceil(need / 2)
            _v80 = s.inv.get('iron ore')
            if ((_v80 if _v80 is not None else 0)) < bars and skills.effective('mining') < 15:
                return Record({
                'kind': 'wait',
                'reason': 'Mining 15 is required for iron ore; train Mining or obtain iron ore, steel bars or Nails',
            })
            _v81 = s.inv.get('coal')
            if ((_v81 if _v81 is not None else 0)) < bars * 2 and skills.effective('mining') < 30:
                return Record({
                'kind': 'wait',
                'reason': 'Mining 30 is required for coal; train Mining or obtain coal, steel bars or Nails',
            })
        return custom(f"smith {need} nails for {planks_wanted} plank{('' if planks_wanted == 1 else 's')}" + f' ({held_id(s, DS_ID.NAILS)} carried / {banked_id(s, DS_ID.NAILS)} banked)', lambda log: smith_nails(need, log))
    nails = Record({
        'id': DS_ID.NAILS,
        'name': DS_ITEM.NAILS,
        'qty': planks_wanted * SHIP_REPAIR.nails_per_plank,
        'source': _fn78,
    })
    # Why: at the spawns a part-filled pack is a trip half done rather than a hull half patched, and read the other way it sent the bot back to Port Sarim after every plank.
    planks_to_fetch = (SHIP_REPAIR.planks if in_plank_graveyard(snap.tile) else planks_wanted)
    # Why: smithing belongs to the boat leg rather than the shopping, as it is eighteen slots of ore and wants the pack the map pieces and the Oracle's four charms were using.
    # Why: the hammer comes before it, as the anvil answers nothing without one, and the planks after, as three slots the ore leg would only bank and draw again.
    return stock(snap, [bought(DS_ID.HAMMER, DS_ITEM.HAMMER), nails, bought(DS_ID.PLANK, DS_ITEM.PLANK, planks_to_fetch)])


def decide(snap):
    stage = (snap.progress.stage if snap.progress is not None else None)
    if snap.journal == 'complete' or stage == DRAGON_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if stage is None:
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    bankless = in_maze(snap.tile) or in_oracle_chest_room(snap.tile) or aboard(snap.tile) or on_crandor(snap.tile)
    if not snap.bank_known and not bankless:
        return Record({'kind': 'scan_bank'})
    # Owning provisioning also owns the three-fish travel float, including a restart during ship supplies.
    food = quest_food.name
    if (food and not bankless and stage in [DRAGON_STAGE.BOUGHT_SHIP, DRAGON_STAGE.REPAIRED_SHIP]
            and snap.inv.get(food.lower(), 0) == 0):
        space = snap.free_slots if snap.free_slots is not None else 28
        draw = min(3, (snap.bank or {}).get(food.lower(), 0), space)
        if draw > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': food, 'qty': draw}]})
    if (stage in [DRAGON_STAGE.BOUGHT_SHIP, DRAGON_STAGE.REPAIRED_SHIP] and not bankless
            and held_id(snap, DS_ID.MAP) == 0 and banked_id(snap, DS_ID.MAP) > 0):
        return Record({'kind': 'withdraw', 'items': [{'name': DS_ITEM.MAP, 'qty': 1, 'id': DS_ID.MAP}]})
    if stage == DRAGON_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': GUILDMASTER})
    if stage == DRAGON_STAGE.SPOKEN_GUILDMASTER:
        return custom('talk to Oziach', talk_oziach)
    if stage == DRAGON_STAGE.SPOKEN_OZIACH:
        if in_oracle_chest_room(snap.tile) and held_id(snap, DS_ID.MAP_ORACLE) > 0:
            return custom('leave the oracle chest room', lambda log: open_oracle_magic_door(log, False))
        if aboard(snap.tile):
            return custom('go ashore', leave_ship)
        # The maze is one-way in; nothing else can start until the bot walks back out.
        if in_maze(snap.tile) and anywhere(snap, DS_ID.MAP_MELZAR):
            return custom("walk out of Melzar's Maze", leave_maze)
        # Why: Oziach sets the 3 briefing flags and hands over the maze key across several branches, so this keeps returning until all are set.
        # Why: he won't re-issue the key, so scan and withdraw before calling it nowhere (#379).
        key = where(snap, DS_ID.MAZE_KEY)
        if has_flag(snap.progress, 'needs-briefing'):
            return custom(f'get the briefing from Oziach — {describe_journal()} mazekey={key}', talk_oziach)
        if key == 'banked':
            return Record({
                'kind': 'withdraw',
                'items': [{'name': DS_ITEM.MAZE_KEY, 'qty': 1, 'id': DS_ID.MAZE_KEY}],
            })
        if key == 'nowhere' and not snap.bank_known:
            return Record({'kind': 'scan_bank'})
        if key == 'nowhere':
            return custom(f'get the briefing from Oziach — {describe_journal()} mazekey={key}', talk_oziach)
        # Why: each piece sits behind a one-way trip, so the map comes first and in one pass; errands in between left the maze half-run.
        banked = banked_pieces(snap)
        if len(banked) > 0 and not held_by_id(DS_ID.MAP):
            return Record({'kind': 'withdraw', 'items': banked})
        if not anywhere(snap, DS_ID.MAP):
            if not anywhere(snap, DS_ID.MAP_MELZAR):
                melee = combat_gear(snap, not in_maze(snap.tile))
                if melee:
                    return melee
                if not in_maze(snap.tile):
                    potions = combat_potions(snap)
                    if potions:
                        return potions
                food = quest_food.name
                if food and not in_maze(snap.tile):
                    held = snap.inv.get(food.lower(), 0)
                    banked = (snap.bank or {}).get(food.lower(), 0)
                    space = snap.free_slots if snap.free_slots is not None else 28
                    draw = min(MAZE_FOOD - held, banked, space)
                    if draw > 0:
                        return Record({'kind': 'withdraw', 'items': [{'name': food, 'qty': draw}]})
                return custom("Melzar's Maze", lambda log: maze.step(log))
            if not anywhere(snap, DS_ID.MAP_ORACLE):
                # Why: asking her sets dragon_oracle to 2, which is what prints the rhyme, and going through her door sets it to 3, which stops printing it.
                # Why: the journal flag therefore goes out again the moment the door is used and cannot gate this on its own.
                # Why: holding all four charms is the honest test, as the door eats them, and standing past it is the one place their absence proves nothing.
                if not in_oracle_chest_room(snap.tile):
                    charms = stock(snap, ORACLE_CHARMS)
                    if charms:
                        return charms
                    if not has_flag(snap.progress, 'asked-oracle'):
                        return Record({'kind': 'talk', 'stop': ORACLE})
                return custom('the chest under Ice Mountain', oracle_chest)
            if not anywhere(snap, DS_ID.MAP_WORMBRAIN):
                short = coins_short(snap, WORMBRAIN_PRICE)
                if short:
                    return short
                return custom('buy the map piece from Wormbrain', buy_map_from_wormbrain)
            return custom('join the map pieces', combine_map)
        # Then the shield, on the way past Lumbridge to the docks.
        if not has_flag(snap.progress, 'has-shield') and not anywhere(snap, DS_ID.SHIELD):
            return Record({'kind': 'talk', 'stop': DUKE})
        for_ship = coins_short(snap, SHIP_PRICE)
        if for_ship:
            return for_ship
        return Record({'kind': 'talk', 'stop': KLARENSE})
    if stage == DRAGON_STAGE.BOUGHT_SHIP:
        errand = hull_errand(snap)
        if errand:
            return (custom('go ashore', leave_ship) if aboard(snap.tile) else errand)
        # Why: hiring Ned leaves no journal trace, so the repair, which the journal can confirm, gates it.
        if not has_flag(snap.progress, 'ship-repaired'):
            return custom('patch the Lady Lumbridge', repair_ship)
        return Record({'kind': 'talk', 'stop': NED_HIRE})
    if stage == DRAGON_STAGE.REPAIRED_SHIP:
        # The patch leaves the bot a deck below where it boarded, off the nav graph.
        if aboard(snap.tile):
            return custom('go ashore', leave_ship)
        # Hire and hand-over are two dialogues: the first visit gets his promise, the second takes the map.
        return Record({'kind': 'talk', 'stop': NED_HIRE})
    if stage == DRAGON_STAGE.NED_GIVEN_MAP:
        here = snap.tile
        if here and here.level >= 3:
            return Record({'kind': 'talk', 'stop': NED_ABOARD})
        if not aboard(here):
            gear = gear_up(snap)
            if gear:
                return gear
        return custom('board the Lady Lumbridge', board_for_crandor)
    # Why: off the island at this stage means she killed us; the re-stock includes boat fare since the navigator prunes Pay-fare crossings it can't afford.
    if not on_crandor(snap.tile):
        gear = gear_up(snap)
        if gear:
            return gear
        fare = coins_short(snap, KARAMJA_FARE)
        if fare:
            return fare
    # Without the way back in, a death against Elvarg ends the run.
    if not has_flag(snap.progress, 'secret-passage') and not shortcut_opened:
        return custom('open the secret passage out of Crandor', unlock_shortcut)
    return custom('kill Elvarg', kill_elvarg)


dragonslayer = QuestModule(**{
    'record': ([r for r in QUESTS if r.id == 'dragon'] or [None])[0],
    'pray': Record({'protect': 'melee', 'potions': 2}),
    'bank': 'nearest',
    # A restart in the maze, on the ship or on Crandor cannot service generic provisioning's first bank scan.
    'owns_inventory': True,
    'resume_at': lambda tile: in_maze(tile) or in_oracle_chest_room(tile) or aboard(tile) or on_crandor(tile),
    'grind': ['Giant rat', 'Ghost', 'Skeleton', 'Zombie', 'Melzar the mad', 'Lesser demon', 'Elvarg'],
    'food': 3,
    'tools': ['coins', 'maze key', 'key', 'map part', 'crandor map', 'plank', 'nails', 'hammer', 'dragonfire shield', "wizard's mind bomb", 'unfired bowl', 'lobster pot', 'silk', 'shark', 'lobster', 'swordfish', 'tuna', 'salmon', 'trout'] + list(SUPPLY_TOOLS),
    'sustain': Record({'foods': ['Shark', 'Lobster', 'Swordfish', 'Tuna', 'Salmon', 'Trout'], 'eat_below_hp': 0.65}),
    'coin_float': 0,
    'exit': leave_crandor,
    'read_progress': read_dragon_progress,
    'decide': decide,
})
