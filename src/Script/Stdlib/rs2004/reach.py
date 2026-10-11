"""The last mile: walk to a stand, then use a loc, an NPC or anything else, and when the server says it can't
reach it, open the door in the way (or close the open one swung across it) and try again. Mirrors rs2b0t's
api/walking/Reach.ts (MIT, see thirdparty/rs2b0t).

    status = yield from reach.loc_op('Bank booth', 'Use-quickly', Tile(3253, 3420, 0), lambda: bank.is_open())
    if status == 'unreachable':
        ...

Each gives 'done' when expect() held, 'retry' when it didn't yet, and 'unreachable' when the stand or the
target can't be reached and no door in front explains it. For a loc, the server's "I can't reach that!"
decides; for an NPC, which can wander and so put the server's verdict off for good, the scene is searched
within PROBE_RADIUS tiles first.
"""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import local_tile, locs, npcs
from rs2004.game import direct_navigator
from rs2004.geometry import Tile
from rs2004.messages import CANT_REACH, game_messages

__all__ = ['reach', 'is_openable_barrier', 'is_open_barrier_leaf', 'open_op', 'close_op', 'talk_op', 'toward_dest']

REACH_DOOR_ATTEMPTS = 8
# Within this many tiles, a failed search of the scene means blocked rather than out of range.
PROBE_RADIUS = 10
LEAF_CLOSE_RADIUS = 3
DOOR_RADIUS = 6
TOWARD_SLACK = 4
LOC_SCENE_MS = 3000
DOOR_OPEN_MS = 5000
STAND_TIMEOUT_MS = 90000
DOOR_WALK_TIMEOUT_MS = 30000


def _first_starting(actions, prefix):
    for action in actions:
        if action.lower().startswith(prefix):
            return action
    return None


def open_op(actions):
    return _first_starting(actions, 'open')


def close_op(actions):
    return _first_starting(actions, 'close')


def talk_op(actions):
    return _first_starting(actions, 'talk')


def _is_barrier(name):
    lower = (name or '').lower()
    return 'door' in lower or 'gate' in lower


def is_openable_barrier(name, actions):
    """A shut door or gate: named so, with an Open option."""
    return _is_barrier(name) and open_op([a for a in actions if a is not None]) is not None


def is_open_barrier_leaf(name, actions):
    """An open door or gate: named so, with a Close option."""
    return _is_barrier(name) and close_op([a for a in actions if a is not None]) is not None


def toward_dest(door, here, dest):
    """The door is no further from dest than you are, give or take a few tiles."""
    return door.distance_to(dest) <= here.distance_to(dest) + TOWARD_SLACK


def _same_level(a, b):
    return a.level == b.level


def _can_reach(tile, adjacent=False):
    """A walk reaches the tile, or one beside it, from where you are."""
    here = local_tile()
    if not _same_level(here, tile):
        return False
    if adjacent:
        return _core.can_reach_entity(tile.x, tile.z)
    return _core.is_reachable(tile.x, tile.z)


def _door_approachable(door):
    """A wall door blocks the step onto its own tile, and it's used from either side, so any tile on or beside
    it will do."""
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            if _can_reach(Tile(door.x + dx, door.z + dz, door.level)):
                return True
    return False


def _wall_barrier(loc, test):
    """A door or gate in the wall layer. rs2b0t's name test alone also takes a trapdoor for a door."""
    return loc.layer == LAYER_WALL and test(loc.name, loc.actions())


def _barrier_at(tile, test):
    return locs.query().where(lambda l: l.tile() == tile and _wall_barrier(l, test)).nearest()


def _walk(dest, radius, timeout_ms):
    arrived = yield from direct_navigator.walk_to(dest, radius, timeout_ms)
    return arrived


def _close_in(near, radius, say):
    arrived = yield from _walk(near, radius, STAND_TIMEOUT_MS)
    if not arrived and direct_navigator.last_outcome == 'unreachable':
        say(f'reach: {near} is unreachable')
        return 'unreachable'
    return 'retry'


def _open_blocking_door(toward, say):
    here = local_tile()
    door = locs.query().where(lambda l: _wall_barrier(l, is_openable_barrier) and l.distance() <= DOOR_RADIUS and toward_dest(l.tile(), here, toward) and _door_approachable(l.tile())).nearest()
    if door is None:
        return False
    tile = door.tile()
    if here.distance_to(tile) > 1:
        yield from _walk(tile, 1, DOOR_WALK_TIMEOUT_MS)
    shut = _barrier_at(tile, is_openable_barrier)
    if shut is None:
        return True
    op = open_op(shut.actions())
    if op is None:
        return False
    say(f"reach: opening the blocking {shut.name} at {tile}")
    if not shut.interact(op):
        return False
    opened = yield from execution.delay_until(lambda: _barrier_at(tile, is_openable_barrier) is None, DOOR_OPEN_MS)
    return opened


def _close_swung_leaf(toward, say):
    """Closes an open door whose leaf stands across the way to toward."""
    here = local_tile()
    if not _same_level(here, toward) or _can_reach(toward, True):
        return False
    leaf = locs.query().where(lambda l: _wall_barrier(l, is_open_barrier_leaf) and l.distance() <= LEAF_CLOSE_RADIUS and l.tile().distance_to(toward) <= 1 and not _core.can_step(l.tile().x, l.tile().z, toward.x, toward.z)).nearest()
    op = close_op(leaf.actions()) if leaf is not None else None
    if op is None:
        return False
    say(f"reach: closing the {leaf.name} at {leaf.tile()} to reach {toward}")
    if not leaf.interact(op):
        return False
    closed = yield from execution.delay_until(lambda: _can_reach(toward, True), DOOR_OPEN_MS)
    return closed


def _clear_blocking_door(toward, say):
    closed = yield from _close_swung_leaf(toward, say)
    if closed:
        return True
    opened = yield from _open_blocking_door(toward, say)
    return opened


def _saw(mark, pattern):
    return pattern is not None and game_messages.saw_since(mark, pattern)


def _through_doors(attempt, expect, expect_ms, target_tile, what, say, retry_after_timeout=True, probe_unreachable=False, refused=None):
    for i in range(REACH_DOOR_ATTEMPTS):
        # The server says it can't reach something only once its own search gives up, which a target that
        # keeps moving can put off for ever; for those, search the scene first.
        if probe_unreachable and not expect():
            blocked = target_tile()
            here = local_tile()
            if blocked is not None and _same_level(here, blocked) and here.distance_to(blocked) <= PROBE_RADIUS and not _can_reach(blocked, True):
                cleared = yield from _clear_blocking_door(blocked, say)
                if cleared:
                    continue
        mark = game_messages.mark()
        dispatched = attempt()
        if dispatched:
            yield from execution.delay_until(lambda: expect() or _saw(mark, CANT_REACH) or _saw(mark, refused), expect_ms)
            if expect():
                return 'done'
            if _saw(mark, refused):
                say(f'reach: {what} refused the op; not retrying')
                return 'retry'
            if _saw(mark, CANT_REACH):
                toward = target_tile()
                cleared = False
                if toward is not None:
                    cleared = yield from _clear_blocking_door(toward, say)
                if not cleared:
                    say(f"reach: {what} at {toward}: the server can't reach it and there's no door in front to open or close")
                    return 'unreachable'
                continue
        if not retry_after_timeout:
            if not dispatched:
                yield from execution.delay_ticks(1)
            return 'retry'
        yield from execution.delay_ticks(1)
    return 'retry'


def _logger(log):
    return log if log is not None else (lambda message: None)


def _scene_settled(find, near, within):
    """A teleport or level change empties the scene for a few ticks, so a loc that's missing while you stand
    among it is asked for again before it counts as absent."""
    here = local_tile()
    if not _same_level(here, near) or here.distance_to(near) > within:
        return False
    found = yield from execution.delay_until(lambda: find() is not None, LOC_SCENE_MS)
    return found


class _Reach:
    """Walk, use, and open the door in the way. Each is a generator, used with yield from."""

    def entity_op(self, find, op, expect, open_when_unreachable=False, expect_ms=5000, what=None, log=None):
        """Uses op on whatever find() gives (an Npc, Loc, GroundItem or Player, or None), until expect().
        With open_when_unreachable, searches the scene for a door in the way rather than waiting for the
        server's verdict."""
        def attempt():
            if expect():
                return True
            entity = find()
            return entity is not None and entity.interact(op)

        def target_tile():
            entity = find()
            return entity.tile() if entity is not None else None

        status = yield from _through_doors(attempt, expect, expect_ms, target_tile, what or op, _logger(log), False, open_when_unreachable)
        return status

    def loc_op(self, name, op, near, expect, within=10, id=None, expect_ms=12000, refused=None, log=None):
        """Walks to near, then uses op on the nearest loc named name with that option within within tiles (of
        id, when the name is shared), until expect(). refused is a game message, text or a callable, that
        says the op can't run yet, so it isn't retried."""
        say = _logger(log)

        def find():
            # pocketpy's lambda can't read loc_op's id from here, so it gets a copy.
            wanted = id
            return locs.query().name(name).action(op).within(within).where(lambda l: wanted is None or l.id == wanted).nearest()

        if find() is None:
            settled = yield from _scene_settled(find, near, within)
            if not settled:
                status = yield from _close_in(near, 2, say)
                return status
        arrived = yield from _walk(near, 1, STAND_TIMEOUT_MS)
        if not arrived and direct_navigator.last_outcome == 'unreachable':
            say(f'reach: the stand {near} is unreachable')
            return 'unreachable'

        def attempt():
            loc = find()
            return loc is not None and loc.interact(op)

        def target_tile():
            loc = find()
            return loc.tile() if loc is not None else None

        status = yield from _through_doors(attempt, expect, expect_ms, target_tile, name, say, True, False, refused)
        return status

    def npc_dialog(self, name, near, open_ms=15000, log=None):
        """Walks to near and talks to the NPC until a dialogue opens."""
        say = _logger(log)
        if chat_dialog.is_open():
            current = npcs.query().name(name).nearest()
            if current is not None and current.distance() <= 1:
                return 'done'
            return 'retry'

        def find():
            return npcs.query().name(name).where(lambda n: talk_op(n.actions()) is not None).nearest()

        if find() is None:
            status = yield from _close_in(near, 3, say)
            return status
        arrived = yield from _walk(near, 1, STAND_TIMEOUT_MS)
        if not arrived and direct_navigator.last_outcome == 'unreachable':
            say(f'reach: the stand {near} is unreachable')
            return 'unreachable'

        def attempt():
            npc = find()
            return npc is not None and npc.interact(talk_op(npc.actions()) or 'Talk-to')

        def target_tile():
            npc = find()
            return npc.tile() if npc is not None else None

        status = yield from _through_doors(attempt, lambda: chat_dialog.is_open() or chat_dialog.can_continue(), open_ms, target_tile, name, say, True, True)
        return status


reach = _Reach()
