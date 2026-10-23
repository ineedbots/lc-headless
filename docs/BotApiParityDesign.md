# Bot API Parity Design

Plan for porting the rest of rs2b0t. [BotApiDesign.md](BotApiDesign.md)'s nine phases ported rs2b0t's public API (`index.d.ts`) and what three of its bundled bots needed. This ports everything else a headless bot can use:
- the modules rs2b0t's bots import beyond the public API;
- the walker's left-out pieces;
- the market, combat hunting, duels and bank sorting;
- the clue and quest engines;
- every bundled bot.

It keeps BotApiDesign's shape (§1–3 there): rs2b0t's names in snake_case, `yield from` where rs2b0t awaits, and a Python standard library over the C++ core. It replaces that document's "Not ported" row for the quest and clue engines and the market. Phases continue its numbering, from 10. Code style follows [CONVENTIONS.md](CONVENTIONS.md).

The gap below was measured against rs2b0t at `46a83506` (2026-10-20). rs2b0t keeps moving, so each phase starts by measuring again at its tip (§4, the coverage tool).

Reference sources:

- `rs2b0t/src/bot/api/`: every module below; `api/ai/clues/` and `api/ai/quests/` for the engines
- `rs2b0t/src/bot/scripts/`: the 75 bundled bots, and `scripts/index.ts`, their manifests
- `rs2b0t/src/bot/event/webwalk/`: the walker's remaining pieces
- `rs2b0t/src/bot/runtime/`: `ScriptActivity.ts`, `Settings.ts` (`SettingsStore` and the `Global` keys), `Scheduler.ts`
- `rs2b0t/src/bot/data/`: the tables not generated yet
- `rs2b0t/test/`: 763 test files; those for the modules below port with them
- `rs2b0t/docs/reference/quest-*.md`, `clues-*.md` and `clue-*.md`: how the engines work; `docs/decisions/quest-pitfalls-*.md`: what broke them live
- `rs2b0t/docs/ACCOUNT_LEVELER_METHODS.md` and `ACCOUNT_LEVELER_COMBAT.md`: the account leveler
- `289server/content/scripts/`: the quests, clue trails and interfaces the engines drive

---

## 1. The gap

Measured by checking each rs2b0t export's snake_case name against the stdlib, the stubs and the examples, then reading the misses to drop false ones.

| Area | rs2b0t | Here |
|---|---|---|
| Public API, `packages/rs2b0t-api/index.d.ts` | 1,331 lines | All but the names in §4 |
| `api/` less `ai/` | 103 files, 13,600 lines | 45 files whole, 17 in part, 38 not at all (§4, §5, §7–9) |
| Walker, `event/webwalk/` | 69 files | All but jewellery teleports, the bank-for-route planner, and the quest-gate and essence-mine pieces (§6) |
| Runtime, `runtime/` | 31 files | All a headless bot needs, less child bots, recovery hints, settings that save, pause and resume, and `EventSignal` (§4) |
| Data, `data/` | 22 tables | Most generated into `catalogs/_data.py`. Missing: `DROP_DB`, `ITEM_DB`, `STAFF_RUNES`, `MARKET_PRICES`, `ITEM_ALIASES`, `NAME_SYNONYMS`, `NAME_COLLISIONS`, `UNTRADEABLE_IDS` |
| Clue engine, `api/ai/clues/` | 30 files, 3,900 lines | None |
| Quest engine, `api/ai/quests/` | Engine and primitives 3,800 lines; 63 quests in 318 files, 70,400 lines | The quest tab only (`quests`) |
| Bots, `scripts/` | 75 bots in 72 folders, 61,000 lines | ChickenKiller, CowKiller and GatheringBot's Miner. BankFletcher less its cut+string mode. Thiever, ArdyCakes and ArdyThiever folded into one `aio_thiever.py` |

Of the public API, the names missing are few and small (§4). Most of the gap is what rs2b0t's bots import from outside `index.d.ts`. 61 of its 72 bot folders import at least one name the stdlib lacks. The 11 that don't are AIOTeleport, BoneBurier, DartFletcher, GnomeMagicChopper, JiveCaskets, JiveEnchanter, MuleTrader, NatureCrafter, RangingGuild, TannerBot and VialFiller.

### Not ported

| rs2b0t | Why |
|---|---|
| `paint/`, `panel/`, `multibox/`, the map picker and basemap, `desktop/`, `cameraFollow.ts`, the path overlays | They draw or take input, and headless has no screen. Progress reports stand in for paint |
| `Game.cameraYaw`, `cameraPitch`, `setCameraYaw` | No camera |
| `Input` (a mouse walk, an inventory click) | A ported bot calls the facade the click stands for: `direct_navigator.walk`, `InvItem.interact` |
| `runtime/diag/`, `RenderGate`, `WorkerClock`, `producers.ts` | Browser frame timing, and the event producers the host replaces |
| `AutoRelogin`, `LoginBackoff`, `LoginCoordination`, `Credentials`, `WorldSwitch` | `Account` logs in, retries and spaces logins out (`connectAttempts`, `loginIntervalSeconds`, `reloginDelaySeconds`) |
| `WelcomeScreen` | The webclient opens the welcome screen itself on `LAST_LOGIN_INFO`; this client doesn't |
| `ScriptRegistry`, `registerScript`, `apiVersion`, `ScriptRunner.paintControls` | An account file names its script. Nothing is listed, bundled or version-checked |
| Bank snapshot generations: `Bank.snapshotGeneration`, `snapshotReady`, `waitSnapshotAfter`, `reader.bankSnapshotGeneration` | As BotApiDesign §7 decided: the deposit and withdraw generators wait for the update, so a port drops these calls |
| `Tile.toString`, `AcquireTask`'s constructor | Python's `repr` and `__init__` |

---

## 2. Decisions

| Topic | Decision |
|---|---|
| Scope | Everything in §1 except the "Not ported" table, rs2b0t's bots included: they are as much its functionality as the API is |
| Where bots live | `scripts/bots/`, one file per rs2b0t bot (`scripts/bots/gnome_course.py`). A bot rs2b0t splits across files is a package (`scripts/bots/gathering/`). `ScriptVm::ResolveImport` already finds its modules as `bots.gathering.<name>`, and each bot it registers has its own entry file (`woodcutter.py`, `fisher.py`, `miner.py`). The rs2b0t ports in `scripts/examples/` move there. Three files stay as examples: `walker.py` and `power_miner.py`, which rs2b0t doesn't have, and `aio_thiever.py`, which combines three of its bots |
| Shared code | A module that two or more bots import goes in the stdlib, as rs2b0t keeps it under `api/`. Code only one bot uses stays with that bot, as in rs2b0t |
| Engines | `rs2004.clues` and `rs2004.quests` are stdlib packages, since bots besides the solvers import them: seven fighters and thieves call `SolveClue` on a clue they're dropped, and seven bots besides AIOQuester use the quest primitives or a quest's own code. A quest is `rs2004/quests/defs/<id>.py`, or a package of that name, as rs2b0t's are. The queue imports a quest's module the first time it needs it, so an account running one quest compiles one |
| Translation | A tool, `tools/port/ts2py.ts`, writes a first draft of each module. It runs with Bun over rs2b0t's tree using TypeScript's compiler API. It turns names into snake_case and object-literal steps into `Record`s, arrow functions into lambdas or local `def`s, template strings into f-strings, and optional chaining into explicit `None` checks. It writes `yield from` wherever the callee returns a `Promise`. The type checker knows which calls those are, so no `yield from` is missed or added. Each draft is then fixed by hand for pocketpy's dialect and this client's differences, tested, and committed. Nothing is regenerated over hand edits |
| Interrupts | `event_signal.pending()` and `set_interrupt(fn)` port rs2b0t's `EventSignal`. Here the guardian drops the bot's generator when it takes over at the next tick (BotApiDesign §10). `pending()` asks it whether it sees an event it would handle, so a long loop can stop at a safe point first. Any state a step must keep across an interruption lives on an object, never in a generator's locals, as rs2b0t's clue guardian keeps its `GuardianEncounter` on the solver |
| Child bots | `ScriptActivity` runs a bot inside another, as rs2b0t's account leveler runs its training methods. The child's manifest is its module's `BOT`, imported like any other module (`from bots.woodcutter import BOT`). Its settings are its schema's defaults plus the parent's overrides, checked as an account's are. Its `delegated` is true, and its `request_finish` ends the activity, not the account |
| Saved settings | `settings_store.save(name, key, value)` and `settings_store.saved(name, key)` write into and read from the account file's `script.settings["<name>"]`, through `JsoncEditor`, as defaults already are (BotApiDesign §4). Loadouts, price books and the `Global` keys a headless bot uses are namespaces there, where rs2b0t keeps them in the panel's storage |
| `show_if` | `SettingDef` takes it, and the schema check fails a `show_if` that names a key the schema lacks. Nothing hides settings headlessly, so otherwise it only documents them |
| Pause | The console's `pause` and `resume` commands call `on_pause` and `on_resume`, and the host doesn't step the bot between them. Upkeep keeps running, so a paused account still answers random events and keeps its run on |
| Market | rs2b0t's catalog, price books, appraisal and chat protocol come whole. Prices start from its generated `MARKET_PRICES`, and books are account settings |
| Client reads | What the engines need that the core doesn't expose is added to `_core` (§3), and found by what the interface shows, as BotApiDesign §1 requires |
| Verification | As before: rs2b0t's tests port with their modules, and each phase ends with its bots running against the local engine |

Rejected:

- **Hand-porting all of it.** Phases 1–9 hand-ported about 12,000 lines. The quests alone are six times that, and the commonest mistake, leaving out the `yield from` on a call that waits, is one the type checker rules out.
- **A JavaScript engine in the client** to run rs2b0t's bundle. It would be a second runtime and a second VM per account, its bots couldn't call the Python API, and the webclient adapter it expects doesn't exist here.
- **The engines in `scripts/lib`.** Bots import them, and they reach into the stdlib's internals. They would version apart from it, which is why BotApiDesign §1 embeds the stdlib.
- **Free-to-play quests only.** The engine is the same for all 63 quests, and each members' quest's pitfalls are documented in rs2b0t; leaving them out only defers the work.

---

## 3. Core additions

The Python phases need these from the C++ core. Each lands in the phase that first needs it.

| `_core` | Gives | For | Phase |
|---|---|---|---|
| `hint_arrow()` | The decoded `HintArrow_s` (`GameState_s::hintArrow`): a tile, an NPC or a player | Quests and clues that point at their target | 11 |
| `line_of_sight(a, b)` | rs2b0t's `geometry/lineOfSight.ts`, over the loaded scene's `RANGE_` collision flags | `reachability.line_of_sight`, safespots, ranged and magic hunting | 11 |
| `scene_flags(x, z)` | A loaded tile's collision flags | The firemaking lane finder (`find_burn_lane`) | 11 |
| `facing()` | The local player's face entity (`Entity_s::faceEntity`) | `facing_player`, `PLAYER_FACE_BASE` | 11 |
| `overhead_text()` | The local player's overhead text (`Entity_s::say`) | rs2b0t's `reader.selfChat` | 11 |
| `move_item(com, from, to, mode=None)` | The bank's swap or insert drag. `GameActions::MoveItem` already takes a `DragMode_e`; `ScriptActions::MoveItem` passes it through | `sort_bank`, `InvItem.move_to(slot, insert=False)` | 13 |

The duel's offer screens and the clue puzzle box need nothing new from the core. They're inventories in modals, read by `reader.inventory(com)` and found in the open interfaces by their options and items, as the shop's and trade's are (BotApiDesign §7).

---

## 4. Phase 10: tooling, runtime, and the public API's remainder

### Tooling

- **`tools/port/coverage.py`:** the check §1 came from. It lists, by rs2b0t file, each export whose snake_case name the stdlib and stubs lack, less an allow-list for the "Not ported" table. Each later phase's "Done when" runs it over that phase's modules.
- **`tools/port/ts2py.ts`:** the translator (§2). Its output names the rs2b0t file each function came from, as the hand ports do.
- **`tools/port/lint.py`:** checks drafts and hand-written Python alike for what pocketpy does differently (added in the building; see "As built").
- **`tools/catalogs/export_rs2b0t.ts`** gains the tables the later phases need, each named where it's used.

### Runtime

| Python | Ports | Notes |
|---|---|---|
| `ScriptActivity(log)` | `runtime/ScriptActivity.ts` | `start(manifest, overrides)`, `loop()`, `interrupt(reason)`, `stop()`, `child`, `outcome` (an `ActivityOutcome(kind, reason)`, the kind `'finished'`, `'failed'` or `'interrupted'`) and `current_task`. `start` and `loop` are generators. `loop()` honours the child's cadence as the host honours a bot's. `stop()` resets what the child set: its subscriptions, `sustain`, `run_manager.override`, the interrupt, and the grind targets and ignored randoms the guardian reads |
| `AbstractBot.delegated`, `bind_finish(sink)`, `bind_log(sink)` | `api/bot/Bot.ts` | What `ScriptActivity` hooks into |
| `on_pause()`, `on_resume()` | `AbstractBot` | Called by the console (§2) |
| `event_signal` | `api/execution/EventSignal.ts` | The guardian is its provider (§2). `set_interrupt(fn)` adds a bot's own reason, such as a death |
| `recovery_hints` | `runtime/RecoveryHints.ts` | `take_anchor()` and `clear()`: the stall guard's recovery tells the restarted bot where it was, as ChickenKiller reads it |
| `settings_store` | `runtime/Settings.ts`'s `SettingsStore` | `save`, `saved`, `resolve`, `on_change`, `display_string` |
| `SettingDef(..., show_if=None)` | `SettingDef.showIf` | §2 |
| The `Global` namespace: `script.settings["Global"]` | rs2b0t's `Global` keys a headless bot reads | Changed in the building; see "As built" |

### The public API's remainder

| rs2b0t | Python | Notes |
|---|---|---|
| `BANK_LOCATIONS`, `nearestUsableBank`, `resolveBankOpenRoute` | `BANK_LOCATIONS`, `nearest_usable_bank(tile, usable)`, `resolve_bank_open_route(...)` | Beside today's `bank_locations()` and `nearest_bank`, which `banking.open` keeps using |
| `TOOL_ACQUIRE_SETTING`, `FORGETFUL_BANK_SETTING` | The same, as `SettingDef`s | In `rs2004.catalogs` |
| `Traversal.pureWalk`, `withTeles`, `preload()` | `traversal.pure_walk`, `with_teles`, `preload()` | `preload()` does nothing: `WalkMap` is built at startup |
| `Game.openSideTab(tab)` | `yield from game.open_side_tab(tab)` | Returns `True` at once: every tab's interface is readable without opening it (BotApiDesign §6) |
| `Game.sceneReady()`, `sceneState()` | `game.scene_ready()`, `game.scene_state()` | `ingame()`, and 2 or 0 to match it |

- **Done when:**
    - [x] `coverage.py` runs, and reports nothing missing from `index.d.ts` but the "Not ported" table.
    - [x] `ts2py.ts` translates `api/tasks/Anchor.ts`, `api/bank/bankRules.ts` and `api/combat/eatTiming.ts`, three modules already ported by hand. After the hand fixes it lists, its drafts pass those modules' tests in `tests/Stdlib`.
    - [x] Tests: a child bot's settings checked and its finish ending only the activity; `pause` and `resume` from the console; `settings_store.save` keeping the account file's comments; `show_if` naming a missing key failing the schema.
    - [x] Against the local engine, an activity runs `cow_killer`'s `BOT` for ten minutes inside a parent bot, and the parent stops it and starts `miner`'s.

### As built

- **The Global settings** are a namespace, `script.settings["Global"]`, not new top-level account keys. rs2b0t's `SettingsStore` keeps them as one namespace among the bots' own, so here they sit beside the bots' objects too. `settings_store.global_bag()` reads them, `GLOBAL_SETTINGS` is their schema (`lamp_skill`, `bank_common_junk`, `clue_duel_partner`, `use_zanaris_bank`, `use_mage_bank`, `nav_teleports`, `nav_path_stall_ticks` and `nav_path_deviation`), and they're checked before login like a bot's. No C++ config change was needed. `runAuto` and `runEnergyMin` stay the account file's own keys, as before. `bank_unlocked` and `traversal.teleports_enabled()` read the Global settings, and a bot's default `lamp_skill()` does too.
- **Saving.** `_core.save_setting(name, key, value_json)` queues the save on `ScriptControl`. At the end of each `ScriptHost::Step`, and after `Finish`, the host writes the queue into its own copy of the settings, so a reloaded script sees what it saved, and hands each save to `ScriptHostOptions_s::onSettingSave`. `Account` passes it to `AccountFile::SetScriptSetting`, which uses the new `JsoncEditor::Set`: values already there are replaced in place, the rest added as `AddMissing` adds them, and the file is rewritten only when it changes.
- **Pause** is the runtime's, not `AccountRunner`'s. The runtime adds `pause` and `resume` to every script's console commands, `console.command` refuses them, and while paused `step()` returns a 250 ms wait without stepping the bot. The guardian's solver still steps, and the stall guard counts the pause as busy.
- **`ScriptActivity`** drives the child's generator itself, one step at a time, rather than with `yield from`, so an `interrupt()` between steps ends the child at its next wait. A child's `request_finish` raises `ActivityFinished` through its step when it's called from inside one, as rs2b0t's throws, and ends the activity directly when it's called from an event callback. The child's `on_<event>` hooks become its own subscriptions.
- **`event_signal.pending()`** asks the guardian's new `random_events.pending(bot)`, checked once a tick, as rs2b0t's is.
- **pocketpy, probed.** A throwaway test checked what the translator may emit. Two forms build wrong values without an error: `{**a}` and `[*a, b]`. Generator expressions, nested comprehensions and implicit string concatenation don't parse, and `str.isdigit`, `str.isupper`, `str.replace` with a count, `min(default=)`, `dict.setdefault` and `dict(a_dict)` are missing. `ts2py.ts` avoids all of them: spreads become loops, `flatMap` a loop, `find` a comprehension's first item. f-string `{{ }}`, `@property`, `@staticmethod`, `super()`, sort keys and `if False: yield` all work. A scan found none of the broken forms in the stdlib.
- **The translator,** run on `Anchor.ts`, `bankRules.ts` and `eatTiming.ts`, wrote drafts that passed the hand ports' own test cases with no hand fixes. The only changes were in the test calls, where the hand ports' signatures differ: `should_bank_now` takes a state there and the draft its fields, and the anchor host has rs2b0t's methods. It takes rs2b0t's TypeScript compiler from the rs2b0t checkout, so it needs no packages of its own.
- **The live check.** A parent bot on a fresh account ran `cow_killer`'s `BOT` as an activity at the field north-west of Lumbridge for ten minutes: Strength rose by 752 xp and Hitpoints by 245. It then stopped it and ran `miner`'s, which walked through the gate to Southwest Varrock Mine and mined 14 tin in five minutes, and logged out. `settings_store.save` wrote the parent's stage into the account file at each switch, keeping its comment. There were no script errors.
- **`lint.py`.** `tools/port/lint.py` checks Python for the pocketpy pitfalls above, and for a function two deep reading the outermost function's locals. It finds nothing in the stdlib, the scripts or the tests. Over drafts of all 103 `api/` modules, `ts2py.ts` writes no syntax errors, and the lint finds seven such closures for the hand fixes.
- **Where the bots went.** `cow_killer.py`, `miner.py` and `bank_fletcher.py` moved to `scripts/bots/`, a package. `chicken_killer.py` stays in `scripts/examples/` for now: it's the docs' first example, and account files outside the repository name it.

---

## 5. Phase 11: the modules bots share

What rs2b0t's bots import from `api/` and `event/webwalk/` outside combat, the economy and the engines, and the bots that need nothing more.

### Modules

| rs2b0t | Here | What |
|---|---|---|
| `event/webwalk/geometry/Reachability.ts` | `reachability` | `can_reach`, `can_step`, `walkable`, `probeable`, `line_of_sight`. Today's `world_state()` keeps its checks for the walker's requirements |
| `event/webwalk/walkOpening.ts` | `walk_opening(dest, radius, obstacles, log=None, door_step_ticks=None)` | Walks within the scene, opening the named obstacles on the way. Also `is_openable_obstacle`, `open_op`, `close_op`. `banking.open`'s `obstacles` uses it, where today it's accepted and unused |
| `event/webwalk/Navigator.ts` | `navigator.find_path(start, dest, ...)` | The world route without walking it. `traversal.route_cost` becomes a reading of it |
| `api/bank/Banking.ts`, `BankLocations.ts` (rest) | `bank`, `banking` | `open_bank_access`, `purge_pack_at_bank`, `bank_pace`, `bank_pace_ticks`, `withdraw_coins`, `approach_of`, `nearest_walkable_bank`, `locked_bank_at`, `USE_MAGE_BANK`, `USE_ZANARIS_BANK` |
| `api/inventory/packRules.ts` | `rs2004.catalogs` | `matches_any`, `count_matching`, `slots_matching`, `should_bank`, `should_restock`, `should_eat`, `should_panic` |
| `api/thieving/` | `rs2004.catalogs.thieving` | The cake stall (`steal_cakes`, `carried_cakes`, `needs_cake_restock`, its tiles and lockouts), `steal_rules` and `targets`. `aio_thiever.py` then imports them rather than keeping its own |
| `api/firemaking/` | `rs2004.catalogs` | `light_fire`, and the lane finder BotApiDesign §12 left out (`find_burn_lane`, `burn_lane_want`, `run_in_dir` and the rest), on `_core.scene_flags` |
| `api/altar/Altars.ts`, `api/map/Teleport.ts`, `api/map/regions.ts` | `rs2004.catalogs` | `nearest_altar`, `resolve_teleport`, `teleport_button_text`, `in_ess_mine` |
| `api/walking/karamjaRecovery.ts`, `event/webwalk/wilderness.ts` | `traversal` | `missing_boat_fare`, `recover_boat_fare`, `wilderness_level_at` |
| `api/combat/CombatStyle.ts`, `CombatStyleLogic.ts` (rest) | `rs2004.catalogs.combat` | `CombatStyleController`, `describe_combat_style`, `resolve_split_combat_settings`, `runes_per_cast`, `casts_available`, `rune_withdraw_list`, `spell_button_com`. Here because ChickenKiller, HillGiant and ArdyFighter use them as well as the fighters of §8. The autocast buttons are found by shape, as `autocast` finds them, not by rs2b0t's ids |
| `api/game/Game.ts` (rest) | `game` | `retaliate_on_from_varp`, `facing_player`, `PLAYER_FACE_BASE` |
| `api/query/Query.ts` | `matches_entity_name` | |
| `api/loadout/` (rest) | `rs2004.catalogs` | `LOADOUT_SETTING`, `serialize_loadouts`, saved through `settings_store` |
| `api/ai/quests/exec/primitives.ts`, `prompts.ts` | `rs2004.quests.exec` | `talk_through`, `drive_dialog`, `drive_choice`, `goto_npc`, `walk_with_hops`, `settle_scene`, `prompt_loc`, `use_on_loc`, `loc_near`, `held_id`, `pick_preferred`. These come now, ahead of the engine, because bots outside quests use them |
| `data/dropdb.ts`, `itemdb.ts`, `spelldb.ts`'s `STAFF_RUNES` | `rs2004.catalogs` | Generated. `ITEM_DB` keeps only what the cache lacks: the wear slot and how an item is consumed. `reader.item_type` gives the rest |

### Bots

These need nothing beyond phase 11, so they're ported now, less the clue solving that phase 15 adds to some:

- **Skilling:** CookBot, DartFletcher, Firemaker, FlaxAIO, FlaxPicker, FlaxSpinner, GemCutter, GnomeMagicChopper, HerbCleaner, HerbloreSecondaries, JiveBalls, JiveCaskets, JiveCrafting, JiveEnchanter, LeatherCrafter, NatureCrafter, PotionMaker, RuneCrafter, CoalTrucks, SmelterBot, SmithingBot, Superheater, TannerBot, VialFiller, ClimbingBoots, BoneBurier, and BankFletcher's cut+string mode.
- **GatheringBot:** Woodcutter and Fisher, with cooking, chop-and-burn and tick manipulation, and the rest of Miner. Its feather buyout and mule hand-offs come with phase 13.
- **Agility:** GnomeCourse (AgilityBot), WildyAgility, EdgevilleMonkeyBars, BrimhavenAgility.
- **Thieving:** Thiever (ThievingBot), ArdyCakes, ArdyThiever, and ArdyFighter, each as rs2b0t has it.
- **Movement and magic:** WalkTo, DoorOpener, AIO Teleport.
- **Simple fighting:** ChaosDruidKiller, HillGiant.

The bots phases 1–9 ported are brought up to rs2b0t's current versions as well. ChickenKiller and CowKiller gain casting (`casts_available`, `rune_withdraw_list`) and `recovery_hints`, and Miner and BankFletcher gain what rs2b0t added after their port.

- **Done when:**
    - [x] `coverage.py` reports the modules above whole, less `karamjaRecovery.ts` and bank sorting (see "As built").
    - [x] rs2b0t's tests for them are ported and pass, including `test/api/bank`'s (less bank sorting), the firemaking lane finder's, `test/scripts/GatheringBot`'s and the thieving rules', less those that stub the facades (see "As built").
    - [x] Real-cache tests: `line_of_sight` against rs2b0t's cases. `hint_arrow` is read from a `FakeGameServer` packet.
    - [ ] Against the local engine, every bot above runs 15 minutes without a script error. Each banks at least once where it banks, and Firemaker burns a full backpack in a lane it found.

### As built

- **What's left for later.** `karamjaRecovery.ts` (`missing_boat_fare`, `recover_boat_fare`) goes to phase 12 with the rest of the walker's crossings. Bank sorting (`bankSort*.ts`) and `bankQuestJunk.ts`, which only BankSorter uses, go to phase 13 with BankSorter. `coverage.py` reports the rest of the table whole. GatheringBot's mule hand-offs, its feather buyout and ShiloSupplyTrip go to phase 13, with the mule and feather settings, so `fisher.py` and `miner.py` don't offer them yet.
- **GatheringBot** is the package `scripts/bots/gathering/`: `bot.py` is the bot, and `logic.py`, `camp.py`, `miner_logic.py`, `fish_cook.py`, `tick_manip.py`, `chop_burn.py`, `desert_camp.py`, `tool_acquire_exec.py` and `tasks.py` are rs2b0t's files of the same names. `miner.py`, `woodcutter.py` and `fisher.py` in `scripts/bots/` are the entries, each with rs2b0t's registry text and settings. They stay at the top of `scripts/bots/`, not in the package, so an account file names `bots/woodcutter.py` and the load test, which doesn't recurse, covers them. Tick manipulation is ported but off, as rs2b0t ships it (`TICK_MANIP_SHIPPED` is false).
- **Where the catalogs' shapes differ from rs2b0t's,** the bots follow ours: `fishing_restock_plan` gives `(name, qty)` pairs, `with_bait_target` a gear list, `resolve_fire_spot` `(name, plot)`, and `tool_restock_plan` `ToolRestockStep`s. A bank from `nearest_bank` or `BANK_LOCATIONS` is a dict in rs2b0t's camelCase. `npc.max_health` stands in for rs2b0t's `snap.totalHealth`, and `combat_styles()` gives `(mode, label)` pairs.
- **The logic functions take their fields as arguments,** where rs2b0t's take one options object (`should_flee_combat(in_combat, event_pending, has_attacker)`), in the options' order, with rs2b0t's optional fields last and defaulted. They're called by position: pocketpy binds a parameter without a default only by position, so `f(a=1)` fails when `a` has none.
- **Animation lengths.** The cache loader reads each sequence's length from its frames, and an entity's `animation` reads -1 once it has played out, as the webclient's does. GatheringBot's and the agility bots' "still busy" checks need it.
- **The bank snapshot** has rs2b0t's `loaded()`, `snapshot_ready()` and `snapshot_generation()`. The generation is the tick the item list arrived on, so `wait_snapshot_after(generation)` waits for a deposit's or withdrawal's answer.
- **`nearest_bank_reachable`** prices the 8 banks nearest by straight line, not every usable bank as rs2b0t does, since each route is planned while the script waits.
- **The frame cadence.** A loop that returns 0, rs2b0t's "next frame", now waits `('update', 20)`, 20 ms, not the next poll. Why: NatureCrafter's trade loop returned 0 while it waited for its partner, and at the poll interval it starved the other accounts in the process, so their trades never completed.
- **Settings.** A blank string passes a setting's options check, as an empty choice in rs2b0t's panel does, and reads as unset, so the bot uses its fallback. WildyAgility's food setting needs it.
- **`lint.py`** gained four rules from this phase's bugs: strings side by side counts f-strings (from 3.12 they tokenize as `FSTRING_START`); `dict(name)` is flagged, not only `dict({...})`; `str.capitalize` is missing; and a keyword argument naming a parameter without a default is flagged across files, looking definitions up in the stdlib and scripts whatever is linted. The f-string rule found two of them in the Desert Mining Camp's port, which wouldn't load; the `dict(name)` rule came after a test found `tick_manip`'s; and the keyword rule found nothing in shipped code but the GatheringBot calls it was written for. `ts2py.ts` now merges an object literal's spreads in source order, so `{a: 1, ...over}` lets `over` win, as JavaScript does. It had applied the literal's own keys last.
- **rs2b0t's tests** are in `tests/Stdlib/rs2b0t/`, in its describe/test/expect form on `spec.py`'s versions, which the C++ runner loads before each file. They import from `scripts/`, so they reach `bots.gathering`. Those that read the walker's data, `bank-locations` and `mageBankGate`, are in `nav/` and run as a real-cache test with a `Navigation`. 292 tests are ported: GatheringBot's logic, gathering camps, miner food, fish cooking, firemaking, target picks, tick manipulation, the Desert Mining Camp's plans and location settings; the bank's common rules, withdraw ops and locations; and the Ardougne thieving rules. Left out are the files that stub the facades with `spyOn` (`bank-chest`, `bank-id`, `bank-transfer`, `banking-access`, `zanaris-bank`, `npc-bank-scripts`, `legends-guild`, `ThievingBotBanking`, `FiremakerBanking`, and GatheringBot's `CatherbySweep`, `BankProvision`, `PowerDrop`, `MinerBankFood`, `GatheringCombat` and `MiningTargets`). In pocketpy an attribute set on an instance doesn't replace its class's method, so the stubs would do nothing. Tests needing rs2b0t's own nav pack or `transports.json` were left out too, as were the feather buyout's, which wait for phase 13. `banking-route` was already in `test_bank.py`, and `lineOfSight` in `LineOfSightTests.cpp`. Porting them found two bugs: `tick_manip`'s `dict(base)`, which pocketpy rejects, and the Desert Mining Camp's supply counts, read with `.items()` from a Record that had made its dicts Records.
- **The live runs.** Batches of four to six bots ran 12 minutes each against the local engine, with each account's starter items banked first. Each ran without a script error, and each that banks banked:
    - Skilling: herb cleaner, gem cutter, potion maker, jive enchanter, leather crafter, vial filler, flax spinner, jive crafting, smelter (54 bars), tanner (81), superheater (52 bars), rune crafter (81 runes), cook bot (cooked until its stock ran out), BankFletcher cut+string (strung its stock over 8 bank trips, then stopped as the bank ran out of bow strings), HerbloreSecondaries (162 over 7 trips), AIO Teleport (46 casts), CoalTrucks (54 in the truck), FlaxAIO (picked, spun and banked).
    - Agility: EdgevilleMonkeyBars (116 swings), BrimhavenAgility (15 minutes: 9 tickets, 952 xp).
    - Woodcutting: GnomeMagicChopper (5,500 xp of magic logs in 12 minutes, one tree hop). Its "Chopped" count stays 0, as rs2b0t counts it: only logs that land inside a chop step's wait, which ends here when the swing's animation does.
    - Thieving and fighting: ArdyThiever (72 steals), HillGiant (7 kills, a bank trip), ChaosDruidKiller in Edgeville dungeon (14 kills, 15 loots, a bank trip), ChickenKiller (30 kills, 34 bones buried), CowKiller (4 kills and 2 deaths on an account the harness's stat cheats missed), and `aio_thiever.py`, now on the catalogs' `steal_cakes` (43 steals, 28 stall food banked).
    - NatureCrafter: a runner and its master traded 50 essence, and the master crafted 50 air runes.
    - GatheringBot: Miner at Southeast Varrock Mine (a load of copper and tin banked), Fisher at Draynor (27 shrimps banked) and Catherby (55 caught, 48 cooked and 6 burnt, banked over 2 trips), Woodcutter at Draynor's willows, and chop-then-burn around Lumbridge (54 logs, 27 fires).
- **Found live, left for later:**
    - WildyAgility stalls at (2944, 3911): the walker clicks (2965, 3917) and doesn't move. It's the walker's, for phase 12.
    - At Draynor, dark wizards' magic ("You feel weakened") killed the Fisher and Woodcutter, at a named camp too, and FleeCombat never ran, so a magic attacker isn't seen as one. A probe that stood or paced there wasn't attacked, nor would a wizard fight it when it attacked, so it wasn't reproduced. It goes to phase 14, with the attacker checks. With Location Auto, rs2b0t's gatherers don't flee at all ("may die"), and the Woodcutter then lost its axe and waited, as rs2b0t's does, for one to be banked.
    - ClimbingBoots needs Death Plateau, which a fresh account hasn't done, so it wasn't run.

---

## 6. Phase 12: the walker's remainder

What BotApiDesign §9 left out of `traversal`, as rs2b0t has it:

| rs2b0t | Here |
|---|---|
| `teleportExecute.ts` | Jewellery teleports: rub the item, worn or held, choose the destination, and await the landing. `teleports.json` already holds the glory, games necklace and ring of dueling edges, which today a walk can plan but not take |
| `bankPlan.ts`, `virtualState.ts` | The bank-for-route planner. When a route needs what the backpack lacks (a toll's coins, a fare, a teleport's runes) and the bank has it, the walk banks for it first. `bank_item_counts` stops being accepted and unused |
| `gateItems.ts` | `explain_unreachable(dest)`: which held item would open the route, for a walk's failure reason |
| `data/postQuestTalks.ts` | The talk that unlocks a gate after its quest, done when a route crosses one |
| `exec/questLock.ts` | Detecting a quest-locked crossing from its dialogue, dismissing it, and blacklisting the edge for the session |
| `essenceSession.ts`, `essenceExit.ts` | The essence mine's session: the portal back leads where you came in from, so the route out depends on the way in |
| `iceQueenRockslide.ts`, `desertMiningCampDoors.ts` | Their extra edges |
| `routeState.ts`, `pathFollowPolicy.ts` | `navPathStallTicks` and `navPathDeviation` as the account keys of §4, and per walk |

### Bots

EssMiner, whose trips out of the mine need the essence session.

- **Done when:**
    - [x] rs2b0t's `test/event/webwalk` tests for these pieces are ported and pass, less those driving its own PathFinder (see "As built").
    - [x] Against the local engine, with teleports on (see "As built" for the guild's and EssMiner's):
        - a glory takes an account from Varrock to Draynor;
        - a walk from Lumbridge to Karamja with no coins banks for the fare first;
        - EssMiner's trips leave the mine by the right portal from both banks;
        - a quest-locked gate is detected and routed around.

### As built

- **Where it lives.** rs2b0t's pure pieces are the new stdlib module `rs2004.routeplan`: `bankPlan.ts`, `virtualState.ts`, `gateItems.ts`, `slashTool.ts`, `essenceSession.ts`, `essenceExit.ts`, `pathFollowPolicy.ts`, `exec/questLock.ts`, `data/postQuestTalks.ts`, and the special-crossing lookup and `pick_choice`, which moved there from `traversal`. `traversal` is the walker that uses them; it still exports what moved. `Navigation` now hands the stdlib `teleports.json` too, for the jewellery's item names and dialogue.
- **Jewellery teleports.** The planner already routed the glory, the games necklace and the ring of dueling the backpack holds; the walker now takes them: it rubs the item, picks the destination with the catalog's `dialogueChoose`, and waits for the landing, as `teleportExecute.ts` does.
- **Banking for a route.** As rs2b0t's: once a walk, the route's items (summed fares, peak keys and tools, a teleport's runes, a knife for webs) are checked against the backpack, a route from the nearest bank is planned with the bank's stock assumed held, and the walk banks when that's cheaper; a route that still lacks items doesn't set off, and `last_missing_gate_items` says what. It goes further in one case. The core's planner gates fares and tolls on the coins held, so with none it plans no route at all, and rs2b0t gives up there with the missing coins named. Here the walker banks for the kit `explain_unreachable` names and plans again. That's what the "no coins" check below needs.
- **The essence mine.** The exits' `essenceExitReturn` requirement is the core's now (`NavRequires_s`), against the state's `essence_exit_return`: a known return that doesn't match fails, an unknown one passes, as rs2b0t's `requires.ts` has it. rs2b0t also carries the return through the path search's state, for a route that enters and leaves the mine in one plan; nothing plans that, so it's left out. `essence_session` remembers the return from a wizard's crossing or Teleport hop, and EssMiner, which teleports in itself, notes Aubury.
- **Quest-locked crossings.** rs2b0t reads its lock phrases only from the dialogue. The 289 doors refuse in the chatbox first ("The door won't open - you need at least 32 Quest Points."), so the walker reads the game messages since the click too, and "won't" joins the phrases. pocketpy has no `re`, so the ten patterns are word matches.
- **Follow settings.** `path_follow` on a walk, then the Global `nav_path_stall_ticks` and `nav_path_deviation`, then the defaults, with `door_step_ticks` waited between a door opening and the step through.
- **The camp's doors.** The Desert Mining Camp's scripted leaves are never matched by a neighbour, nor opened by `try_nearby_door`. The exporter already left out the doors rs2b0t replaces, and the rockslide's and the essence exits' edges were already in `edges.json`.
- **Moved to later phases.** `karamjaRecovery.ts` fills Luthas's banana crate through Pirate's Treasure's quest steps, so it goes to phase 16 with the quest engine.
- **Found and fixed live:**
    - WildyAgility's stall at (2944, 3911). The server has no map for square (45, 61), so its tiles are off the map and every step onto them is refused. The cache has none either, but the scene's collision left a missing square open, so the client's path for a click ran west through it, and the server dropped the whole walk. The world planner already treated it as having no floor. `WorldMap` now blocks a square a loaded cache has no map for (`GameCache_s::squaresComplete`; a cache built by hand for a test holds only what it's given). WildyAgility then ran 4 laps, 2,333 xp, without a death.
    - An attacked walk didn't move. On this server a hit makes a retaliating player attack back unless it's busy, and walking isn't busy, so every hit cancelled the walk, and rs2b0t's "hold course" held it in place. A walk under attack that isn't moving turns auto retaliate off until it ends.
- **Tests.** rs2b0t's `bankPlan`, `gateItems`, `essenceSession`, `pathFollowPolicy`, `questLock` and the catalog half of `jewelleryAndStateAware` are in `tests/Stdlib/rs2b0t/`, those reading the real crossings in `nav/`, and EssMiner's logic beside them. `essenceMinePortal`, `essenceMineTransit`, `routeFunding` and `questGatedCrossings` drive rs2b0t's own PathFinder over its pack, or stub the executor; here the planner's real-cache tests cover the exits (`WorldPathFinderRealTests.cpp`: each known return leaves by its own portal), and the live checks the rest. `test_routeplan.py` has the cases that differ from rs2b0t.
- **The live checks,** each on a fresh account against the local engine:
    - Varrock to Draynor with an amulet of glory and teleports on: it rubbed the amulet, chose Draynor Village, landed, and arrived.
    - Lumbridge to Karamja with no coins held and 100 banked: it banked at Al Kharid for 40 (the toll back out and the fare), paid both, sailed, and arrived with none left.
    - Into the Champions' Guild with no quest points: the door refused, the walker read the refusal as a lock and left the door out, and the walk ended unreachable, since there's no other way in. So the detection is shown; a route around needs a refused crossing with another way past, which this one hasn't.
    - EssMiner, on an account whose quests the engine's `~cq` cheat had completed: Aubury's teleport in, a full pack, the portal back, the Varrock East bank, twice in 12 minutes, 53 essence banked. EssMiner banks only at Varrock East and leaves by the portal itself, not through the walker, so "both banks" was one; the walker's exits are the planner test's. The cheat completes the quests a few seconds apart, each behind its quest scroll, and the quest list shows them only from the next login.
    - WildyAgility, after the two fixes above: 4 laps and 2,333 xp in 12 minutes, without a death.

---

## 7. Phase 13: the economy

| rs2b0t | Here | What |
|---|---|---|
| `api/shop/BuyoutLogic.ts`, `StockModel.ts`, `shopPrice.ts` | `rs2004.catalogs.shops` | `buyout_plan`, `expected_stock` (stock coming back over ticks), `unit_price`, `units_under_policy`, `shop_buy_price`, `buyout_cost` |
| `api/trade/PartnerHandoff.ts`, `drivePartnerTrade.ts` | `rs2004.catalogs.partner` | `run_handoff`, `decide_open_trade`, `drive_active_partner_trade`, `trade_screen_state`, `stable_closed_poll`. BotApiDesign §12 ported only the policy |
| `api/bank/bankSort*.ts`, `bankQuestJunk.ts` | `bank` | `sort_bank(options)`, `plan_bank_sort` (the longest increasing subsequence and its moves), the category rules and ranks, `QUEST_JUNK`, `find_quest_junk`. It drags with the insert or swap mode (§3), first setting the bank's mode (varp 304) with its button, found by its label |
| `api/market/`, `data/marketprices.ts`, `itemAliases.ts`, `nameCollisions.ts`, `untradeable.ts` | `rs2004.market` | The tradeable catalog (`build_catalog`, `search_catalog`, `resolve_by_name`, noted and unnoted ids, categories and shelves), price books (parse, upsert, serialise, resolve), `appraise`, the chat protocol (commands, counts, formatted quotes within the chat limit), the ledger, sale intents, sets, and matching offers. The tables are generated, and checked against the cache |

Price books are account settings, saved through `settings_store`. A market bot talks to players in public chat, and a real player's chat line is a `chat_message` with type `'public'`.

### Bots

ShopBuyout, ShopRunner, FlaxRunner, MuleCrafter, MuleTrader, BankSorter, MarketMaker, JiveMarketDumper and Alcher, and GatheringBot's feather buyout and mule hand-offs.

- **Done when:**
    - [ ] rs2b0t's `test/api/shop`, `test/api/market` and bank-sort tests are ported and pass, and the real-cache test checks every market table name.
    - [ ] Against the local engine:
        - BankSorter sorts a shuffled bank of 200 items in insert mode;
        - ShopBuyout buys a stock down and waits for it back;
        - FlaxRunner and a gathering account hand over flax, run as two clients;
        - MarketMaker quotes and completes a trade with a second account's script, which talks to it in public chat.

---

## 8. Phase 14: combat

| rs2b0t | Here | What |
|---|---|---|
| `api/combat/equipment.ts`, `meleeWeapons.ts`, `ranged.ts`, `rangedSettings.ts` | `rs2004.catalogs.combat` | `BOWS`, `CROSSBOWS`, `DARTS`, `ARROWS`, `BOLTS`, `MELEE_WEAPONS`, `STAFFS`, `best_melee_weapon`, `known_melee_weapon`, `RANGED_WEAPONS`, `range_loadout_of`, `range_supply_empty`, `CUSTOM_RANGED_SETTINGS`, `ranged_item` |
| `api/prayer/Prayer.ts` (rest) | `prayer` | `PROTECT_FROM_MAGIC` and the other protection names |
| `api/combat/hunting/` | `rs2004.hunting` | rs2b0t's boss and dragon framework. `combat.py`: the `Fight`, `Retreat`, `HoldSafespot` and `WalkToSpot` tasks over a `CombatHost`. `logic.py`: safespot ladders, retreat and loot decisions, prayer and antifire timing, attack and engage ranges, shield and style gates. `sites.py`: the dragon sites, their gates, fees, stands and exits. `supply.py`: dose plans for antipoison, prayer and antifire, escape runes, lairs entered and left, keys and cells. `guarded.py`: loot under guard |
| `api/duel/Duel.ts`, `ClueDuel.ts` | `duel` | The challenge, the rules-and-stake screen, the confirm screen, the win screen, the arenas (`fight_arena_at`, `in_duel_challenge_area`) and the partner's name from the header, found by shape. `duel_request` is already an event. `ClueDuel.ts`'s lobby, handshake, search and helper come too: DuelArena uses them, as phase 15's duel-arena clue legs do |

### Bots

MossGiant, BrimhavenMossGiants, FireGiant, GreenDragon, RockCrab, RangingGuild, AutoFighter, JiveChests, JiveDemons, JiveKBD, JiveKQ, JiveDragons and the Duel Arena Combat Trainer (DuelArena). Those that carry clues get the solver in phase 15.

- **Done when:**
    - [ ] rs2b0t's `test/api/combat` and the bots' own tests (`test/scripts/JiveDragons`, `AutoFighter`, `RockCrab`, `JiveDemons`, `JiveKBD`, `DuelArena`) are ported and pass.
    - [ ] `line_of_sight` agrees with the engine: a ranged account on a known safespot is never hit in melee for ten minutes.
    - [ ] Against the local engine, each bot runs 30 minutes, through a bank trip, without a script error. JiveDragons kills blue dragons under antifire and a shield. DuelArena finishes a duel between two accounts.

---

## 9. Phase 15: the clue engine

`rs2004.clues`, ported from `api/ai/clues/`:

| Part | rs2b0t | Notes |
|---|---|---|
| The database | `data/cluedb.ts`, `challengeAnswers.ts`, `digAnchors.ts`, `killAnchors.ts`, `talkAnchors.ts`, `puzzlePieces.ts`, `clueGates.ts`, `unreachable.ts`, `toolAcquire.ts` | Generated, and checked against the cache |
| Solving | `SolveClue.ts`, `ClueExecutor.ts`, `ClueLogic.ts`, `ClueTrace.ts` | `SolveClue` runs inside a host bot, as rs2b0t's does. The trace goes to the account's log |
| Steps | `AcquireTools.ts`, `Guardian.ts`, `guardianKit.ts`, `hans.ts`, `gnomePilot.ts` | Spade and sextant-watch-chart acquisition; dig guardians under Protect from Magic; Hans; the gnome pilot |
| Travel | `duelTravel.ts`, `kharaziTravel.ts`, `tirannwnTravel.ts`, `teleportKit.ts` | With phase 12's jewellery teleports, and phase 14's `duel` with the partner from `clueDuelPartner` |
| Preparation | `hardClueKit.ts`, `hardCluePreparation.ts`, `packPlan.ts`, `bankAccess.ts` | |
| Puzzle boxes | `puzzleLogic.ts`, `PuzzleBox.ts` | The pure solver, and the driver that re-reads the board after every move. The board is found as §3 says |

- **The guardian across an interruption.** rs2b0t yields between hits, and keeps the `GuardianEncounter` so the dig isn't repeated. Here the step is dropped (§2). The encounter lives on the `SolveClue` object, which the host bot keeps, so the next step resumes it.
- **Hint arrows.** Talk and kill steps check `hint_arrow()` where the trail points at an NPC.

### Bots

ClueSolver. `SolveClue` is also wired into the bots that carry it: ArdyCakes, ArdyFighter, ArdyThiever, AutoFighter, GreenDragon, JiveDragons and RockCrab.

- **Done when:**
    - [ ] rs2b0t's clue tests are ported and pass, including the puzzle solver against 10,000 shuffles.
    - [ ] Against the local engine, given clues by a staff debugproc, ClueSolver:
        - finishes an easy, a medium and a hard trail, hard including a dig guardian and a puzzle box;
        - finishes a trail with a duel-arena leg, run with a partner account.

---

## 10. Phase 16: the quest engine, and the free-to-play quests

`rs2004.quests`, ported from `api/ai/quests/`:

| Part | rs2b0t | Notes |
|---|---|---|
| The engine | `engine/QuestEngine.ts`, `queue.ts`, `provisioning.ts`, `watchdog.ts`, `trace.ts`, `types.ts` | The queue, parking with reasons, and the progress watchdog. Provisioning assembles each pack bank-first. A step is a `Record` with rs2b0t's `kind`s: `talk`, `grabGround`, `pickLoc`, `interactLoc`, `useOn`, `equip`, `withdraw`, `deposit`, `mineRock`, `buy`, `custom`, `wait` and `done` |
| Execution | `exec/steps.ts`, `legs.ts`, `fundCoins.ts`, `garlic.ts`, `wool.ts` | On phase 11's primitives |
| Requirements | `EligibilityEvaluator.ts`, `RequirementChecker.ts`, `ItemChecker.ts`, `data/quests.ts` | The quest records are generated |
| Kit | `gear.ts`, `armour.ts`, `weapons.ts`, `food.ts`, `prayer.ts`, `strike.ts`, `strikeCombat.ts`, `journalText.ts` | |
| Barcrawl | `barcrawl/` | The barcrawl card, which some quests and bots need |

A quest module is a `QuestModule`: `record`, `hops`, `bank`, `grind`, `food`, `gather`, `tools`, `owns_inventory`, `read_stage` or `read_progress`, `sustain`, `warn_readiness` and `decide(snap)`. `decide` stays a pure function of the snapshot, so a quest restarts from wherever it's interrupted, by a random event or a crash, as in rs2b0t. Quest state is read as rs2b0t reads it: the tab's colours, the journal, items and messages, never varps the server doesn't send.

The free-to-play quests, as `rs2004/quests/defs/`:

> Cook's Assistant, Sheep Shearer, The Restless Ghost, Romeo & Juliet, Rune Mysteries, Imp Catcher, Witch's Potion, Doric's Quest, Goblin Diplomacy, Ernest the Chicken, Pirate's Treasure, Prince Ali Rescue, Black Knight's Fortress, Demon Slayer, Vampire Slayer, The Knight's Sword, Shield of Arrav, Dragon Slayer

### Bots

AIOQuester, ArravSupplier and Barcrawl.

- **Done when:**
    - [ ] rs2b0t's quest engine and free-to-play quest tests are ported and pass.
    - [ ] Against the local engine, AIOQuester takes a fresh account, off Tutorial Island with skills set by debugproc, through all 18 free-to-play quests in one queue. A quest that parks gives its reason, and is fixed or recorded with it here.
    - [ ] ArravSupplier banks a certificate from both gangs.

---

## 11. Phase 17: the members' quests

The other 45, in three batches. Each batch orders quests so that `EligibilityEvaluator` puts prerequisites first. Each quest's pitfalls in rs2b0t's `docs/decisions/quest-pitfalls-*.md` are read before porting it.

| Batch | Quests |
|---|---|
| 17a | Druidic Ritual, Gertrude's Cat, Monk's Friend, Sheep Herder, Witch's House, Fishing Contest, Clock Tower, Plague City, Tree Gnome Village, Waterfall Quest, Jungle Potion, Tribal Totem, Hazeel Cult, Murder Mystery, Priest in Peril, Scorpion Catcher, Sea Slug Quest, Dwarf Cannon, Observatory Quest, Fight Arena, Merlin's Crystal, Lost City, Death Plateau, Big Chompy Bird Hunting, The Tourist Trap, Biohazard |
| 17b | Nature Spirit, Elemental Workshop, Holy Grail, Hero's Quest, Family Crest, Temple of Ikov, Digsite Quest, The Grand Tree, Troll Stronghold, Eadgar's Ruse, Horror from the Deep, Shades of Mortton, Tai Bwo Wannai Trio, Watch Tower, Shilo Village |
| 17c | Underground Pass, Regicide, The Fremennik Trials, Legends Quest |

FlourCollector comes with Murder Mystery, and RoguesPurse with Jungle Potion, since each imports its quest's constants.

- **Done when:** for each batch,
    - [ ] its quests' tests are ported and pass;
    - [ ] against the local engine, AIOQuester completes every quest in the batch, on an account with the prerequisites done and skills set by debugproc.

---

## 12. Phase 18: the account leveler

AccountLeveler is the last bot because it uses nearly everything above. Its 21 files become `scripts/bots/account_leveler/`. It plans training by method and combat progression, shops and stocks for each, and runs each method as a child bot (phase 10's `ScriptActivity`). It reads the market (phase 13) for what to buy and sell.

Three of its reads change here:
- It finds each method's bot through `ScriptRegistry`; here it imports the bot's `BOT` (§2).
- It keeps its plan in the desktop's storage; here that goes to `settings_store`.
- It reads the world number from the webclient's URL, since Seers' player market is on world 1. Here it reads a `world` key in the account's `server` section, through `game.world()`.

- **Done when:**
    - [ ] Its tests are ported and pass.
    - [ ] Against the local engine, a fresh account levels for two hours across at least three methods, buying its tools and supplies, without a script error.
    - [ ] `coverage.py` over all of rs2b0t reports nothing but the "Not ported" table.

---

## 13. Tests

As BotApiDesign §13:
- C++ tests cover the core additions (§3).
- Python tests in `tests/Stdlib/` cover the ported modules, with rs2b0t's own tests ported beside them in `tests/Stdlib/rs2b0t/`, in its describe/test/expect form (see §5, "As built").
- Real-cache tests check every name the generated tables use.

rs2b0t's tests use Bun's `expect`. `ts2py.ts` turns `expect(a).toBe(b)` and its kin into plain `assert`s, since pocketpy has no unittest.

The live checks run against the local engine, with the accounts and debugprocs this repository's live tests already use: setting skills, teleporting, spawning items, starting a macro event, and taking an account off Tutorial Island.

---

## 14. Implementation order

10. **Tooling, runtime, and the public API's remainder** (§4).
11. **The modules bots share** (§5), and 41 bots.
12. **The walker's remainder** (§6), and EssMiner.
13. **The economy** (§7), and 9 bots.
14. **Combat** (§8), and 13 bots.
15. **The clue engine** (§9), ClueSolver, and the clue-carrying bots.
16. **The quest engine and the free-to-play quests** (§10), and 3 bots.
17. **The members' quests** (§11), in three batches, and 2 bots.
18. **The account leveler** (§12).

Phases 12 to 14 depend only on 10 and 11, and can go in any order. Phase 15 needs 12's jewellery teleports and 14's duels and combat helpers. Phase 16 needs 11's primitives and 12's quest gates.

With each phase:
- `scripts/typings/__builtins__.pyi` and `docs/scripting/` gain what it adds.
- The porting table in ScriptingApi.md maps each rs2b0t module it ports to its Python home, and each bot to its file in `scripts/bots/`.
