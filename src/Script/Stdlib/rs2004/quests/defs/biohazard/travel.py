"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/travel.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, BIO_LOC, BIO_NPC, BIO_TILE, bio_area
from rs2004.quests.defs.biohazard.gear import wear
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import drive_until, prompt_loc, settle_scene
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['area', 'loc_by_id', 'walk_to', 'talk_at', 'enter_hq', 'go_west', 'go_mainland']

OMART_CROSS = ['Ok, lets do it.']
KILRON_CROSS = ['Yes I do.']


def area():
    return bio_area(game.tile())


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


# Why: Both wall crossings require completing an `if_close`/`mes`/`p_delay` chain before `p_teleport` runs.
def arrive(want, prefer, log, ms=25000):
    landed = yield from drive_until(lambda: want(area()), prefer, log, ms)
    if landed:
        yield from settle_scene()
    return landed


def talk_at(npc, near, prefer, log, radius=2):
    _w2 = yield from walk_to(near, radius, log)
    if not (_w2):
        return False
    yield from settle_scene()
    _w3 = yield from reach.npc_dialog(npc, near, log=log)
    if (_w3) != 'done':
        log(f'no dialogue with {npc} near ({near.x},{near.z})')
        return False
    _result4 = yield from talk_strict(npc, prefer, log)
    return _result4


# Why: Omart's answer is 5 `if_close`/`mes`/`p_delay` beats before the crossing choice, each leaving the chat modal shut, which `talkStrict` reads as the end and returns on, so the arrival poll drives the choice.
def climb_with_omart(log):
    """Omart's rope ladder. Only offered between released_pigeons and found_distillator."""
    yield from talk_at(BIO_NPC.OMART, BIO_TILE.OMART, OMART_CROSS, log)
    _result5 = yield from arrive(lambda a: a == 'west' or a == 'hq', OMART_CROSS, log)
    return _result5


def climb_with_kilron(log):
    """Kilron's end of the same ladder; he offers it from climbed_ladder onward, forever."""
    yield from talk_at(BIO_NPC.KILRON, BIO_TILE.KILRON, KILRON_CROSS, log)
    _result6 = yield from arrive(lambda a: a == 'mainland', KILRON_CROSS, log)
    return _result6


# Why: the door answers Open with "In you go doc." and only opens once that box is clicked through, which the walker's door crossing gives up on; mourners wander both faces and one on the stand tile fails the client's path search, so `Reach.locOp` owns the approach from either side.
def cross_hq_door(near, want, log):
    _result7 = yield from prompt_loc(Record({
        'name': 'Door',
        'id': BIO_LOC.HQ_DOOR,
        'op': 'Open',
        'near': near,
        'within': 8,
        'expect': lambda: want(area()),
        'expect_ms': 25000,
    }), log)
    return _result7


def enter_hq(log):
    if area() == 'hq' or area() == 'hqUpstairs':
        return True
    _w8 = yield from wear(BIO_ITEM.DOCTOR_GOWN, log)
    if not (_w8):
        log("the Doctors' gown has to be worn before the mourners open their door")
        return False
    landed = yield from cross_hq_door(BIO_TILE.HQ_DOOR, lambda a: a == 'hq' or a == 'hqUpstairs', log)
    if landed:
        yield from settle_scene()
    return landed


def leave_hq(log):
    """The same door from the inside, where the script opens it for anyone."""
    _c9 = area() == 'hqUpstairs'
    if _c9:
        _w10 = yield from walk_to(BIO_TILE.HQ_INSIDE, 4, log)
        _c9 = not (_w10)
    if _c9:
        return False
    if area() != 'hq':
        return area() == 'west' or area() == 'mainland'
    out = yield from cross_hq_door(BIO_TILE.HQ_INSIDE, lambda a: a == 'west' or a == 'mainland', log)
    if out:
        yield from settle_scene()
    return out


def go_west(log):
    """West Ardougne, or the headquarters when that is where the caller was heading."""
    _case11 = area()
    if _case11 in ['west', 'hq', 'hqUpstairs']:
        return True
    elif _case11 == 'mainland':
        _result12 = yield from climb_with_omart(log)
        return _result12
    elif _case11 == 'castleUpstairs':
        _w14 = yield from walk_to(BIO_TILE.ELENA, 6, log)
        _c13 = (_w14)
        if not (_c13):
            return _c13
        _result15 = yield from climb_with_omart(log)
        return _result15
    elif _case11 == 'sewer':
        _w17 = yield from walk_to(BIO_TILE.ARDOUGNE_BANK, 4, log)
        _c16 = (_w17)
        if not (_c16):
            return _c16
        _result18 = yield from climb_with_omart(log)
        return _result18
    else:
        return False


# Why: Kilron crosses from climbed_ladder onward and costs one dialogue, but the manhole and mud pile are baked edges with no requirement eastbound, so there's a way out even when Kilron refuses.
def go_mainland(log):
    _case19 = area()
    if _case19 == 'mainland':
        return True
    elif _case19 in ['hq', 'hqUpstairs']:
        _w21 = yield from leave_hq(log)
        _c20 = (_w21)
        if not (_c20):
            return _c20
        _result22 = yield from go_mainland(log)
        return _result22
    elif _case19 == 'west':
        _w23 = yield from climb_with_kilron(log)
        if _w23:
            return True
        log('Kilron would not cross — walking out through the manhole instead')
        _result24 = yield from walk_to(BIO_TILE.ARDOUGNE_BANK, 4, log)
        return _result24
    elif _case19 in ['sewer', 'castleUpstairs']:
        _result25 = yield from walk_to(BIO_TILE.ARDOUGNE_BANK, 4, log)
        return _result25
    else:
        return False
