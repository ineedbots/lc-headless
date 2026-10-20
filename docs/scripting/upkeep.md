# Upkeep: random events, the run manager and the stall guard

While a script runs, the client looks after a few things for it once a server tick, as rs2b0t's runtime services do. A script steers them with hooks and settings rather than running them itself.

- [Random events](#random-events)
- [The run manager](#the-run-manager)
- [The stall guard](#the-stall-guard)
- [Tutorial Island](#tutorial-island)

## Random events

Once a server tick, the client asks `random_events` whether an event needs answering. When one does, the bot's step in progress is dropped, the solver runs until it's done, and then `loop()` starts afresh. `on_start` isn't interrupted. `"randomEvents": false` in the account file turns all this off.

| Event | `kind` | `name` | What's done |
|---|---|---|---|
| Genie, drunken dwarf, mysterious old man, sandwich lady, frog | `'dialog'` | The NPC's name, lower case, such as `'genie'` | Talks to it and goes through the dialogue |
| Strange plant | `'pick'` | `'strange plant'` | Picks its fruit once it can be picked |
| A hostile event that has hit you: swarm, river troll, rock golem, zombie, shade, watchman, tree spirit | `'evade'` | The NPC's name, lower case | Runs 20 tiles away until it's gone, then walks back. It chases until you're 15 tiles from where it appeared |
| Poisonous gas chest, smoking rocks, whirlpools | `'hazard'` | `'poisonous gas'`, `'smoking rock'` or `'whirlpool'` | Steps away and waits a minute |
| An ent you're chopping | `'hijack'` | `'ent'` | Steps off it |
| The mime's stage | `'mime'` | `'mime'` | Copies each emote he performs |
| The maze | `'maze'` | `'maze'` | Opens the doors on the route to the centre, read from the cache's map, then touches the shrine |
| A tool whose head flew off | `'lost-tool'` | `'lost tool'` | Picks the head up and fixes the tool, wielding it again if it was worn |
| Fishing gear knocked from your hands | `'lost-gear'` | The gear's name, lower case | Picks it back up |
| A strange box in the backpack | `'box'` | `'strange box'` | Reads the question and clicks the right colour or shape |
| A lamp in the backpack | `'lamp'` | `'lamp'` | Rubs it for `lamp_skill()`'s skill |

### Choosing

Define these as bot methods, or module-level functions in a script without `BOT`:

| Hook | Default | Meaning |
|---|---|---|
| `ignored_randoms()` | `[]` | Event names, from the `name` column, to leave alone, such as `['drunken dwarf', 'genie']` |
| `grind_targets()` | `[]` | NPC names you fight on purpose, which are never taken for a hostile event |
| `lamp_skill()` | `'strength'` | The skill the lamp's experience goes to |

They're read again each tick, so they can depend on state.

### Rules

- An event NPC that's following another player is left alone.
- An event that isn't over after 4 tries is ignored for 45 seconds, except the maze, the mime, a box and a lamp, which hold you or can't be dropped, so they're tried again.
- The time a random event takes doesn't count toward the stall guard.

### `random_events`

For a script with `"randomEvents": false` that answers events itself.

| Member | Gives or does |
|---|---|
| `random_events.detect()` | The event that needs answering, or `None`. Ignored events, and those given up on in the last 45 seconds, aren't returned |
| `random_events.handle(event, log=None)` | **Wait.** Answers the event. Gives whether it acted. `log` is given progress lines |
| `random_events.handling` | `True` while a solver runs |

An event has `kind`, `name`, `tile` (for a hazard, the tile it's on; otherwise `None`) and `key()`, which is `'kind:name'`.

```python
def loop():
    event = random_events.detect()
    if event is not None:
        yield from random_events.handle(event, log)
        return 0
    ...
```

## The run manager

Turns run back on once energy reaches the account's `runEnergyMin` (20), when its `runAuto` is on (the default). It checks every 1.5 seconds, or at once when you're being hit.

It leaves run alone while a main interface is open, since clicking run makes the server close it, which could shut a bank mid-trip, unless you're being hit, when any energy at all will do.

### `run_manager`

| Method | Gives or does |
|---|---|
| `run_manager.override(run_auto=None, energy_min=None)` | Replaces the account file's choices for this script. The last call wins as a whole; a call with neither goes back to the account file's. `energy_min` is clamped to 0 to 100 |
| `run_manager.policy()` | The choices in force, as `(run_auto, energy_min)` |

```python
def on_start():
    run_manager.override(run_auto=False)       # this script walks
```

## The stall guard

Watches for progress: a change of tile, any experience gained, or [`execution.note_progress()`](waiting.md#executionnote_progress). After the account's `stallMinutes` (10) without any, it steps in:

- When the bot's `recovery_anchor()` gives a `Tile` that's more than 8 tiles away or on another level, it walks back there with `traversal.walk_resilient`.
- Otherwise, or if that walk fails, it restarts the bot: `on_stop` with the reason `"the stall guard restarted the bot"`, then `BOT`'s `create()` makes a new bot and `on_start` runs again. A module's globals stay as they were.

It steps in once, then not again for 15 minutes. Time spent logged out, a gap of more than 5 seconds between ticks (such as a relog), and time a random event takes aren't stalls. `"stallMinutes": 0` turns it off.

`recovery_anchor()` is a bot method or module-level function:

```python
def recovery_anchor():
    return Tile(3255, 3288, 0)    # the cow field
```

A bot that waits a long time on purpose, such as a mule standing by a bank, should call `execution.note_progress()` while it waits.

## Tutorial Island

An account that starts on Tutorial Island leaves it before `on_start` runs. If the character design screen is open, the client saves a plain design. Then it talks to the RuneScape Guide and answers "Yes please." when he offers to skip the tutorial, which sends the player to Lumbridge. Hooks and subscribers don't hear the game events that arrive meanwhile.

The guide only offers this on a server that isn't live, and only before the player has gone further into the tutorial. If he doesn't, the client logs that the player is still on the island, and the script starts anyway.
