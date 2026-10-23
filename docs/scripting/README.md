# Scripting API reference

The complete reference for writing Python scripts for rs2004-headless: every builtin function, object, constant, event and hook a script can use. For a guided introduction, start with [ScriptingApi.md](../ScriptingApi.md); for working examples, read `scripts/examples/`, and for rs2b0t's bots, ported, `scripts/bots/`.

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
| [The bank](bank.md) | `bank`, `banking`, deposit rules, `PeriodicBank` |
| [Shops and trades](shops-and-trades.md) | `shop`, `trade` |
| [The side tabs](side-tabs.md) | `quests`, `prayer`, `special`, combat styles, `autocast` |
| [Upkeep](upkeep.md) | Random events, `random_events`, `run_manager`, the stall guard, Tutorial Island |
| [Console and messages](console-and-messages.md) | `console`, `Command`, `send_bot_message`, progress reports |
| [Constants](constants.md) | Every builtin constant and its value |
| [Catalogs](catalogs.md) | `rs2004.catalogs`: rs2b0t's data tables, planners and tasks |
| [Quest steps](quests.md) | `rs2004.quests.exec`: talking to NPCs, walking to them across ladders, and answering what locs and doors ask; `rs2004.quests.prayer` |
| [Python, imports, tools and porting](python-dialect.md) | pocketpy's dialect, imports, `--watch`, `--debugger`, revisions, porting from rs2b0t |

## Conventions used in this reference

- **Builtins.** Everything here except [`rs2004.catalogs`](catalogs.md) and [`rs2004.quests`](quests.md) is in every script's builtins, with no import.
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
| `InvItem` | [items](items.md#invitem) |
| `Component` | [interfaces](interfaces.md#component) |
| `MakeProduct` | [interfaces](interfaces.md#makeproduct) |
| `Quest`, `CombatStyleResolution`, `CombatStyleController` | [side-tabs](side-tabs.md) |
| `HintArrow` | [game](game.md#hintarrow) |
| `PeriodicBank` | [bank](bank.md#periodic-banking) |
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
| `parse_combat_style`, `try_parse_combat_style`, `parse_interface_combat_style`, `resolve_combat_style`, `parse_range_style`, `describe_combat_style`, `resolve_split_combat_settings` | [side-tabs](side-tabs.md#combat-style-functions) |

### Constants

`INVENTORY`, `EQUIPMENT`, `BANK`, `BANK_INVENTORY`, `INVENTORY_SIZE`, the skill constants (`ATTACK` ... `RUNECRAFT`), `LAYER_WALL`, `LAYER_WALL_DECOR`, `LAYER_GROUND`, `LAYER_GROUND_DECOR`, `COMBAT_TICKS`, `MAKE_X`, `MAKE_ALL`, `SA_MAX_ENERGY`, `PRAYER_NAMES`, `AUTOCAST_SPELLS`, `COMBAT_STYLE_OPTIONS`, `RANGE_STYLE_OPTIONS`, `NAV_PURE_WALK`, `NAV_WITH_TELES`, `BANK_LOCATIONS`, `USE_MAGE_BANK`, `USE_ZANARIS_BANK`, `SPELL_MAX_WILDERNESS`, `GLORY_MAX_WILDERNESS`, `PLAYER_FACE_BASE`, `OVERHEAD_TICKS`, `PROTECT_FROM_MAGIC`, `PROTECT_FROM_MISSILES`, `PROTECT_FROM_MELEE`, `GLOBAL_SETTINGS`, `CANT_REACH`, `COMMON_BANK_LOOT`, `RANDOM_EVENT_CASKET_ID`, `NEARBY_BANK_RADIUS`, `PERIODIC_BANK_SETTINGS`, `SELL_STACK_STEP`: see [Constants](constants.md).

### Hooks

Lifecycle: `on_start`, `on_stop`, `on_pause`, `on_resume`, `on_progress_report` ([script-structure](script-structure.md#lifecycle-hooks)). Upkeep: `grind_targets`, `ignored_randoms`, `lamp_skill`, `recovery_anchor` ([upkeep](upkeep.md)). Events: `on_<event>` for each [event](events.md#the-full-list-of-names).
