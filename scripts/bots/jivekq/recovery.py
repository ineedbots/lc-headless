"""A teammate's death, and the items worth taking back off the pile: rs2b0t's scripts/JiveKQ/recovery.ts (MIT, see
thirdparty/rs2b0t)."""

from bots.jivekq.loadout import BOW, GEAR
from bots.jivekq.policy import near


def is_number(v):
    return (type(v) is int or type(v) is float) and v == v


def is_integer(v):
    return is_number(v) and int(v) == v


def is_point(v):
    return isinstance(v, dict) and is_number(v.get('x')) and is_number(v.get('z')) and is_number(v.get('level'))


def to_tile(v):
    return Tile(int(v['x']), int(v['z']), int(v['level']))


def tile_message(t):
    return {'x': t.x, 'z': t.z, 'level': t.level}


class RecoveryItem:
    def __init__(self, id, count):
        self.id = id
        self.count = count

    def to_message(self):
        return {'id': self.id, 'count': self.count}


class DeathReport:
    """When (at, ms) and where an account died, what it held (items) and what already lay on the tile (ground)."""

    def __init__(self, at, tile, items, ground):
        self.at = at
        self.tile = tile
        self.items = items
        self.ground = ground

    def to_message(self):
        return {'at': self.at, 'tile': tile_message(self.tile), 'items': [i.to_message() for i in self.items], 'ground': [i.to_message() for i in self.ground]}


class Casualty:
    def __init__(self, name, session, trip, death):
        self.name = name
        self.session = session
        self.trip = trip
        self.death = death


def _items(value):
    if not isinstance(value, list) or len(value) > 56:
        return None
    out = []
    for i in value:
        if not isinstance(i, dict):
            return None
        id = i.get('id')
        count = i.get('count')
        if not is_integer(id) or id <= 0 or id >= 65536 or not is_integer(count) or count <= 0 or count > 2147483647:
            return None
        out.append(RecoveryItem(int(id), int(count)))
    return out


def death_report(value, now):
    """The report a teammate's message carries, or None for one malformed, from the future or over three minutes old."""
    if not isinstance(value, dict):
        return None
    at = value.get('at')
    tile = value.get('tile')
    if not is_number(at) or at > now + 1000 or now - at > 180000 or not isinstance(tile, dict):
        return None
    for k in ['x', 'z', 'level']:
        v = tile.get(k)
        if not is_integer(v) or v < 0 or v >= (4 if k == 'level' else 16384):
            return None
    items = _items(value.get('items'))
    ground = _items(value.get('ground'))
    if items is None or ground is None:
        return None
    return DeathReport(at, to_tile(tile), items, ground)


def recovery_drops(death, drops):
    """The drops on the death tile the account held and that outnumber what lay there before, gear first. Each drop
    has id, count and tile."""
    gear = set(GEAR + [BOW])
    pile = [d for d in drops if near(d.tile, death.tile, 0)]

    def counted(items, id):
        return sum([i.count for i in items if i.id == id])

    wanted = [d for d in pile if any([i.id == d.id for i in death.items]) and counted(pile, d.id) > counted(death.ground, d.id)]
    wanted.sort(key=lambda d: (0 if d.id in gear else 1, d.id))
    return wanted
