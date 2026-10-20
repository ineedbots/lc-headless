# The world: NPCs, players, scenery and ground items

Four facades find what's in the loaded area: `npcs`, `players`, `locs` (scenery) and `ground_items`. Each has `query()`, a chain of filters that ends in a terminal such as `nearest()`.

```python
guard = npcs.query().name('Guard').action('Pickpocket').within(3).nearest()
if guard is not None:
    guard.interact('Pickpocket')

oak = locs.query().name('Oak').action('Chop down').reachable().nearest()
coins = ground_items.query().name('Coins').within(12).nearest()
```

- [Facades](#facades)
- [EntityQuery](#entityquery)
- [Common to every thing](#common-to-every-thing)
- [Npc](#npc), [Player](#player), [Loc](#loc), [GroundItem](#grounditem), [Projectile](#projectile)
- [interact()](#interactaction)
- [Cache types](#cache-types): NpcType, ItemType, LocType

## Facades

### `npcs`

| Method | Gives |
|---|---|
| `npcs.query()` | An `EntityQuery` over the NPCs in view |
| `npcs.all()` | Every NPC in view, as a list of `Npc` |
| `npcs.get(index)` | The NPC with that index as it is now, or `None` once it's gone. Keep an NPC's `index` to find it again |
| `npcs.nearest(count=1)` | A **list** of the `count` nearest NPCs |

### `players`

| Method | Gives |
|---|---|
| `players.query()` | An `EntityQuery` over the other players in view |
| `players.all()` | Every other player in view |
| `players.local()` | You, as a `Player` |

### `locs`

| Method | Gives |
|---|---|
| `locs.query()` | An `EntityQuery` over the scenery in the loaded area, nearest first |
| `locs.at(tile, layer=None)` | The scenery on a tile now: the server's change, or else the cache's. Without `layer`, the first in layer order, preferring scenery that's there to a removed one. `None` when there's none |

### `ground_items`

| Method | Gives |
|---|---|
| `ground_items.query()` | An `EntityQuery` over the items on the ground |

## EntityQuery

Filters return the query, so they chain. Nothing is searched until a terminal runs; each terminal searches the scene as it is at that moment.

### Filters

| Filter | Keeps |
|---|---|
| `name(*names)` | Any of the names, matched whole and without regard to case. Takes several names, or lists of them. A thing whose type has no name never matches. A second `name()` replaces the first |
| `id(*ids)` | Any of the ids. Takes several ids, or lists. A second `id()` replaces the first |
| `action(action)` | Things whose menu offers the option, matched without regard to case |
| `within(dist)` | Things within `dist` tiles of you (Chebyshev; another level is too far) |
| `within_of(origin, dist)` | Things within `dist` tiles of `origin`, a `Tile` or `(x, z)`. Compares `x` and `z` only, not the level |
| `inside(area)` | Things inside an [`Area`](geometry.md#area), or a dict of `min_x`, `max_x`, `min_z` and `max_z` (rs2b0t's `minX` and so on work too; a dict ignores the level) |
| `layer(layer)` | Scenery in one [layer](constants.md#scenery-layers). Ignored on the other queries |
| `reachable()` | Things a walk can reach, by the same rule the matching interaction walks by |
| `where(predicate)` | Things for which `predicate(thing)` is true |

`name`, `id`, `within` and `layer` narrow the search inside the client, so they're cheap. The rest test each result in Python.

### Terminals

| Terminal | Gives |
|---|---|
| `results()` | A list of every match, in the server's order (scenery nearest first) |
| `nearest()` | The nearest match by tile distance, or `None`. A tie goes to the first |
| `nearest_prefer_local(prefer_radius)` | The nearest among matches within `prefer_radius` of you when there are any, otherwise the nearest of all. `None` without matches |
| `first()` | The first match, or `None` |
| `exists()` | Whether there's a match |
| `count()` | How many match |

"Nearest" counts tiles, not walking steps: with `reachable()`, the nearest reachable target may still be a long walk round.

## Common to every thing

`Npc`, `Player`, `Loc` and `GroundItem` are **snapshots** taken when the query ran. Their fields don't change; call `valid()` to ask whether the thing is still there, or query again.

| Method | Gives |
|---|---|
| `tile()` | Where it is, as a `Tile` (an NPC's south-west tile) |
| `distance()` | Chebyshev tiles from you; another level counts as 1,000,000 or more |
| `actions()` | The options its right-click menu shows, without empty slots |
| `interact(action)` | Walks there and uses the option. See [interact()](#interactaction) |
| `valid()` | Whether it's still there |

## `Npc`

| Field | Meaning |
|---|---|
| `index` | Its slot in the server's NPC list; stable while it's in view |
| `id` | Its type id |
| `name` | Its name, or `None` when the cache has no type for it |
| `level` | Its combat level, 0 for none |
| `size` | Tiles along each side |
| `in_combat` | It was hit within the last [`COMBAT_TICKS`](constants.md#combat) (8) ticks. 2004 has no combat-state packet |
| `health`, `max_health` | From its last hit splat; 0 until a hit shows them |
| `animation` | The animation playing, -1 for none |
| `moving` | Whether it's moving |
| `target` | What it's facing: `('npc', index)`, `('player', index)`, or `None` |

| Method | Gives |
|---|---|
| `valid()` | An NPC with the same index and name is still in view |
| `targets_me()` | It's facing you |
| `targets_another_player()` | It's facing a player other than you |
| `network_tile()` | The same as `tile()`, for rs2b0t compatibility |

## `Player`

| Field | Meaning |
|---|---|
| `index` | Its slot in the server's player list |
| `name` | Its name, or `None` until its appearance arrives |
| `combat_level` | Its combat level, 0 until its appearance arrives |
| `in_combat`, `health`, `max_health`, `animation`, `moving`, `target` | As for `Npc` |

| Method | Gives |
|---|---|
| `actions()` | The player menu the server set, such as `['Follow', 'Trade with']`. On revision 225 it's fixed: `Duel-with`, `Attack`, `Follow`, `Trade with` |
| `valid()` | A player with the same index and name is still in view |
| `targets_me()` | It's facing you |

## `Loc`

Scenery: trees, rocks, doors, booths, ladders.

| Field | Meaning |
|---|---|
| `id` | Its type id; -1 when the server removed it |
| `name` | Its name, or `None` |
| `shape` | Its shape, 0 to 22 (a wall, a corner, a ground decoration...) |
| `angle` | Its rotation, 0 to 3 |
| `layer` | Its [layer](constants.md#scenery-layers): wall, wall decoration, ground or ground decoration |
| `changed` | `False` as the cache placed it, `True` when the server added or changed it |

| Method | Gives |
|---|---|
| `valid()` | The same id is still on its tile in its layer |
| `interact_via(points, action)` | As `interact`, but walks your `(x, z)` waypoints, each leg in a straight line, instead of a computed route |

Every ore rock is named "Rocks", so find rocks by id. See [`ROCK_TYPES`](catalogs.md#fishing-and-mining).

## `GroundItem`

| Field | Meaning |
|---|---|
| `id` | Its item id |
| `name` | Its name, or `None` |
| `count` | The stack size |

`valid()` is true while an item with the same id lies on the same tile. Its `actions()` offer "Take" where its type has nothing in that slot, as the game's menu does.

## `Projectile`

Passed to the `projectile` event; not found by a query.

| Member | Meaning |
|---|---|
| `spotanim` | Its graphic id |
| `source()`, `destination()` | Where it was launched from and aimed at, as `Tile`s |
| `target` | `('npc', index)`, `('player', index)`, or `None` for one aimed at the ground |
| `start_delay`, `end_delay` | When it leaves and lands, in the client's 20 ms cycles |
| `tick` | The server tick it was launched on |
| `targets_me()` | It's aimed at you |

## `interact(action)`

`action` is the option's text as the menu shows it, matched without regard to case (`'Attack'`, `'chop down'`), or its number, 1 to 5.

- It walks to the thing first, routing around walls and scenery as the game's own client does, then uses the option. It returns at once, after queuing the packets: the effects show in the state over the next ticks.
- **Returns** `False`, sending nothing, when the thing has no such option (including a number outside 1 to 5, or an empty slot) or has gone; `True` otherwise.

```python
cow = npcs.query().name('Cow').within(8).where(lambda n: not n.in_combat).nearest()
if cow is not None and cow.interact('Attack'):
    yield from execution.delay_until(lambda: game.in_combat(), 3000)
```

To use an item on a thing, see [`InvItem.use_on`](items.md#invitem). To cast a spell on one, see [Spells](side-tabs.md#spells).

## Cache types

The cache's definitions, from [`reader`](game.md#reader). Each returns `None` for an id the cache doesn't have.

### `NpcType` — `reader.npc_type(id)`

| Field | Meaning |
|---|---|
| `id`, `name`, `examine` | Its id, name and examine text (`None` where absent) |
| `ops` | Five strings, `None` where the menu has nothing |
| `size` | Tiles along each side |
| `combat_level` | Its combat level, or `None` |

### `ItemType` — `reader.item_type(id)`

| Field | Meaning |
|---|---|
| `id`, `name`, `examine` | As above |
| `ops` | Its ground options, five, `None` where empty |
| `inventory_ops` | Its backpack options, five, `None` where empty |
| `stackable`, `members` | Whether it stacks, and whether it's members-only |
| `value` | Its shop value |
| `note_of` | For a banknote, the id of the item it's a note of; else `None` |

### `LocType` — `reader.loc_type(id)`

| Field | Meaning |
|---|---|
| `id`, `name`, `examine`, `ops` | As above |
| `width`, `length` | Its size in tiles |
| `blocks_walk`, `blocks_projectiles` | Whether it blocks movement and projectiles |

`reader.item_ids(name)`, `reader.npc_ids(name)` and `reader.loc_ids(name)` look a name up the other way, giving every id with that name, without regard to case.

Names and options are exactly as the server's cache has them, loaded at startup from `client.cacheDirectory`.
