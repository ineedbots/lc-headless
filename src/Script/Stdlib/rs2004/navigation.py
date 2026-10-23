"""Questions about the loaded area, and walking through its doors: rs2b0t's Reachability
(event/webwalk/geometry/Reachability.ts), walkOpening (event/webwalk/walkOpening.ts) and Navigator
(event/webwalk/Navigator.ts), ported (MIT, see thirdparty/rs2b0t).

    if reachability.line_of_sight(game.tile(), npc.tile(), npc.size):
        game.cast_on_npc('Wind strike', npc)
    arrived = yield from walk_opening(Tile(2725, 3491, 0), 2, ['door'])
"""

import json

import _core
from rs2004 import execution
from rs2004 import walkgeom
from rs2004.entities import local_tile, locs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.reach import open_op, toward_dest

__all__ = [
    'reachability', 'navigator', 'walk_opening', 'is_openable_obstacle', 'face_steps', 'opened_neighbour', 'far_side',
]

# rs2b0t's CollisionFlag.SQ_BLOCKED: the ground, an NPC or player, or scenery on the tile.
SQ_BLOCKED = 0x280100
# How far to search for a shut door after a walk stalls.
ESCAPE_RADIUS = 14
OPEN_WAIT_MS = 4000
STEP_WAIT_MS = 2000
SEGMENTS = 8
SEGMENT_TIMEOUT_MS = 90000
DOOR_WALK_TIMEOUT_MS = 45000
# West, north, east, south: the four faces a wall door can sit on.
FACES = [(-1, 0), (0, 1), (1, 0), (0, -1)]


def _tile(t):
    return Tile.from_tile(t)


class Reachability:
    """Probes of the loaded area, on your level."""

    def can_reach(self, dest, adjacent_ok=False, max_steps=None):
        """Whether a walk from where you stand ends on dest, or with adjacent_ok beside it."""
        dest = _tile(dest)
        me = game.tile()
        if me is None or me.level != dest.level:
            return False
        if adjacent_ok:
            return _core.can_reach_entity(dest.x, dest.z)
        return _core.is_reachable(dest.x, dest.z)

    def can_step(self, a, b):
        """Whether one step from a to its neighbour b is open."""
        a = _tile(a)
        b = _tile(b)
        if a.level != b.level or max(abs(a.x - b.x), abs(a.z - b.z)) != 1:
            return False
        return _core.can_step(a.x, a.z, b.x, b.z)

    def line_of_sight(self, a, b, size=1):
        """Whether the server's sight ray from a reaches a body of size whose south-west tile is b."""
        a = _tile(a)
        b = _tile(b)
        if a.level != b.level:
            return False
        return _core.line_of_sight(a.x, a.z, b.x, b.z, size)

    def walkable(self, dest):
        """Whether dest is loaded and nothing stands on it."""
        dest = _tile(dest)
        me = game.tile()
        if me is None or me.level != dest.level:
            return False
        flags = _core.scene_flags(dest.x, dest.z)
        return flags is not None and (flags & SQ_BLOCKED) == 0

    def probeable(self, dest):
        """Whether dest is in the loaded area, on your level."""
        dest = _tile(dest)
        me = game.tile()
        return me is not None and me.level == dest.level and _core.scene_flags(dest.x, dest.z) is not None

    def flags(self, dest):
        """A loaded tile's collision flags, or None."""
        dest = _tile(dest)
        return _core.scene_flags(dest.x, dest.z)

    def arrival_probe(self):
        """What walkgeom.is_arrived asks."""
        return _ArrivalProbe(self)


class _ArrivalProbe:
    def __init__(self, reach):
        self._reach = reach

    def can_reach(self, tile):
        return self._reach.can_reach(tile)

    def walkable(self, tile):
        return self._reach.walkable(tile)

    def can_reach_adjacent(self, tile):
        return self._reach.can_reach(tile, True)

    def probeable(self, tile):
        return self._reach.probeable(tile)


reachability = Reachability()


class _Route:
    """A route the walker would plan: ok, reason, cost, expanded, and waypoints as Tiles."""

    def __init__(self, data):
        self.ok = bool(data.get('ok'))
        self.reason = data.get('reason')
        self.cost = data.get('cost')
        self.expanded = data.get('expanded', 0)
        self.waypoints = [Tile(w['x'], w['z'], w['level']) for w in data.get('waypoints', []) if isinstance(w, dict)]
        self.raw = data

    def __repr__(self):
        return f'Route(ok={self.ok}, cost={self.cost}, {len(self.waypoints)} waypoints)'


class Navigator:
    """rs2b0t's Navigator: the walker's route search, without walking."""

    def find_path(self, start, dest, avoid_doors=None, max_expansions=None, policy=None, use_teleport_catalog=None, avoid_zones=None, state=None):
        """The route from start to dest, as a Route. state is world_state()'s dict, the account's own by
        default, against which hops' requirements are checked."""
        from rs2004.traversal import world_state
        a = _tile(start)
        b = _tile(dest)
        request = {
            'from': [a.x, a.z, a.level],
            'to': [b.x, b.z, b.level],
            'avoid_doors': [[d.x, d.z] for d in [_tile(t) for t in (avoid_doors or [])]],
            'use_teleport_catalog': bool(use_teleport_catalog),
            'policy': policy or {},
            'state': state if state is not None else world_state(),
            'avoid_zones': avoid_zones or [],
        }
        if max_expansions is not None:
            request['max_expansions'] = max_expansions
        text = _core.find_world_path(json.dumps(request))
        if text is None:
            return _Route({'ok': False, 'reason': 'navigation unavailable: the client has no walker data'})
        return _Route(json.loads(text))


navigator = Navigator()


def _face_tile(door, face):
    dx, dz = FACES[face]
    return Tile(door.x + dx, door.z + dz, door.level)


def face_steps(door, can_step=None):
    """Which of a door tile's four faces can be stepped across now, west, north, east and south."""
    door = _tile(door)
    step = can_step if can_step is not None else reachability.can_step
    return [step(door, _face_tile(door, face)) for face in range(len(FACES))]


def opened_neighbour(door, before, after):
    """The neighbour across the face that opening swung free, or None while none has."""
    door = _tile(door)
    for face in range(len(FACES)):
        if after[face] and not before[face]:
            return _face_tile(door, face)
    return None


def far_side(door, across, here):
    """Of the two tiles a passage joins, the one you aren't on."""
    if here.x == door.x and here.z == door.z:
        return across
    if here.x == across.x and here.z == across.z:
        return door
    return across if walkgeom.chebyshev(here, across) >= walkgeom.chebyshev(here, door) else door


def is_openable_obstacle(name, actions, obstacles):
    """Named like one of obstacles (by part, in lower case), with an Open option."""
    lower = (name or '').lower()
    named = len([o for o in obstacles if o in lower]) > 0
    return named and open_op([a for a in actions if a is not None]) is not None


def _openable_near(obstacles, after, dest):
    def openable_in_range(loc):
        return is_openable_obstacle(loc.name, loc.actions(), obstacles) and loc.distance() <= ESCAPE_RADIUS and reachability.can_reach(loc.tile(), True)

    toward = locs.query().where(openable_in_range).where(lambda l: after is None or toward_dest(l.tile(), after, dest)).nearest()
    if toward is not None:
        return toward
    return locs.query().where(openable_in_range).nearest()


def _shut_at(tile, obstacles):
    return locs.query().where(lambda l: l.tile().x == tile.x and l.tile().z == tile.z and is_openable_obstacle(l.name, l.actions(), obstacles)).nearest()


def _step_through(door, before, step_ticks, say):
    seen = game.tick()
    found = []

    def opened():
        across = opened_neighbour(door, before, face_steps(door))
        if across is not None:
            found.append(across)
            return True
        return game.tick() > seen

    yield from execution.delay_until(opened, STEP_WAIT_MS)
    here = game.tile()
    if not found or here is None:
        return
    if step_ticks > 0:
        yield from execution.delay_ticks(step_ticks)
    far = far_side(door, found[0], here)
    direct_navigator.walk(far)
    crossed = yield from execution.delay_until(lambda: local_tile() == far, STEP_WAIT_MS)
    say(f'stepped through to {far.x},{far.z} ({"crossed" if crossed else "not crossed"})')


def walk_opening(dest, radius, obstacles, log=None, door_step_ticks=None):
    """Walks to dest, opening the obstacles named (by part: 'door', 'gate') that block the way: each walk that
    stops short opens the nearest one, toward dest if it can. With door_step_ticks, it waits that many ticks
    after a door opens and steps through. Use with yield from; True on arrival."""
    from rs2004.traversal import traversal
    dest = _tile(dest)
    say = log if log is not None else (lambda message: None)
    wanted = [o.strip().lower() for o in obstacles if o and o.strip()]
    probe = reachability.arrival_probe()
    for _ in range(SEGMENTS):
        here = game.tile()
        if here is not None and walkgeom.is_arrived(here, dest, radius, probe):
            return True
        yield from traversal.walk_to(dest, radius=radius, timeout_ms=SEGMENT_TIMEOUT_MS, log=lambda m: say(f'  {m}'))
        after = game.tile()
        if after is not None and walkgeom.is_arrived(after, dest, radius, probe):
            return True

        door = _openable_near(wanted, after, dest)
        if door is None:
            return False
        door_tile = door.tile()
        current = game.tile()
        if current is not None and door_tile.distance_to(current) > 1:
            say(f'walking to {door.name} at {door_tile.x},{door_tile.z} to open it')
            yield from traversal.walk_to(door_tile, radius=1, timeout_ms=DOOR_WALK_TIMEOUT_MS, log=lambda m: say(f'  {m}'))

        shut = _shut_at(door_tile, wanted)
        if shut is None:
            continue
        op = open_op([a for a in shut.actions() if a is not None])
        say(f'opening {shut.name} at {door_tile.x},{door_tile.z}')
        before = face_steps(door_tile)
        if not shut.interact(op):
            yield from execution.delay_ticks(2)
            continue
        swung = yield from execution.delay_until(lambda: _shut_at(door_tile, wanted) is None, OPEN_WAIT_MS)
        if swung and door_step_ticks is not None:
            yield from _step_through(door_tile, before, door_step_ticks, say)
    here = game.tile()
    return here is not None and walkgeom.is_arrived(here, dest, radius, probe)
