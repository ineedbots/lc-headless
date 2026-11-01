# ---- api/ai/quests/defs/upass/grid.ts
"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/grid.ts (MIT, see thirdparty/rs2b0t). A ts2py draft: fix what's
marked "ts2py:", then this line."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.quests.defs.upass.areas import GRID_ZONE, UP_LOC, UP_TILE, past_grid_tile
from rs2004.quests.defs.upass.pass_ import travel_to
from rs2004.quests.defs.upass.stall import release_journal, stalled_crossing

__all__ = ['in_grid', 'in_pit', 'past_grid', 'at_lever', 'cross_grid']

# Why: the safe path through the spiked grid is 3 digits in `%ibanmulti` bits 22-31, and `ibanmulti` is `scope=perm` with no `transmit`, so the client can't read it. The journal stall walks over all of it instead.
PIT = Record({'min_z': 9536, 'max_z': 9599})
HANDHOLD_RETURN = UP_TILE.GRID_EAST


def here():
    return game.tile()


def in_grid():
    t = here()
    return t is not None and t.x >= GRID_ZONE.min_x and t.x <= GRID_ZONE.max_x and t.z >= GRID_ZONE.min_z and t.z <= GRID_ZONE.max_z


def in_pit():
    t = here()
    return t is not None and t.z >= PIT.min_z and t.z <= PIT.max_z


def past_grid():
    """West of the grid, on the portcullis side. The crossing is done."""
    return past_grid_tile(here())


def at_lever():
    """West of the trapped columns, beside the lever. The walk is over, the lever's script has not run."""
    t = here()
    return t is not None and t.x < GRID_ZONE.min_x and t.z >= GRID_ZONE.min_z and t.z <= GRID_ZONE.max_z


def climb_out_of_pit(log):
    # Why: `p_teleport` can leave the old scene visible for two ticks, so wait before querying the rocks.
    for attempt in range(8):
        if not (in_pit()):
            break
        rocks = locs.query().where(lambda loc: loc.id == UP_LOC.GRID_HANDHOLDS).action('Climb').within(12).nearest()
        _c1 = rocks and (rocks.interact('Climb'))
        if _c1:
            _w2 = yield from execution.delay_until(lambda: not in_pit(), 8000)
            _c1 = (_w2)
        if _c1:
            return True
        yield from execution.delay_ticks(2)
    if in_pit():
        log('grid: no protruding rocks in the pit to climb')
        return False
    return True


def to_approach(log):
    """Back to the staging tile the stall is launched from. Why: the launch tile has to sit outside the trapped rectangle by more than the walk covers before the journal lands, and Koftik's lip is the only tile east of the grid the route reaches."""
    _c3 = in_pit()
    if _c3:
        _w4 = yield from climb_out_of_pit(log)
        _c3 = not (_w4)
    if _c3:
        return False
    # Why: with the grid behind you a `travelTo` at the east side hunts seams across the cavern. The lever counts as behind: the pack calls the portcullis blocked, so the lip is unreachable from there too.
    if past_grid() or at_lever():
        return True
    t = here()
    if t and UP_TILE.GRID_APPROACH.distance_to(t) <= 1:
        return True
    # Why: the rope swing is in travelTo's vocabulary, so the approach is one call and the caller doesn't pick seams.
    _result5 = yield from travel_to(UP_TILE.GRID_APPROACH, 1, log)
    return _result5


def lever():
    return locs.query().where(lambda loc: loc.id == UP_LOC.PORTCULLIS_LEVER).action('Pull').within(40).nearest()


def pull_through(log):
    """Close the journal, pull the lever, and wait for its forced movement. Why: `Player.tryInteract` cannot send the lever op while the journal blocks access."""
    for attempt in range(3):
        if not (not past_grid()):
            break
        yield from release_journal()
        _w6 = yield from execution.delay_until_ticks(past_grid, 20)
        if _w6:
            return True
        # Why: `loc_change(upass_lever_down, 15)` swaps the lever for 15 ticks after a pull, so nothing in reach means the pull landed and its forced move is on its way; wait, don't click again.
        target = lever()
        if target:
            target.interact('Pull')
    if not past_grid():
        t = here()
        log(f'grid: the lever would not carry us through — standing at ({(t.x if t is not None else None)},{(t.z if t is not None else None)})')
    return past_grid()


def cross_grid(log):
    """East to west over the spiked grid, ending west of the portcullis."""
    if past_grid():
        return True
    if at_lever():
        _result7 = yield from pull_through(log)
        return _result7
    _w8 = yield from to_approach(log)
    if not (_w8):
        return False
    # Why: the stalled walk owns the trapped columns only and ends beside the lever, because the op that finishes the job can't run until the journal comes down.
    carried = yield from stalled_crossing(Record({
        'find': lever,
        'op': 'Pull',
        'arrived': lambda: past_grid() or at_lever(),
        'abort': in_pit,
        'recover': lambda: to_approach(log),
        'log': log,
    }))
    if not carried:
        return False
    _result9 = yield from pull_through(log)
    return _result9

