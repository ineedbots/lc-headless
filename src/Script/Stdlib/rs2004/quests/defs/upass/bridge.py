"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/bridge.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import CANT_REACH, game_messages
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_LOC, UP_NPC, UP_TILE, upass_area
from rs2004.quests.defs.upass.pass_ import travel_to
from rs2004.quests.defs.upass.supplies import BOW_IDS
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import drive_choice, drive_until, held_id, settle_scene
from rs2004.quests.prayer import prayer_upkeep
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['walk_to', 'drive_through_boxes', 'fight_until_gone', 'await_drop', 'take_drop', 'loc_by_id', 'cross_to_west', 'cross_to_east', 'start_quest', 'meet_koftik', 'enter_cave', 'leave_with_koftik', 'leave_pass', 'report_to_lathas', 'get_damp_cloth', 'make_fire_arrow', 'arm_fire_arrow', 'shoot_guiderope']

KOFTIK = 'Koftik'
FIGHT_MS = 180000
RENEW_MS = 6000
DROP_TICKS = 6
TAKE_TRIES = 4
TAKE_MS = 4000


# Why: inside the pass every destination past an obstacle is "unreachable" to the navigator, so the shared mover is the pocket-crossing one; above ground it degrades to a plain resilient walk on its first round.
def walk_to(to, radius, log):
    here = game.tile()
    if here and here.level == to.level and to.distance_to(here) <= radius:
        return True
    _result1 = yield from travel_to(to, radius, log)
    return _result1


# Why: `driveUntil` handles chat only; Kardia's chest and Koftik's greeting use main-modal boxes.
def drive_through_boxes(expect, prefer, log, ms=30000):
    """`driveUntil` that also clicks through the main-modal boxes a script puts in the way."""
    deadline = _core.step_time() + ms
    while _core.step_time() < deadline:
        if expect():
            return True
        yield from modals.close_if_open()
        yield from drive_until(expect, prefer, log, 1500)
    return expect()


# Why: one Attack and a wait lost whole fights live: a second paladin engaging lapses the attack, the retaliation kills the other one, and the target stands there for the full wait. So the attack is renewed, and it eats and prays as it goes, since sustain is call-driven. This departs from rs2b0t.
def fight_until_gone(find, log):
    """Attacks what find() gives until it gives None, or the fight has run too long."""
    deadline = _core.step_time() + FIGHT_MS
    renew_at = 0
    while _core.step_time() < deadline:
        target = find()
        if target is None:
            return True
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drive_choice([], log)
        yield from sustain.run()
        yield from prayer_upkeep()
        if _core.step_time() >= renew_at:
            if not target.interact('Attack'):
                return False
            renew_at = _core.step_time() + RENEW_MS
        yield from execution.delay_ticks(1)
    return find() is None


def _item_is(id):
    return lambda item: item.id == id


# Why: `ai_queue3` runs `gosub(npc_death)` and then `obj_add`, so the NPC can leave the scene a moment before its drop lands, and one look missed a crest live. This departs from rs2b0t.
def await_drop(id):
    """The drop with this id near you, given a few ticks to land, or None."""
    for tick in range(DROP_TICKS):
        drop = ground_items.query().where(_item_is(id)).within(10).nearest()
        if drop:
            return drop
        yield from execution.delay_ticks(1)
    return None


# Why: a second paladin's hit can cancel the walk to the pile, which on every live run lost a crest and with it a full attempt at the step. This departs from rs2b0t.
def take_drop(id, log):
    """Waits for a drop to land and picks it up, trying again while it's still on the floor. False when it never came to the pack."""
    for attempt in range(TAKE_TRIES):
        drop = yield from await_drop(id)
        if not drop:
            return held_id(id) > 0
        if drop.interact('Take'):
            taken = yield from drive_until(lambda: held_id(id) > 0, [], log, TAKE_MS)
            if taken:
                return True
    return held_id(id) > 0


def loc_by_id(id, op, within=12):
    base = locs.query().where(lambda loc: loc.id == id)
    return ((base if op is None else base.action(op))).within(within).nearest()


def talk_at(npc_id, near, prefer, log):
    _w2 = yield from walk_to(near, 2, log)
    if not (_w2):
        return False
    yield from settle_scene()
    # Why: 5 NPCs all render as "Koftik", so find the guide by id, then talk by name.
    guide = npcs.query().where(lambda npc: npc.id == npc_id).within(12).nearest()
    if not guide:
        log(f'no npc {npc_id} near ({near.x},{near.z})')
        return False
    _w3 = yield from reach.npc_dialog((guide.name if guide.name is not None else KOFTIK), near, log=log)
    if (_w3) != 'done':
        log(f'no dialogue with npc {npc_id} near ({near.x},{near.z})')
        return False
    _result4 = yield from talk_strict((guide.name if guide.name is not None else KOFTIK), prefer, log)
    return _result4


# Why: neither Plague City's nor Biohazard's crossing survives here: the garden dig is refused once Biohazard starts ("the ground's been filled in and packed hard") and Omart won't re-hang the rope ladder after it. `west_ardougne_open_city_doors` opens the city gates outright at `%biohazard = complete`.
# Why: the navigator has no edge through them, so the crossing is walked and opened by hand.
def open_wall_gate(from_, to, log):
    _w5 = yield from walk_to(from_, 1, log)
    if not (_w5):
        return False
    yield from settle_scene()
    _v6 = loc_by_id(UP_LOC.WALL_DOOR_L, 'Open', 8)
    gate = (_v6 if _v6 is not None else loc_by_id(UP_LOC.WALL_DOOR_R, 'Open', 8))
    if not gate:
        log(f'no Ardougne wall gate within reach of ({from_.x},{from_.z})')
        return False
    if not (gate.interact('Open')):
        return False

    def _fn7():
        now = game.tile()
        return now is not None and abs(now.x - to.x) <= 3 and abs(now.z - to.z) <= 4
    _w8 = yield from drive_until(_fn7, [], log, 12000)
    if not (_w8):
        return False
    # Why: the gate leaves you in the gateway, which the region test counts as neither side, so a step that stopped here would be asked to cross again through a shut gate. The last 3 tiles onto the far stand are a plain walk.
    yield from traversal.walk_resilient(to, radius=1, attempts=2, timeout_ms=20000, log=log)
    return upass_area(game.tile()) == upass_area(to)


# Why: the gate teleport lands 1 tile short of the stand on either side, so "am I across yet" is the region test the rest of the module uses.
def cross_to_west(log):
    """Through the Ardougne wall gates into West Ardougne."""
    if upass_area(game.tile()) == 'westardougne':
        return True
    _result9 = yield from open_wall_gate(UP_TILE.WALL_GATE_EAST, UP_TILE.WALL_GATE_WEST, log)
    return _result9


def cross_to_east(log):
    """Back out through the same gates."""
    if upass_area(game.tile()) == 'mainland':
        return True
    _result10 = yield from open_wall_gate(UP_TILE.WALL_GATE_WEST, UP_TILE.WALL_GATE_EAST, log)
    return _result10


def start_quest(log):
    """King Lathas starts the quest; his branch needs Biohazard complete and base Ranged 25."""
    _w11 = yield from walk_to(UP_TILE.LATHAS, 2, log)
    if not (_w11):
        return False
    yield from settle_scene()
    _result12 = yield from talk_strict('King Lathas', [], log)
    return _result12


def meet_koftik(log):
    """Koftik at the cave mouth, the "I'll take my chances" branch moves the stage without the lore detour."""
    return talk_at(UP_NPC.KOFTIK_SURFACE, UP_TILE.CAVE_MOUTH, ["I'll take my chances"], log)


def enter_cave(log):
    _v13 = (game.tile().z if game.tile() is not None else None)
    if ((_v13 if _v13 is not None else 0)) > 9000:
        return True
    # Why: the cave mouth is a 4x2 loc whose origin tile sits inside the footprint and can't be walked to, so Koftik's tile is the stand and the op-click closes the gap.
    _w14 = yield from walk_to(UP_TILE.CAVE_MOUTH, 3, log)
    if not (_w14):
        return False
    yield from settle_scene()
    mouth = loc_by_id(UP_LOC.CAVE_ENTRANCE, 'Enter', 16)
    if not mouth:
        log('no cave entrance at the far west of West Ardougne')
        return False
    if not (mouth.interact('Enter')):
        return False
    _result15 = yield from drive_until(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 0)) > 9000, [], log, 20000)
    return _result15


# Why: Koftik leads the way out: `koftik_whereami` teleports you from the second cavern up to the landing chamber, and the cave exit there is the only loc that leaves the pass.
def leave_with_koftik(log):
    """Koftik, sane again once Iban is dead, leads the way up to the landing chamber."""
    return talk_at(UP_NPC.KOFTIK_LAST, UP_TILE.LAST_OUT, [], log)


def leave_pass(log):
    """Out through the cave exit at the top of the landing chamber."""
    _w16 = yield from walk_to(UP_TILE.CAVE_EXIT, 3, log)
    if not (_w16):
        return False
    yield from settle_scene()
    exit = loc_by_id(UP_LOC.CAVE_EXIT, None, 12)
    op = ((exit.actions() if exit is not None else None) or [None])[0]
    if not exit or not op:
        log('no cave exit in the landing chamber')
        return False
    if not (exit.interact(op)):
        return False
    _result17 = yield from drive_until(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < 9000, [], log, 20000)
    return _result17


def report_to_lathas(log):
    """King Lathas takes the report; his `upass_defeated_iban` branch closes the quest with no choices."""
    _w18 = yield from walk_to(UP_TILE.LATHAS, 2, log)
    if not (_w18):
        return False
    yield from settle_scene()
    _result19 = yield from talk_strict('King Lathas', [], log)
    return _result19


def get_damp_cloth(log):
    """Koftik by the bridge hands over the damp cloth."""
    return talk_at(UP_NPC.KOFTIK_BRIDGE, UP_TILE.KOFTIK_BRIDGE, ['Not to worry'], log)


def make_fire_arrow(log):
    """Damp cloth on a bronze arrow, then the tinderbox on the result."""
    if held_id(UP_ITEM.LIT_ARROW.id) > 0:
        return True
    if held_id(UP_ITEM.UNLIT_ARROW.id) == 0:
        cloth = ([item for item in inventory.items() if item.id == UP_ITEM.DAMP_CLOTH.id] or [None])[0]
        arrow = ([item for item in inventory.items() if item.id == UP_ITEM.BRONZE_ARROW.id] or [None])[0]
        if not cloth or not arrow:
            log(f"missing {('a bronze arrow' if cloth else 'the damp cloth')} for the fire arrow")
            return False
        if not (cloth.use_on(arrow)):
            return False
        _w20 = yield from drive_until(lambda: held_id(UP_ITEM.UNLIT_ARROW.id) > 0, [], log, 10000)
        if not (_w20):
            log('the damp cloth would not wrap an arrow')
            return False
    unlit = ([item for item in inventory.items() if item.id == UP_ITEM.UNLIT_ARROW.id] or [None])[0]
    tinderbox = ([item for item in inventory.items() if item.id == UP_ITEM.TINDERBOX.id] or [None])[0]
    if not unlit or not tinderbox:
        log(f"missing {('the tinderbox' if unlit else 'the unlit arrow')} to light the fire arrow")
        return False
    # Why: `[opheldu,tinderbox]` fires off the target, so the arrow is the item used and the tinderbox is the target.
    if not (unlit.use_on(tinderbox)):
        return False
    _result21 = yield from drive_until(lambda: held_id(UP_ITEM.LIT_ARROW.id) > 0, [], log, 10000)
    return _result21


def arm_fire_arrow(log, bows=None):
    """Bow in hand, lit arrow in the quiver, the rope shot reads both off `worn`."""
    if bows is None:
        bows = BOW_IDS
    bow = ([item for item in inventory.items() if (item.id in bows)] or [None])[0]
    if bow and not (bow.interact('Wield')):
        log(f"could not wield the {(bow.name if bow.name is not None else 'bow')}")
        return False
    if held_id(UP_ITEM.LIT_ARROW.id) > 0:
        lit = ([item for item in inventory.items() if item.id == UP_ITEM.LIT_ARROW.id] or [None])[0]
        if not lit or not (lit.interact('Wield')):
            log('could not equip the lit arrow')
            return False
        yield from execution.delay_ticks(2)
    return True


# Why: `inv_del(worn, $worn_ammo, 1)` runs before the `stat_random(ranged, 160, 300)` roll and one damp cloth makes one arrow, so a loop fires every later shot from an empty quiver. Koftik hands over another cloth when the pack has none, so the retry is decide() rebuilding the arrow and this step fires once.
# Why: the trigger is `aploc1`, which only runs within 10 tiles and with line of sight (`inApproachDistance`). A stand that fails either produces no script at all, which reads like a miss unless the chat is read, and the map data can't answer line of sight, so the stands are probed until one draws a reply.
SHOT_STANDS = [Tile(2448, 9721, 0), Tile(2447, 9720, 0), Tile(2450, 9720, 0), Tile(2446, 9722, 0), Tile(2452, 9721, 0)]


def shoot_guiderope(log):
    """Fire the lit arrow at the bridge stay rope; the script walks the player across on a hit."""
    for stand in SHOT_STANDS:
        # Why: these 5 stands are a few tiles apart in one pocket, so an unwalkable stand is the next stand's turn. `walkTo` reaches for the pocket traveller, and one bad stand sent it sweeping the cavern end to end.
        _w22 = yield from traversal.walk_resilient(stand, radius=0, attempts=1, timeout_ms=20000)
        if not (_w22):
            continue
        yield from settle_scene()
        rope = loc_by_id(UP_LOC.GUIDEROPE, None, 12)
        if not rope:
            log('no bridge guide rope in range of the shooting stand')
            return False
        mark = game_messages.mark()
        if not (rope.interact('Fire-at')):
            log(f"the guide rope refused Fire-at (ops: {' | '.join(rope.actions())})")
            return False
        crossed = yield from drive_until(lambda: (((game.tile().x if game.tile() is not None else None) if (game.tile().x if game.tile() is not None else None) is not None else 9999)) < 2445, [], log, 12000)
        if crossed:
            log(f'the arrow impaled the rope from ({stand.x},{stand.z})')
            return True
        replies = [m.text for m in game_messages.since(mark)]
        said = ' | '.join(replies)
        # Why: "I can't reach that!" is the server's path search dead-ending, so the script never ran and no arrow was spent; this stand is wrong.
        if len(said) == 0 or any([CANT_REACH in text.lower() for text in replies]):
            log(f'({stand.x},{stand.z}) cannot reach the rope — trying the next stand')
            continue
        log(f'the shot did not carry from ({stand.x},{stand.z}) — server said: {said}')
        return False
    log('no shooting stand drew a reply from the guide rope')
    return False

