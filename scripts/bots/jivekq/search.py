"""Finding the queen and pulling her onto open ground: rs2b0t's scripts/JiveKQ/search.ts (MIT, see
thirdparty/rs2b0t)."""

from bots.jivekq.policy import in_lair, near


class QueenSighting:
    """Where a teammate or this account last saw the queen, which form (id), when (at, ms) and whether she was
    fighting one of the team."""

    def __init__(self, id, tile, at, engaged):
        self.id = id
        self.tile = tile
        self.at = at
        self.engaged = engaged

    def to_message(self):
        return {'id': self.id, 'tile': {'x': self.tile.x, 'z': self.tile.z, 'level': self.tile.level}, 'at': self.at, 'engaged': self.engaged}


WAYPOINTS = [Tile(x, z, 0) for x, z in [(3488, 9496), (3472, 9508), (3496, 9512), (3506, 9492), (3486, 9484), (3470, 9488)]]


def _distance(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


def approach_queen(queen, from_, usable):
    """The usable lair tile six out from the queen nearest from_, or None."""
    tiles = []
    for x in range(-6, 7):
        for z in range(-6, 7):
            if max(abs(x), abs(z)) == 6:
                tiles.append(Tile(queen.x + x, queen.z + z, queen.level))
    tiles.sort(key=lambda p: _distance(p, from_))
    for p in tiles:
        if in_lair(p) and usable(p):
            return p
    return None


def pull_queen(queen, phase, cross, step, usable, attempt=0):
    """Where to walk so the queen follows onto a tile the cross fits around: along each open direction her body
    can step, the first tile cross() accepts, out past her attack range. attempt picks among the directions."""
    candidates = []
    span = 18 if phase == 'melee' else 13
    for dx, dz in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
        from_ = queen
        for n in range(1, 9):
            to = Tile(queen.x + dx * n, queen.z + dz * n, queen.level)
            if not step(from_, to):
                break
            from_ = to
            target = Tile(to.x + dx * span, to.z + dz * span, to.level)
            if cross(to) and in_lair(target) and usable(target):
                candidates.append(target)
                break
    return candidates[attempt % len(candidates)] if candidates else None


class QueenSearch:
    """A circuit of the chamber, broken off for a fresh sighting."""

    def __init__(self):
        self.index = 0
        self.target = None
        self.since = 0
        self.visited_at = 0

    def _settle(self, now, usable):
        anchor = WAYPOINTS[self.index]
        for radius in range(4):
            for x in range(-radius, radius + 1):
                for z in range(-radius, radius + 1):
                    p = Tile(anchor.x + x, anchor.z + z, anchor.level)
                    if usable(p):
                        self.target = p
                        self.since = now
                        return

    def next(self, here, sighting, now, usable):
        if sighting is not None and now - sighting.at <= 8000 and sighting.at > self.visited_at:
            target = approach_queen(sighting.tile, here, usable)
            if target is not None and not near(here, target, 1):
                return target
            self.visited_at = sighting.at
        for _ in range(len(WAYPOINTS)):
            if self.target is not None and (near(here, self.target, 2) or now - self.since > 8000):
                self.index = (self.index + 1) % len(WAYPOINTS)
                self.target = None
            if self.target is None:
                self._settle(now, usable)
            if self.target is not None and not near(here, self.target, 2):
                return self.target
            self.index = (self.index + 1) % len(WAYPOINTS)
            self.target = None
        return None
