# Features

[Back to README](../README.md) · [Requirements](Requirements.md) · [Configuration](Configuration.md) · [Running](Running.md) · [Building](Building.md)

LostCity Headless maintains game state from server packets and exposes it to Python scripts. It does not render a game window. It targets LostCity private servers using revisions 289, 274 or 225; see the [protocol references](design/tcp-protocol-289.md) for packet details, with separate references for [274](design/tcp-protocol-274.md) and [225](design/tcp-protocol-225.md).

## Connections and accounts

Connections can use WebSocket (`ws`), secure WebSocket (`wss`) or the engine's raw TCP port (`tcp`). Each supports SOCKS5, including proxy authentication. For `wss`, certificate verification uses the platform trust store or a configured PEM CA bundle.

One process runs up to 16 accounts. Each account has its own Python interpreter, game state, script settings and log name. The game cache and protocol revision are shared. Accounts can connect to different worlds of the same revision, with separate server and proxy sections in their account files. These sections replace the process-wide sections; see [account overrides](Configuration.md#account-overrides).

Logins are spaced by `scripting.loginIntervalSeconds`, including retries and reconnects. Temporary connection failures use a bounded exponential retry delay. Unexpected session endings have a separate relogin delay. The [running guide](Running.md#retries-and-reconnects) explains the controls.

## Cache, state and navigation

The server's cache is loaded once per process. It supplies login CRCs, item and NPC definitions, scenery names and interaction options, map data and collision. This includes static scenery that the server has never sent as a change. The cache must match the configured server revision and deployment.

Scripts can query players, NPCs, scenery, ground items and inventories, then filter by properties such as name, distance and reachability. Local movement routes around collision; the world walker combines local routing with the navigation data in `data/nav`. See [queries and world objects](scripting/world.md), [walking](scripting/walking.md) and the [navigation data notes](../data/nav/README.md).

Revision differences still matter:

| Revision | Script considerations |
|---|---|
| 289 | The bundled catalogs and walker data are based on this revision. |
| 274 | Content introduced after 274 is absent. Map differences can affect routes from the bundled walker data. |
| 225 | Later content is absent. The protocol does not report membership, so traversal plans as on a free world. The player menu is fixed. |

Use `game.revision()` when a script needs revision-specific behavior. Supporting a protocol does not make every catalog entry or route valid on that revision.

## Python scripting

Scripts run on embedded pocketpy 2.2.0. No separate Python installation is needed to run the client. pocketpy implements a subset of Python 3 and cannot use pip packages; consult the [dialect and import reference](scripting/python-dialect.md) before porting a script.

Two entry styles are supported:

- A `loop()` function returning a delay in milliseconds, with optional lifecycle and event hooks.
- `BOT = define_bot(...)`, creating a `LoopingBot`, `TaskBot` or `TreeBot`, with typed settings and reusable tasks or tree nodes.

The API provides facades such as `inventory`, `bank`, `npcs`, `game` and `traversal`, chained queries, interactions, event subscriptions and cooperative waits. The [scripting reference](scripting/README.md) documents the API, and [example scripts](../scripts/examples) show complete bots. Random-event handling, run energy management and a stall guard are configured per account; see [upkeep](scripting/upkeep.md).

## Script development and coordination

| Tool | Purpose | Reference |
|---|---|---|
| `--watch` | Recreate the script when it or an imported module is saved, while keeping the account logged in. | [Reloading](Running.md#script-development) |
| `--debugger` | Attach VS Code to one account's interpreter on `127.0.0.1:6110`. | [Debugger setup](scripting/python-dialect.md#debugging-in-vs-code) |
| `--profile` | Record Python line timings with source snapshots, separately for each account and reload. | [Script profiling](Running.md#script-profiling) |
| Type stubs | Complete and check scripts in Pylance or Pyright. | [Editor support](scripting/python-dialect.md#editor-support) |
| Progress reports | Write a script's `on_progress_report()` results to a file at a configured interval. | [Progress reports](scripting/console-and-messages.md#progress-reports) |
| Console commands | Add script commands and send commands to one account or all applicable scripts. | [Console API](scripting/console-and-messages.md#console-commands) |
| Bot messages | Send JSON-compatible data between account scripts in the same process. | [Messaging API](scripting/console-and-messages.md#messages-between-scripts) |

Scripts share a process and are stepped cooperatively. Blocking work delays other accounts; use the API's waits rather than `time.sleep()`. The script watchdog limits calls into Python during normal execution. A paused debugger pauses the whole process, so debugging requires selecting a single account.
