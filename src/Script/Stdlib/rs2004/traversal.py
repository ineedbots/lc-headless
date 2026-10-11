"""Walking across the world: routes beyond the loaded area, through doors, up and down stairs and ladders,
over tolls and onto ships. Mirrors rs2b0t's api/walking/Traversal.ts and event/webwalk/WalkExecutor.ts, with
its exec/ crossings (MIT, see thirdparty/rs2b0t).

    arrived = yield from traversal.walk_resilient(Tile(3253, 3420, 0), 2)

The route comes from the core's search over the whole map (WorldPathFinder, with rs2b0t's walker graph);
the walker then follows it as rs2b0t's does. It finds itself on the route, clicks the furthest tile ahead the
client can walk to, takes each hop when it reaches the tile before it, and plans again when the world
disagrees: a refused door, a stall, or a step off the route.
"""

import json
import random

import _core
from rs2004 import execution
from rs2004 import walkgeom
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import local_tile, locs, npcs
from rs2004.events import SKILL_NAMES
from rs2004.game import direct_navigator, game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import CANT_REACH, game_messages
from rs2004.reach import close_op, is_open_barrier_leaf, is_openable_barrier, open_op
from rs2004.tabs import quests

__all__ = ['traversal', 'NAV_PURE_WALK', 'NAV_WITH_TELES', 'world_state', 'special_crossing_for_transport', 'pick_choice', 'nearest_bank', 'nearest_banks', 'nearest_reachable_bank', 'bank_unlocked', 'bank_locations']

# Passed with ** to walk_to or walk_resilient, to walk without teleports or with them.
NAV_PURE_WALK = {'use_teleport_catalog': False, 'policy': {'use_teleports': False}}
NAV_WITH_TELES = {'use_teleport_catalog': True, 'policy': {'use_teleports': True}}

TARGET_STEPS = 20
TARGET_JITTER = 4
ARRIVE_RADIUS = 4
PROGRESS_WINDOW = 26
CORRIDOR = 3
MAX_REPATHS = 5
MIN_FOLLOW_REMAINING_MS = 3000
TRANSPORT_WAIT_MS = 8000
SCENE_REBUILD_MS = 3000
CANDIDATE_SETTLE_TRIES = 3
APPROACH_STEP_MS = 4000
STALL_TICKS = 5
DEVIATION = 10
APPROACH_TRIGGER = 4
UNREACH_CLICK_IDLE_TICKS = 3
DIALOGUE_STEPS = 24
SHIP_DIALOGUE_STEPS = 40
DOOR_CROSS_MS = 12000
DOOR_STRIKES = 2
LANDING_TOLERANCE = 3
DEFAULT_TIMEOUT_MS = 300000
DEFAULT_MAX_BUDGET = 1200000
SCENE_TIMEOUT_MS = 6000
QUEST_STATUSES = {'not_started': 'not_started', 'in_progress': 'started', 'complete': 'complete'}


def _load(name):
    text = _core.nav_data(name)
    return json.loads(text) if text is not None else []


_crossings = None
_banks = None


def crossings():
    """rs2b0t's special crossings: tolls, ships, keyed doors and the rest, as dicts in its camelCase."""
    global _crossings
    if _crossings is None:
        _crossings = _load('crossings')
    return _crossings


def bank_locations():
    """rs2b0t's banks: dicts of name, tile (x, z, level), and how to open each when it isn't a booth."""
    global _banks
    if _banks is None:
        _banks = _load('banks')
    return _banks


def bank_unlocked(bank, settings=None):
    """Whether the account can use the bank: its skill level and quest, and, for a bank a script opts into
    (Zanaris, the Mage Arena), the setting named in settings, a dict of booleans."""
    needs = bank.get('requires')
    if not needs:
        return True
    skill = needs.get('skill')
    if skill is not None and skills.level(skill['name']) < skill['level']:
        return False
    if needs.get('quest') is not None and quests.status(needs['quest']) != 'complete':
        return False
    if needs.get('setting') is not None and not (settings or {}).get(needs['setting'], False):
        return False
    return True


def _bank_stand(bank):
    stand = bank.get('approach') or bank['tile']
    return Tile(stand['x'], stand['z'], stand['level'])


def nearest_banks(tile, settings=None):
    """The banks the account can use, nearest first, by straight-line distance whatever the level, as
    rs2b0t ranks them."""
    usable = [bank for bank in bank_locations() if bank_unlocked(bank, settings)]
    usable.sort(key=lambda bank: (_bank_stand(bank).x - tile.x) ** 2 + (_bank_stand(bank).z - tile.z) ** 2)
    return usable


def nearest_bank(tile, settings=None):
    """The nearest bank the account can use, or None."""
    banks = nearest_banks(tile, settings)
    return banks[0] if banks else None


def nearest_reachable_bank(tile, candidates=4, settings=None):
    """Of the few nearest banks, the one the shortest route reaches, as rs2b0t's nearestBankReachable picks,
    since in a dungeon or on an island the straight line misleads. None when none is reachable."""
    best = None
    best_cost = None
    for bank in nearest_banks(tile, settings)[:candidates]:
        stand = Tile(bank['tile']['x'], bank['tile']['z'], bank['tile']['level'])
        path = traversal._request(tile, stand, None, {'use_teleports': False}, False, [])
        if path['ok'] and (best_cost is None or path['cost'] < best_cost):
            best = bank
            best_cost = path['cost']
    return best


def pick_choice(options, choose):
    """The first option containing any of the wanted texts, without regard to case."""
    wanted = [c.lower() for c in choose]
    for option in options:
        lower = option.lower()
        for want in wanted:
            if want in lower:
                return option
    return None


def _counts(items):
    counts = {}
    for item in items:
        if item.name is None:
            continue
        counts[item.name] = counts.get(item.name, 0) + max(1, item.count)
    return counts


def world_state():
    """What the account has, for the route's requirements: rs2b0t's WorldState."""
    levels = {}
    for index, name in SKILL_NAMES.items():
        levels[name] = _core.get_max_stat(index)
    statuses = {}
    for quest in quests.all():
        statuses[quest.name] = QUEST_STATUSES.get(quest.status, 'unknown')
    return {
        'members': _core.is_members(),
        'skills': levels,
        'items': _counts(inventory.items()),
        'worn': _counts(equipment.items()),
        'quests': statuses,
        'free_slots': inventory.free(),
    }


class _Probe:
    """Arrival's questions about the area you're in."""

    def can_reach(self, tile):
        return tile.level == _core.get_level() and _core.is_reachable(tile.x, tile.z)

    def walkable(self, tile):
        found = _core.walk_tile(tile.x, tile.z, tile.level)
        if found is not None:
            return found[0] == 1
        return _core.is_reachable(tile.x, tile.z)

    def can_reach_adjacent(self, tile):
        return tile.level == _core.get_level() and _core.can_reach_entity(tile.x, tile.z)

    def probeable(self, tile):
        return tile.level == _core.get_level() and _core.in_scene(tile.x, tile.z)


_probe = _Probe()


def _arrived(dest, radius):
    return walkgeom.is_arrived(local_tile(), dest, radius, _probe)


def _clickable(tile):
    return tile.level == _core.get_level() and _core.in_scene(tile.x, tile.z) and _core.is_reachable(tile.x, tile.z)


def _approachable(tile):
    return tile.level == _core.get_level() and _core.can_reach_entity(tile.x, tile.z)


def _can_step(a, b):
    return a.level == b.level and a.level == _core.get_level() and _core.can_step(a.x, a.z, b.x, b.z)


def _same(a, b):
    return a.x == b.x and a.z == b.z and a.level == b.level


def _near(tile, x, z, radius):
    return max(abs(tile.x - x), abs(tile.z - z)) <= radius


# Transport locs.

def _name_aliases(name):
    names = [name]
    if name.lower() == 'staircase':
        names.append('Stairs')
    elif name.lower() == 'stairs':
        names.append('Staircase')
    return names


def _ids_of(transport):
    ids = []
    for key in ('loc_id', 'open_loc_id'):
        if transport.get(key) is not None:
            ids.append(transport[key])
    return ids


def find_transport_loc(transport):
    """The loc that makes the hop: by its name, option and placement, else by name and option near the
    placement, else any stairs there. None when an open leaf shows the door is open already."""
    names = _name_aliases(transport['loc_name'])
    action = transport['action']
    x = transport['loc_x']
    z = transport['loc_z']
    ids = _ids_of(transport)
    exact = locs.query().name(names).action(action).where(lambda l: _near(l.tile(), x, z, 1) and (not ids or l.id in ids)).nearest()
    if exact is not None:
        return exact
    near = locs.query().name(names).action(action).where(lambda l: _near(l.tile(), x, z, 5)).nearest()
    if near is not None:
        return near
    if 'climb' in action.lower() and 'stair' in transport['loc_name'].lower():
        stairs = locs.query().action(action).where(lambda l: _near(l.tile(), x, z, 2) and 'stair' in (l.name or '').lower()).nearest()
        if stairs is not None:
            return stairs
    return None


def _open_leaf_near(transport):
    x = transport['loc_x']
    z = transport['loc_z']
    return locs.query().name(transport['loc_name']).where(lambda l: _near(l.tile(), x, z, 3) and close_op(l.actions()) is not None).nearest()


def matches_landing(transport, expected_level, before, current):
    """Whether a hop that lands on a tile has: on its level within a few tiles of its landing, and, for a
    short hop, on it exactly. A hop that lands anywhere counts once the level or the area changes."""
    if current is None:
        return False
    to_tile = transport.get('to_tile')
    if to_tile is not None and current.level == expected_level and _near(current, to_tile[0], to_tile[1], LANDING_TOLERANCE):
        if before is None or current.level != before.level:
            return True
        landing = Tile(to_tile[0], to_tile[1], expected_level)
        span = walkgeom.chebyshev(before, landing)
        if span <= LANDING_TOLERANCE:
            return walkgeom.chebyshev(current, landing) == 0
        return walkgeom.chebyshev(current, landing) < walkgeom.chebyshev(current, before)
    if transport.get('accept_any_landing') and before is not None:
        return current.level != before.level or walkgeom.chebyshev(current, before) > 64
    return False


# Special crossings.

def _to_tile_matches(crossing, step):
    to = crossing.get('toTile')
    if to is None:
        return True
    return to['x'] == step.x and to['z'] == step.z and (to.get('level') is None or to['level'] == step.level)


def special_crossing_for_transport(transport, approach, step):
    """The special crossing a hop makes, keyed at the tile it leaves, its loc, or the tile it reaches, on
    either level; ones whose landing isn't the hop's are left out. Mirrors rs2b0t's lookup."""
    levels = [approach.level]
    if step is not None and step.level not in levels:
        levels.append(step.level)
    candidates = []
    ranks = []
    for level in levels:
        for crossing in crossings():
            if crossing['level'] != level:
                continue
            rank = None
            if crossing['x'] == approach.x and crossing['z'] == approach.z:
                rank = 0
            elif crossing['x'] == transport['loc_x'] and crossing['z'] == transport['loc_z']:
                rank = 1
            elif step is not None and crossing['x'] == step.x and crossing['z'] == step.z:
                rank = 2
            if rank is None:
                continue
            if crossing in candidates:
                i = candidates.index(crossing)
                ranks[i] = min(ranks[i], rank)
            else:
                candidates.append(crossing)
                ranks.append(rank)
    if not candidates:
        return None
    name = (transport.get('loc_name') or '').lower()
    if name:
        named = [i for i in range(len(candidates)) if candidates[i]['locName'].lower() == name or (candidates[i].get('npc') or '').lower() == name]
        if named:
            candidates = [candidates[i] for i in named]
            ranks = [ranks[i] for i in named]
    if step is not None:
        landing = [i for i in range(len(candidates)) if _to_tile_matches(candidates[i], step)]
        if landing:
            candidates = [candidates[i] for i in landing]
            ranks = [ranks[i] for i in landing]
        elif len([c for c in candidates if c.get('toTile') is not None]) > 0:
            return None
        if len(candidates) > 1:
            for crossing in candidates:
                if crossing.get('toTile') is not None and _to_tile_matches(crossing, step):
                    return crossing
    best = 0
    for i in range(1, len(candidates)):
        if ranks[i] < ranks[best]:
            best = i
    return candidates[best]


def _near_landing(crossing, radius):
    to = crossing.get('toTile')
    if to is None:
        return False
    here = local_tile()
    return here.level == to.get('level', here.level) and _near(here, to['x'], to['z'], radius)


class _Traversal:
    """Walking across the world. last_outcome says how the last walk ended: 'arrived', 'closest' (as near as
    the route goes), 'blocked', 'budget', 'failed', 'unreachable' or 'interrupted'. remaining is how many
    route tiles were left. Each walk is a generator, used with yield from."""

    remaining = 0
    last_outcome = None
    last_reason = None
    _force_repath = False

    def __init__(self):
        self._avoid_doors = []
        self._door_strikes = {}
        self._suppressed_teleports = []

    def teleports_enabled(self):
        """Whether walks use teleports unless told otherwise: off, as rs2b0t's default is."""
        return False

    def request_repath(self, reason=None):
        """Plans the walk in progress again at its next step."""
        self._force_repath = True

    def _request(self, me, dest, max_expansions, policy, use_teleports, zones):
        request = {
            'from': [me.x, me.z, me.level],
            'to': [dest.x, dest.z, dest.level],
            'avoid_doors': self._avoid_doors,
            'use_teleport_catalog': use_teleports,
            'policy': policy,
            'state': world_state(),
            'avoid_zones': zones,
        }
        if max_expansions is not None:
            request['max_expansions'] = max_expansions
        text = _core.find_world_path(json.dumps(request))
        if text is None:
            return {'ok': False, 'reason': 'navigation unavailable: the client has no walker data'}
        return json.loads(text)

    def route_cost(self, start, dest, max_expansions=300000):
        """The cost of the route the walker would plan from start to dest, without teleports, or None when it
        finds none, as for a camp past a gate this account can't open. The budget keeps a search for a route
        that doesn't exist to a fraction of a second in a Release build."""
        path = self._request(Tile.from_tile(start), Tile.from_tile(dest), max_expansions, {'use_teleports': False}, False, [])
        return path['cost'] if path['ok'] else None

    def walk_to(self, dest, radius=2, timeout_ms=None, max_expansions=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None, force_repath=False):
        """Walks to within radius of dest, anywhere on the map. True on arrival, or when the route ends as
        close as it can get (last_outcome 'closest' or 'blocked')."""
        say = log if log is not None else (lambda message: None)
        dest = Tile.from_tile(dest) if not isinstance(dest, Tile) else dest
        timeout = DEFAULT_TIMEOUT_MS if timeout_ms is None else timeout_ms
        use_teleports = self.teleports_enabled() if use_teleport_catalog is None else use_teleport_catalog
        walk_policy = {'use_teleports': use_teleports, 'deny_teleport_ids': list(self._suppressed_teleports)}
        if policy is not None:
            for key, value in policy.items():
                walk_policy[key] = value
        if walk_policy.get('use_teleports') is False:
            use_teleports = False
        start = local_tile()
        zones = walkgeom.resolve_danger_zones(avoid_zones, True, game.combat_level(), start, dest)
        if force_repath:
            self._force_repath = True
        self.last_outcome = None
        self.last_reason = None
        self._avoid_doors = []
        deadline = _core.step_time() + timeout
        settle = [CANDIDATE_SETTLE_TRIES]
        for repaths in range(MAX_REPATHS + 1):
            me = local_tile()
            if _arrived(dest, radius):
                self.last_outcome = 'arrived'
                return True
            path = self._request(me, dest, max_expansions, walk_policy, use_teleports, zones)
            if not path['ok']:
                self.last_reason = path['reason']
                say(f'no path to {dest}: {path["reason"]}')
                self.last_outcome = walkgeom.classify_reason(path['reason'])
                return False
            waypoints = [walkgeom.PathTile(w['x'], w['z'], w['level'], w.get('transport')) for w in path['waypoints']]
            hops = [f'{w.transport["action"]} {w.transport["loc_name"]}' for w in waypoints if w.transport is not None]
            say(f'path: cost {path["cost"]}, {len(waypoints)} waypoints, {path["expanded"]} expanded, hops {hops}' + (f' (repath {repaths})' if repaths > 0 else ''))
            tiles = walkgeom.expand_waypoints(waypoints)
            terminal = tiles[-1]
            if _same(me, terminal):
                self.last_outcome = 'arrived' if _arrived(dest, radius) else 'closest'
                return True
            if deadline - _core.step_time() < MIN_FOLLOW_REMAINING_MS:
                say(f'walk timed out after {timeout} ms')
                self.last_outcome = 'failed'
                return False
            result = yield from self._follow(tiles, dest, radius, deadline, say, settle)
            if result == 'arrived' or result == 'closest' or result == 'blocked':
                self.last_outcome = result
                return True
            if result == 'failed':
                say(f'walk timed out after {timeout} ms')
                self.last_outcome = 'failed'
                return False
            if result == 'interrupted':
                self.last_outcome = 'interrupted'
                return False
        say(f'giving up after {MAX_REPATHS} repaths')
        self.last_outcome = 'failed'
        return False

    def _follow(self, tiles, dest, radius, deadline, say, settle):
        """Follows one route: 'arrived', 'closest', 'blocked', 'repath', 'failed' or 'interrupted'."""
        path_idx = 0
        click_idx = -1
        clicks = 0
        stall_retries = 0
        last_tile = None
        click = {'mark': None, 'at': None}
        last_move_tick = _core.tick()
        while _core.step_time() < deadline:
            if self._force_repath:
                self._force_repath = False
                say('repath requested')
                return 'repath'
            me = local_tile()
            if click['at'] is not None and not _same(me, click['at']):
                click['mark'] = None
                click['at'] = None
            if click['mark'] is not None and game_messages.saw_since(click['mark'], CANT_REACH):
                say(f"the server can't reach the walk toward route tile {click_idx}; repathing")
                return 'repath'
            if _arrived(dest, radius):
                say(f'arrived ({clicks} clicks)')
                return 'arrived'
            terminal = tiles[-1]
            if _same(me, terminal):
                return 'closest'

            limit = len(tiles) - 1
            for i in range(path_idx, len(tiles)):
                if tiles[i].transport is not None:
                    limit = i
                    break
            found = walkgeom.locate_on_path(tiles, me, path_idx, PROGRESS_WINDOW, CORRIDOR, limit)
            if found != -1:
                path_idx = found
            off = walkgeom.min_chebyshev_to_path(tiles, me, path_idx, PROGRESS_WINDOW, limit)
            if off > DEVIATION:
                say(f'off the route at {me} by {off}; repathing')
                return 'repath'
            self.remaining = len(tiles) - 1 - path_idx

            moved = last_tile is None or not _same(me, last_tile)
            if moved:
                last_move_tick = _core.tick()
            last_tile = me
            idle = _core.tick() - last_move_tick

            crossing = -1
            for i in range(max(1, path_idx), len(tiles)):
                if tiles[i].transport is not None:
                    crossing = i
                    break

            if crossing != -1 and path_idx >= crossing - 1:
                approach = tiles[crossing - 1]
                hop = tiles[crossing]
                if walkgeom.crossing_eligible(me, approach, hop, APPROACH_TRIGGER, _approachable):
                    outcome = yield from self._take_hop(approach, hop, say)
                    if outcome == 'repath':
                        return 'repath'
                    path_idx = max(path_idx, crossing)
                    last_move_tick = _core.tick()
                    stall_retries = 0
                    click_idx = -1
                    last_tile = None
                    continue

            if click_idx != -1 and not moved and idle >= UNREACH_CLICK_IDLE_TICKS and not _clickable(tiles[click_idx]):
                click_idx = -1
                click['mark'] = None
                click['at'] = None

            if idle >= STALL_TICKS:
                recover_limit = crossing - 1 if crossing != -1 else len(tiles) - 1
                recover = walkgeom.find_forward_recovery_index(tiles, me, path_idx, _clickable, CORRIDOR, PROGRESS_WINDOW + 20, recover_limit) if stall_retries == 0 else -1
                phase = walkgeom.stall_phase(stall_retries, recover, game.in_combat())
                if phase == 'recover':
                    target = tiles[recover]
                    say(f'stalled {idle} ticks; clicking route tile {recover} at {target.x},{target.z}')
                    mark = game_messages.mark()
                    if _core.walk_to(target.x, target.z, False):
                        click['mark'] = mark
                        click['at'] = me
                        click_idx = recover
                        clicks += 1
                        stall_retries = 1
                        last_move_tick = _core.tick()
                        yield from execution.delay_ticks(2)
                        continue
                    return 'repath'
                if phase == 'combat':
                    stall_retries = 0
                    click_idx = -1
                    last_move_tick = _core.tick()
                else:
                    opened = yield from self.try_nearby_door(say, tiles, path_idx)
                    if opened:
                        stall_retries = 0
                        click_idx = -1
                        last_tile = None
                        last_move_tick = _core.tick()
                        continue
                    end = tiles[-1]
                    if clicks == 0 and me.level == end.level and walkgeom.chebyshev(me, end) <= 1:
                        say(f'{end.x},{end.z} is blocked; as close as it gets')
                        return 'blocked'
                    say(f'stuck at {me} for {idle} ticks; repathing')
                    return 'repath'

            need_click = click_idx == -1 or click_idx <= path_idx or walkgeom.chebyshev(me, tiles[click_idx]) <= ARRIVE_RADIUS
            if need_click:
                limit_idx = crossing - 1 if crossing != -1 else len(tiles) - 1
                steps = TARGET_STEPS + random.randint(-TARGET_JITTER, TARGET_JITTER)
                chosen = walkgeom.select_client_walk_target(tiles, path_idx, steps, limit_idx, me.level, _clickable, lambda i: self._try_walk(tiles, i, me, click))
                if chosen == -1:
                    starve = walkgeom.starved_terminal_index(tiles, me, _clickable)
                    if starve != -1 and (crossing == -1 or path_idx == len(tiles) - 1) and self._try_walk(tiles, starve, me, click):
                        chosen = starve
                if chosen != -1:
                    click_idx = chosen
                    clicks += 1
                else:
                    click['mark'] = None
                    click['at'] = None
                    if crossing != -1:
                        approach = tiles[crossing - 1]
                        hop = tiles[crossing]
                        if me.level == approach.level and walkgeom.chebyshev(me, approach) <= max(APPROACH_TRIGGER, ARRIVE_RADIUS):
                            outcome = yield from self._take_hop(approach, hop, say)
                            if outcome == 'repath':
                                return 'repath'
                            path_idx = max(path_idx, crossing)
                            last_move_tick = _core.tick()
                            stall_retries = 0
                            click_idx = -1
                            last_tile = None
                            continue
                    if clicks == 0 and settle[0] > 0:
                        settle[0] -= 1
                        yield from execution.delay_ticks(2)
                        continue
                    say(f'no tile ahead of route tile {path_idx} can be walked to; repathing')
                    return 'repath'

            yield from execution.delay_ticks(2)
        return 'failed'

    def _try_walk(self, tiles, i, me, click):
        tile = tiles[i]
        if tile.x == me.x and tile.z == me.z:
            return False
        mark = game_messages.mark()
        if not _core.walk_to(tile.x, tile.z, False):
            return False
        click['mark'] = mark
        click['at'] = me
        return True

    def _take_hop(self, approach, hop, say):
        """Takes a hop: 'crossed', or 'repath' after noting a door that refused."""
        transport = hop.transport
        handled = yield from self._handle_transport(approach, hop, say)
        if handled:
            hop.transport = None
            to_tile = transport.get('to_tile')
            here = local_tile()
            if transport.get('accept_any_landing') and to_tile is not None and (here.level != hop.level or not _near(here, to_tile[0], to_tile[1], 3)):
                say(f'{transport["loc_name"]} landed at {here}, not where planned; repathing')
                return 'repath'
            return 'crossed'
        key = f'{transport["loc_x"]},{transport["loc_z"]}'
        strikes = self._door_strikes.get(key, 0) + 1
        self._door_strikes[key] = strikes
        if strikes >= DOOR_STRIKES:
            self._avoid_doors.append([transport['loc_x'], transport['loc_z']])
            say(f'avoiding {transport["loc_name"]} at {key} on the next route')
        teleport = transport.get('teleport_id')
        if teleport is not None and teleport not in self._suppressed_teleports:
            self._suppressed_teleports.append(teleport)
        return 'repath'

    def _handle_transport(self, approach, step, say):
        transport = step.transport
        if transport.get('kind') == 'teleport':
            done = yield from self._teleport(transport, say)
            return done
        crossing = special_crossing_for_transport(transport, approach, step)
        if crossing is not None:
            done = yield from self._special_crossing(approach, step, crossing, say)
            return done
        if transport.get('to_level') is None and transport.get('to_tile') is None and walkgeom.chebyshev(approach, step) >= 1:
            done = yield from self._cross_door(approach, step, transport, say)
            return done
        done = yield from self._use_transport_loc(approach, step, transport, say)
        return done

    def _teleport(self, transport, say):
        if transport.get('family') != 'spell':
            say(f'{transport["loc_name"]}: only spell teleports are taken so far')
            return False
        before = local_tile()
        if not game.teleport(transport['loc_name']):
            say(f'{transport["loc_name"]}: the spellbook has no such teleport')
            return False
        landed = yield from execution.delay_until(lambda: matches_landing(transport, 0, before, local_tile()), 10000)
        if landed:
            yield from execution.delay_ticks(2)
        return landed

    def _use_transport_loc(self, approach, step, transport, say):
        """Stairs, ladders, trapdoors, gangplanks and shortcuts: use the loc and wait to land."""
        for attempt in range(2):
            loc = find_transport_loc(transport)
            if loc is None:
                yield from execution.delay_until(lambda: find_transport_loc(transport) is not None, SCENE_REBUILD_MS)
                loc = find_transport_loc(transport)
            if loc is None:
                opened = yield from self._open_shut_trapdoor(transport, say)
                if opened:
                    continue
                say(f'{transport["loc_name"]} not found near {transport["loc_x"]},{transport["loc_z"]}')
                return False
            before = local_tile()
            mark = game_messages.mark()
            if not loc.interact(transport['action']):
                say(f'{transport["loc_name"]} has no {transport["action"]} (it has {loc.actions()})')
                return False
            to_level = transport.get('to_level')
            if to_level is not None:
                crossed = yield from execution.delay_until(lambda: _core.get_level() == to_level or game_messages.saw_since(mark, CANT_REACH), TRANSPORT_WAIT_MS)
                crossed = _core.get_level() == to_level
            else:
                landed = yield from execution.delay_until(lambda: matches_landing(transport, step.level, before, local_tile()) or game_messages.saw_since(mark, CANT_REACH), TRANSPORT_WAIT_MS)
                crossed = matches_landing(transport, step.level, before, local_tile())
            if crossed:
                if to_level is not None:
                    yield from execution.delay_ticks(2)
                say(f'{transport["action"]} {transport["loc_name"]} at {transport["loc_x"]},{transport["loc_z"]}')
                return True
            if game_messages.saw_since(mark, CANT_REACH) and attempt == 0 and not _same(local_tile(), approach):
                say(f"the server can't reach {transport['loc_name']} from here; stepping onto {approach.x},{approach.z}")
                _core.walk_to(approach.x, approach.z, False)
                yield from execution.delay_until(lambda: _same(local_tile(), approach), APPROACH_STEP_MS)
                continue
            if game_messages.saw_since(mark, CANT_REACH):
                return False
        return False

    def _open_shut_trapdoor(self, transport, say):
        x = transport['loc_x']
        z = transport['loc_z']
        shut = locs.query().name(transport['loc_name']).where(lambda l: _near(l.tile(), x, z, 3) and open_op(l.actions()) is not None).nearest()
        if shut is None:
            return False
        if not shut.interact(open_op(shut.actions())):
            return False
        say(f'opening {shut.name} at {shut.tile()}')
        opened = yield from execution.delay_until(lambda: find_transport_loc(transport) is not None, SCENE_REBUILD_MS)
        return opened

    def _cross_door(self, approach, step, transport, say):
        """A door or gate across the route: open it if it's shut, and step through."""
        if find_transport_loc(transport) is None or _can_step(approach, step):
            if walkgeom.is_on_far_side(local_tile(), approach, step):
                return True
            if _can_step(approach, step) or _approachable(step):
                if _same(local_tile(), approach):
                    _core.walk_to(step.x, step.z, False)
                    yield from execution.delay_until(lambda: walkgeom.is_on_far_side(local_tile(), approach, step), 2500)
                return True
        deadline = _core.step_time() + DOOR_CROSS_MS
        while _core.step_time() < deadline:
            here = local_tile()
            if walkgeom.is_on_far_side(here, approach, step):
                say(f'through the {transport["loc_name"]} at {transport["loc_x"]},{transport["loc_z"]}')
                return True
            shut = find_transport_loc(transport)
            if shut is not None and not _same(here, approach) and walkgeom.chebyshev(here, approach) <= 4:
                _core.walk_to(approach.x, approach.z, False)
                yield from execution.delay_until(lambda: _same(local_tile(), approach), APPROACH_STEP_MS)
                shut = find_transport_loc(transport)
            if shut is not None:
                mark = game_messages.mark()
                if not shut.interact(transport['action']):
                    say(f'{transport["loc_name"]} has no {transport["action"]} (it has {shut.actions()})')
                    return False
                yield from execution.delay_until(lambda: find_transport_loc(transport) is None or _can_step(approach, step) or game_messages.saw_since(mark, CANT_REACH), TRANSPORT_WAIT_MS)
                if game_messages.saw_since(mark, CANT_REACH):
                    say(f"the server can't reach the {transport['loc_name']} at {transport['loc_x']},{transport['loc_z']}")
                    return False
                if find_transport_loc(transport) is not None and not _can_step(approach, step):
                    say(f'the {transport["loc_name"]} at {transport["loc_x"]},{transport["loc_z"]} did not open')
                    return False
                yield from execution.delay_ticks(1)
            _core.walk_to(step.x, step.z, False)
            yield from execution.delay_until(lambda: walkgeom.is_on_far_side(local_tile(), approach, step), 3000)
        return walkgeom.is_on_far_side(local_tile(), approach, step)

    def _special_crossing(self, approach, step, crossing, say):
        """Tolls, ships and the other crossings that pay, talk or use an item."""
        label = crossing.get('label', crossing['locName'])
        needs = crossing.get('requires')
        waiver = crossing.get('questWaivesItems')
        waived = waiver is not None and quests.status(waiver) == 'complete'
        if needs is not None and not waived and inventory.count(needs['item']) < needs['count']:
            say(f'{label}: need {needs["count"]} {needs["item"]}')
            return False
        skill = crossing.get('requiresSkill')
        if skill is not None and skills.level(skill['name']) < skill['level']:
            say(f'{label}: need {skill["name"]} {skill["level"]}')
            return False
        choose = crossing.get('dialogue', {}).get('choose', [])
        radius = crossing.get('arrivalRadius', 2)
        if crossing.get('npc') is not None:
            done = yield from self._npc_crossing(crossing, label, choose, radius, approach, say)
            return done

        transport = step.transport
        if crossing['action'].lower() == 'open' and crossing.get('useItem') is None and find_transport_loc(transport) is None:
            if self._crossed(crossing, radius, approach, step):
                return True
            if _can_step(approach, step):
                if _same(local_tile(), approach):
                    _core.walk_to(step.x, step.z, False)
                    yield from execution.delay_until(lambda: self._crossed(crossing, radius, approach, step), 2500)
                return True
        tries = 2 if crossing.get('reopenAfterDialogue') else 1
        for attempt in range(tries):
            if self._crossed(crossing, radius, approach, step):
                break
            loc = find_transport_loc(transport)
            if crossing.get('useItem') is not None:
                x = crossing['x']
                z = crossing['z']
                loc = locs.query().name(crossing['locName']).where(lambda l: _near(l.tile(), x, z, 3)).nearest()
            if loc is None:
                if crossing['action'].lower() == 'open' and (self._crossed(crossing, radius, approach, step) or _can_step(approach, step)):
                    return True
                say(f'{label}: {crossing["locName"]} not found')
                return False
            if crossing.get('useItem') is not None:
                item = inventory.first(crossing['useItem']['name'])
                if item is None or not item.use_on(loc):
                    say(f'{label}: need {crossing["useItem"]["name"]}')
                    return False
            elif not loc.interact(crossing['action']):
                say(f'{label}: {crossing["locName"]} has no {crossing["action"]} (it has {loc.actions()})')
                return False
            for i in range(DIALOGUE_STEPS):
                if self._crossed(crossing, radius, approach, step):
                    break
                yield from self._dialogue_step(choose)
        crossed = self._crossed(crossing, radius, approach, step)
        if crossed:
            say(f'{label}: crossed')
        else:
            say(f'{label}: did not cross')
        return crossed

    def _crossed(self, crossing, radius, approach, step):
        if crossing.get('toTile') is not None:
            return _near_landing(crossing, radius)
        return walkgeom.is_on_far_side(local_tile(), approach, step)

    def _dialogue_step(self, choose):
        pick = pick_choice(chat_dialog.options(), choose) if choose else None
        if pick is not None:
            yield from chat_dialog.choose_option(pick)
        elif chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        else:
            yield from execution.delay_ticks(1)

    def _npc_crossing(self, crossing, label, choose, radius, approach, say):
        """A ship's captain, a ferryman or a guide: pay or talk, answer, and wait to land."""
        action = crossing['action']
        tries = [action, 'Talk-to'] if action not in ('Open', 'Go-through', 'Pull', 'Talk-to') else ['Talk-to']
        stand = Tile(crossing['x'], crossing['z'], crossing['level'])
        talked = False
        for act in tries:
            npc = npcs.query().name(crossing['npc']).action(act).within_of(stand, 10).nearest()
            if npc is None:
                npc = npcs.query().name(crossing['npc']).action(act).within(12).nearest()
            if npc is not None and npc.interact(act):
                talked = True
                break
        if not talked:
            say(f'{label}: {crossing["npc"]} is not here to talk to')
            return False
        for i in range(SHIP_DIALOGUE_STEPS):
            if _near_landing(crossing, radius):
                break
            pick = pick_choice(chat_dialog.options(), choose) if choose else None
            if pick is not None:
                yield from chat_dialog.choose_option(pick)
            elif chat_dialog.can_continue():
                yield from chat_dialog.continue_()
            elif modals.is_open():
                yield from modals.close()
                yield from execution.delay_ticks(1)
            else:
                yield from execution.delay_ticks(1)
        if _near_landing(crossing, radius):
            yield from execution.delay_ticks(2)
            say(f'{label}: arrived')
            return True
        say(f'{label}: did not land')
        return False

    def try_nearby_door(self, log=None, tiles=None, path_idx=0):
        """Opens a shut door or gate beside you, near the route ahead when one is given. Use with yield from."""
        say = log if log is not None else (lambda message: None)
        ahead = tiles[path_idx:path_idx + PROGRESS_WINDOW] if tiles is not None else None
        door = locs.query().where(lambda l: l.layer == LAYER_WALL and is_openable_barrier(l.name, l.actions()) and l.distance() <= 2 and (ahead is None or _near_route(l.tile(), ahead))).nearest()
        if door is None:
            return False
        tile = door.tile()
        say(f'opening the {door.name} at {tile}')
        if not door.interact(open_op(door.actions())):
            return False
        opened = yield from execution.delay_until(lambda: not _shut_door_at(tile), 4000)
        return opened

    def walk_resilient(self, dest, radius=2, attempts=None, timeout_ms=None, scene_radius=None, max_budget=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None):
        """walk_to behind rs2b0t's escalation ladder: a world route, then a walk in the loaded area, then an
        unstick step and a backoff, until arrival or, after attempts passes without progress, giving up."""
        say = log if log is not None else (lambda message: None)
        dest = Tile.from_tile(dest) if not isinstance(dest, Tile) else dest
        scene = radius + 1 if scene_radius is None else scene_radius
        budget = DEFAULT_MAX_BUDGET if max_budget is None else max_budget
        world_timeout = 90000 if timeout_ms is None else timeout_ms
        state = walkgeom.LadderState(walkgeom.walk_chebyshev(local_tile(), dest))
        last = None
        unstick = 0
        for i in range(1000):
            rung, state = walkgeom.advance(state, walkgeom.walk_chebyshev(local_tile(), dest), _arrived(dest, radius), False, last)
            kind = rung[0]
            if kind == 'arrived':
                return True
            if kind == 'interrupted':
                self.last_outcome = 'interrupted'
                return False
            if kind == 'unreachable':
                say(f'walk_resilient: {dest} is unreachable')
                self.last_outcome = 'unreachable'
                return False
            if attempts is not None and state.no_progress_passes >= attempts:
                say(f'walk_resilient: {attempts} passes made no progress')
                self.last_outcome = 'failed'
                return False
            if kind == 'world':
                expansions = budget if rung[1] else None
                yield from self.walk_to(dest, radius, world_timeout, expansions, use_teleport_catalog, policy, bank_item_counts, avoid_zones, say)
                outcome = self.last_outcome
                if outcome == 'blocked':
                    return True
                last = 'failed' if outcome == 'unreachable' else outcome
            elif kind == 'scene':
                yield from direct_navigator.walk_to(dest, scene, SCENE_TIMEOUT_MS)
                last = 'failed'
            elif kind == 'unstick':
                yield from self.try_nearby_door(say)
                me = local_tile()
                step = walkgeom.pick_unstick_step(lambda dx, dz: _core.can_step(me.x, me.z, me.x + dx, me.z + dz), unstick)
                unstick = (unstick + 3) % 8
                if step is not None:
                    yield from direct_navigator.walk_to(Tile(me.x + step[0], me.z + step[1], me.level), 0, 3000)
                last = 'failed'
            elif kind == 'backoff':
                yield from execution.delay_ticks(rung[1])
                last = 'failed'
            elif kind == 'verify':
                me = local_tile()
                probe = self._request(me, dest, budget, {'use_teleports': False}, False, [])
                last = 'probe-fresh' if probe['ok'] else 'probe-dead'
        self.last_outcome = 'failed'
        return False


def _shut_door_at(tile):
    return locs.query().where(lambda l: l.tile() == tile and is_openable_barrier(l.name, l.actions())).nearest() is not None


def _near_route(tile, ahead):
    for point in ahead:
        if point.level == tile.level and walkgeom.chebyshev(point, tile) <= 1:
            return True
    return False


traversal = _Traversal()
