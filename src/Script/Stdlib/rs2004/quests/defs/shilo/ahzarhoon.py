"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/ahzarhoon.ts (MIT, see thirdparty/rs2b0t)."""

import _core

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import game, reader
from rs2004.items import inventory
from rs2004.quests.defs.shilo.areas import SV_ITEM, SV_LOC, SV_TILE
from rs2004.quests.defs.shilo.scene import drive_choice, drive_until, held_id, here, loc_near, prompt_loc, settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['dig_mound', 'light_fissure', 'rope_fissure', 'enter_fissure', 'cross_cave_in', 'take_tattered_scroll', 'take_crumpled_scroll', 'take_zadimus_corpse', 'read_scroll', 'leave_ah_za_rhoon', 'bury_zadimus']

YES_CRAWL = ["Yes, I'll give it a go!"]
YES_SEARCH = ["Yes, I'm quite sure."]
YES_CORPSE = ['Yes, I may find something else on the corpse.']
YES_PATH = ["Yes, I'll follow the path."]
YES_READ = ['Yes please.']
YES_WRIGGLE = ["Yes, I'll wriggle through."]


def in_caves():
    area = here()
    return area == 'ahZaRhoonNorth' or area == 'ahZaRhoonSouth'


def fissure():
    return loc_near(SV_LOC.FISSURE, 'Search', 10)


# Why: the fissure is a 50-tick `loc_change` over the mound, and looking at the mound re-creates whichever fissure the stage has earned.
def ensure_fissure(log):
    """Make sure the stage's fissure exists before acting on it."""
    if fissure():
        return True
    _result1 = yield from prompt_loc(Record({
        'name': SV_LOC.MOUND,
        'op': 'Look-at',
        'near': SV_TILE.MOUND_STAND,
        'expect': lambda: fissure() is not None,
        'expect_ms': 10000,
    }), log)
    return _result1


def dig_mound(log):
    if fissure():
        return True
    _result2 = yield from use_on_loc(SV_ITEM.SPADE.id, Record({'name': SV_LOC.MOUND, 'near': SV_TILE.MOUND_STAND}), [], lambda: fissure() is not None, log)
    return _result2


def light_fissure(log):
    """The light source is burned by the fissure, so its disappearance is the receipt."""
    before = held_id(SV_ITEM.LIT_CANDLE.id)
    if before == 0:
        log('no lit candle to drop into the fissure')
        return False
    _w3 = yield from ensure_fissure(log)
    if not (_w3):
        return False
    _result4 = yield from use_on_loc(SV_ITEM.LIT_CANDLE.id, Record({'name': SV_LOC.FISSURE, 'near': SV_TILE.MOUND_STAND}), [], lambda: held_id(SV_ITEM.LIT_CANDLE.id) < before, log)
    return _result4


def rope_fissure(log):
    before = held_id(SV_ITEM.ROPE.id)
    if before == 0:
        log('no rope to tie to the fissure')
        return False
    _w5 = yield from ensure_fissure(log)
    if not (_w5):
        return False
    _result6 = yield from use_on_loc(SV_ITEM.ROPE.id, Record({'name': SV_LOC.FISSURE, 'near': SV_TILE.MOUND_STAND}), [], lambda: held_id(SV_ITEM.ROPE.id) < before, log)
    return _result6


def enter_fissure(log):
    if in_caves():
        return True
    _w7 = yield from ensure_fissure(log)
    if not (_w7):
        return False
    ok = yield from prompt_loc(Record({
        'name': SV_LOC.FISSURE,
        'op': 'Search',
        'near': SV_TILE.MOUND_STAND,
        'prefer': YES_CRAWL,
        'expect': lambda: here() == 'ahZaRhoonNorth',
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def in_south_room(log):
    """The south room is 2 crossings from the surface, and a death or restart puts us back on Karamja."""
    _c8 = not in_caves()
    if _c8:
        _w9 = yield from enter_fissure(log)
        _c8 = not (_w9)
    if _c8:
        return False
    _result10 = yield from cross_cave_in('ahZaRhoonSouth', log)
    return _result10


def cross_cave_in(to, log):
    """The two cave rooms are separate mapsquares joined only by this rubble squeeze."""
    if here() == to:
        return True
    near = (SV_TILE.CAVE_IN_NORTH if to == 'ahZaRhoonSouth' else SV_TILE.CAVE_IN_SOUTH)
    ok = yield from prompt_loc(Record({
        'name': SV_LOC.CAVE_IN,
        'op': 'Search',
        'near': near,
        'prefer': YES_WRIGGLE,
        'expect': lambda: here() == to,
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def take_tattered_scroll(log):
    if held_id(SV_ITEM.TATTERED_SCROLL.id) > 0:
        return True
    _w11 = yield from in_south_room(log)
    if not (_w11):
        return False
    # Why: a failed Agility roll drops the ceiling on you, and the step runs again.
    _result12 = yield from prompt_loc(Record({
        'name': SV_LOC.LOOSE_ROCKS,
        'op': 'Search',
        'near': SV_TILE.LOOSE_ROCKS,
        'prefer': YES_SEARCH,
        'expect': lambda: held_id(SV_ITEM.TATTERED_SCROLL.id) > 0,
    }), log)
    return _result12


def take_crumpled_scroll(log):
    if held_id(SV_ITEM.CRUMPLED_SCROLL.id) > 0:
        return True
    _w13 = yield from in_south_room(log)
    if not (_w13):
        return False
    _result14 = yield from prompt_loc(Record({
        'name': SV_LOC.OLD_SACKS,
        'op': 'Search',
        'near': SV_TILE.OLD_SACKS,
        'expect': lambda: held_id(SV_ITEM.CRUMPLED_SCROLL.id) > 0,
    }), log)
    return _result14


def take_zadimus_corpse(log):
    if held_id(SV_ITEM.ZADIMUS_CORPSE.id) > 0 or held_id(SV_ITEM.BONE_SHARD.id) > 0 or held_id(SV_ITEM.BONE_KEY.id) > 0:
        return True
    _w15 = yield from in_south_room(log)
    if not (_w15):
        return False
    _result16 = yield from prompt_loc(Record({
        'name': SV_LOC.GALLOWS,
        'op': 'Search',
        'near': SV_TILE.GALLOWS,
        'prefer': YES_CORPSE,
        'expect': lambda: held_id(SV_ITEM.ZADIMUS_CORPSE.id) > 0,
    }), log)
    return _result16


# Why: reading sets the bits that gate the Bervirius tomb and the necklace craft, and the journal stops rendering them once the dolmen is searched, so read on sight.
def read_scroll(item_id):
    """Read a scroll, setting the tomb and necklace bits."""

    def _fn17(log):
        scroll = ([item for item in inventory.items() if item.id == item_id] or [None])[0]
        if not scroll:
            log(f'no scroll {item_id} in the pack to read')
            return False
        if not (scroll.interact('Read')):
            return False
        yield from execution.delay_ticks(2)
        _w18 = yield from drive_choice(YES_READ, log)
        if not (_w18):
            return False
        # Why: the scroll body is a main modal built with if_settext, so driveChoice can't see it, and every journal read comes back empty while it's up.
        yield from execution.delay_until(lambda: reader.modals().main != -1, 6000)
        if reader.modals().main != -1:
            _core.close_interfaces()
            yield from execution.delay_ticks(1)
        return True
    return _fn17


def leave_ah_za_rhoon(log):
    """The waterfall path is the repeatable way out; the raft is a one-shot."""
    if not in_caves():
        return True
    _w19 = yield from cross_cave_in('ahZaRhoonNorth', log)
    if not (_w19):
        return False
    ok = yield from prompt_loc(Record({
        'name': SV_LOC.WATERFALL_ROCKS,
        'op': 'Search',
        'near': SV_TILE.WATERFALL_ROCKS,
        'prefer': YES_PATH,
        'expect': lambda: not in_caves(),
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def bury_zadimus(log):
    """Zadimus only rests on the sacred ground behind Trufitus's hut."""
    if held_id(SV_ITEM.BONE_SHARD.id) > 0 or held_id(SV_ITEM.BONE_KEY.id) > 0:
        return True
    _w20 = yield from traversal.walk_resilient(SV_TILE.SACRED_GROUND, radius=1, attempts=4, timeout_ms=240000, log=log)
    if not (_w20):
        return False
    tile = game.tile()
    if not tile or tile.x < 2794 or tile.x > 2798 or tile.z < 3087 or tile.z > 3090:
        log('not standing on the sacred ground yet')
        return False
    corpse = ([item for item in inventory.items() if item.id == SV_ITEM.ZADIMUS_CORPSE.id] or [None])[0]
    if not corpse:
        log('no Zadimus corpse to bury')
        return False
    if not (corpse.interact('Bury')):
        return False
    # Dig, apparition, speech, shard, closing box: a chain with gaps, so the shard ends the step.
    _result21 = yield from drive_until(lambda: held_id(SV_ITEM.BONE_SHARD.id) > 0, [], log, 60000)
    return _result21
