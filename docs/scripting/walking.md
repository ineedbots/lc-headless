# Walking: `direct_navigator`, `traversal`, `reach` and `game_messages`

Three layers, from short to long:

| Facade | Range | Use it for |
|---|---|---|
| [`direct_navigator`](#direct_navigator) | The loaded area, about 104 × 104 tiles around you | A click on a nearby tile, routed around walls |
| [`traversal`](#traversal) | The whole map | Getting anywhere: through doors and gates, up and down stairs, through tolls and onto ships |
| [`reach`](#reach) | The last few tiles | Walk to a stand, use something, and open the door in the way if the server says it can't be reached |

A destination is a [`Tile`](geometry.md#tile), or an `(x, z)` pair on your level.

## `direct_navigator`

Walking within the loaded area, with routes computed as the game's own client computes them.

| Method | Gives or does |
|---|---|
| `direct_navigator.walk(dest, run=False)` | One walk click toward `dest`. `False` when `dest` is in view but can't be reached; a tile beyond the loaded area is walked to in a straight line. Doesn't wait |
| `direct_navigator.walk_to(dest, radius=2, timeout_ms=45000, run=False)` | **Wait.** Walks until within `radius` tiles of `dest`, checking every 2 ticks, and clicking again when you stop moving or every 2.4 seconds. `True` on arrival, `False` when unreachable or at the timeout |
| `direct_navigator.walk_path(points, run=False)` | Walks through up to 25 `(x, z)` waypoints, each leg in a straight line, without routing. Doesn't wait |
| `direct_navigator.reachable(dest)` | Whether a walk can end on the tile |
| `direct_navigator.path(dest)` | The waypoints a walk would send, as `Tile`s, or `None` without a route |
| `direct_navigator.destination()` | Where the last walk is heading, until it ends, or `None` |
| `direct_navigator.last_outcome` | How the last `walk_to` ended: `'arrived'`, `'unreachable'` or `'timeout'` |

`run=True` holds the run key for that walk, as Ctrl-click does.

```python
yield from direct_navigator.walk_to(Tile(3222, 3218), radius=1)
```

## `traversal`

Walks anywhere on the map. The route comes from a search over the whole world, built from the cache at startup together with rs2b0t's walker data (`client.navDirectory`): doors, gates, stairs, ladders, the Al Kharid toll, ships, and other crossings. The walker then follows it as rs2b0t's does: it clicks the furthest tile ahead it can walk to, takes each crossing when it reaches it, and plans again when the world disagrees, such as a door that won't open, a stall, or a step off the route.

```python
arrived = yield from traversal.walk_resilient(Tile(3253, 3420, 0), 2)
if not arrived:
    log('Walk failed:', traversal.last_outcome, traversal.last_reason)
```

### `traversal.walk_to(dest, radius=2, timeout_ms=None, max_expansions=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None, force_repath=False)`

**Wait.** One planned walk to within `radius` of `dest`, replanning up to 5 times.

| Parameter | Meaning |
|---|---|
| `dest` | A `Tile`, or anything [`Tile.from_tile`](geometry.md#tile) takes |
| `radius` | How near counts as there |
| `timeout_ms` | The whole walk's limit; 5 minutes when `None` |
| `max_expansions` | The route search's budget, in nodes; the default when `None` |
| `use_teleport_catalog` | Plan spell teleports the backpack has runes for. `None` uses `teleports_enabled()`, which is `False` |
| `policy` | A dict of `use_teleports`, `use_ships`, `use_shortcuts`, `allow_teleport_ids`, `deny_teleport_ids`. `use_teleports: False` also turns the catalog off |
| `bank_item_counts` | Accepted for rs2b0t compatibility; not used yet |
| `avoid_zones` | Areas a route never enters, though it may leave one it starts in: catalog ids such as `'white-wolf-mountain'`, or dicts of `min_x`, `max_x`, `min_z`, `max_z` and optionally `level`. The automatic zones are always added: `'draynor-jail-guards'` at combat level 50 and below, unless the walk starts or ends inside it |
| `log` | A function given progress lines, such as `log` itself |
| `force_repath` | Plan again at the next step |

**Gives** `True` on arrival, or when the route ends as close as it can get (`last_outcome` `'closest'` or `'blocked'`); `False` otherwise.

`**NAV_PURE_WALK` and `**NAV_WITH_TELES` are ready-made keyword sets:

```python
yield from traversal.walk_to(dest, 2, **NAV_WITH_TELES)
```

| Constant | Value |
|---|---|
| `NAV_PURE_WALK` | `{'use_teleport_catalog': False, 'policy': {'use_teleports': False}}` |
| `NAV_WITH_TELES` | `{'use_teleport_catalog': True, 'policy': {'use_teleports': True}}` |

### `traversal.walk_resilient(dest, radius=2, attempts=None, timeout_ms=None, scene_radius=None, max_budget=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None)`

**Wait.** `walk_to` behind rs2b0t's escalation ladder. Prefer it for most walks. When a world walk fails it tries, in turn, a `direct_navigator` walk, opening a door beside you and an unstick step, then a backoff of 2 to 16 ticks, and plans again. After three passes without getting nearer, it checks with a fresh search whether `dest` is reachable at all.

| Parameter | Meaning |
|---|---|
| `attempts` | Give up after this many passes without progress; `None` keeps going until the goal is found unreachable |
| `timeout_ms` | Each world walk's limit; 90 seconds when `None` |
| `scene_radius` | The radius for the loaded-area walk; `radius + 1` when `None` |
| `max_budget` | The search budget of a retry with a bigger budget; 1,200,000 when `None` |
| The rest | As `walk_to` |

**Gives** `True` on arrival or `'blocked'`; `False` when unreachable, interrupted, or out of attempts.

### Other members

| Member | Gives or does |
|---|---|
| `traversal.last_outcome` | How the last walk ended: `'arrived'`, `'closest'` (as near as the route goes), `'blocked'`, `'budget'` (the search ran out of budget), `'failed'`, `'unreachable'` or `'interrupted'` |
| `traversal.last_reason` | Why the last search failed, as text, or `None` |
| `traversal.remaining` | Route tiles left on the walk in progress |
| `traversal.request_repath(reason=None)` | Plans the walk in progress again at its next step |
| `traversal.route_cost(start, dest, max_expansions=300000)` | The cost of the route a walk would plan, without teleports and without walking, or `None` when there's none, as past a gate the account can't open |
| `traversal.try_nearby_door(log=None)` | **Wait.** Opens a shut door or gate within 2 tiles, and waits up to 4 seconds for it to open. `True` when it did |
| `traversal.teleports_enabled()` | Whether walks use teleports unless told otherwise: `False`, as in rs2b0t |

### Requirements

Each hop of a route is checked against the account: skill levels, quest status from the quest tab, the coins for a toll or fare, items it needs, and members' areas. A hop the account can't make isn't planned, so a walk into Al Kharid without 10 coins goes round rather than through the toll gate. On revision 225 the server doesn't say whether the world is members, so walks are planned as on a free world.

`world_state()` gives what's checked, as a dict: `members`, `skills` (name to base level), `items` and `worn` (name to count), `quests` (name to `'not_started'`, `'started'`, `'complete'` or `'unknown'`) and `free_slots`.

### Banks

rs2b0t's list of banks, ranked for the account. A bank is a dict in rs2b0t's camelCase: `name`, `tile` (`{'x', 'z', 'level'}`), and where needed `approach` (a stand tile), `access` (a chest or other loc: `name`, `op`, `openFirst`), `npcAccess` (a banker: `name`, `op`, `choose`) and `requires` (`skill`, `quest`, `setting`).

| Function | Gives |
|---|---|
| `bank_locations()` | Every known bank |
| `bank_unlocked(bank, settings=None)` | Whether the account can use it: its skill level, its quest, and for a bank a script opts into (Zanaris, the Mage Arena), the named key in `settings`, a dict of booleans |
| `nearest_banks(tile, settings=None)` | The usable banks, nearest first, by straight-line distance whatever the level |
| `nearest_bank(tile, settings=None)` | The first of those, or `None` |
| `nearest_reachable_bank(tile, candidates=4, settings=None)` | Of the `candidates` nearest, the one the shortest route reaches, or `None`. Slower: it plans routes |

[`banking.open()`](bank.md#banking) uses these to walk to a bank when none is near.

### Helpers

| Function | Gives |
|---|---|
| `pick_choice(options, choose)` | The first of `options` containing any text in `choose`, without regard to case, or `None` |
| `special_crossing_for_transport(transport, approach, step)` | The walker's special crossing (toll, ship and so on) for a route hop, or `None`. Used inside the walker |

## `reach`

The last mile. Walk to a stand, use something, and when the server answers "I can't reach that!", open the door in front (or close an open one swung across the way) and try again. Each function is a **Wait** that gives a status:

| Status | Means |
|---|---|
| `'done'` | `expect()` held |
| `'retry'` | It didn't yet; call again later |
| `'unreachable'` | The stand or the target can't be reached, and no door explains it |

`reach` walks to the stand within the loaded area, so the stand must be reachable from where you are: it opens the door between the stand and the target, not doors on the way there. Use `traversal` to get near first.

### `reach.loc_op(name, op, near, expect, within=10, id=None, expect_ms=12000, refused=None, log=None)`

Walks to `near`, then uses `op` on the nearest loc named `name` offering `op` within `within` tiles, until `expect()` is true or `expect_ms` passes.

- `id` picks one loc when several share the name.
- `refused` is a game message, text or a callable, meaning the op can't run yet, so it isn't retried.

```python
mark = game_messages.mark()
status = yield from reach.loc_op('Crate', 'Search', Tile(3208, 3210),
                                 lambda: game_messages.saw_since(mark, 'You search the crate'))
```

### `reach.npc_dialog(name, near, open_ms=15000, log=None)`

Walks to `near` and talks to the NPC (its Talk option) until a dialogue opens. An NPC can wander, which would put the server's verdict off for good, so the scene within 10 tiles is searched for a door in the way first. Gives `'done'` at once when a dialogue is already open beside the NPC.

### `reach.entity_op(find, op, expect, open_when_unreachable=False, expect_ms=5000, what=None, log=None)`

Uses `op` on whatever `find()` gives (an `Npc`, `Loc`, `GroundItem` or `Player`, or `None`), until `expect()`. With `open_when_unreachable`, searches the scene for a door rather than waiting for the server's verdict. `what` names the target in log lines.

### Door rules

| Function | Gives |
|---|---|
| `is_openable_barrier(name, actions)` | A shut door or gate: its name contains "door" or "gate", and it has an option starting "Open" |
| `is_open_barrier_leaf(name, actions)` | An open one: the same, with an option starting "Close" |
| `open_op(actions)`, `close_op(actions)`, `talk_op(actions)` | The first option starting "open", "close" or "talk", without regard to case, or `None` |
| `toward_dest(door, here, dest)` | The door is no further from `dest` than you are, give or take 4 tiles |

## `game_messages`

What the server said after an action. It keeps the last 100 game messages.

```python
mark = game_messages.mark()
loc.interact('Open')
blocked = yield from execution.delay_until(lambda: game_messages.saw_since(mark, CANT_REACH), 3000)
```

| Method | Gives |
|---|---|
| `game_messages.mark()` | A mark: messages after now come after it. Marks carry on across reconnects |
| `game_messages.since(mark)` | The messages after `mark`, oldest first, as `GameMessage`s with `seq` (its place in order) and `text` |
| `game_messages.saw_since(mark, pattern)` | Whether one matches |
| `game_messages.first_since(mark, pattern)` | The first that matches, or `None` |
| `game_messages.recent(limit=8)` | The newest messages, newest first |

A pattern is text, matched as part of the message without regard to case, or a callable given the text.

| Constant | Matches |
|---|---|
| `CANT_REACH` | `"i can't reach that"` |
| `WRONG_SIDE(text)` | A function: "You can't do that from here." or "You cannot do that from here." |
