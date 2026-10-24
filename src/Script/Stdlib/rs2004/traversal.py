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
from rs2004.interfaces import interfaces
from rs2004.items import equipment, inventory
from rs2004.messages import CANT_REACH, game_messages
from rs2004.reach import close_op, is_open_barrier_leaf, is_openable_barrier, open_op
from rs2004.routeplan import WEB_SLASH_KNIFE_NAME, crossings, essence_session, explain_unreachable, gate_item_candidates, is_quest_lock_dialogue, is_quest_lock_text
from rs2004.routeplan import missing_items_for_path, path_has_teleport, pick_choice, plan_bank_leg, post_quest_talk_for, records_have_slash_tool
from rs2004.routeplan import resolve_path_follow_config, special_crossing_for_transport, teleport_by_id, virtualize_with_items
from rs2004.settings import settings_store
from rs2004.tabs import quests
from rs2004.walkgeom import GLORY_MAX_WILDERNESS, SPELL_MAX_WILDERNESS, wilderness_level_at

__all__ = [
    'traversal', 'NAV_PURE_WALK', 'NAV_WITH_TELES', 'world_state', 'special_crossing_for_transport', 'pick_choice', 'nearest_bank',
    'nearest_banks', 'nearest_bank_reachable', 'nearest_usable_bank', 'bank_unlocked', 'bank_locations', 'BANK_LOCATIONS',
    'approach_of', 'locked_bank_at', 'nearest_walkable_bank', 'bank_cost_for_navigator', 'USE_MAGE_BANK', 'USE_ZANARIS_BANK',
    'wilderness_level_at', 'SPELL_MAX_WILDERNESS', 'GLORY_MAX_WILDERNESS', 'essence_session', 'DESERT_MINING_CAMP_SCRIPTED_DOOR_IDS',
]

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
UNREACH_CLICK_IDLE_TICKS = 3
DIALOGUE_STEPS = 24
SHIP_DIALOGUE_STEPS = 40
DOOR_CROSS_MS = 12000
DOOR_STRIKES = 2
LANDING_TOLERANCE = 3
DEFAULT_TIMEOUT_MS = 300000
DEFAULT_MAX_BUDGET = 1200000
SCENE_TIMEOUT_MS = 6000
# How often a resilient walk says where its ladder stands.
PROGRESS_LOG_MS = 15000
POST_QUEST_TALK_STEPS = 60
POST_QUEST_TALK_OPEN_MS = 4000
TELEPORT_LAND_MS = 8000
TELEPORT_DIALOGUE_MS = 4000
QUEST_STATUSES = {'not_started': 'not_started', 'in_progress': 'started', 'complete': 'complete'}


def _load(name):
    text = _core.nav_data(name)
    return json.loads(text) if text is not None else []


_banks = None


def bank_locations():
    """rs2b0t's banks: dicts of name, tile (x, z, level), and how to open each when it isn't a booth."""
    global _banks
    if _banks is None:
        _banks = _load('banks')
    return _banks


# rs2b0t's BANK_LOCATIONS: the same list bank_locations() gives.
BANK_LOCATIONS = bank_locations()

# The Global settings that open the Mage Arena's and Zanaris's banks to the walker and banking.open.
USE_MAGE_BANK = 'use_mage_bank'
USE_ZANARIS_BANK = 'use_zanaris_bank'


def _snake(name):
    out = ''
    for c in name:
        out += c if c == c.lower() else '_' + c.lower()
    return out


def bank_unlocked(bank, settings=None):
    """Whether the account can use the bank: its skill level and quest, and, for a bank a script opts into
    (Zanaris, the Mage Arena), the setting it names: from settings, a dict of booleans, when given, and
    otherwise the Global settings (use_zanaris_bank, use_mage_bank)."""
    needs = bank.get('requires')
    if not needs:
        return True
    skill = needs.get('skill')
    if skill is not None and skills.level(skill['name']) < skill['level']:
        return False
    if needs.get('quest') is not None and quests.status(needs['quest']) != 'complete':
        return False
    setting = needs.get('setting')
    if setting is not None:
        if settings is not None:
            return bool(settings.get(setting, settings.get(_snake(setting), False)))
        return settings_store.global_bag().bool(_snake(setting), False)
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


def approach_of(bank):
    """The tile a bank is ranked by: its approach when it has one, else its stand."""
    return _bank_stand(bank)


def locked_bank_at(tile):
    """A bank within 14 tiles of tile, on its level, that the account can't use, or None."""
    tile = Tile.from_tile(tile)
    for bank in bank_locations():
        stand = bank['tile']
        if stand['level'] == tile.level and Tile(stand['x'], stand['z'], stand['level']).distance_to(tile) <= 14 and not bank_unlocked(bank):
            return bank
    return None


def nearest_walkable_bank(tile, path_cost):
    """Of the usable banks, the one path_cost(tile, stand) prices lowest; a cost of None is no route."""
    best = None
    best_cost = None
    for bank in nearest_banks(tile):
        stand = bank['tile']
        cost = path_cost(tile, Tile(stand['x'], stand['z'], stand['level']))
        if cost is not None and (best_cost is None or cost < best_cost):
            best = bank
            best_cost = cost
    return best


def bank_cost_for_navigator(navigator, max_expansions=None):
    """A path_cost for nearest_walkable_bank: the cost of the route navigator.find_path plans, without
    teleports, or None."""
    def cost(start, dest):
        route = navigator.find_path(start, dest, max_expansions=max_expansions, policy={'use_teleports': False})
        return route.cost if route.ok else None

    return cost


def nearest_usable_bank(tile, usable):
    """The nearest bank, by straight line to its stand, for which usable(bank) holds, or None."""
    best = None
    best_distance = None
    for bank in bank_locations():
        if not usable(bank):
            continue
        stand = _bank_stand(bank)
        distance = (stand.x - tile.x) ** 2 + (stand.z - tile.z) ** 2
        if best_distance is None or distance < best_distance:
            best = bank
            best_distance = distance
    return best


# Standing this near the nearest bank, it's the one in reach, and no route is priced.
NEAR_BANK_RADIUS = 4
BANK_SEARCH_EXPANSIONS = 500000


def nearest_bank_reachable(here, navigator, candidates=8):
    """rs2b0t's: the bank the cheapest route reaches, since from a dungeon or an island the straight line
    misleads, or the nearest by the straight line when no route reaches one. Within 4 tiles of the nearest, that
    one at once. rs2b0t prices every usable bank; this prices the candidates nearest, since each route is planned
    while the script waits. None with no usable bank."""
    near = nearest_bank(here)
    if near is not None and _bank_tile(near).distance_to(here) <= NEAR_BANK_RADIUS:
        return near
    cost = bank_cost_for_navigator(navigator, BANK_SEARCH_EXPANSIONS)
    best = None
    best_cost = None
    for bank in nearest_banks(here)[:candidates]:
        price = cost(here, _bank_tile(bank))
        if price is not None and (best_cost is None or price < best_cost):
            best = bank
            best_cost = price
    return best if best is not None else near


def _bank_tile(bank):
    stand = bank['tile']
    return Tile(stand['x'], stand['z'], stand['level'])


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
    items = _counts(inventory.items())
    worn = _counts(equipment.items())
    state = {
        'members': _core.is_members(),
        'skills': levels,
        'items': items,
        'worn': worn,
        'quests': statuses,
        'free_slots': inventory.free(),
        'can_slash_web': records_have_slash_tool(items, worn),
    }
    # Unknown until a walk goes in through a wizard: then the planner takes the portal that leads back there.
    essence = essence_session.get_return_id()
    if essence is not None:
        state['essence_exit_return'] = essence
    return state


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

# The Desert Mining Camp's doors and gates that a script answers, each leaf its own.
DESERT_MINING_CAMP_SCRIPTED_DOOR_IDS = [2673, 2674, 2675, 2676, 2687, 2688, 2690, 2691]

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


def _exact_placement(transport):
    """Whether only the loc on the hop's own tile will do. Slashable webs sit a tile apart with one id
    (Yanille), and ladders with one id stand a few tiles apart (Ice Queen's lair), so a neighbour would
    make a different hop."""
    action = transport['action'].lower()
    name = transport['loc_name'].lower()
    if action == 'slash' and 'web' in name:
        return True
    return transport.get('loc_id') is not None and action.startswith('climb') and 'ladder' in name


def find_transport_loc(transport):
    """The loc that makes the hop: by its name, option and placement, else by name and option near the
    placement, else any stairs there. None when an open leaf shows the door is open already."""
    names = _name_aliases(transport['loc_name'])
    action = transport['action']
    x = transport['loc_x']
    z = transport['loc_z']
    ids = _ids_of(transport)
    slack = 0 if _exact_placement(transport) else 1
    exact = locs.query().name(names).action(action).where(lambda l: _near(l.tile(), x, z, slack) and (not ids or l.id in ids)).nearest()
    if exact is not None or slack == 0:
        return exact
    # Why: the camp's neighbouring leaves have different handlers, so a missing one mustn't pick its sibling.
    if transport.get('loc_id') in DESERT_MINING_CAMP_SCRIPTED_DOOR_IDS:
        return None
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

def _near_landing(crossing, radius):
    to = crossing.get('toTile')
    if to is None:
        return False
    here = local_tile()
    return here.level == to.get('level', here.level) and _near(here, to['x'], to['z'], radius)


# Quest-locked crossings.

def chat_shows_quest_lock():
    """Whether the dialogue open says a crossing won't open for you now."""
    if not chat_dialog.is_open() and not chat_dialog.can_continue():
        return False
    return is_quest_lock_dialogue(chat_dialog.texts())


def lock_message_since(mark):
    """Whether a game message since mark says a crossing won't open now. Why: rs2b0t reads only the dialogue, but
    the 289 doors refuse in the chatbox, as the Champions' Guild's does before its guild master speaks."""
    return len([m for m in game_messages.since(mark) if is_quest_lock_text(m.text)]) > 0


def dismiss_quest_lock_dialogue(max_steps=8):
    """Clicks through the lock's message, so the walk can plan again. Use with yield from."""
    for _ in range(max_steps):
        if not chat_dialog.is_open() and not chat_dialog.can_continue():
            return
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        else:
            yield from execution.delay_ticks(1)


class _Traversal:
    """Walking across the world. last_outcome says how the last walk ended: 'arrived', 'closest' (as near as
    the route goes), 'blocked', 'budget', 'failed', 'unreachable' or 'interrupted'. remaining is how many
    route tiles were left. Each walk is a generator, used with yield from."""

    remaining = 0
    last_outcome = None
    last_reason = None
    # What the last walk's route needed and the account didn't hold, as MissingItems: a toll's coins, a fare, a
    # knife for webs. Empty when nothing was missing.
    last_missing_gate_items = []
    _force_repath = False

    # rs2b0t's Traversal.pureWalk and withTeles: the same as NAV_PURE_WALK and NAV_WITH_TELES.
    pure_walk = NAV_PURE_WALK
    with_teles = NAV_WITH_TELES

    def __init__(self):
        self._avoid_doors = []
        self._door_strikes = {}
        self._suppressed_teleports = []
        self._post_quest_talks = []
        self._bank_leg_done = False
        self._in_bank_leg = False
        self._bank_item_counts = None
        self._restore_retaliate = False
        self._follow = resolve_path_follow_config()

    def preload(self):
        """Nothing to do: the walker's map is built when the client starts. rs2b0t warms its worker here."""
        return None

    def teleports_enabled(self):
        """Whether walks use teleports unless told otherwise: the Global nav_teleports setting, off by default,
        as rs2b0t's is."""
        return settings_store.global_bag().bool('nav_teleports', False)

    def request_repath(self, reason=None):
        """Plans the walk in progress again at its next step."""
        self._force_repath = True

    def _request(self, me, dest, max_expansions, policy, use_teleports, zones, state=None):
        request = {
            'from': [me.x, me.z, me.level],
            'to': [dest.x, dest.z, dest.level],
            'avoid_doors': self._avoid_doors,
            'use_teleport_catalog': use_teleports,
            'policy': policy,
            'state': state if state is not None else world_state(),
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

    def walk_to(self, dest, radius=2, timeout_ms=None, max_expansions=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None, force_repath=False,
                path_follow=None):
        """Walks to within radius of dest, anywhere on the map. See _walk_to. An attacked walk that turned auto
        retaliate off to get away turns it back on at the end."""
        # A walk within a walk, such as a bank leg's, keeps the outer walk's own.
        outer = self._restore_retaliate
        self._restore_retaliate = False
        arrived = yield from self._walk_to(dest, radius, timeout_ms, max_expansions, use_teleport_catalog, policy, bank_item_counts, avoid_zones, log, force_repath, path_follow)
        if self._restore_retaliate:
            game.set_auto_retaliate(True)
        self._restore_retaliate = outer
        return arrived

    def _walk_to(self, dest, radius=2, timeout_ms=None, max_expansions=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None, force_repath=False,
                 path_follow=None):
        """Walks to within radius of dest, anywhere on the map. True on arrival, or when the route ends as
        close as it can get (last_outcome 'closest' or 'blocked').

        When the route needs what the backpack lacks, such as a toll's coins or a teleport's runes, and a bank
        leg is cheaper than going without, it banks for them first, once a walk: from bank_item_counts, a dict
        of name to count, when given, else from the bank when it's open, else on the chance the bank has every
        gate's item. path_follow overrides the follow settings: stall_ticks, deviation_chebyshev,
        transport_approach_chebyshev and door_step_ticks."""
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
        self._follow = resolve_path_follow_config(path_follow)
        self._bank_item_counts = bank_item_counts
        # A walk to the bank for a route's items doesn't plan one of its own.
        self._bank_leg_done = self._in_bank_leg
        self.last_outcome = None
        self.last_reason = None
        self.last_missing_gate_items = []
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
                short = self._explain_unreachable(me, dest, path['reason'], max_expansions, walk_policy, use_teleports, zones)
                # Why: the planner won't route a fare or toll the backpack can't pay, so with none held there's no
                # route to fund; rs2b0t gives up here, while this banks for the kit that would open one.
                if short and not self._bank_leg_done:
                    banked = yield from self._maybe_bank_for_route(me, dest, None, None, max_expansions, walk_policy, use_teleports, zones, say)
                    if banked:
                        self._bank_leg_done = True
                        continue
                why = path['reason'] + (f" without {', '.join([repr(m) for m in short])}" if short else '')
                say(f'no path to {dest}: {why}')
                self.last_outcome = walkgeom.classify_reason(path['reason'])
                return False
            waypoints = _waypoints(path)
            if not self._bank_leg_done:
                banked = yield from self._maybe_bank_for_route(me, dest, path, waypoints, max_expansions, walk_policy, use_teleports, zones, say)
                if banked:
                    self._bank_leg_done = True
                    continue
            if not self._check_route_items(waypoints, say):
                return False
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

    # Why: one more route request, only when the answer is unreachable; a budget or off-graph failure has no list.
    def _explain_unreachable(self, me, dest, reason, max_expansions, policy, use_teleports, zones):
        """Turns a bare unreachable into the items that would open the route, kept in last_missing_gate_items."""
        self.last_missing_gate_items = []
        if 'unreachable' not in reason.lower():
            return []
        state = world_state()

        def probe(probe_state):
            return self._request(me, dest, max_expansions, policy, use_teleports, zones, probe_state)

        self.last_missing_gate_items = explain_unreachable(probe, state, _waypoints)
        return self.last_missing_gate_items

    def _read_bank_item_counts(self):
        if self._bank_item_counts:
            return self._bank_item_counts
        from rs2004.bank import bank
        if not bank.is_open():
            return None
        return _counts(bank.items())

    def _maybe_bank_for_route(self, me, dest, direct, direct_waypoints, max_expansions, policy, use_teleports, zones, say):
        """Banks once for what the route needs when the bank's stock makes a cheaper route, or any route when
        direct is None: True when the walk should plan again. Use with yield from."""
        from rs2004.bank import bank, banking
        known = self._read_bank_item_counts()
        # Why: with no bank in view, a Varrock to Ardougne walk never withdrew its second fare, so it's assumed the
        # bank has every gate's item, and the withdrawals find out.
        bank_items = known if known else gate_item_candidates()
        state = world_state()
        direct_missing = missing_items_for_path(direct_waypoints, state) if direct is not None else self.last_missing_gate_items
        if direct is not None and len(direct_missing) == 0 and path_has_teleport(direct_waypoints):
            return False
        stand_bank = nearest_bank(me)
        if stand_bank is None:
            return False
        stand = _bank_tile(stand_bank)
        to_bank = self._request(me, stand, max_expansions, policy, use_teleports, zones)
        if not to_bank['ok'] or len(missing_items_for_path(_waypoints(to_bank), state)) > 0:
            return False
        bank_to_dest = self._request(stand, dest, max_expansions, policy, use_teleports, zones, virtualize_with_items(state, bank_items))
        if not bank_to_dest['ok']:
            return False
        bank_waypoints = _waypoints(bank_to_dest)
        direct_cost = None if direct is None or len(direct_missing) > 0 else direct['cost']
        plan = plan_bank_leg(direct_cost, False, to_bank['cost'], bank_to_dest['cost'], missing_items_for_path(bank_waypoints, state))
        if plan.action != 'bank':
            return False
        say(f"bank plan: withdraw {', '.join([repr(m) for m in plan.missing])} (est cost {plan.estimated_cost}, direct {'underfunded' if direct_cost is None else direct_cost})")
        self._bank_leg_done = True
        follow = self._follow
        reached = yield from self._walk_to_bank_only(stand, say)
        self._follow = follow
        if not reached:
            say('bank plan: could not reach bank, continuing direct')
            return False
        opened = yield from banking.open(prefer_nearby=True, log=lambda m: say(f'  {m}'))
        if not opened:
            say('bank plan: could not open bank, continuing direct')
            return False
        for item in missing_items_for_path(bank_waypoints, world_state()):
            took = yield from bank.withdraw_x(item.name, item.count)
            say(f'bank plan: withdrew {item!r}' if took else f'bank plan: failed to withdraw {item!r}')
        if bank.is_open():
            yield from bank.close()
        yield from execution.delay_ticks(1)
        return True

    def _walk_to_bank_only(self, stand, say):
        """A walk to the bank that doesn't plan a bank leg of its own. Use with yield from."""
        self._in_bank_leg = True
        reached = yield from self.walk_to(stand, 4, 120000, log=lambda m: say(f'  {m}'))
        self._in_bank_leg = False
        self._bank_leg_done = True
        return reached

    def _check_route_items(self, waypoints, say):
        """False, with last_outcome unreachable, when the route needs what the account doesn't hold."""
        missing = missing_items_for_path(waypoints, world_state())
        if len(missing) == 0:
            return True
        self.last_missing_gate_items = missing
        self.last_outcome = 'unreachable'
        say(f"route needs {', '.join([repr(m) for m in missing])} before departure")
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
            if off > self._follow.deviation_chebyshev:
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
                if walkgeom.crossing_eligible(me, approach, hop, self._follow.transport_approach_chebyshev, _approachable):
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

            if idle >= self._follow.stall_ticks:
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
                    # Why: on this server a hit makes a retaliating player attack back unless it's busy, and
                    # walking isn't, so every hit cancels the walk; rs2b0t holds course, which here never moves.
                    if game.auto_retaliate_on() and game.set_auto_retaliate(False):
                        self._restore_retaliate = True
                        say('under attack and not moving: auto retaliate off for the walk')
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
                    locked = _quest_lock_door_near()
                    if locked is not None:
                        say(f'quest-locked door at {locked.x},{locked.z}, leaving it out')
                        self._blacklist_door(locked.x, locked.z)
                        yield from dismiss_quest_lock_dialogue()
                        return 'repath'
                    if chat_shows_quest_lock():
                        yield from dismiss_quest_lock_dialogue()
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
                        if me.level == approach.level and walkgeom.chebyshev(me, approach) <= max(self._follow.transport_approach_chebyshev, ARRIVE_RADIUS):
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
        # Why: a teleport hop has no loc, so only a door or a loc hop earns strikes; a teleport is suppressed instead.
        if transport.get('loc_x') is not None:
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
        """A spell cast, or a jewellery rub and its destination chosen: True when it lands. Mirrors rs2b0t's
        teleportExecute.ts."""
        before = local_tile()
        teleport = teleport_by_id(transport.get('teleport_id'))
        level = teleport['to']['level'] if teleport is not None else before.level
        if transport.get('family') == 'spell':
            if not game.teleport(transport['loc_name']):
                say(f'{transport["loc_name"]}: the spellbook has no such teleport')
                return False
        else:
            started = yield from self._rub_jewellery(teleport, transport, say)
            if not started:
                return False
        landed = yield from execution.delay_until(lambda: matches_landing(transport, level, before, local_tile()), TELEPORT_LAND_MS)
        if landed:
            yield from execution.delay_ticks(2)
            say(f'{transport["loc_name"]}: landed')
        else:
            say(f'{transport["loc_name"]}: did not land')
        return landed

    def _rub_jewellery(self, teleport, transport, say):
        """Rubs the matching jewellery in the backpack and picks the destination. Use with yield from."""
        if teleport is None or teleport.get('family') != 'jewellery':
            say(f'teleport hop {transport.get("teleport_id")}: unknown id, repathing')
            return False
        wanted = [m.lower() for m in teleport.get('itemNameMatch', [])]
        item = None
        for held in inventory.items():
            if held.name is not None and len([m for m in wanted if m in held.name.lower()]) > 0:
                item = held
                break
        if item is None:
            say(f'{teleport["teleportId"]}: no matching jewellery in the backpack')
            return False
        rub = None
        for action in item.actions():
            if action.lower() == 'rub':
                rub = action
        if rub is None:
            say(f'{teleport["teleportId"]}: {item.name} has no Rub ({item.actions()})')
            return False
        say(f'rubbing {item.name} for {teleport.get("label", teleport["teleportId"])}')
        if not item.interact(rub):
            say(f'rub failed on {item.name}')
            return False
        choose = teleport.get('dialogueChoose', [])
        if len(choose) == 0:
            return True
        shown = yield from execution.delay_until(lambda: len(chat_dialog.options()) > 0, TELEPORT_DIALOGUE_MS)
        if not shown:
            say(f'{teleport["teleportId"]}: no dialogue after the rub')
            return False
        pick = pick_choice(chat_dialog.options(), choose)
        if pick is None:
            say(f"{teleport['teleportId']}: none of [{' | '.join(chat_dialog.options())}] is {'/'.join(choose)}")
            return False
        yield from chat_dialog.choose_option(pick)
        return True

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
                crossed = yield from execution.delay_until(lambda: _core.get_level() == to_level or game_messages.saw_since(mark, CANT_REACH) or chat_shows_quest_lock() or lock_message_since(mark),
                                                           TRANSPORT_WAIT_MS)
                crossed = _core.get_level() == to_level
            else:
                landed = yield from execution.delay_until(lambda: matches_landing(transport, step.level, before, local_tile()) or game_messages.saw_since(mark, CANT_REACH) or chat_shows_quest_lock()
                                                          or lock_message_since(mark),
                                                          TRANSPORT_WAIT_MS)
                crossed = matches_landing(transport, step.level, before, local_tile())
            if crossed:
                if to_level is not None:
                    yield from execution.delay_ticks(2)
                say(f'{transport["action"]} {transport["loc_name"]} at {transport["loc_x"]},{transport["loc_z"]}')
                # The essence mine's way back is the wizard who sent you in.
                essence = essence_session.note_entry_from_transport(transport)
                if essence is not None:
                    say(f'essence session return: {essence}')
                return True
            locked = yield from self._quest_lock(transport, say, mark)
            if locked:
                return False
            talked = yield from self._post_quest_talk(transport, approach, say)
            if talked:
                # The conversation is the unlock, so one more try settles it.
                continue
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
                yield from execution.delay_until(lambda: find_transport_loc(transport) is None or _can_step(approach, step) or game_messages.saw_since(mark, CANT_REACH) or chat_shows_quest_lock()
                                                 or lock_message_since(mark),
                                                 TRANSPORT_WAIT_MS)
                if game_messages.saw_since(mark, CANT_REACH):
                    say(f"the server can't reach the {transport['loc_name']} at {transport['loc_x']},{transport['loc_z']}")
                    return False
                locked = yield from self._quest_lock(transport, say, mark)
                if locked:
                    return False
                if find_transport_loc(transport) is not None and not _can_step(approach, step):
                    say(f'the {transport["loc_name"]} at {transport["loc_x"]},{transport["loc_z"]} did not open')
                    return False
                if self._follow.door_step_ticks > 0:
                    yield from execution.delay_ticks(self._follow.door_step_ticks)
            _core.walk_to(step.x, step.z, False)
            yield from execution.delay_until(lambda: walkgeom.is_on_far_side(local_tile(), approach, step), 3000)
        if walkgeom.is_on_far_side(local_tile(), approach, step):
            return True
        yield from self._quest_lock(transport, say)
        return False

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
            self._note_essence_entry(crossing, label, say)
        else:
            say(f'{label}: did not cross')
            yield from self._quest_lock(transport, say)
        return crossed

    def _note_essence_entry(self, crossing, label, say):
        # The server never sends the mine's way back, so it's remembered from the wizard.
        essence = essence_session.note_entry_from_crossing_label(label) or essence_session.note_entry_from_npc(crossing.get('npc') or crossing.get('locName'))
        if essence is not None:
            say(f'essence session return: {essence} (in through {label})')

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
        map_clicked = False
        for i in range(SHIP_DIALOGUE_STEPS):
            if _near_landing(crossing, radius):
                break
            pick = pick_choice(chat_dialog.options(), choose) if choose else None
            if pick is not None:
                yield from chat_dialog.choose_option(pick)
            elif chat_dialog.can_continue():
                yield from chat_dialog.continue_()
            elif crossing.get('mapChoice') and not map_clicked:
                # Why: the glider's dialogue opens a map, and its destination is a button beside the place's name; a
                # map is answered before any open modal is closed.
                button = interfaces.button_near_text(crossing['mapChoice'], _core.get_main_modal()) if modals.is_open() else None
                if button is not None and interfaces.click(button):
                    map_clicked = True
                    say(f"{label}: map → {crossing['mapChoice']}")
                else:
                    yield from execution.delay_ticks(1)
            elif modals.is_open():
                yield from modals.close()
                yield from execution.delay_ticks(1)
            else:
                yield from execution.delay_ticks(1)
        if _near_landing(crossing, radius):
            yield from execution.delay_ticks(2)
            say(f'{label}: arrived')
            self._note_essence_entry(crossing, label, say)
            return True
        say(f'{label}: did not land')
        return False

    def _blacklist_door(self, x, z):
        """Leaves the crossing at (x, z) out of this walk's routes."""
        if [x, z] not in self._avoid_doors:
            self._avoid_doors.append([x, z])

    def _quest_lock(self, transport, say, mark=None):
        """When the crossing answered with a lock phrase, in the dialogue or a game message since mark, leaves it
        out of the walk and clears the message: True when it did. Use with yield from."""
        if not chat_shows_quest_lock() and (mark is None or not lock_message_since(mark)):
            return False
        say(f"quest-locked {transport['loc_name']} at {transport['loc_x']},{transport['loc_z']}, leaving it out")
        self._blacklist_door(transport['loc_x'], transport['loc_z'])
        yield from dismiss_quest_lock_dialogue()
        return True

    # Why: some crossings open only after a talk the quest journal can't show, so this runs once a placement a
    # session, after the crossing refused.
    def _post_quest_talk(self, transport, approach, say):
        """Talks the NPC through the conversation that unlocks a crossing which refused, and walks back: True
        when it did. Use with yield from."""
        talk = post_quest_talk_for(transport['loc_x'], transport['loc_z'], approach.level)
        if talk is None:
            return False
        key = f"{talk['loc_x']},{talk['loc_z']},{talk['level']}"
        if key in self._post_quest_talks:
            return False
        if quests.status(talk['require_complete']) != 'complete':
            say(f"{talk['label']}: {talk['require_complete']} is not complete, nothing to unlock")
            return False
        self._post_quest_talks.append(key)
        say(f"{talk['label']}: the crossing refused; talking to {talk['npc']} to unlock it")
        reached = yield from self.walk_to(talk['stand'], 4, 180000, log=lambda m: say(f'  {m}'))
        if not reached:
            say(f"{talk['label']}: could not reach {talk['npc']}")
            return False
        for _ in range(talk.get('talks', 1)):
            npc = npcs.query().name(talk['npc']).nearest()
            if npc is None or not npc.interact('Talk-to'):
                say(f"{talk['label']}: {talk['npc']} can't be talked to")
                return False
            # Why: the dialogue takes a tick to arrive, and leaving on the first frame without it does nothing.
            shown = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), POST_QUEST_TALK_OPEN_MS)
            if not shown:
                say(f"{talk['label']}: {talk['npc']} said nothing")
                return False
            for _ in range(POST_QUEST_TALK_STEPS):
                pick = pick_choice(chat_dialog.options(), talk['choose']) if talk['choose'] else None
                if pick is not None:
                    yield from chat_dialog.choose_option(pick)
                elif chat_dialog.can_continue():
                    yield from chat_dialog.continue_()
                elif not chat_dialog.is_open():
                    again = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), POST_QUEST_TALK_OPEN_MS)
                    if not again:
                        break
                else:
                    yield from execution.delay_ticks(1)
        say(f"{talk['label']}: talked; back to the crossing")
        back = yield from self.walk_to(approach, 2, 180000, log=lambda m: say(f'  {m}'))
        return back

    def try_nearby_door(self, log=None, tiles=None, path_idx=0):
        """Opens a shut door or gate beside you, near the route ahead when one is given. Use with yield from."""
        say = log if log is not None else (lambda message: None)
        ahead = tiles[path_idx:path_idx + PROGRESS_WINDOW] if tiles is not None else None
        door = locs.query().where(lambda l: l.layer == LAYER_WALL and l.id not in DESERT_MINING_CAMP_SCRIPTED_DOOR_IDS and is_openable_barrier(l.name, l.actions()) and l.distance() <= 2
                                  and (ahead is None or _near_route(l.tile(), ahead))).nearest()
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
        # Why: rs2b0t's walkResilient pumps sustain and checks for an event every pass, and a backoff leaves no
        # outcome, so the pass after one plans the route again; without that the ladder circled scene, unstick and
        # backoff for good after one failed walk, silent and never giving up.
        from rs2004.catalogs.tasks import sustain
        state = walkgeom.LadderState(walkgeom.walk_chebyshev(local_tile(), dest))
        last = None
        unstick = 0
        last_terminal = None
        logged_at = _core.step_time()
        for i in range(100000):
            yield from sustain.run()
            if execution.event_signal.pending():
                say('walk interrupted by a runtime event; yielding to the runtime')
                self.last_outcome = 'interrupted'
                return False
            rung, state = walkgeom.advance(state, walkgeom.walk_chebyshev(local_tile(), dest), _arrived(dest, radius), False, last)
            kind = rung[0]
            if kind == 'arrived':
                return True
            if kind == 'interrupted':
                say('walk interrupted by a runtime event; yielding to the runtime')
                self.last_outcome = 'interrupted'
                return False
            if attempts is not None and state.no_progress_passes >= attempts:
                say(f'walk_resilient: {attempts} passes made no progress')
                self.last_outcome = 'failed'
                return False
            if _core.step_time() - logged_at > PROGRESS_LOG_MS:
                logged_at = _core.step_time()
                say(f'walk_resilient: {kind} toward ({dest.x},{dest.z}), best {state.best_dist} tiles, pass {state.no_progress_passes}')
            if kind == 'world':
                expansions = budget if rung[1] else None
                yield from self.walk_to(dest, radius, world_timeout, expansions, use_teleport_catalog, policy, bank_item_counts, avoid_zones, say)
                outcome = self.last_outcome
                if outcome == 'blocked':
                    return True
                if (outcome == 'failed' or outcome == 'unreachable') and len(self.last_missing_gate_items) > 0:
                    return False
                last = 'failed' if outcome == 'unreachable' else outcome
            elif kind == 'scene':
                yield from direct_navigator.walk_to(dest, scene, SCENE_TIMEOUT_MS)
                last = 'interrupted' if execution.event_signal.pending() else 'failed'
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
                last = None
            elif kind == 'verify':
                me = local_tile()
                probe = self._request(me, dest, budget, {'use_teleports': False}, False, [])
                points = (probe.get('waypoints') or []) if probe['ok'] else []
                terminal = Tile(points[-1]['x'], points[-1]['z'], points[-1]['level']) if points else None
                last = walkgeom.judge_probe(last_terminal, probe['ok'], terminal)
                if terminal is not None:
                    last_terminal = terminal
                if last == 'probe-dead':
                    say('walk_resilient: verify probe dead')
                else:
                    say(f'walk_resilient: verify probe fresh (terminal {terminal.x},{terminal.z})')
            elif kind == 'unreachable':
                say(f'walk_resilient: {dest} unreachable from here; stopping (best {state.best_dist} tiles)')
                self.last_outcome = 'unreachable'
                return False
        say('walk_resilient: iteration cap hit; yielding')
        self.last_outcome = 'failed'
        return False


def _quest_lock_door_near():
    """The door or gate within 3 tiles, when the dialogue open says it's locked, or None."""
    if not chat_shows_quest_lock():
        return None
    door = locs.query().where(lambda l: 'door' in (l.name or '').lower() or 'gate' in (l.name or '').lower()).within(3).nearest()
    return door.tile() if door is not None else None


def _waypoints(path):
    return [walkgeom.PathTile(w['x'], w['z'], w['level'], w.get('transport')) for w in path['waypoints']]


def _shut_door_at(tile):
    return locs.query().where(lambda l: l.tile() == tile and is_openable_barrier(l.name, l.actions())).nearest() is not None


def _near_route(tile, ahead):
    for point in ahead:
        if point.level == tile.level and walkgeom.chebyshev(point, tile) <= 1:
            return True
    return False


traversal = _Traversal()
