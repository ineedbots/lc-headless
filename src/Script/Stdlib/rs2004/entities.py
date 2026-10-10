"""NPCs, players, scenery and ground items, and the query that finds them. Mirrors rs2b0t's api/model/,
api/query/Query.ts and the Npcs, Players, Locs and GroundItems facades (MIT, see third_party/rs2b0t).

    guard = npcs.query().name('Guard').action('Pickpocket').within(3).nearest()
    if guard:
        guard.interact('Pickpocket')

Every object is a snapshot of the moment it was found; valid() asks whether it's still there.
"""

import _core
from rs2004.geometry import Tile

__all__ = [
    'Npc', 'Player', 'Loc', 'GroundItem', 'NpcType', 'ItemType', 'LocType', 'EntityQuery',
    'npcs', 'players', 'locs', 'ground_items',
]


def present_ops(ops):
    """The options a menu shows: its slots that hold one."""
    return [op for op in ops if op is not None and op != 'hidden']


def op_index(ops, action):
    """The option's number, 1 to 5, from its number or its text, matched without regard to case; -1 when
    the menu has no such option."""
    if isinstance(action, int) and not isinstance(action, bool):
        return action if 1 <= action <= len(ops) and ops[action - 1] is not None else -1
    wanted = str(action).lower()
    for i in range(len(ops)):
        if ops[i] is not None and ops[i].lower() == wanted:
            return i + 1
    return -1


def local_tile():
    return Tile(_core.get_x(), _core.get_z(), _core.get_level())


def _self_target(target):
    return target is not None and target[0] == 'player'


class _Located:
    """A world object: tile() is where it is, distance() how far it is from you, in tiles, Chebyshev, with
    another level very far away."""

    def tile(self):
        return Tile(self._x, self._z, self._plane)

    def distance(self):
        return local_tile().distance_to(self.tile())

    def actions(self):
        return present_ops(self._ops)


class Npc(_Located):
    """name, id, level (combat level, 0 for none), index, size, in_combat, health (0 until a hit shows it),
    max_health, animation (-1 for none), moving, and target: ('npc' or 'player', index) or None."""

    def interact(self, action):
        """Uses the option named action, walking there first. False when the NPC has no such option or has gone."""
        op = op_index(self._ops, action)
        if op == -1:
            return False
        return _core.interact_npc(self.index, op)

    def valid(self):
        current = _core.get_npc(self.index)
        return current is not None and current.name == self.name

    def network_tile(self):
        return self.tile()

    def targets_me(self):
        return _self_target(self.target) and self.target[1] == _core.get_pid()

    def targets_another_player(self):
        return _self_target(self.target) and self.target[1] != _core.get_pid()

    def __repr__(self):
        return f'Npc(index={self.index}, id={self.id}, name={self.name}, tile=({self._x}, {self._z}, {self._plane}))'


class Player(_Located):
    """name (None until its appearance arrives), index, combat_level, in_combat, health, max_health,
    animation, moving and target."""

    def actions(self):
        return present_ops(_core.get_player_menu())

    def interact(self, action):
        op = op_index(_core.get_player_menu(), action)
        if op == -1:
            return False
        return _core.interact_player(self.index, op)

    def valid(self):
        for player in _core.get_players():
            if player.index == self.index and player.name == self.name:
                return True
        return False

    def targets_me(self):
        return _self_target(self.target) and self.target[1] == _core.get_pid()

    def __repr__(self):
        return f'Player(index={self.index}, name={self.name}, tile=({self._x}, {self._z}, {self._plane}))'


class Loc(_Located):
    """Scenery: name, id (-1 when the server removed it), shape, angle, layer (a LAYER_* constant), and
    changed: False as the cache has it, True when the server changed it."""

    def interact(self, action):
        op = op_index(self._ops, action)
        if op == -1:
            return False
        return _core.interact_loc(self.id, self._x, self._z, op)

    def interact_via(self, points, action):
        """The same, walking the given (x, z) waypoints, each in a straight line, instead of a route."""
        op = op_index(self._ops, action)
        if op == -1:
            return False
        return _core.interact_loc_via(points, self.id, self._x, self._z, op)

    def valid(self):
        current = _core.get_loc_at(self._x, self._z, self.layer)
        return current is not None and current.id == self.id

    def __repr__(self):
        return f'Loc(id={self.id}, name={self.name}, tile=({self._x}, {self._z}, {self._plane}), layer={self.layer})'


class GroundItem(_Located):
    """An item on the ground: name, id and count."""

    def interact(self, action):
        op = op_index(self._ops, action)
        if op == -1:
            return False
        return _core.interact_ground_item(self, op)

    def valid(self):
        for item in _core.get_ground_items([self.id]):
            if item._x == self._x and item._z == self._z:
                return True
        return False

    def __repr__(self):
        return f'GroundItem(id={self.id}, name={self.name}, count={self.count}, tile=({self._x}, {self._z}, {self._plane}))'


class NpcType:
    def __repr__(self):
        return f'NpcType(id={self.id}, name={self.name})'


class ItemType:
    def __repr__(self):
        return f'ItemType(id={self.id}, name={self.name})'


class LocType:
    def __repr__(self):
        return f'LocType(id={self.id}, name={self.name})'


def _flatten(values):
    result = []
    for value in values:
        if isinstance(value, (list, tuple)):
            result.extend(value)
        else:
            result.append(value)
    return result


def _area_test(area):
    if hasattr(area, 'contains'):
        return lambda tile: area.contains(tile)
    min_x = area.get('min_x', area.get('minX'))
    max_x = area.get('max_x', area.get('maxX'))
    min_z = area.get('min_z', area.get('minZ'))
    max_z = area.get('max_z', area.get('maxZ'))
    return lambda tile: min_x <= tile.x <= max_x and min_z <= tile.z <= max_z


class EntityQuery:
    """Chainable filters, then a terminal that evaluates them against the scene as it is now. Names,
    ids and within() narrow the search in the client; the rest test each result."""

    def __init__(self, supply, reach):
        self._supply = supply
        self._reach = reach
        self._ids = None
        self._names = None
        self._radius = None
        self._layer = None
        self._filters = []

    def name(self, *names):
        """Any of the names, matched whole without regard to case."""
        self._names = [name.strip() for name in _flatten(names)]
        return self

    def id(self, *ids):
        self._ids = _flatten(ids)
        return self

    def action(self, action):
        """Offers this option, matched without regard to case."""
        wanted = action.lower()
        self._filters.append(lambda e: any([op.lower() == wanted for op in e.actions()]))
        return self

    def within(self, dist):
        """Within dist tiles of you."""
        self._radius = dist if self._radius is None else min(self._radius, dist)
        self._filters.append(lambda e: e.distance() <= dist)
        return self

    def within_of(self, origin, dist):
        """Within dist tiles of another tile, such as a camp's centre or a bank stand."""
        centre = Tile.from_tile(origin)
        radius = max(0, int(dist))
        self._filters.append(lambda e: max(abs(e._x - centre.x), abs(e._z - centre.z)) <= radius)
        return self

    def inside(self, area):
        """Inside an Area, or a dict of min_x, max_x, min_z and max_z (rs2b0t's minX and so on work too)."""
        test = _area_test(area)
        self._filters.append(lambda e: test(e.tile()))
        return self

    def layer(self, layer):
        """Scenery in one layer, a LAYER_* constant."""
        self._layer = layer
        return self

    def reachable(self):
        """Only targets a walk can reach, by the rule the matching interaction walks by."""
        self._filters.append(self._reach)
        return self

    def where(self, predicate):
        self._filters.append(predicate)
        return self

    def results(self):
        found = []
        for entity in self._supply(self._ids, self._names, self._radius, self._layer):
            if all([test(entity) for test in self._filters]):
                found.append(entity)
        return found

    def nearest(self):
        best = None
        best_distance = None
        for entity in self.results():
            distance = entity.distance()
            if best is None or distance < best_distance:
                best = entity
                best_distance = distance
        return best

    def nearest_prefer_local(self, prefer_radius):
        """The nearest, but only among results within prefer_radius of you when there are any."""
        radius = max(0, int(prefer_radius))
        found = self.results()
        if not found:
            return None
        pool = found
        if radius > 0:
            local = [entity for entity in found if entity.distance() <= radius]
            if local:
                pool = local
        best = None
        for entity in pool:
            if best is None or entity.distance() < best.distance():
                best = entity
        return best

    def first(self):
        found = self.results()
        return found[0] if found else None

    def exists(self):
        return len(self.results()) > 0

    def count(self):
        return len(self.results())


def _by_name(entities, names):
    if names is None:
        return entities
    wanted = [name.lower() for name in names]
    return [e for e in entities if e.name is not None and e.name.lower() in wanted]


class _Npcs:
    def query(self):
        return EntityQuery(
            lambda ids, names, radius, layer: _core.get_npcs(ids, radius, names),
            lambda npc: _core.can_reach_entity(npc._x, npc._z),
        )

    def all(self):
        return _core.get_npcs()

    def get(self, index):
        """The NPC with this index as it is now, or None once it's gone. Keep an index to find one again."""
        return _core.get_npc(index)

    def nearest(self, count=1):
        return sorted(self.all(), key=lambda npc: npc.distance())[:count]


class _Players:
    def query(self):
        return EntityQuery(
            lambda ids, names, radius, layer: _by_name(_core.get_players(radius), names),
            lambda player: _core.can_reach_entity(player._x, player._z),
        )

    def all(self):
        return _core.get_players()

    def local(self):
        """You, as a Player."""
        return _core.get_local_player()


class _Locs:
    def query(self):
        return EntityQuery(
            lambda ids, names, radius, layer: _core.get_locs(ids, radius, layer, names),
            lambda loc: _core.can_reach_loc(loc.id, loc._x, loc._z),
        )

    def at(self, tile, layer=None):
        """The scenery on a tile now: the server's change, or else the cache's."""
        where = Tile.from_tile(tile)
        return _core.get_loc_at(where.x, where.z, layer)


class _GroundItems:
    def query(self):
        return EntityQuery(
            lambda ids, names, radius, layer: _core.get_ground_items(ids, radius, names),
            lambda item: _core.can_reach_ground_item(item._x, item._z),
        )


npcs = _Npcs()
players = _Players()
locs = _Locs()
ground_items = _GroundItems()
