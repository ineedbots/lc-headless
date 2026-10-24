# Clues

`rs2004.clues` is rs2b0t's clue engine (`api/ai/clues/`). It covers:

- the database of every clue scroll this cache has, and the step each one wants;
- the puzzle-box solver and its driver;
- the kit a trail packs, the guardian fought at a hard dig, and the special talk steps;
- the travel the walker's graph can't do;
- the executor that walks a trail to its casket, and `SolveClue`, the task a bot adds to solve the clues it picks up.

ClueSolver (`scripts/bots/clue_solver.py`) is built on it. So is every bot that carries a clue drop: ArdyCakes, ArdyFighter, ArdyThiever, AutoFighter, GreenDragon, JiveDragons and RockCrab. A script imports it:

```python
from rs2004.clues import SolveClue, SolveClueHost, held_clue_like_id, walk_to_bank
```

- [Adding the task to a bot](#adding-the-task-to-a-bot)
- [What a trail does](#what-a-trail-does)
- [The database](#the-database)
- [The puzzle box](#the-puzzle-box)
- [Packing and the hard kit](#packing-and-the-hard-kit)
- [The guardian](#the-guardian)
- [The special steps](#the-special-steps)
- [Travel](#travel)
- [The executor](#the-executor)
- [The trace](#the-trace)
- [Entrana and route requirements](#entrana-and-route-requirements)
- [What isn't here yet](#what-isnt-here-yet)

## Adding the task to a bot

`SolveClue(host)` is a `Task`. It validates while the pack holds a clue scroll or a casket. Put it after the bot's emergencies (eating, retreat, panic banking) and before its own bank run. The host gives:

| Member | For |
|---|---|
| `log(message)`, `set_status(text)` | Logging and the status line; `set_status('clue solved')` is how a host hears a trail finished |
| `is_food(name)`, `food_name()`, `food_withdraw()` | The host's food, and how many a grind trip takes; a trail packs at most 10 |
| `weapon_name()` | Optional: the weapon a trail keeps in the pack and puts back after |
| `enabled()` | Optional: whether to solve now; a fight in progress or a loot run returns `False` |
| `hard_food_target` | Optional attribute: the Sharks a hard trail packs, 15 by default |
| `ranged_loadout()` | Optional: a `GuardianRangedLoadout(weapon, ammo, quantity, mode)` to fight the guardian with a bow, or `None` for melee |
| `prepare_initial_bank()` | Optional, **Wait**: gets to the first bank the host's own way, such as out of a lair; `False` blocks the trail |
| `restore_prayer()`, `use_teleports()` | Optional: whether to top up prayer at an altar before a hard trail, and whether legs route through teleports |

A bot whose own names clash, such as one keeping its food in a `food_name` attribute, hands `SolveClue` a `SolveClueHost` built from functions:

```python
self.solve_clue = SolveClue(SolveClueHost(log=self.log, set_status=self.clue_status, is_food=lambda n: is_food_item(n, self.food_name),
                                          food_name=lambda: self.food_name, food_withdraw=lambda: self.food_withdraw,
                                          weapon_name=lambda: self.weapon, enabled=lambda: self.solve_clues))
```

Members:

- `note_death()`: call it from the bot's death handler. A death on a hard trail stops it until `retry()`.
- `owns_equipment()`: `True` while the trail has the host's gear in hand. While it does, a bot mustn't re-gear, reset its attack style or bank for its grind; JiveDragons' gear tasks check it.
- `clue_status()`: the trail's state for a progress report.
- `executor`: the `ClueExecutor`; its `current` is the leg in progress.

## What a trail does

`SolveClue.execute()` works through a trail in this order:

1. **The bank stop.** At the nearest bank, it deposits everything but the trail's kit: the clue, a casket, the spade, the sextant, watch and chart, coins, the clue's own items, the weapon, and teleport runes the account can cast. Then it stocks that kit, 1000 coins for toll gates, and food capped to the trail. A hard trail also gets the guardian's weapon, a Superantipoison and its Sharks.
2. **Prayer.** Before a hard trail, it prays at the nearest altar a route reaches, if the host allows.
3. **The executor.** The `ClueExecutor` solves the trail leg by leg.
4. **Putting the host's gear back.** It re-equips the host's weapon, or anything the Entrana stop banked, from the pack or the nearest bank.

The executor's outcome decides what happens next:

| Outcome | Then |
|---|---|
| `'done'` | The gear goes back on, and `set_status('clue solved')` is sent |
| `'yield'` | A random event or a wait; the next `execute()` resumes the same leg |
| `'supplies-needed'` | One more bank stop for the same leg. If that one comes up short too, the kit is blocked: `validate()` stays `False` until the pack or the bank's contents change |
| `'reset-needed'` | The leg made no progress after four attempts. It banks at the nearest bank, rebuilds the pack and retries the clue once |
| `'abandon'` | The clue stays in the pack and the trail stops; the trace is kept (see [The trace](#the-trace)) |
| `'dead'`, `'guardian-lost'` | The trail stops. Before the gear goes back, it retreats to a bank out of the guardian's reach |

## The database

The tables come from rs2b0t's clue database (`tools/catalogs/export_rs2b0t.ts` writes `rs2004/catalogs/_clues.py`):

| Name | Is |
|---|---|
| `CLUE_DB` | Every clue scroll by item id. Each row is a dict: `obj`, `id`, `type`, and as the step needs them `coord` (a `Tile`), `npc`, `needs_sextant`, `items`, `guardian`, `puzzle` (`obj`, `id`), `key_from` (`npc`, `key_obj`, `key_id`), `casket_obj` and `casket_id` |
| `CASKET_IDS` | Casket item id to its object name |
| `TALK_ANCHORS`, `KILL_ANCHORS`, `DIG_ANCHORS` | Where a talk, kill or dig step is done, by clue id |
| `CHALLENGE_ANSWERS` | The answer to each clue's challenge question; `challenge_answer(clue_id)` |
| `PUZZLE_PIECE_SLOT` | Each puzzle box's pieces, as the slot each belongs in |
| `PACK_UNREACHABLE` | Why rs2b0t's map can't route to a clue |
| `CLUE_GATES` | Clues a quest seals; `clue_gate(id, quests.status)` is the reason, or `None` |

`identify_step(held_ids)` is the step the pack's clue or casket wants, or `None` when it holds neither. A casket's step is `open_casket_step(casket_obj, casket_id)`.

## The puzzle box

The solver works on a board: a list of 25 piece numbers, `PUZZLE_BLANK_SLOT` (24) being the gap.

- `read_puzzle_board(slots, slot_of_piece)` turns a modal's (slot, item id) pairs into a board.
- `solve_puzzle(board)` is the list of slots to click, or `None` for a board that can't be solved. It plans in about 40ms.
- `apply_puzzle_move`, `puzzle_neighbours` and `is_puzzle_solved` are the board's rules.

The driver is `rs2004.clues.puzzle_box`:

- `solve_held(puzzle_id, log)`: **Wait**. It opens the box the pack holds, solves it and closes it, and replans when a click didn't land.
- `board_now()`: the open box's board.

## Packing and the hard kit

`trail_food_target(host_want, held_food, free_slots, reserve_slots)` caps a trail's food at `TRAIL_FOOD_CAP` and leaves room for the coordinate tools. `hard_trail_food_target` does the same for a hard trail's Sharks, never below the minimum.

`hard_clue_kit(HardKitSnapshot(attack, lost_city, items, ranged))` is `'ready'` or what's short: `'weapon'`, `'ammo'`, `'attack'` (60 for a dragon weapon), `'lost-city'` (which a dragon weapon needs), `'superantipoison'` or `'sharks'`. The guardian's weapons are `GUARDIAN_WEAPON_IDS`: the dragon dagger, its poisoned form, and the dragon longsword. A ranged loadout needs the bow worn and its ammo.

`hard_kit_snapshot(include_bank, ranged)` reads the account, the bank too when asked. `hard_kit_fingerprint` is a string that changes when anything the kit checks changes, so a blocked kit is retried only then.

At an open bank, two Waits stock the kit:

- `stock_hard_weapon(entrana, remember, preferred_weapon, minimum_sharks, ranged)` wears the guardian's weapon, or the ranged loadout. It tells `remember(name)` what the weapon replaced.
- `stock_hard_supplies(reserve_slots, bankable_items, minimum_sharks)` takes a dose and the Sharks.

`TeleportKit` and `teleport_kit_for(world_state())` list the runes for the teleports this account can cast. `is_teleport_item(name, kit)` is whether a bank stop keeps an item for them.

## The guardian

A hard dig can spawn a wizard who must die before the dig finds the next clue.

- `GuardianProtection(guardian, ranged)`:
  - `prepare()` wears the weapon and, against the Saradomin wizard, drinks a Superantipoison dose. It refuses below `GUARDIAN_MIN_SHARKS` Sharks.
  - `maintain()` drinks again before the dose's 570 ticks run out, or on a poison message.
- `GuardianEncounter(name, protection).fight(log)`: **Wait**. It prays Protect from Magic, and attacks only a guardian that targets us or stands at the dig. It walks around fences to a melee tile, or to a tile in line of sight for a bow. It stops before the last three Sharks. Its result is `'killed'` (only for a death it saw), `'yield'`, `'supplies-needed'`, `'dead'` or `'guardian-lost'`.
- `fight_guardian(name, log, protection)` runs one encounter.

`died_since(mark)` is whether "Oh dear, you are dead!" came since a `game_messages.mark()`. `sustain_until(cond, ms)` waits with the sustain hook pumped every tick.

## The special steps

`rs2004.clues.steps`:

- `solve_hans(clue_id, walk, log)`: waits where Hans's patrol passes, by the Lumbridge teleport, and chases him only with run energy to spare.
- `solve_mountain_pilot(walk, log)`: shelters behind the glider on White Wolf Mountain until the wolves lose interest, solves the pilot's puzzle box, and turns auto retaliate off for the talk.

## Travel

Legs walk with the walker. `trail_walk_opts(log, radius)` gives the options, which allow teleports beyond 40 tiles while `set_trail_teleports(True)` holds. A few places aren't on the walker's graph:

- **The Duel Arena's pens.** `walk_across_clue_duel(dest, radius, log)` enters the pen the clue wants by an unstaked obstacle duel. The partner is the account the Global `clue_duel_partner` names, which runs DuelArena as the clue helper, or else whoever in the lobby takes one. A wrong pen forfeits and tries once more; leaving forfeits.
- **The Kharazi Jungle** (`in_kharazi`, `jungle_crossing`, `jungle_kit_missing`): the bank stop packs a machete, the best axe and Radimus's notes for one of `KHARAZI_CLUES`.
- **Isafdar** (`in_isafdar`, `crosses_tirannwn`).

The walk into the Kharazi Jungle and the walk across Isafdar fail with a log line for now (see [What isn't here yet](#what-isnt-here-yet)).

`walk_to_bank(tile, log)` is the walk a trail takes to a bank, with those crossings. `open_clue_bank(log)` opens the nearest bank its own way (a banker, a chest or a booth), and `reopen_clue_bank()` opens it again and waits for it to be ready.

## The executor

`ClueExecutor().solve_held_clue(log, needs_bank, ranged)` is **Wait**. It solves the trail the pack holds, to its casket and reward, and returns one of the outcomes above.

- Each leg gets four attempts and one reset at a bank.
- It fetches a missing spade or coordinate tool before giving up.
- It answers challenge scrolls, and hunts a riddle's key from its keeper.
- It buys a Shantay pass when the desert's gate asks.
- It yields to a random event mid-step, then picks up the same leg, and the same guardian, on the next call.
- `needs_bank()` returning `True` stops it with `'supplies-needed'` before any travel.

Each `SolveClue` owns one executor, where rs2b0t keeps one for the process.

## The trace

Every leg's notes go into a `ClueTrace`. An abandoned trail logs the trace and keeps the last five in `settings_store`, under the namespace `'ClueTrace'` and the key `'ring'`. `read_trace_ring(storage, key)` reads them back.

## Entrana and route requirements

`rs2004.routeplan` gained:

- `is_entrana_restricted_gear(name)` and `names_have_entrana_restricted_gear(names)`: the boat to Entrana refuses weapons and armour. A trail bound there banks every worn item first, and wears them again after.
- `meets_requires(requires, state)`: `(ok, reason)` for a teleport catalog entry's requirements against `world_state()`.

## What isn't here yet

- **The Kharazi Jungle and Isafdar.** Cutting into the jungle needs Legends' Quest's jungle code, and crossing Isafdar needs Regicide's seams. Both come with phase 17's members' quests. Until then, a trail that needs either abandons the clue and logs why.
- **The clue scroll paint.** rs2b0t's `cluePaint.ts` draws an overlay, which a headless client has no use for.
