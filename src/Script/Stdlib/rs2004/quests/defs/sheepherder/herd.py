"""Ported from rs2b0t's src/bot/api/ai/quests/defs/sheepherder/herd.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import npcs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.navigation import reachability
from rs2004.quests.defs.sheepherder.areas import GATE_ZONE, PEN, SHEEP_SPAWN, in_box, sheep_name
from rs2004.quests.defs.sheepherder.herd_path import HERD_DIRS, herd_cost, herd_directions, herd_plan
from rs2004.traversal import traversal

__all__ = ['SceneGrid', 'sheep_in_pen', 'clear_refusal', 'herd_to_pen']

# Why: the shortest route is 31 pushes and the longest 58, and drift near a sheep's spawn roughly triples that (90 pushes on the 31-tile leg live).
PROD_BUDGET = 260
PROGRESS_EVERY = 25
STUCK_LIMIT = 8
APPROACH_RADIUS = 6
FOLLOW_RADIUS = 14
APPROACH_RAY = 3
STRAY_LIMIT = 6
# Why: (2610,3351), (2612,3349) and (2610,3348) on the enclosure's south-east corner are walkable, on the way home and have no standable side, so wait briefly then go for another copy.
PINNED_WAIT = 3
PINNED_LIMIT = 8
LOCK_RADIUS = 5


class SceneGrid:
    """The loaded scene's walking, as herd_path reads it, remembered per tile until reset."""

    # Why: one push plans over about 4,000 tiles, and asking the client for each on every plan outran the script's
    # step budget live; the leg's fences don't move.
    def __init__(self):
        self.reset()

    def reset(self):
        self._walkable = {}
        self._steps = {}

    def walkable(self, x, z):
        key = x * 100000 + z
        known = self._walkable.get(key)
        if known is None:
            known = reachability.walkable(Tile(x, z, 0))
            self._walkable[key] = known
        return known

    def can_step(self, x, z, dx, dz):
        key = (x * 100000 + z) * 16 + (dx + 1) * 4 + (dz + 1)
        known = self._steps.get(key)
        if known is None:
            known = reachability.can_step(Tile(x, z, 0), Tile(x + dx, z + dz, 0))
            self._steps[key] = known
        return known


SCENE_GRID = SceneGrid()


def copies(n):
    return npcs.query().name(sheep_name(n)).results()


# Why: 3 copies of every sheep share one quest bit and name and the herded one stays within a tile or two of where it was last seen, so lock on its last tile; client slots churn on scene rebuilds.
def near_last(n, last):
    """The copy still standing where the herd left it."""
    best = None
    for npc in copies(n):
        t = npc.tile()
        d = max(abs(t.x - last.x), abs(t.z - last.z))
        if d <= LOCK_RADIUS and (best is None or d < best.d):
            best = Record({'npc': npc, 'd': d})
    return best.npc if best is not None else None


def route_cost(npc):
    t = npc.tile()
    return herd_cost(herd_plan(SCENE_GRID, t, GATE_ZONE), t.x, t.z)


# Why: a sheep in a trap has no route and the other 2 copies carry the same quest bit, so the leg fetches one of those and skips the 500-tick teleport wait.
def pick_sheep(n):
    """The copy with the shortest push route home, ignoring any that no push can move. Use with yield from."""
    best = None
    for i, npc in enumerate(copies(n)):
        # Why: each copy is a full route search, so each gets a step of its own.
        if i > 0:
            yield from execution.delay_ticks(1)
        cost = route_cost(npc)
        if cost is None:
            continue
        if best is None or cost < best.cost:
            best = Record({'npc': npc, 'cost': cost})
    return best.npc if best is not None else None


def sheep_in_pen(n):
    return ([npc for npc in copies(n) if in_box(PEN, npc.tile())] or [None])[0]


# Why: an npc only enters the client's list within about 15 tiles, so "not in the scene" says where you're standing.
def find_sheep(n, log):
    """Walk to the sheep's map spawn when no copy of it is both in range and movable."""
    here = yield from pick_sheep(n)
    if here:
        return here
    log(f'sheepherder: no movable {sheep_name(n)} in range — walking to its field at ({SHEEP_SPAWN[n].x},{SHEEP_SPAWN[n].z})')
    _w4 = yield from traversal.walk_resilient(SHEEP_SPAWN[n], radius=4, attempts=3, timeout_ms=180000, log=log)
    if not (_w4):
        return None
    yield from execution.delay_ticks(2)
    SCENE_GRID.reset()
    found = yield from pick_sheep(n)
    if not found:
        # Why: `npc_del` on the map spawn queues a respawn, so an empty field means wait.
        log(f'sheepherder: {sheep_name(n)} not at its field — waiting out the respawn')
        yield from execution.delay_ticks(8)
    return found


def clear_refusal():
    """Refusals arrive as a mesbox or a player line; both have to be cleared before the next push."""
    seen = False
    i = 0
    while i < 8 and (modals.is_open() or chat_dialog.is_open() or chat_dialog.can_continue()):
        seen = True
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        elif modals.is_open():
            yield from modals.close()
        else:
            break
        yield from execution.delay_ticks(1)
        i += 1
    return seen


# Why: the 2 gate tiles are baked door edges, and a world-walk that ends on one spends its budget opening the gate; a stalled follow cost 66s live and the sheep wandered home.
# Why: the follow is always inside the loaded scene, so the client pathfinder does it and the world-walker only does the opening approach.
# Why: the Prod op walks you to an adjacent tile itself, so standing anywhere on the line behind the sheep lets the server take the last step, which halves the cycle and the sheep's wander time.
def behind_sheep(me, sheep, dir):
    """Whether a Prod issued from here will be run from the tile the push needs."""
    if not me or me.level != 0:
        return False
    for step in range(1, APPROACH_RAY + 1):
        if me.x == sheep.x - dir.dx * step and me.z == sheep.z - dir.dz * step:
            return True
    return False


def stand_opposite(sheep, dir, log):
    """Step onto the tile the push has to be issued from."""
    stand = Tile(sheep.x - dir.dx, sheep.z - dir.dz, 0)

    def on():
        t = game.tile()
        return t is not None and t.level == 0 and t.x == stand.x and t.z == stand.z

    if on():
        return True
    here = game.tile()
    if here and here.level == 0 and max(abs(here.x - stand.x), abs(here.z - stand.z)) <= FOLLOW_RADIUS:
        yield from direct_navigator.walk_to(stand, 0, 8000)
    else:
        yield from traversal.walk_resilient(stand, radius=0, attempts=1, timeout_ms=20000, log=log)
    if on():
        return True
    log(f'sheepherder: could not stand at ({stand.x},{stand.z}) to push {sheep.x},{sheep.z}')
    return False


# Why: inside the gate zone the jump reads the sheep's own coord before the walk, so any push sends it over and the nearest stand is the fastest one.
def any_stand(tile):
    """Every tile a prod can be issued from, for a sheep already standing in the gate zone."""
    me = game.tile()
    return sorted([dir for dir in HERD_DIRS if SCENE_GRID.walkable(tile.x - dir.dx, tile.z - dir.dz) and SCENE_GRID.can_step(tile.x - dir.dx, tile.z - dir.dz, dir.dx, dir.dz)], key=lambda a: stand_cost(tile, a, me))


def stand_cost(tile, dir, me):
    if not me:
        return 0
    return max(abs(tile.x - dir.dx - me.x), abs(tile.z - dir.dz - me.z))


def push_once(n, npc, dir, log):
    before = npc.tile()
    if not (npc.interact('Prod')):
        log(f'sheepherder: no Prod op on {sheep_name(n)}')
        return 'refused'

    def _fn5():
        now = near_last(n, before)
        return now is None or now.tile().x != before.x or now.tile().z != before.z
    moved = yield from execution.delay_until(_fn5, 6000)
    yield from clear_refusal()
    if not moved:
        return 'refused'
    landed = near_last(n, before)
    after = landed.tile() if landed is not None else None
    wanted = after is not None and after.x == before.x + dir.dx and after.z == before.z + dir.dz
    return ('wanted' if wanted else 'elsewhere')


def herd_to_pen(n, log):
    """Push one sheep out to the tiles west of the gate and then over it. Why: the route is re-derived from the sheep's tile on every push, since its ai_timer returns it to wander mode and it drifts back toward spawn."""
    SCENE_GRID.reset()
    first = yield from find_sheep(n, log)
    if not first:
        return False
    _w6 = yield from traversal.walk_resilient(first.tile(), radius=APPROACH_RADIUS, attempts=3, timeout_ms=180000, log=log)
    if not (_w6):
        return False
    _v7 = yield from pick_sheep(n)
    last = ((_v7 if _v7 is not None else first)).tile()
    stuck = 0
    pinned = 0
    strayed = 0
    for push in range(PROD_BUDGET):
        sheep = near_last(n, last)
        if sheep is None:
            sheep = yield from pick_sheep(n)
        if not sheep:
            log(f'sheepherder: lost {sheep_name(n)} mid-herd')
            return False
        tile = sheep.tile()
        last = tile
        if in_box(PEN, tile):
            log(f'sheepherder: {sheep_name(n)} is in the enclosure after {push} push(es)')
            return True
        if push > 0 and push % PROGRESS_EVERY == 0:
            me = game.tile()
            log(f'sheepherder: {sheep_name(n)} at ({tile.x},{tile.z}) after {push} push(es), herder at ({(me.x if me is not None else None)},{(me.z if me is not None else None)})')
        dirs = (any_stand(tile) if in_box(GATE_ZONE, tile) else herd_directions(SCENE_GRID, tile, GATE_ZONE))
        # Why: a sheep on a tile with no standable side (the strip north of the enclosure's south fence is one) is pinned, so the leg waits it out and keeps its pushes.
        if len(dirs) == 0:
            pinned += 1
            if pinned > PINNED_LIMIT:
                log(f'sheepherder: {sheep_name(n)} stayed pinned at ({tile.x},{tile.z})')
                return False
            yield from execution.delay_ticks(PINNED_WAIT)
            continue
        pinned = 0
        if stuck >= STUCK_LIMIT:
            log(f'sheepherder: {sheep_name(n)} refused {STUCK_LIMIT} pushes near ({tile.x},{tile.z})')
            return False
        # Why: a refused push falls through to the next-best direction.
        dir = dirs[min(stuck, len(dirs) - 1)]
        ready = strayed < STRAY_LIMIT and behind_sheep(game.tile(), tile, dir)
        _c9 = not ready
        if _c9:
            _w10 = yield from stand_opposite(tile, dir, log)
            _c9 = not (_w10)
        if _c9:
            stuck += 1
            continue
        now = near_last(n, tile)
        if not now or now.tile().x != tile.x or now.tile().z != tile.z:
            # Why: the sheep wandered while the walk landed, so the stand behind it is the wrong tile now.
            yield from execution.delay_ticks(1)
            continue
        outcome = yield from push_once(n, now, dir, log)
        # Why: an off-axis landing is usually the sheep's own wander step, so the count is a streak: 6 in a row means the server is picking its own approach side, and 1 good push clears it.
        # Why: it resets since walking every stand doubles the cycle and the sheep's walk home, which strays it again; one unlucky run spent 20 minutes on one sheep.
        strayed = (0 if outcome == 'wanted' else strayed + 1)
        if strayed == STRAY_LIMIT:
            log(f'sheepherder: {sheep_name(n)} kept landing off the push axis — walking the stand until one lands')
        stuck = (stuck + 1 if outcome == 'refused' else 0)
    log(f'sheepherder: {sheep_name(n)} not penned within {PROD_BUDGET} pushes')
    return False
