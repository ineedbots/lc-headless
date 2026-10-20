# Tiles and areas

## `Tile`

```python
Tile(x, z, level=0)
```

A world tile. `x` runs west to east, `z` south to north, and `level` is the floor, 0 to 3. The fields `x`, `z` and `level` are plain attributes.

Most functions that take a tile also take an `(x, z)` pair, which means "on my level" (or on the tile's level, for `distance_to`), or an `(x, z, level)` tuple.

| Member | Gives |
|---|---|
| `Tile.from_tile(tile)` | A `Tile` from anything with `x`, `z` and `level` attributes (a missing level is 0), or from an `(x, z)` or `(x, z, level)` tuple or list. Static |
| `tile.distance_to(other)` | The Chebyshev distance in tiles, the game's movement metric: `max(abs(dx), abs(dz))`. An `(x, z)` pair is on this tile's level. A tile on another level is 1,000,000 plus the distance, so it never counts as near |
| `tile.translate(dx, dz)` | A new `Tile` offset by `dx` and `dz`, on the same level |
| `tile.equals(other)` | Whether `other` is the same tile; an `(x, z)` pair is on this tile's level |
| `tile == other`, `tile != other` | The same, between two `Tile`s |
| `hash(tile)` | Tiles can be `dict` keys and `set` members |
| `x, z, level = tile` | Tiles unpack |
| `repr(tile)` | `Tile(3222, 3218, 0)` |

```python
here = game.tile()
bank = Tile(3253, 3420)
if here.distance_to(bank) > 10:
    yield from traversal.walk_resilient(bank)
```

## `Area`

A region on one level. Make one with a static constructor; every kind has `contains(tile)` and `get_random_tile()`.

### `Area.rectangular(a, b)`

The rectangle with corners `a` and `b`, any two opposite corners, both included, on `a`'s level.

### `Area.circular(center, radius)`

The tiles within `radius` of `center` by straight-line distance (`dx² + dz² ≤ radius²`), on `center`'s level. Note that this is a disc, unlike `Tile.distance_to`, which is a square.

### `Area.polygon(points, level=0)`

The polygon through the `(x, z)` points, in order, edges included, on `level`. Fewer than 3 points raises `ValueError`.

### Methods

| Method | Gives |
|---|---|
| `area.contains(tile)` | Whether the tile is inside. `tile` is a `Tile`, or an `(x, z, level)` tuple; **an `(x, z)` pair is on level 0** |
| `area.get_random_tile()` | A random tile inside. A circle or polygon tries 64 times, then falls back to its centre or first point |

```python
FIELD = Area.rectangular(Tile(3253, 3255), Tile(3265, 3298))
if not FIELD.contains(game.tile()):
    yield from direct_navigator.walk_to(FIELD.get_random_tile(), 1)

cows = npcs.query().name('Cow').inside(FIELD).results()
```

An `Area`, or a dict of `min_x`, `max_x`, `min_z` and `max_z`, can be passed to a query's [`inside()`](world.md#filters).
