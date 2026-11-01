"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/navigator.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.quests.defs.fremenniktrials.areas import FT_LOC, FT_TILE, MAZE_ROUTE, SWENSEN, in_maze
from rs2004.quests.defs.fremenniktrials.supplies import walk_to
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.primitives import drive_dialog
from rs2004.quests.exec.prompts import settle_scene
from rs2004.reach import reach

__all__ = ['navigator_step', 'maze_leg_at']

NEAR = 3


def navigator_step(snap):
    """Swensen's trial: 7 portals from one end of his labyrinth to the other."""
    if has_flag(snap.progress, 'navigator-done'):
        return None
    if not has_flag(snap.progress, 'navigator-started'):
        return Record({'kind': 'talk', 'stop': SWENSEN(['Yes'])})
    return Record({'kind': 'custom', 'name': "walk Swensen's maze", 'run': run_maze})


# Why: an attempt that ends before its portal fires leaves us on that portal's stand tile, which is mid-route; reading it as scattered ropes out and throws away every leg won.
def maze_leg_at(here):
    """Which leg of the route a tile belongs to, or -1 when the maze has scattered us."""
    if not here:
        return -1
    if FT_TILE.MAZE_ENTRY.distance_to(here) <= NEAR:
        return 0
    landed = ([_i for _i, leg in enumerate(MAZE_ROUTE) if leg.land.distance_to(here) <= NEAR] or [-1])[0]
    if landed >= 0:
        return landed + 1
    standing = ([_i for _i, leg in enumerate(MAZE_ROUTE) if leg.stand.distance_to(here) <= NEAR] or [-1])[0]
    return (-1 if standing < 0 else standing)


def leg_at():
    return maze_leg_at(game.tile())


def escape(log):
    rope = locs.query().name('Escape rope').action('Climb-up').within(12).nearest()
    if not rope:
        log('scattered in the maze with no escape rope in range')
        return False
    log('a wrong portal scattered us — taking the escape rope and starting again')
    if not (rope.interact('Climb-up')):
        return False
    return True
    if False:
        yield


def run_maze(log):
    if not in_maze(game.tile()):
        down = yield from reach.loc_op('Ladder', 'Climb-down', FT_TILE.MAZE_LADDER, lambda: in_maze(game.tile()), id=FT_LOC.MAZE_LADDER_TOP, log=log)
        if down != 'done':
            return False
        yield from settle_scene()
    leg = leg_at()
    if leg < 0:
        yield from escape(log)
        return False
    while leg < len(MAZE_ROUTE):
        hop = MAZE_ROUTE[leg]

        def _fn1():
            t = game.tile()
            return t is not None and hop.land.distance_to(t) <= NEAR
        status = yield from reach.loc_op('Portal', 'Use', hop.stand, _fn1, id=hop.id, log=log)
        yield from settle_scene()
        if status != 'done':
            log(f'portal {leg + 1}: {status}')
            return False
        if leg_at() != leg + 1:
            log(f'portal {leg + 1} did not land us where the route expects')
            return False
        log(f'maze: through portal {leg + 1} of {len(MAZE_ROUTE)}')
        leg += 1
    _w2 = yield from walk_to(FT_TILE.MAZE_EXIT_STAND, 0, log)
    if not (_w2):
        return False
    out = yield from reach.loc_op('Ladder', 'Climb-up', FT_TILE.MAZE_EXIT_STAND, lambda: not in_maze(game.tile()), id=FT_LOC.MAZE_EXIT, log=log)
    if out != 'done':
        return False
    # Why: the vote is queued by the exit ladder's own conversation with Swensen, so leaving it undriven loses it.
    yield from drive_dialog([], log)
    return True
