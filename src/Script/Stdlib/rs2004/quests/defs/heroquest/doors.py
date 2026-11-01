"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/doors.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.messages import game_messages
from rs2004.quests.defs.heroquest.areas import HERO_ID, HERO_LOC, HERO_SAY, HERO_TILE, in_brimhaven_hq, in_garden, in_kitchen, in_mansion, in_side_room, in_treasure_room, in_yard
from rs2004.quests.exec.prompts import cross_teleport_door, settle_scene, use_on_loc

__all__ = ['enter_brimhaven_hq', 'leave_brimhaven_hq', 'enter_mansion', 'leave_mansion', 'enter_kitchen', 'leave_kitchen', 'push_panel', 'push_panel_back', 'return_to_street', 'cross_side_door_in', 'cross_side_door_out', 'cross_treasure_door_in', 'cross_treasure_door_out']

# Why: every door here is script-gated and absent from the baked graph, so the module owns both directions of each one; a crossing the navigator lacks seals whatever it guards.
def log2(log, mark, what):
    for line in game_messages.since(mark):
        log(f'{what}: {line.text}')


def enter_brimhaven_hq(log):
    """Grubor's door: the first Open raises his challenge, and only the answer unbars it. The second Open crosses."""
    if in_brimhaven_hq(game.tile()):
        return True
    # Why: every pocket in this quest is sealed in the baked graph, so from another one there's no route to this door and the walk reads `unreachable`.
    _w1 = yield from return_to_street(log)
    if not (_w1):
        return False
    mark = game_messages.mark()
    for attempt in range(2):
        if not (not in_brimhaven_hq(game.tile())):
            break
        yield from cross_teleport_door(Record({
            'id': HERO_LOC.GRUBOR_DOOR,
            'stand': HERO_TILE.GRUBOR_DOOR,
            'is_far': lambda: in_brimhaven_hq(game.tile()),
            'prefer': [HERO_SAY.BLACK_ARM_PASSWORD],
            'log': log,
        }))
        yield from settle_scene()
    if in_brimhaven_hq(game.tile()):
        return True
    log2(log, mark, 'grubor door')
    return False


def leave_brimhaven_hq(log):
    if not in_brimhaven_hq(game.tile()):
        return True
    _result2 = yield from cross_teleport_door(Record({
        'id': HERO_LOC.GRUBOR_DOOR,
        'stand': HERO_TILE.GRUBOR_DOOR_INNER,
        'is_far': lambda: not in_brimhaven_hq(game.tile()),
        'log': log,
    }))
    return _result2


def enter_mansion(log):
    """Garv's door: the first Open is his challenge, which only passes with the papers in the pack and the black armour worn, and it unlocks the door without swinging it. The second Open crosses."""
    if in_mansion(game.tile()):
        return True
    if in_treasure_room(game.tile()):
        _result3 = yield from cross_treasure_door_out(log)
        return _result3
    # Why: Garv's door is out of the baked graph, so from the hideout or the kitchen there's no route to it and the pocket has to be left before the walk can be planned.
    _w4 = yield from return_to_street(log)
    if not (_w4):
        return False
    mark = game_messages.mark()
    for attempt in range(2):
        if not (not in_mansion(game.tile())):
            break
        yield from cross_teleport_door(Record({
            'id': HERO_LOC.GARV_DOOR,
            'stand': HERO_TILE.GARV_DOOR,
            'is_far': lambda: in_mansion(game.tile()),
            'prefer': [],
            'log': log,
        }))
        yield from settle_scene()
    if in_mansion(game.tile()):
        return True
    log2(log, mark, 'garv door')
    return False


def leave_mansion(log):
    if not in_mansion(game.tile()):
        return True
    _result5 = yield from cross_teleport_door(Record({
        'id': HERO_LOC.GARV_DOOR,
        'stand': HERO_TILE.GARV_DOOR_INNER,
        'is_far': lambda: not in_mansion(game.tile()),
        'log': log,
    }))
    return _result5


def enter_kitchen(log):
    if in_kitchen(game.tile()) or in_garden(game.tile()) or in_yard(game.tile()) or in_side_room(game.tile()):
        return True
    # Why: the kitchen door is out of the baked graph, so from the hideout or the mansion there's no route to the restaurant floor it's clicked from.
    _w6 = yield from return_to_street(log)
    if not (_w6):
        return False
    _result7 = yield from cross_teleport_door(Record({
        'id': HERO_LOC.KITCHEN_DOOR,
        'stand': HERO_TILE.KITCHEN_DOOR,
        'is_far': lambda: in_kitchen(game.tile()),
        'log': log,
    }))
    return _result7


def leave_kitchen(log):
    if not in_kitchen(game.tile()):
        return True
    _result8 = yield from cross_teleport_door(Record({
        'id': HERO_LOC.KITCHEN_DOOR,
        'stand': HERO_TILE.KITCHEN_DOOR_INNER,
        'is_far': lambda: not in_kitchen(game.tile()),
        'log': log,
    }))
    return _result8


def push_panel(log):
    """The kitchen's secret panel is a Wall with a Push, never a Door, so no derivation ever bakes it."""
    if in_garden(game.tile()):
        return True
    _w9 = yield from enter_kitchen(log)
    if not (_w9):
        return False
    _result10 = yield from cross_teleport_door(Record({
        'id': HERO_LOC.KITCHEN_PANEL,
        'stand': HERO_TILE.KITCHEN_PANEL,
        'name': 'Wall',
        'op': 'Push',
        'is_far': lambda: in_garden(game.tile()),
        'log': log,
    }))
    return _result10


# Why: the yard reaches the garden through an ordinary door the graph already carries, so the panel push works from either tile behind it.
def push_panel_back(log):
    if not in_garden(game.tile()) and not in_yard(game.tile()):
        return True
    _result11 = yield from cross_teleport_door(Record({
        'id': HERO_LOC.KITCHEN_PANEL,
        'stand': HERO_TILE.KITCHEN_PANEL_INNER,
        'name': 'Wall',
        'op': 'Push',
        'is_far': lambda: in_kitchen(game.tile()),
        'log': log,
    }))
    return _result11


def return_to_street(log):
    """Undo the sealed pocket you're standing in, so a walk to a bank, a shop or a partner has a route. Every door here is out of the baked graph."""
    _c12 = in_treasure_room(game.tile())
    if _c12:
        _w13 = yield from cross_treasure_door_out(log)
        _c12 = not (_w13)
    if _c12:
        return False
    _c14 = in_mansion(game.tile())
    if _c14:
        _w15 = yield from leave_mansion(log)
        _c14 = not (_w15)
    if _c14:
        return False
    _c16 = in_side_room(game.tile())
    if _c16:
        _w17 = yield from cross_side_door_out(log)
        _c16 = not (_w17)
    if _c16:
        return False
    _w18 = yield from push_panel_back(log)
    if not (_w18):
        return False
    _w19 = yield from leave_kitchen(log)
    if not (_w19):
        return False
    _result20 = yield from leave_brimhaven_hq(log)
    return _result20


# Why: `[oploc1,pete_sidedoor]` only opens for someone on the door's own row, which is the side room; from the yard it answers "This door is locked" and yields only to the key.
def cross_side_door_in(log):
    """Into the 5-tile side room, which needs Grip's spare key from a Black Arm partner."""
    if in_side_room(game.tile()):
        return True
    mark = game_messages.mark()
    ok = yield from use_on_loc(HERO_ID.MISC_KEY, Record({'name': 'Door', 'near': HERO_TILE.YARD, 'within': 4, 'id': HERO_LOC.SIDE_DOOR}), [], lambda: in_side_room(game.tile()), log)
    if not ok:
        log2(log, mark, 'side door')
    return ok


def cross_side_door_out(log):
    if not in_side_room(game.tile()):
        return True
    _result21 = yield from cross_teleport_door(Record({
        'id': HERO_LOC.SIDE_DOOR,
        'stand': HERO_TILE.SIDE_ROOM,
        'is_far': lambda: not in_side_room(game.tile()),
        'log': log,
    }))
    return _result21


def cross_treasure_door_in(log):
    """Into the treasure room, which yields only to Grip's own keyring and only after the papers."""
    if in_treasure_room(game.tile()):
        return True
    mark = game_messages.mark()
    ok = yield from use_on_loc(HERO_ID.GRIP_KEYS, Record({'name': 'Door', 'near': HERO_TILE.TREASURE_DOOR, 'within': 4, 'id': HERO_LOC.TREASURE_DOOR}), [], lambda: in_treasure_room(game.tile()), log)
    if not ok:
        log2(log, mark, 'treasure door')
    return ok


def cross_treasure_door_out(log):
    if not in_treasure_room(game.tile()):
        return True
    _result22 = yield from cross_teleport_door(Record({
        'id': HERO_LOC.TREASURE_DOOR,
        'stand': HERO_TILE.TREASURE_DOOR_INNER,
        'is_far': lambda: not in_treasure_room(game.tile()),
        'log': log,
    }))
    return _result22
