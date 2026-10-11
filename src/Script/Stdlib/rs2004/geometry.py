"""Tiles and areas. Ported from rs2b0t's geometry/Tile.ts and Area.ts (MIT, see thirdparty/rs2b0t)."""

import random

__all__ = ['Tile', 'Area']

# rs2b0t: a tile on another level is this far away, so it never counts as near.
OTHER_LEVEL_DISTANCE = 1000000


def _coords(tile, level=0):
    """x, z and level from a tile, or from an (x, z) pair, which is on the given level."""
    if isinstance(tile, (tuple, list)):
        if len(tile) == 2:
            return tile[0], tile[1], level
        return tile[0], tile[1], tile[2]

    level = getattr(tile, 'level', 0)
    return tile.x, tile.z, 0 if level is None else level


class Tile:
    """A world tile. Distances are Chebyshev, the game's movement metric."""

    def __init__(self, x, z, level=0):
        self.x = x
        self.z = z
        self.level = level

    @staticmethod
    def from_tile(tile):
        """A Tile from anything with x, z and level, or an (x, z) or (x, z, level) tuple."""
        x, z, level = _coords(tile)
        return Tile(x, z, level)

    def distance_to(self, other):
        """Chebyshev distance; an (x, z) pair is on this tile's level."""
        x, z, level = _coords(other, self.level)
        distance = max(abs(self.x - x), abs(self.z - z))
        if self.level != level:
            return OTHER_LEVEL_DISTANCE + distance
        return distance

    def translate(self, dx, dz):
        return Tile(self.x + dx, self.z + dz, self.level)

    def equals(self, other):
        x, z, level = _coords(other, self.level)
        return self.x == x and self.z == z and self.level == level

    def __eq__(self, other):
        if not isinstance(other, Tile):
            return NotImplemented
        return self.equals(other)

    def __ne__(self, other):
        if not isinstance(other, Tile):
            return NotImplemented
        return not self.equals(other)

    def __hash__(self):
        return hash((self.x, self.z, self.level))

    def __iter__(self):
        return iter((self.x, self.z, self.level))

    def __repr__(self):
        return f'Tile({self.x}, {self.z}, {self.level})'


class Area:
    """A region of the map on one level: a rectangle, a circle or a polygon."""

    def contains(self, tile):
        raise NotImplementedError

    def get_random_tile(self):
        raise NotImplementedError

    @staticmethod
    def rectangular(a, b):
        """The rectangle with corners a and b, both included, on a's level."""
        return _RectangularArea(a, b)

    @staticmethod
    def circular(center, radius):
        return _CircularArea(center, radius)

    @staticmethod
    def polygon(points, level=0):
        """The polygon through the (x, z) points, its edges included."""
        return _PolygonArea(points, level)


class _RectangularArea(Area):
    def __init__(self, a, b):
        ax, az, alevel = _coords(a)
        bx, bz, _ = _coords(b)
        self.min_x = min(ax, bx)
        self.max_x = max(ax, bx)
        self.min_z = min(az, bz)
        self.max_z = max(az, bz)
        self.level = alevel

    def contains(self, tile):
        x, z, level = _coords(tile)
        return level == self.level and self.min_x <= x <= self.max_x and self.min_z <= z <= self.max_z

    def get_random_tile(self):
        return Tile(random.randint(self.min_x, self.max_x), random.randint(self.min_z, self.max_z), self.level)

    def __repr__(self):
        return f'Area.rectangular(({self.min_x}, {self.min_z}, {self.level}), ({self.max_x}, {self.max_z}, {self.level}))'


class _CircularArea(Area):
    def __init__(self, center, radius):
        self.center = Tile.from_tile(center)
        self.radius = radius

    def contains(self, tile):
        x, z, level = _coords(tile)
        dx = x - self.center.x
        dz = z - self.center.z
        return level == self.center.level and dx * dx + dz * dz <= self.radius * self.radius

    def get_random_tile(self):
        for _ in range(64):
            x = self.center.x + random.randint(-self.radius, self.radius)
            z = self.center.z + random.randint(-self.radius, self.radius)
            if self.contains((x, z, self.center.level)):
                return Tile(x, z, self.center.level)
        return Tile(self.center.x, self.center.z, self.center.level)

    def __repr__(self):
        return f'Area.circular({self.center}, {self.radius})'


class _PolygonArea(Area):
    def __init__(self, points, level):
        self.points = [(p[0], p[1]) for p in points]
        if len(self.points) < 3:
            raise ValueError('a polygon needs at least 3 points')
        self.level = level

    def _on_edge(self, x, z):
        count = len(self.points)
        for i in range(count):
            ax, az = self.points[i]
            bx, bz = self.points[(i + 1) % count]
            cross = (bx - ax) * (z - az) - (bz - az) * (x - ax)
            if cross == 0 and min(ax, bx) <= x <= max(ax, bx) and min(az, bz) <= z <= max(az, bz):
                return True
        return False

    def contains(self, tile):
        x, z, level = _coords(tile)
        if level != self.level:
            return False
        if self._on_edge(x, z):
            return True

        inside = False
        count = len(self.points)
        j = count - 1
        for i in range(count):
            xi, zi = self.points[i]
            xj, zj = self.points[j]
            if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
                inside = not inside
            j = i
        return inside

    def get_random_tile(self):
        xs = [p[0] for p in self.points]
        zs = [p[1] for p in self.points]
        for _ in range(64):
            x = random.randint(min(xs), max(xs))
            z = random.randint(min(zs), max(zs))
            if self.contains((x, z, self.level)):
                return Tile(x, z, self.level)
        return Tile(self.points[0][0], self.points[0][1], self.level)

    def __repr__(self):
        return f'Area.polygon({self.points}, {self.level})'
