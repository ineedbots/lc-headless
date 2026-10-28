# Scripting API reference

The complete reference for writing Python scripts for rs2004-headless: every builtin function, object, constant, event and hook a script can use. Start with the quick start below, then use the topic pages for details. The API follows rs2b0t's bot API in Python's style: facades, chained queries and cooperative waits with `yield from`. The implementation plans are in [ScriptingDesign.md](../design/ScriptingDesign.md) and [BotApiDesign.md](../design/BotApiDesign.md).

## Quick start

First configure the server, RSA key and matching cache as described in [Configuration](../Configuration.md).

1. Copy `accounts/example.jsonc.sample` to `accounts/<name>.jsonc` and fill in the username and password. The file name becomes the account's name in log lines.
2. Point `script.file` at a script, relative to `scripting.scriptsDirectory` (default `scripts/`), such as `examples/chicken_killer.py`.
3. Run `Rs2004Headless client.jsonc` (use `.\Rs2004Headless.exe` in PowerShell or `./Rs2004Headless` on Linux) to run every enabled file in `accounts/`, logging them in `scripting.loginIntervalSeconds` apart, or add `--account accounts/<name>.jsonc` to run just that one. One process runs up to 16 scripted accounts.

An account file can have its own `server` section to log into another world of the same revision. The section replaces the process-wide server section; see [account overrides](../Configuration.md#account-overrides).

Ctrl+C asks each script to finish (see [lifecycle hooks](script-structure.md#lifecycle-hooks)). A second Ctrl+C logs every account out at once, and one more closes any connection whose logout the server is still refusing. The exit code is 0 when every account logged out cleanly and no script failed.

While it runs, the client takes commands typed into its console: `help` lists them, `status` shows where each account is, and `quit` does what Ctrl+C does. Scripts can add commands of their own (see [Console commands](console-and-messages.md#console-commands)).

Each account retries temporary login failures and reconnects independently while other accounts keep playing. Retry limits and delays are configurable; see [Retries and reconnects](../Running.md#retries-and-reconnects).

A script is a bot, as in rs2b0t's API: either a class set with `BOT = define_bot(...)`, or a module-level `loop()` with `on_*` hooks, which runs as a `LoopingBot`. It finds things with queries, acts on what it finds, and returns how long to wait before `loop()` runs again:

```python
def on_start():
    log('Starting at', game.tile())

def loop():
    if game.in_combat():
        return 600          # the next server tick

    chicken = npcs.query().name('Chicken').within(8).where(lambda npc: not npc.in_combat).nearest()
    if chicken is not None and chicken.interact('Attack'):
        # Wait until the fight starts, or 3 seconds.
        yield from execution.delay_until(lambda: game.in_combat(), 3000)

def on_server_message(msg):
    if msg.startswith('Oh dear'):
        stop_account()
```

The same as a bot, with its settings declared, and tasks chosen in priority order:

```python
class Fighter(TaskBot):
    def on_start(self):
        self.add(
            Task(lambda: game.in_combat(), lambda: None, label='fight'),
            Task(lambda: True, self.attack, label='attack'),
        )

    def attack(self):
        target = npcs.query().name(self.settings.npc).within(8).where(lambda npc: not npc.in_combat).nearest()
        if target is not None and target.interact('Attack'):
            yield from execution.delay_ticks(2)

BOT = define_bot(name='Fighter', create=Fighter, settings_schema={'npc': SettingDef('string', 'Chicken')})
```

[`scripts/examples/`](../../scripts/examples) has complete scripts:

- `chicken_killer.py` is a `TaskBot` that kills chickens, collects feathers and optionally buries bones. Set `combat_style`, `start_location` and `bury_bones` under `script.settings["Chicken Killer"]`; `radius` controls the fighting area, and the bot walks back when outside it.
- `power_miner.py` is a `LoopingBot` that mines and drops the ore.
- `walker.py` is a module-level script that walks a loop of tiles, optionally for a set number of laps, telling a partner account about each one. Its `laps` console command changes the number of laps, and like every script it has `pause` and `resume`.

All three make progress reports. `scripts/bots/` has rs2b0t's bots, ported (see [Catalogs and behaviours](catalogs.md#ported-bots)).

For working on a script, `--watch` reloads it whenever you save it, and `--debugger` lets VS Code debug it (see [Working on a script](python-dialect.md#working-on-a-script)).

## Pages

| Page | Covers |
|---|---|
| [Script structure, bots and control](script-structure.md) | Module-level scripts and `BOT`, `define_bot`, `LoopingBot`, `TaskBot`, `Task`, `TreeBot`, what `loop()` returns, lifecycle hooks, `ScriptActivity`, `log`, `stop_script`, `stop_account`, `relog`, timing rules |
| [Waiting](waiting.md) | `execution`: `delay`, `delay_ticks`, `delay_until`, `delay_until_ticks`, `note_progress`; `event_signal` |
| [Settings](settings.md) | `settings`, `SettingsBag`, `SettingDef`, schemas, `settings_store`, the Global settings, account file keys |
| [Events](events.md) | `events`, `Event`, every event and its arguments |
| [Tiles and areas](geometry.md) | `Tile`, `Area` |
| [The world](world.md) | `npcs`, `players`, `locs`, `ground_items`, queries, `Npc`, `Player`, `Loc`, `GroundItem`, `Projectile`, cache types |
| [Items](items.md) | `inventory`, `equipment`, `InvItem` |
| [You and the game](game.md) | `game`, `skills`, `reader`, `chat`, `friends`, `ignores` |
| [Walking](walking.md) | `direct_navigator`, `traversal`, banks on the map, `reachability`, `navigator`, `walk_opening`, `reach`, `game_messages` |
| [Interfaces and dialogues](interfaces.md) | `chat_dialog`, `MakeProduct`, `modals`, `interfaces`, `Component` |
| [The bank](bank.md) | `bank`, `banking`, deposit rules, `PeriodicBank`, sorting the bank |
| [Shops, trades and duels](shops-and-trades.md) | `shop`, `trade`, `duel` and the clue duel |
| [The side tabs](side-tabs.md) | `quests`, `prayer`, `special`, combat styles, `autocast` |
| [Upkeep](upkeep.md) | Random events, `random_events`, `run_manager`, the stall guard, Tutorial Island |
| [Console and messages](console-and-messages.md) | `console`, `Command`, `send_bot_message`, progress reports |
| [Constants](constants.md) | Every builtin constant and its value |
| [Catalogs](catalogs.md) | `rs2004.catalogs`: rs2b0t's data tables, planners, tasks and the ported bot table |
| [The market](market.md) | `rs2004.market`: the tradeable catalog, price books, appraising a trade, the chat protocol |
| [Hunting](hunting.md) | `rs2004.hunting`: the dragon sites, the safespot and chase fight tasks, lairs entered and left, the bank trip, and the decisions under them |
| [Clues](clues.md) | `rs2004.clues`: the clue database, `SolveClue` for a bot that carries clues, the executor, the puzzle box, the guardian, and the travel a trail needs |
| [Quest steps](quests.md) | `rs2004.quests.exec`: talking to NPCs, walking to them across ladders, and answering what locs and doors ask; `rs2004.quests.prayer` |
| [Python, imports, tools and porting](python-dialect.md) | pocketpy's dialect, imports, `--watch`, `--debugger`, revisions, porting from rs2b0t and plutonium |

## Conventions used in this reference

- **Builtins.** Everything here except [`rs2004.catalogs`](catalogs.md), [`rs2004.market`](market.md), [`rs2004.hunting`](hunting.md), [`rs2004.clues`](clues.md) and [`rs2004.quests`](quests.md) is in every script's builtins, with no import.
- **Wait.** A function marked **Wait** is a generator. Call it with `yield from` inside `loop()`, `on_start()`, a task's `execute()`, or another generator, and it gives back its result: `ok = yield from bank.close()`. Called without `yield from`, it does nothing. Everything not marked **Wait** returns at once.
- **Actions queue.** Actions such as `interact()` queue packets and return at once. Their effects show in the state over the next ticks, so wait for them with [`execution.delay_until`](waiting.md#executiondelay_untilcond-timeout_ms6000).
- **Snapshots.** Objects such as `Npc`, `InvItem` and `Component` are snapshots of when they were found. Query again, or call `valid()`, to see the present.
- **Names.** Item, NPC and scenery names, and menu options, are exactly as the server's cache has them. Lookups by name match the whole name without regard to case unless the page says otherwise; dialogue and make-menu lookups match by part.
- **Tiles.** Where a function takes a tile, a [`Tile`](geometry.md#tile) or an `(x, z)` pair on your level will do.
- **Errors.** A wrong argument type raises `TypeError`, and a value out of range raises `ValueError`. An uncaught exception stops the script.

## Index of builtins

### Objects and facades

| Name | Page |
|---|---|
| `autocast` | [side-tabs](side-tabs.md#autocast) |
| `bank` | [bank](bank.md#bank) |
| `banking` | [bank](bank.md#banking) |
| `chat` | [game](game.md#chat) |
| `chat_dialog` | [interfaces](interfaces.md#chat_dialog) |
| `console` | [console-and-messages](console-and-messages.md#console-commands) |
| `direct_navigator` | [walking](walking.md#direct_navigator) |
| `equipment` | [items](items.md#equipment) |
| `event_signal` | [waiting](waiting.md#event_signal) |
| `events` | [events](events.md#events) |
| `execution` | [waiting](waiting.md) |
| `friends`, `ignores` | [game](game.md#friends-and-ignores) |
| `game` | [game](game.md#game) |
| `game_messages` | [walking](walking.md#game_messages) |
| `ground_items` | [world](world.md#ground_items) |
| `interfaces` | [interfaces](interfaces.md#interfaces) |
| `inventory` | [items](items.md#inventory) |
| `locs` | [world](world.md#locs) |
| `modals` | [interfaces](interfaces.md#modals) |
| `npcs` | [world](world.md#npcs) |
| `players` | [world](world.md#players) |
| `prayer` | [side-tabs](side-tabs.md#prayer) |
| `quests` | [side-tabs](side-tabs.md#quests) |
| `random_events` | [upkeep](upkeep.md#random_events) |
| `navigator` | [walking](walking.md#navigator) |
| `reach` | [walking](walking.md#reach) |
| `reachability` | [walking](walking.md#reachability) |
| `reader` | [game](game.md#reader) |
| `recovery_hints` | [upkeep](upkeep.md#recovery_hints) |
| `run_manager` | [upkeep](upkeep.md#run_manager) |
| `settings` | [settings](settings.md#settingsbag) |
| `settings_store` | [settings](settings.md#saved-settings-settings_store) |
| `shop` | [shops-and-trades](shops-and-trades.md#shop) |
| `skills` | [game](game.md#skills) |
| `special` | [side-tabs](side-tabs.md#special) |
| `trade` | [shops-and-trades](shops-and-trades.md#trade) |
| `duel` | [shops-and-trades](shops-and-trades.md#duel) |
| `traversal` | [walking](walking.md#traversal) |

### Classes

| Name | Page |
|---|---|
| `AbstractBot`, `LoopingBot`, `TaskBot`, `TreeBot` | [script-structure](script-structure.md#abstractbot) |
| `Task`, `BranchTask`, `LeafTask` | [script-structure](script-structure.md#taskbot-and-task) |
| `ScriptActivity`, `ActivityOutcome` | [script-structure](script-structure.md#running-a-bot-inside-another-scriptactivity) |
| `BotManifest` | [script-structure](script-structure.md#define_bot) |
| `SettingDef`, `SettingsBag` | [settings](settings.md) |
| `Event` | [events](events.md#payload-events) |
| `Tile`, `Area` | [geometry](geometry.md) |
| `EntityQuery` | [world](world.md#entityquery) |
| `Npc`, `Player`, `Loc`, `GroundItem`, `Projectile` | [world](world.md) |
| `NpcType`, `ItemType`, `LocType` | [world](world.md#cache-types) |
| `ObjRecord` | [game](game.md#reader) |
| `InvItem` | [items](items.md#invitem) |
| `Component` | [interfaces](interfaces.md#component) |
| `MakeProduct` | [interfaces](interfaces.md#makeproduct) |
| `Quest`, `CombatStyleResolution`, `CombatStyleController` | [side-tabs](side-tabs.md) |
| `HintArrow` | [game](game.md#hintarrow) |
| `PeriodicBank` | [bank](bank.md#periodic-banking) |
| `DuelOffers`, `ClueDuelHandshake`, `ClueDuelSearch`, `ClueDuelHelper` | [shops-and-trades](shops-and-trades.md#duel) |
| `Command` | [console-and-messages](console-and-messages.md#command) |

### Functions

| Name | Page |
|---|---|
| `log`, `debug`, `print` | [script-structure](script-structure.md#logging) |
| `stop_script`, `stop_account`, `relog` | [script-structure](script-structure.md#stopping-and-relogging) |
| `send_bot_message` | [console-and-messages](console-and-messages.md#messages-between-scripts) |
| `define_bot`, `resolve_loop_cadence` | [script-structure](script-structure.md) |
| `world_state`, `bank_locations`, `bank_unlocked`, `nearest_bank`, `nearest_banks`, `nearest_bank_reachable`, `nearest_usable_bank`, `approach_of`, `locked_bank_at`, `nearest_walkable_bank`, `bank_cost_for_navigator` | [walking](walking.md#banks) |
| `wilderness_level_at` | [walking](walking.md#the-wilderness) |
| `walk_opening`, `is_openable_obstacle`, `face_steps`, `opened_neighbour`, `far_side` | [walking](walking.md#walking-through-doors-walk_opening) |
| `retaliate_on_from_varp`, `facing_player` | [game](game.md#combat-styles) |
| `backpack_capacity` | [items](items.md#inventory) |
| `matches_entity_name` | [world](world.md#entityquery) |
| `pick_choice`, `special_crossing_for_transport` | [walking](walking.md#helpers) |
| `is_openable_barrier`, `is_open_barrier_leaf`, `open_op`, `close_op`, `talk_op`, `toward_dest` | [walking](walking.md#door-rules) |
| `WRONG_SIDE` | [walking](walking.md#game_messages) |
| `deposit_all_except`, `deposit_matcher`, `matches_common_bank_loot`, `is_disposable_gather_junk`, `withdraw_op` | [bank](bank.md#deposit-rules) |
| `parse_bank_strategy`, `should_bank_now`, `resolve_bank_open_route`, `open_bank_access`, `purge_pack_at_bank`, `bank_pace`, `bank_pace_ticks`, `wait_bank_ready`, `withdraw_coins` | [bank](bank.md#helpers) |
| `shop_op_batch`, `parse_trade_partner_header` | [shops-and-trades](shops-and-trades.md) |
| `parse_duel_partner_header`, `fight_arena_at`, `in_duel_challenge_area`, `clue_duel_name`, `leave_clue_duel` | [shops-and-trades](shops-and-trades.md#duel) |
| `sort_bank`, `plan_bank_sort`, `sortable_bank_items`, `find_quest_junk` | [bank](bank.md#sorting-the-bank) |
| `parse_combat_style`, `try_parse_combat_style`, `parse_interface_combat_style`, `resolve_combat_style`, `parse_range_style`, `describe_combat_style`, `resolve_split_combat_settings` | [side-tabs](side-tabs.md#combat-style-functions) |

### Constants

`INVENTORY`, `EQUIPMENT`, `BANK`, `BANK_INVENTORY`, `INVENTORY_SIZE`, the skill constants (`ATTACK` ... `RUNECRAFT`), `LAYER_WALL`, `LAYER_WALL_DECOR`, `LAYER_GROUND`, `LAYER_GROUND_DECOR`, `COMBAT_TICKS`, `MAKE_X`, `MAKE_ALL`, `SA_MAX_ENERGY`, `PRAYER_NAMES`, `AUTOCAST_SPELLS`, `COMBAT_STYLE_OPTIONS`, `RANGE_STYLE_OPTIONS`, `NAV_PURE_WALK`, `NAV_WITH_TELES`, `BANK_LOCATIONS`, `USE_MAGE_BANK`, `USE_ZANARIS_BANK`, `SPELL_MAX_WILDERNESS`, `GLORY_MAX_WILDERNESS`, `PLAYER_FACE_BASE`, `OVERHEAD_TICKS`, `PROTECT_FROM_MAGIC`, `PROTECT_FROM_MISSILES`, `PROTECT_FROM_MELEE`, `GLOBAL_SETTINGS`, `CANT_REACH`, `COMMON_BANK_LOOT`, `RANDOM_EVENT_CASKET_ID`, `NEARBY_BANK_RADIUS`, `PERIODIC_BANK_SETTINGS`, `SELL_STACK_STEP`, `CATEGORY_ORDER`, `QUEST_JUNK`, `BANK_INSERT_VARP`, `ARRANGE_SWAP_COM`, `ARRANGE_INSERT_COM`, `DUEL_OPTIONS_VARP`, `DUEL_FIGHT_ARENAS`, `CLUE_DUEL_LOBBY`, `CLUE_DUEL_OPTIONS`: see [Constants](constants.md).

### Hooks

Lifecycle: `on_start`, `on_stop`, `on_pause`, `on_resume`, `on_progress_report` ([script-structure](script-structure.md#lifecycle-hooks)). Upkeep: `grind_targets`, `ignored_randoms`, `lamp_skill`, `recovery_anchor` ([upkeep](upkeep.md)). Events: `on_<event>` for each [event](events.md#the-full-list-of-names).
