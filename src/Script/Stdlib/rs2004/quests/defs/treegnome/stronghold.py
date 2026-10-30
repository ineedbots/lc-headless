"""Ported from rs2b0t's src/bot/api/ai/quests/defs/treegnome/stronghold.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.quests.defs.treegnome.areas import TG_ITEM, TG_LOC, TG_TILE, in_chest_floor, in_khazard_hall, in_ladder_room, in_stronghold
from rs2004.quests.defs.treegnome.combat import clear_commander
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.quests.journal_text import normalize_journal
from rs2004.traversal import traversal

__all__ = ['coordinate_choice', 'fire_ballista', 'take_the_orb', 'leave_stronghold']

CHEST_FLOOR_LADDER = Tile(2503, 3253, 1)


def loc_by_id(id, within=6):
    return locs.query().where(lambda l: l.id == id).within(within).nearest()


# Why: Tracker dialogue is not recorded, so these three responses and the ballista check define the leg.
COORDINATE = [['height-coordinate', '0004'], ['x-coordinate', '0003'], ['y-coordinate', '0005']]


def coordinate_choice(texts, options):
    said = normalize_journal(texts)
    hit = ([header for header in COORDINATE if header[0] in said] or [None])[0]
    if not hit:
        return None
    return ([option for option in options if hit[1] in option] or [None])[0]


QUIET_TICKS = 8
FIRE_TICKS = 200


def answer_coordinates(log):
    answered = 0
    quiet = 0
    for i in range(FIRE_TICKS):
        options = chat_dialog.options()
        if len(options) > 0:
            pick = coordinate_choice(chat_dialog.texts(), options)
            if not pick:
                log(f"ballista: no coordinate header above [{' | '.join(options)}]")
                return False
            yield from chat_dialog.choose_option(pick)
            answered += 1
            quiet = 0
            yield from execution.delay_ticks(2)
            continue
        if chat_dialog.can_continue():
            quiet = 0
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        quiet += 1
        if answered >= len(COORDINATE) and quiet >= QUIET_TICKS:
            return True
        yield from execution.delay_ticks(1)
    return answered >= len(COORDINATE)


def fire_ballista(log):
    _w3 = yield from traversal.walk_resilient(TG_TILE.BALLISTA_STAND, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w3):
        return False
    yield from settle_scene()
    ballista = loc_by_id(TG_LOC.BALLISTA, 8)
    if not ballista:
        log(f'no Ballista at ({TG_TILE.BALLISTA_STAND.x},{TG_TILE.BALLISTA_STAND.z})')
        return False
    if not (ballista.interact('Fire')):
        return False
    log('ballista: firing at height 4, x 3, y 5')
    _result4 = yield from answer_coordinates(log)
    return _result4


def climb_crumbled_wall(log):
    _w6 = yield from traversal.walk_resilient(TG_TILE.WALL_STAND, radius=1, attempts=3, timeout_ms=180000, log=log)
    if not (_w6):
        return False
    yield from settle_scene()
    wall = loc_by_id(TG_LOC.CRUMBLED_WALL, 4)
    if not wall:
        log(f'no Crumbled wall at ({TG_TILE.WALL_STAND.x},{TG_TILE.WALL_STAND.z + 1})')
        return False
    if not (wall.interact('Climb-over')):
        return False
    # Why: the op raises "The wall has been reduced to rubble." and pauses on its continue, so a wait that only watches the tile holds the tick the button needs.
    landed = yield from drive_until(lambda: in_stronghold(game.tile()), [], log, 45000)
    if not landed:
        here = game.tile()
        log(f'the crumbled wall did not let us over from ({(here.x if here is not None else None)},{(here.z if here is not None else None)}) — is the ballista shot in?')
        return False
    yield from settle_scene()
    _result7 = yield from clear_commander(log)
    return _result7


# Why: the diagonal door is not a baked edge, so the last tile is a scene step the pathfinder never sees.
def cross_inner_door(log):
    _w9 = yield from traversal.walk_resilient(TG_TILE.INNER_DOOR_STAND, radius=0, attempts=3, timeout_ms=180000, log=log)
    if not (_w9):
        return False
    door = loc_by_id(TG_LOC.INNER_DOOR, 4)
    if door and not (door.interact('Open')):
        return False
    yield from execution.delay_ticks(2)
    yield from direct_navigator.walk_to(TG_TILE.LADDER_STAND, 0, 15000)
    if not in_ladder_room(game.tile()):
        log('the stronghold inner door did not let us through')
        return False
    yield from settle_scene()
    return True


def climb_ladder(stand, id, op, arrived, log):
    _w11 = yield from traversal.walk_resilient(stand, radius=1, attempts=3, timeout_ms=180000, log=log)
    if not (_w11):
        return False
    ladder = loc_by_id(id, 4)
    if not ladder:
        log(f'no Ladder offering {op} at ({stand.x},{stand.z})')
        return False
    if not (ladder.interact(op)):
        return False
    _w12 = yield from drive_until(arrived, [], log, 12000)
    if not (_w12):
        return False
    yield from settle_scene()
    return True


def reach_chest_floor(log):
    if in_chest_floor(game.tile()):
        return True
    _c13 = not in_ladder_room(game.tile()) and not in_khazard_hall(game.tile())
    if _c13:
        _w14 = yield from climb_crumbled_wall(log)
        _c13 = not (_w14)
    if _c13:
        return False
    _c15 = in_khazard_hall(game.tile())
    if _c15:
        _w16 = yield from cross_inner_door(log)
        _c15 = not (_w16)
    if _c15:
        return False
    _result17 = yield from climb_ladder(TG_TILE.LADDER_STAND, TG_LOC.LADDER_UP, 'Climb-up', lambda: in_chest_floor(game.tile()), log)
    return _result17


def take_the_orb(log):
    """Breach to orb: the leg reports the orb, and the next pass walks it out."""
    if held_id(TG_ITEM.ORB.id) > 0:
        return True
    _w19 = yield from reach_chest_floor(log)
    _c18 = not (_w19)
    if not _c18:
        _w20 = yield from clear_commander(log)
        _c18 = not (_w20)
    if _c18:
        return False
    _w22 = yield from traversal.walk_resilient(TG_TILE.CHEST_STAND, radius=0, attempts=3, timeout_ms=180000, log=log)
    if not (_w22):
        return False
    yield from settle_scene()
    chest = loc_by_id(TG_LOC.CHEST_OPEN, 4)
    if not chest:
        shut = loc_by_id(TG_LOC.CHEST_SHUT, 4)
        if not shut:
            log(f'no chest at ({TG_TILE.CHEST_STAND.x},{TG_TILE.CHEST_STAND.z + 1},1)')
            return False
        if not (shut.interact('Open')):
            return False
        # Why: a loc that transforms keeps its old id for a tick, so the open chest has to be polled for.
        yield from execution.delay_until(lambda: loc_by_id(TG_LOC.CHEST_OPEN, 4) is not None, 6000)
        chest = loc_by_id(TG_LOC.CHEST_OPEN, 4)
        if not chest:
            log('the Khazard chest never opened')
            return False
    if not (chest.interact('Search')):
        return False
    _result23 = yield from drive_until(lambda: held_id(TG_ITEM.ORB.id) > 0, [], log, 12000)
    return _result23


def leave_stronghold(log):
    """The front door opens from the inside only, and it is the one way out."""
    if not in_stronghold(game.tile()):
        return True
    _c24 = in_chest_floor(game.tile())
    if _c24:
        _w25 = yield from climb_ladder(CHEST_FLOOR_LADDER, TG_LOC.LADDER_DOWN, 'Climb-down', lambda: in_ladder_room(game.tile()), log)
        _c24 = not (_w25)
    if _c24:
        return False
    _c26 = in_khazard_hall(game.tile())
    if _c26:
        _w27 = yield from cross_inner_door(log)
        _c26 = not (_w27)
    if _c26:
        return False
    _w29 = yield from traversal.walk_resilient(TG_TILE.FRONT_DOOR_STAND, radius=0, attempts=3, timeout_ms=180000, log=log)
    if not (_w29):
        return False
    door = loc_by_id(TG_LOC.FRONT_DOOR, 4)
    if not door:
        log(f'no stronghold door at ({TG_TILE.OUTSIDE_FRONT_DOOR.x},{TG_TILE.OUTSIDE_FRONT_DOOR.z})')
        return False
    if not (door.interact('Open')):
        return False
    _result30 = yield from drive_until(lambda: not in_stronghold(game.tile()), [], log, 10000)
    return _result30
