# Events

Everything the server tells the client arrives as an event. Every event has one name, and a script hears it in either of two ways:

- **A hook**: a function (module-level script) or method (bot) named `on_<name>`, such as `on_skill_xp`.
- **A subscription**: `events.on(name, callback)`, or `self.on(name, callback)` in a bot.

Hooks and subscriptions that aren't there cost nothing: the client skips events nobody listens to.

```python
def on_server_message(msg):
    if msg.startswith('Oh dear'):
        stop_account()

def on_skill_xp(e):
    log('Gained', e.delta, e.name, 'xp')

unsubscribe = events.on('npc_despawned', lambda npc: log(npc.name, 'left'))
```

## `events`

| Method | Does |
|---|---|
| `events.on(event, callback)` | Calls `callback` each time the event happens. Returns a function that ends the subscription. An unknown event name raises `ValueError` (listing the names); a non-callable raises `TypeError` |
| `events.off(event, callback)` | Ends a subscription; does nothing if there isn't one |

A bot's `self.on(event, callback)` subscribes until the bot stops, and returns `None`.

For each event, the hook runs first, then the subscribers in the order they subscribed. Hooks and subscribers can't wait: a hook that returns a generator stops the script with `TypeError`. An exception in either stops the script.

## Payload events

These pass one argument, an `Event`, with one attribute per field. `repr(e)` shows them all.

| Event | Fields | Happens when |
|---|---|---|
| `tick` | `tick` | A server tick passed. `tick` is [`game.tick()`](game.md#game) |
| `chat_message` | `type`, `username`, `text` | Any line arrived in the chat box. `type` is `'game'`, `'public'`, `'private'`, `'trade_request'` or `'duel_request'`; `username` is `None` for a game message |
| `skill_xp` | `skill`, `name`, `xp`, `delta` | A skill gained experience. `skill` is its index (a [skill constant](constants.md#skills)), `name` its lower-case name, such as `'woodcutting'`, `xp` the new total and `delta` the gain |
| `skill_level` | `skill`, `name`, `level`, `previous` | A skill's base level changed |
| `inventory_changed` | `slot`, `id`, `name`, `count`, `previous_id`, `previous_count` | A backpack slot changed. One event per slot; an empty slot's id is -1 and its name `None` |
| `varp_changed` | `index`, `value`, `previous` | A player variable was set |
| `script_finish` | `reason` | The script stopped, after `on_stop` |

## Positional events

These pass their values as separate arguments.

| Event | Arguments | Happens when |
|---|---|---|
| `server_message` | `msg` | A game message arrived, such as "You catch some shrimps." |
| `private_message` | `sender`, `msg` | A private message arrived |
| `trade_request` | `name` | A player asked to trade with you |
| `duel_request` | `name` | A player asked to duel you |
| `npc_spawned` | `npc` | An [`Npc`](world.md#npc) came into view |
| `npc_despawned` | `npc` | An NPC left view. `npc` is its last snapshot, so `npc.health == 0` usually means it died |
| `npc_damaged` | `npc`, `damage` | An NPC took a hit. `npc` is `None` if it has already left view |
| `player_spawned` | `player` | Another [`Player`](world.md#player) came into view |
| `player_despawned` | `player` | A player left view |
| `player_damaged` | `player`, `damage` | Another player took a hit |
| `damaged` | `damage` | You took a hit |
| `ground_item_spawned` | `item` | A [`GroundItem`](world.md#grounditem) appeared |
| `ground_item_despawned` | `item` | A ground item went |
| `ground_item_changed` | `item`, `previous_count` | A ground item's stack count changed |
| `loc_changed` | `loc` | Scenery was added, changed or removed. A removed one is a [`Loc`](world.md#loc) with id -1 |
| `interface_changed` | none | An interface opened or closed |
| `system_update` | `seconds` | The server announced a restart in `seconds` |
| `disconnect` | none | The connection dropped, or `relog()` logged out |
| `reconnect` | none | The player is placed again after a dropped connection or `relog()`. After a server restart this is a fresh login, so the state starts over, except that `game.tick()` and message marks carry on |
| `kill_signal` | none | Ctrl+C was pressed, or `quit` typed in the console. Call `stop_account()` once it's safe; after `scripting.killGraceSeconds` (30) the account logs out anyway |
| `bot_message` | `sender`, `message` | Another script in this process [sent a message](console-and-messages.md#messages-between-scripts) |
| `death` | none | Your hitpoints fell to 0 |
| `npc_say` | `npc`, `text` | An NPC said something over its head. `npc` is `None` if it has already left view |
| `projectile` | `projectile` | A [`Projectile`](world.md#projectile) was launched in the loaded area |

## Lifecycle hooks

`on_start()`, `on_stop(reason)` and `on_progress_report()` are hooks without events: they can't be subscribed to. See [Lifecycle hooks](script-structure.md#lifecycle-hooks).

## The full list of names

Events, usable with `events.on` and as `on_<name>` hooks:

`tick`, `chat_message`, `skill_xp`, `skill_level`, `inventory_changed`, `varp_changed`, `script_finish`, `server_message`, `private_message`, `trade_request`, `duel_request`, `npc_spawned`, `npc_despawned`, `npc_damaged`, `player_spawned`, `player_despawned`, `player_damaged`, `damaged`, `ground_item_spawned`, `ground_item_despawned`, `ground_item_changed`, `loc_changed`, `interface_changed`, `system_update`, `disconnect`, `reconnect`, `kill_signal`, `bot_message`, `death`, `npc_say`, `projectile`.

Hooks only: `start`, `stop`, `progress_report`.

## Notes

- Events report only what the server said. When the map rebuilds, or an area falls out of view, things vanish from the state without a despawn event. Query what's in view rather than keeping your own copy.
- Events that arrive while the client skips Tutorial Island, before `on_start`, aren't delivered.
- `in_combat` and chat `type` names differ from rs2b0t's webclient: see [Porting](python-dialect.md#porting-from-rs2b0t).
