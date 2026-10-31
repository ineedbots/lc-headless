"""Ported from rs2b0t's src/bot/api/ai/quests/defs/plaguecity/travel.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.items import equipment, inventory
from rs2004.quests.defs.plaguecity.areas import PC_ITEM, PC_LOC, PC_TILE, plague_area
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.traversal import traversal

__all__ = ['area', 'loc_by_id', 'walk_to', 'arrive', 'go_upstairs', 'go_cellar', 'go_east', 'go_sewer', 'go_west']


def area():
    return plague_area(game.tile())


def loc_by_id(ids, op, within=10):
    wanted = set(([ids] if ((isinstance(ids, int) or isinstance(ids, float)) and not isinstance(ids, bool)) else ids))
    base = locs.query().where(lambda loc: (loc.id in wanted))
    return ((base if op is None else base.action(op))).within(within).nearest()


def walk_to(to, radius, log):
    here = game.tile()
    if here and here.level == to.level and to.distance_to(here) <= radius:
        return True
    _result1 = yield from traversal.walk_resilient(to, radius=radius, attempts=3, timeout_ms=180000, log=log)
    return _result1


# Why: the garden dig hands the spade objbox before it teleports, so a plain tile poll times out while the crossing waits on a click nobody made.
def arrive(want, log, ms=20000):
    landed = yield from drive_until(lambda: area() == want, [], log, ms)
    if landed:
        yield from settle_scene()
    return landed


def dig_into_sewer(log):
    if area() == 'sewer':
        return True
    _w2 = yield from walk_to(PC_TILE.GARDEN, 1, log)
    if not (_w2):
        return False
    yield from settle_scene()
    spade = ([item for item in inventory.items() if item.id == PC_ITEM.SPADE.id] or [None])[0]
    patch = loc_by_id(PC_LOC.MUD_PATCH, None, 6)
    if not spade or not patch:
        log(f"no {('Mud patch' if spade else 'Spade')} for the dig into the sewer")
        return False
    if not (spade.use_on(patch)):
        return False
    _result3 = yield from arrive('sewer', log)
    return _result3


def climb_mud_pile(log):
    if area() == 'east':
        return True
    _w4 = yield from walk_to(PC_TILE.MUD_PILE, 1, log)
    if not (_w4):
        return False
    yield from settle_scene()
    pile = loc_by_id(PC_LOC.MUD_PILE, 'Climb', 8)
    if not pile or not (pile.interact('Climb')):
        log('no Mud pile offering Climb in the sewer')
        return False
    _result5 = yield from arrive('east', log)
    return _result5


def squeeze_pipe(log):
    if area() == 'west':
        return True
    _w6 = yield from equipment.equip(PC_ITEM.GAS_MASK.name)
    if not (_w6):
        log('the Gas mask has to be worn to squeeze through the sewer pipe')
        return False
    _w7 = yield from walk_to(PC_TILE.SEWER_PIPE, 1, log)
    if not (_w7):
        return False
    yield from settle_scene()
    pipe = loc_by_id(PC_LOC.SEWER_PIPE, 'Search', 8)
    if not pipe or not (pipe.interact('Search')):
        log('no Sewer pipe offering Search at the west end of the sewer')
        return False
    _result8 = yield from arrive('west', log)
    return _result8


# Why: the manhole reverts to its cover 500 ticks after the pipe opened it, and the closed loc only offers Open.
def drop_manhole(log):
    if area() == 'sewer':
        return True
    _w9 = yield from walk_to(PC_TILE.MANHOLE, 1, log)
    if not (_w9):
        return False
    yield from settle_scene()
    shut = loc_by_id(PC_LOC.MANHOLE_SHUT, 'Open', 8)
    if shut:
        if not (shut.interact('Open')):
            return False
        yield from execution.delay_until(lambda: loc_by_id(PC_LOC.MANHOLE_OPEN, 'Climb-down', 8) is not None, 6000)
    open = loc_by_id(PC_LOC.MANHOLE_OPEN, 'Climb-down', 8)
    if not open or not (open.interact('Climb-down')):
        log('no open Manhole to climb down in West Ardougne')
        return False
    _result10 = yield from arrive('sewer', log)
    return _result10


def leave_upstairs(log):
    _w11 = yield from walk_to(PC_TILE.REHNISON_TOP, 2, log)
    if not (_w11):
        return False
    stairs = loc_by_id(PC_LOC.REHNISON_STAIRS_DOWN, 'Walk-down', 8)
    if not stairs or not (stairs.interact('Walk-down')):
        log('no Rehnison stairs down in range')
        return False
    _result12 = yield from arrive('west', log)
    return _result12


def leave_cellar(log):
    _w13 = yield from walk_to(PC_TILE.HOUSE_STAIRS_UP, 2, log)
    if not (_w13):
        return False
    stairs = loc_by_id(PC_LOC.HOUSE_STAIRS_UP, 'Walk-Up', 8)
    if not stairs or not (stairs.interact('Walk-Up')):
        log('no plague house stairs up in the cellar')
        return False
    _result14 = yield from arrive('west', log)
    return _result14


def go_upstairs(log):
    if area() == 'upstairs':
        return True
    _w15 = yield from walk_to(PC_TILE.REHNISON_STAIRS, 1, log)
    if not (_w15):
        return False
    yield from settle_scene()
    stairs = loc_by_id(PC_LOC.REHNISON_STAIRS_UP, 'Walk-up', 8)
    if not stairs or not (stairs.interact('Walk-up')):
        log('no Rehnison stairs up in range')
        return False
    _result16 = yield from arrive('upstairs', log)
    return _result16


def go_cellar(log):
    if area() == 'cellar':
        return True
    _w17 = yield from walk_to(PC_TILE.HOUSE_STAIRS_DOWN, 2, log)
    if not (_w17):
        return False
    yield from settle_scene()
    stairs = loc_by_id(PC_LOC.HOUSE_STAIRS_DOWN, 'Walk-Down', 8)
    if not stairs or not (stairs.interact('Walk-Down')):
        log('no plague house stairs down in range')
        return False
    _result18 = yield from arrive('cellar', log)
    return _result18


def go_east(log):
    """Walk out of whatever pocket the bot is standing in and back onto the mainland."""
    _case19 = area()
    if _case19 == 'east':
        return True
    elif _case19 == 'upstairs':
        _result20 = yield from leave_upstairs(log)
        return _result20
    elif _case19 == 'cellar':
        _result21 = yield from leave_cellar(log)
        return _result21
    elif _case19 == 'west':
        _w22 = yield from drop_manhole(log)
        if not (_w22):
            return False
        _result22 = yield from climb_mud_pile(log)
        return _result22
    elif _case19 == 'sewer':
        _result23 = yield from climb_mud_pile(log)
        return _result23
    else:
        return False


def go_sewer(log):
    """Reach the sewer from wherever the bot is standing; the garden dig needs a Spade."""
    _case24 = area()
    if _case24 == 'sewer':
        return True
    elif _case24 == 'east':
        _result25 = yield from dig_into_sewer(log)
        return _result25
    elif _case24 == 'west':
        _result26 = yield from drop_manhole(log)
        return _result26
    elif _case24 == 'upstairs':
        _result27 = yield from leave_upstairs(log)
        return _result27
    elif _case24 == 'cellar':
        _result28 = yield from leave_cellar(log)
        return _result28
    else:
        return False


def go_west(log):
    """Garden dig, then the sewer pipe. Needs a Spade in the pack and a Gas mask to wear."""
    _case29 = area()
    if _case29 == 'west':
        return True
    elif _case29 == 'upstairs':
        _result30 = yield from leave_upstairs(log)
        return _result30
    elif _case29 == 'cellar':
        _result31 = yield from leave_cellar(log)
        return _result31
    elif _case29 == 'sewer':
        _result32 = yield from squeeze_pipe(log)
        return _result32
    elif _case29 == 'east':
        _w33 = yield from dig_into_sewer(log)
        if not (_w33):
            return False
        _result33 = yield from squeeze_pipe(log)
        return _result33
    else:
        return False
