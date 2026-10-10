"""The walker's geometry: where you are on a route, what to click next, when to take a hop, when you've
arrived, and which areas to keep out of. Mirrors rs2b0t's event/webwalk/geometry/followMath.ts, arrival.ts,
pathExpand.ts, routeRecovery.ts and data/dangerZones.ts (MIT, see third_party/rs2b0t). Tiles are anything
with x, z and level.
"""

import _core

__all__ = []

INFINITY = 1000000000


def _sign(value):
    if value > 0:
        return 1
    return -1 if value < 0 else 0


def chebyshev(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


def same_tile(a, b):
    return a.x == b.x and a.z == b.z and a.level == b.level


def is_on_far_side(me, approach, step):
    return me is not None and me.level == step.level and chebyshev(me, step) < chebyshev(me, approach)


def locate_on_path(tiles, me, from_idx, window, corridor, limit_idx=None):
    """The furthest index in the window within corridor of me, on its level, or -1."""
    if limit_idx is None:
        limit_idx = len(tiles) - 1
    found = -1
    for i in range(from_idx, min(from_idx + window, len(tiles), limit_idx + 1)):
        if tiles[i].level == me.level and chebyshev(tiles[i], me) <= corridor:
            found = i
    return found


def select_click_target(tiles, path_idx, steps, limit_idx, level, is_clickable):
    """The furthest clickable tile ahead, by path index, at most steps on and no further than limit_idx."""
    top = min(path_idx + steps, limit_idx, len(tiles) - 1)
    for i in range(top, path_idx, -1):
        if tiles[i].level == level and is_clickable(tiles[i]):
            return i
    return -1


def select_client_walk_target(tiles, path_idx, steps, limit_idx, level, is_clickable, try_walk):
    """The same, far to near, taking the first whose walk the client accepts; try_walk(i) sends it."""
    top = min(path_idx + steps, limit_idx, len(tiles) - 1)
    for i in range(top, path_idx, -1):
        if tiles[i].level != level or not is_clickable(tiles[i]):
            continue
        if try_walk(i):
            return i
    return -1


def starved_terminal_index(tiles, me, is_clickable):
    """The route's end, when it's clickable and you're not on it, for when nothing else ahead is; else -1."""
    last = len(tiles) - 1
    if last < 0:
        return -1
    end = tiles[last]
    if end.level != me.level or (end.x == me.x and end.z == me.z):
        return -1
    return last if is_clickable(end) else -1


def crossing_eligible(me, approach, far, trigger, reachable):
    """Whether to take the hop: you're within trigger of its approach tile, on its level, and can reach it.
    Being near the far side, or another hop of the same kind, never counts."""
    if me.level != approach.level or chebyshev(me, approach) > trigger:
        return False
    return reachable(approach)


def min_chebyshev_to_path(tiles, me, from_idx, window, limit_idx=None):
    if limit_idx is None:
        limit_idx = len(tiles) - 1
    if not tiles:
        return INFINITY
    best = INFINITY
    for i in range(max(0, from_idx), min(len(tiles) - 1, limit_idx, from_idx + window) + 1):
        if tiles[i].level == me.level:
            best = min(best, chebyshev(me, tiles[i]))
    return best


def choose_cross_click(can_step_edge, can_reach_landing):
    if can_step_edge:
        return 'step'
    return 'landing-click' if can_reach_landing else 'landing-scene'


def should_approach_closed_barrier(me, approach, closed):
    return closed and me is not None and not same_tile(me, approach)


def walk_chebyshev(a, b):
    """Chebyshev on one level; another level is never close."""
    distance = chebyshev(a, b)
    return distance if a.level == b.level else 1000000 + distance


def is_arrived(me, dest, radius, probe):
    """Within radius of dest on its level, and able to reach it, or, when it can't be stood on (a booth or
    a furnace), beside it. probe has can_reach(t), walkable(t), can_reach_adjacent(t) and probeable(t)."""
    if me.level != dest.level:
        return False
    distance = chebyshev(me, dest)
    if distance > radius:
        return False
    if distance == 0 or probe.can_reach(dest):
        return True
    if probe.walkable(dest):
        return False
    return not probe.probeable(dest) or probe.can_reach_adjacent(dest)


def find_forward_recovery_index(tiles, me, from_idx, is_clickable, corridor=3, window=40, limit_idx=None):
    """On a stall: the furthest clickable tile ahead on your level, else the furthest within corridor of you,
    else -1."""
    if not tiles:
        return -1
    if limit_idx is None:
        limit_idx = len(tiles) - 1
    limit_idx = min(limit_idx, len(tiles) - 1)
    best_clickable = -1
    best_on_corridor = -1
    for i in range(from_idx + 1, min(from_idx + window, limit_idx) + 1):
        tile = tiles[i]
        if tile.level != me.level or (tile.x == me.x and tile.z == me.z):
            continue
        if chebyshev(me, tile) <= corridor:
            best_on_corridor = i
        if is_clickable(tile):
            best_clickable = i
    return best_clickable if best_clickable != -1 else best_on_corridor


def stall_phase(stall_retries, recover_idx, in_combat):
    """'recover' with a tile to click ahead the first time, 'combat' while fighting, else 'escalate'."""
    if stall_retries == 0 and recover_idx != -1:
        return 'recover'
    return 'combat' if in_combat else 'escalate'


class PathTile:
    """One tile of a route: x, z, level, and transport, the hop that arrives here, or None."""

    def __init__(self, x, z, level, transport=None):
        self.x = x
        self.z = z
        self.level = level
        self.transport = transport

    def __repr__(self):
        hop = f', {self.transport["action"]} {self.transport["loc_name"]}' if self.transport else ''
        return f'PathTile({self.x}, {self.z}, {self.level}{hop})'


def expand_waypoints(waypoints):
    """Every tile of a route from its waypoints: straight and diagonal steps between them, and each hop's
    tile as it is, so path progress can be tracked tile by tile."""
    if not waypoints:
        return []
    first = waypoints[0]
    tiles = [PathTile(first.x, first.z, first.level, first.transport)]
    for i in range(1, len(waypoints)):
        prev = tiles[-1]
        point = waypoints[i]
        if point.transport is not None or point.level != prev.level:
            tiles.append(PathTile(point.x, point.z, point.level, point.transport))
            continue
        dx = _sign(point.x - prev.x)
        dz = _sign(point.z - prev.z)
        steps = max(abs(point.x - prev.x), abs(point.z - prev.z))
        for step in range(1, steps + 1):
            tiles.append(PathTile(prev.x + dx * step, prev.z + dz * step, point.level))
    return tiles


# Danger zones: areas a route keeps out of.

_known_zones = None


def known_danger_zones():
    """The catalog: dicts of id, label, rects (min_x, max_x, min_z, max_z, level), and optionally automatic,
    avoid_at_or_below_combat and allow_when_endpoint_inside."""
    global _known_zones
    if _known_zones is None:
        import json
        text = _core.nav_data('danger_zones')
        _known_zones = [_zone_from_json(zone) for zone in json.loads(text)] if text is not None else []
    return _known_zones


def _rect_from_json(rect):
    return {'min_x': rect['minX'], 'max_x': rect['maxX'], 'min_z': rect['minZ'], 'max_z': rect['maxZ'], 'level': rect.get('level')}


def _zone_from_json(zone):
    return {
        'id': zone['id'],
        'label': zone.get('label'),
        'rects': [_rect_from_json(rect) for rect in zone['rects']],
        'automatic': zone.get('automatic', False),
        'avoid_at_or_below_combat': zone.get('avoidAtOrBelowCombat'),
        'allow_when_endpoint_inside': zone.get('allowWhenEndpointInside', False),
    }


def tile_in_danger_zones(x, z, level, zones):
    """Whether the tile is in any of the rects, bounds included; a rect without a level is on all of them."""
    if not zones:
        return False
    for rect in zones:
        if rect.get('level') is not None and rect['level'] != level:
            continue
        if rect['min_x'] <= x and x <= rect['max_x'] and rect['min_z'] <= z and z <= rect['max_z']:
            return True
    return False


def resolve_danger_zones(specs, include_automatic=False, combat_level=None, start=None, destination=None, known=None):
    """The rects of the zone ids and rects given, plus the automatic zones when include_automatic. A zone
    for low levels is left out above its combat level, and one that allows it is left out when the route
    starts or ends inside it. Unknown ids are skipped."""
    catalog = known if known is not None else known_danger_zones()
    by_id = {zone['id']: zone for zone in catalog}
    requested = list(specs or [])
    if include_automatic:
        requested.extend([zone['id'] for zone in catalog if zone.get('automatic')])
    rects = []
    seen = []
    for spec in requested:
        if not isinstance(spec, str):
            rects.append(spec)
            continue
        if spec in seen:
            continue
        seen.append(spec)
        zone = by_id.get(spec)
        if zone is None:
            continue
        limit = zone.get('avoid_at_or_below_combat')
        if limit is not None and combat_level is not None and combat_level > limit:
            continue
        if zone.get('allow_when_endpoint_inside'):
            inside = False
            for end in (start, destination):
                if end is not None and tile_in_danger_zones(end.x, end.z, end.level, zone['rects']):
                    inside = True
            if inside:
                continue
        rects.extend(zone['rects'])
    return rects


# rs2b0t's escalation ladder (event/webwalk/walkLadder.ts) for walk_resilient: a world route, then a walk in
# the loaded area, then an unstick step, then a backoff; after three passes without progress it checks
# whether the goal is reachable at all.

UNREACHABLE_PASSES = 3
BACKOFF_MIN = 2
BACKOFF_MAX = 16


class LadderState:
    def __init__(self, best_dist, no_progress_passes=0, phase='world', tried_big_budget=False):
        self.best_dist = best_dist
        self.no_progress_passes = no_progress_passes
        self.phase = phase
        self.tried_big_budget = tried_big_budget

    def __repr__(self):
        return f'LadderState({self.best_dist}, {self.no_progress_passes}, {repr(self.phase)}, {self.tried_big_budget})'


def backoff_ticks(no_progress_passes):
    return min(BACKOFF_MAX, BACKOFF_MIN + 2 * max(0, no_progress_passes - 1))


def classify_reason(reason):
    """'budget' when a search ran out of its budget, else 'failed'."""
    return 'budget' if 'budget' in reason.lower() else 'failed'


def advance(state, cur_dist, within_radius, interrupted, last_outcome):
    """The next rung and the new state: ('world', big_budget), ('scene',), ('unstick',), ('backoff', ticks),
    ('verify',), ('unreachable',), ('arrived',) or ('interrupted',)."""
    if interrupted or last_outcome == 'interrupted':
        return ('interrupted',), state
    if within_radius:
        return ('arrived',), state
    progressed = cur_dist < state.best_dist
    best = min(state.best_dist, cur_dist)
    if progressed:
        return ('world', False), LadderState(best)
    if last_outcome is None:
        return ('world', False), LadderState(best, state.no_progress_passes)
    if state.phase == 'verify':
        if last_outcome == 'probe-dead':
            return ('unreachable',), state
        return ('backoff', backoff_ticks(1)), LadderState(best)
    if state.phase == 'world':
        if last_outcome == 'budget' and not state.tried_big_budget:
            return ('world', True), LadderState(best, state.no_progress_passes, 'world', True)
        return ('scene',), LadderState(best, state.no_progress_passes, 'scene', state.tried_big_budget)
    if state.phase == 'scene':
        return ('unstick',), LadderState(best, state.no_progress_passes, 'unstick', state.tried_big_budget)
    passes = state.no_progress_passes + 1
    if passes >= UNREACHABLE_PASSES:
        return ('verify',), LadderState(best, passes, 'verify', state.tried_big_budget)
    return ('backoff', backoff_ticks(passes)), LadderState(best, passes)


UNSTICK_STEPS = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]


def pick_unstick_step(can_step, start_dir):
    """The first open step round the compass from start_dir, as (dx, dz), or None."""
    for i in range(len(UNSTICK_STEPS)):
        dx, dz = UNSTICK_STEPS[(start_dir + i) % len(UNSTICK_STEPS)]
        if can_step(dx, dz):
            return (dx, dz)
    return None
