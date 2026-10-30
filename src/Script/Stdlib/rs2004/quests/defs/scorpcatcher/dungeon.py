"""Ported from rs2b0t's src/bot/api/ai/quests/defs/scorpcatcher/dungeon.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import direct_navigator, game
from rs2004.items import inventory
from rs2004.quests.defs.scorpcatcher.areas import JAILER_NPC, SC_ID, SC_TILE, VELRAK
from rs2004.quests.exec.primitives import drive_dialog
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.reach import talk_op
from rs2004.tabs import PROTECT_FROM_MAGIC, prayer
from rs2004.traversal import traversal

__all__ = ['locked_in', 'leave_cell', 'enter_deep_dungeon', 'leave_deep_dungeon', 'cross_secret_wall']

WALK_MS = 300000
KILL_MS = 90000
DOOR_MS = 8000


def loc_by_id(id, within=6):
    return locs.query().where(lambda l: l.id == id).within(within).nearest()


def here():
    return game.tile()


def walk_to(dest, radius, log):
    at = here()
    if at and at.level == dest.level and dest.distance_to(at) <= radius:
        return True
    _result1 = yield from traversal.walk_resilient(dest, radius=radius, attempts=3, timeout_ms=WALK_MS, log=log)
    return _result1


# Why: the jail key lies on the floor for 100 ticks and nothing else in the corridor drops one, so a slow pickup means killing the Jailer again.
def take_jail_key(log):
    drop = ground_items.query().where(lambda g: g.id == SC_ID.JAIL_KEY).within(12).nearest()
    if not drop:
        return False
    _c2 = drop.distance() > 1
    if _c2:
        _w3 = yield from traversal.walk_resilient(drop.tile(), radius=1, attempts=2, timeout_ms=30000, log=log)
        _c2 = not (_w3)
    if _c2:
        return False
    again = ground_items.query().where(lambda g: g.id == SC_ID.JAIL_KEY).within(12).nearest()
    if not again or not (again.interact('Take')):
        return False
    _result4 = yield from execution.delay_until(lambda: held_id(SC_ID.JAIL_KEY) > 0, DOOR_MS)
    return _result4


def kill_jailer(log):
    jailer = npcs.query().name(JAILER_NPC).action('Attack').within(14).nearest()
    if not jailer:
        log(f'scorpcatcher: no {JAILER_NPC} in the prison corridor at ({SC_TILE.JAIL_DOOR.x},{SC_TILE.JAIL_DOOR.z})')
        return False
    index = jailer.index

    def live():
        return ([npc for npc in npcs.all() if npc.index == index and npc.name == JAILER_NPC] or [None])[0]

    if not (jailer.interact('Attack')):
        return False
    log(f'scorpcatcher: fighting the {JAILER_NPC} for the jail key')
    deadline = _core.step_time() + KILL_MS
    while _core.step_time() < deadline:
        yield from sustain.run()
        if held_id(SC_ID.JAIL_KEY) > 0:
            return True
        if not live():
            _result5 = yield from take_jail_key(log)
            return _result5
        yield from execution.delay_ticks(1)
    log(f'scorpcatcher: the {JAILER_NPC} outlived {KILL_MS // 1000}s of combat')
    return False


# Why: `unlock_taverley_jaildoor` takes the key on the way in only; the way out is the plain Open op.
def unlock_with_key(key_id, loc_id, expect, what, log):
    if expect():
        return True
    yield from settle_scene()
    door = loc_by_id(loc_id, 5)
    key = ([item for item in inventory.items() if item.id == key_id] or [None])[0]
    if not door or not key:
        log(f'scorpcatcher: no {what} in reach or no key {key_id} to unlock it with')
        return False
    if not (key.use_on(door)):
        return False
    _result6 = yield from drive_until(expect, [], log, DOOR_MS)
    return _result6


def open_loc(loc_id, op, expect, what, log):
    if expect():
        return True
    yield from settle_scene()
    loc = loc_by_id(loc_id, 5)
    if not loc or not (loc.interact(op)):
        log(f'scorpcatcher: no {what} to {op.lower()} here')
        return False
    _result7 = yield from drive_until(expect, [], log, DOOR_MS)
    return _result7


def cell_holds(at):
    return at is not None and at.level == 0 and at.z <= SC_TILE.JAIL_CELL.z and at.x >= 2928 and at.x <= 2934 and at.z >= 9683


def in_cell():
    return cell_holds(here())


# Why: Velrak has no `wanderrange` and drifts 5 tiles around a walled cell, and the shared talk primitive answers an out-of-reach NPC by opening the cell door and walking back out.
def talk_in_cell(log):
    """Talk to Velrak without leaving the cell: scene steps only, no door opened."""
    yield from settle_scene()

    def find():
        return npcs.query().name(VELRAK.npc).where(lambda npc: talk_op(npc.actions()) is not None).nearest()

    velrak = find()
    if not velrak:
        log(f'scorpcatcher: no {VELRAK.npc} in the cell')
        return False
    if velrak.distance() > 1:
        yield from direct_navigator.walk_to(velrak.tile(), 1, 20000)
        velrak = find()
    op = velrak and talk_op(velrak.actions())
    if not velrak or not op or not (velrak.interact(op)):
        log(f'scorpcatcher: {VELRAK.npc} refused the talk')
        return False
    _w8 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), DOOR_MS)
    if not (_w8):
        log(f'scorpcatcher: {VELRAK.npc} never opened a dialogue')
        return False
    _result9 = yield from drive_dialog(VELRAK.prefer, log)
    return _result9


def fetch_dusty_key(log):
    """Velrak's cell: kill the Jailer for his key, unlock the door, and take the dusty key off him."""
    if held_id(SC_ID.DUSTY_KEY) > 0:
        return True
    if not in_cell():
        _w10 = yield from walk_to(SC_TILE.JAIL_DOOR, 1, log)
        if not (_w10):
            return False
        _c11 = held_id(SC_ID.JAIL_KEY) == 0
        if _c11:
            _w12 = yield from kill_jailer(log)
            _c11 = not (_w12)
        if _c11:
            return False
        _w13 = yield from walk_to(SC_TILE.JAIL_DOOR, 0, log)
        if not (_w13):
            return False
        log("scorpcatcher: unlocking Velrak's cell")
        _w14 = yield from unlock_with_key(SC_ID.JAIL_KEY, SC_ID.JAIL_DOOR, in_cell, 'cell door', log)
        if not (_w14):
            return False
        yield from settle_scene()
    _w15 = yield from talk_in_cell(log)
    if not (_w15):
        return False
    got = yield from execution.delay_until(lambda: held_id(SC_ID.DUSTY_KEY) > 0, DOOR_MS)
    if not got:
        log('scorpcatcher: Velrak handed over no dusty key')
        return False
    _result16 = yield from leave_cell(log)
    return _result16


# Why: the cell is a dead end, so the leg has to be back in the corridor before anything else routes from here.
# Why: Velrak wanders the cell and the talk follows him, which left the door 6 tiles off live, past open_loc's reach.
def leave_cell(log):
    """Step to the tile inside the cell door and open it, by scene steps, since nothing routes out of the cell."""
    if not in_cell():
        return True
    yield from direct_navigator.walk_to(SC_TILE.JAIL_CELL, 0, 10000)
    _result = yield from open_loc(SC_ID.JAIL_DOOR, 'Open', lambda: not in_cell(), 'cell door', log)
    return _result


# Why: the entrance corridor from the Taverley ladder runs x 2881-2887 in the same z band as the deep half with only rock at x 2888 between, so a plain "west of the gate" box would count the way in.
def deep_dungeon_holds(at):
    """West of the dusty-key gate: the far half at x <= 2880, and the blue dragon cave east of it."""
    if at is None or at.level != 0 or at.z < 9700:
        return False
    return at.x <= 2880 or (at.x >= 2890 and at.x <= SC_TILE.DEEP_DUNGEON.x and at.z <= 9815)


def in_deep_dungeon():
    return deep_dungeon_holds(here())


# Why: Velrak's cell and the half behind the dusty-key gate have no booth, and a restart inside either spent minutes
# routing to the bank before the quest could leave; the engine defers banking inside these.
def locked_in(tile):
    """Whether the tile is in a pocket only the quest's own legs leave."""
    return cell_holds(tile) or deep_dungeon_holds(tile)


# Why: blue dragons hit 30 through the corridor between the gate and the coffins and 50 when they roll through the defence check, which Protect from Magic caps at 10.
# Why: nothing behind the coffin wall breathes and the catch in there runs for minutes, so the prayer comes down at the wall.
def dragon_guard(on, log):
    if prayer.active(PROTECT_FROM_MAGIC) == on:
        return
    _w17 = yield from prayer.set(PROTECT_FROM_MAGIC, on)
    if _w17:
        log(f"scorpcatcher: Protect from Magic {('on for the dragon corridor' if on else 'off past the coffin wall')}")


def enter_deep_dungeon(log):
    """Through the dusty-key gate into the blue dragon half of Taverley Dungeon."""
    if in_deep_dungeon():
        yield from dragon_guard(not in_secret_room(), log)
        return True
    _w18 = yield from fetch_dusty_key(log)
    if not (_w18):
        return False
    _w19 = yield from walk_to(SC_TILE.DEEP_GATE, 0, log)
    if not (_w19):
        return False
    yield from dragon_guard(True, log)
    log('scorpcatcher: unlocking the deep dungeon gate')
    _result20 = yield from unlock_with_key(SC_ID.DUSTY_KEY, SC_ID.DEEP_GATE, in_deep_dungeon, 'deep dungeon gate', log)
    return _result20


# Why: the walker would path back out through this gate on its own, but one refused Open blacklists it for the session, and the way out is then gone.
def leave_deep_dungeon(log):
    """Back through the gate, so the next leg starts on a route the walker owns."""
    if not in_deep_dungeon():
        return True
    _w21 = yield from walk_to(SC_TILE.DEEP_DUNGEON, 0, log)
    if not (_w21):
        return False
    out = yield from open_loc(SC_ID.DEEP_GATE, 'Open', lambda: not in_deep_dungeon(), 'deep dungeon gate', log)
    if out:
        yield from dragon_guard(False, log)
    return out


def in_secret_room():
    at = here()
    return at is not None and at.level == 0 and at.x >= 2874 and at.x <= 2880 and at.z >= 9793 and at.z <= 9798


# Why: the wall teleports and `check_axis` reads which side we're on, so the same Search works both ways.
def cross_secret_wall(inward, log):
    """Search the old wall by the 2 coffins, in or out of the secret room."""
    if in_secret_room() == inward:
        yield from dragon_guard(not inward, log)
        return True
    stand = (SC_TILE.SECRET_WALL if inward else SC_TILE.SECRET_ROOM)
    _w22 = yield from walk_to(stand, 0, log)
    if not (_w22):
        return False
    # Why: the wall teleports, so the corridor arrives in 1 tick and the prayer has to be up before the Search.
    if not inward:
        yield from dragon_guard(True, log)
    log(f"scorpcatcher: searching the old wall to get {('into' if inward else 'out of')} the secret room")
    _w23 = yield from open_loc(SC_ID.SECRET_WALL, 'Search', lambda: in_secret_room() == inward, 'old wall', log)
    if not (_w23):
        return False
    yield from settle_scene()
    if inward:
        yield from dragon_guard(False, log)
    return True
