# Phase-11 live acceptance

Live acceptance for [issue #36](https://github.com/ineedbots/lc-headless/issues/36),
using the bot list in section 5 of the
[pinned parity design](https://github.com/ineedbots/lc-headless/blob/d4e93e5b0dc377b509951d2e689820fc39546b70/docs/design/BotApiParityDesign.md#5-phase-11-the-modules-bots-share).

## Environment and measurement

- Date: 2026-11-21 (America/Regina).
- Windows x64 Release client, base `68d39960a149948db7edd773b33185a894f734e3`,
  with the two bot fixes described below loaded from the working tree.
- Executable SHA-256:
  `F12AF2CECC8F8703642EFE69D63D582CF44E5059F11151453D44E3E3609A9DDA`.
- Revision-289 engine `278bd51cc17cc0d093e1ea3895536a8054583f97`;
  content `f32c62f66302f76b43c752ede3181de0c0d01369`.
- Members world, **600 ms ticks**, XP rate 1. The harness asserts the tick setting.
  Existing packed content/cache is shared through junctions; configuration,
  database and player saves are isolated under `build/issue36/engine`.
  Preexisting engine checkout changes affect web-client assets only; content
  checkout was clean.
- Initially four client processes, at most 12 accounts each, 45 scenarios total.
  CookBot later moves to a fifth, single-account process. Both
  NatureCrafter roles and an additional GatheringBot chop-and-burn scenario
  are included. These runs do not establish a throughput benchmark.
- Scratch usernames, all skills initially level 85, tutorial complete, Druidic
  Ritual/Rune Mysteries/Lost City prerequisites seeded. DartFletcher additionally
  has Tourist Trap complete; ClimbingBoots has Death Plateau complete and its
  secret-route map state. All initial item IDs/counts, positions, quest vars,
  equipment and settings are preserved in the evidence.
- Common bank: 2,000,000 coins and 2,000 lobsters; production inputs are supplied
  in quantities sufficient to exceed 15 minutes. CoalTrucks starts with 100 coal
  already in the truck; GnomeMagicChopper starts with 26 magic logs, ensuring a
  banking cycle without waiting for 27 slow magic-log successes.
- Random-event guardian and stall guard initially disabled; normal run management retained;
  Python call watchdog 5,000 ms; one-minute progress reports. No accelerated
  ticks or XP multiplier. The server still generates random events; CookBot's
  corrected run enables its guardian, as explained below.
- Durations are conservative wall-clock measurements from one second after
  successful login to the last server sample while that script remains running.
  CookBot's corrected interval starts one second after its guardian returns it
  from the mime event, excluding event recovery from the cooking measurement.
  Script errors and self-stops fail acceptance; keeping an account connected
  does not extend a stopped script's duration. Bank records exclude initial
  seeding and distinguish deposits from withdrawals.

## Sessions and preparation

Initial discovery sessions are separate from acceptance. Fixture corrections
included selecting ordinary bone ID 526 rather than similarly named quest bones,
supplying Superheater's required fire staff, carrying the NatureCrafter master's
talisman, setting actual engine prerequisite varps, and completing Death Plateau's
map state as well as the main quest stage. These are preparation errors, not bot
defects.

The corrected main world started at **23:05:53 UTC**. HillGiant's first bank trip
revealed that its default food is Trout rather than the common Lobster stock.
After stocking 2,000 trout, its nine-account client batch was restarted at
**23:08:45 UTC**; durations for that batch start after the new logins. A brief
debugger breakpoint installed this fixture correction and exposed read-only world
inspection; it is recorded in the harness logs. No skill gains or completed
actions are attributed to that intervention.

CookBot cooked 125 fish and made five bank trips, then the server relocated it
to the mime event between the **23:10:53 and 23:11:23 UTC** server samples. With
its guardian disabled it retried an unreachable mainland range. This stalled
interval is excluded. Only that account was disconnected and relaunched with
the guardian enabled at **23:18:22 UTC**. It solved the mime at **23:19:32.446 UTC**
and resumed cooking without changing bot code or teleporting it through the
harness. Its fresh measurement starts at **23:19:33.446 UTC**.

WalkTo normally stops on arrival. Its acceptance wrapper uses the existing
`bind_finish` and `settings_store` APIs to alternate Falador and Varrock after
successful arrivals, preserving the shipped walk task and its error behavior.
DoorOpener opens the adjacent door and then waits for another closed door, as
designed. Remaining scenarios use the shipped bot entry points directly.

## Defects found and fixed

1. HerbloreSecondaries' `Grind.execute` passed a `has_key` keyword to `min`, raising
   `TypeError` on its first grinding step. Remove the unrelated keyword; key
   requirements remain in the restock rule. Runtime regressions execute the real
   grind task through a complete pack and a refused click.
2. FlaxPicker could see reachable field flax from the bank, while outside its
   picking radius. Neither picking nor travel validated, leaving it idle. Travel
   now also validates outside that radius. Its runtime regression starts at the
   bank with visible flax, travels, enables picking, and verifies that a full pack
   yields to banking.

## Separate banking checks and remaining observation

After the restarted nine-account group's endurance measurements were frozen,
Thiever, ArdyThiever and AIO Teleport received focused bank checks. Their initial
stock/thresholds had not forced a bank operation during that final endurance
interval. These checks are **separate from the fifteen-minute measurements**:

- Thiever: fill its remaining pack slots with six iron ores, then restart the
  ordinary bot. It walks to Edgeville, deposits the ores/coins and tops food up
  from 21 to 22 lobsters.
- ArdyThiever: add one chaos rune to its existing coin stack, crossing the
  configured two-loot-slot threshold. The normal bank task deposits both stacks
  and reports loot slots `2 -> 0`.
- AIO Teleport: empty its carried law runes, then restart with the ordinary
  ten-rune batch setting. It deposits remaining supplies and withdraws law,
  air and fire runes, setting the new batch to ten.

The seed changes occur after the measured interval, and all three bank checks
complete without script errors. Raw operations and UTC boundaries are in
`bank-probe-results.json` and the batch-5 transcript in the evidence archive.
These short checks do not contribute to the endurance durations.

ChaosDruidKiller's `Deaths` counter increments during a normal planned climb out
of Edgeville dungeon for banking. The transcript shows the ladder exit, then the
"surface respawn detected" diagnostic, another restock and a return to fighting.
No script exception accompanies it. This false death/redundant-restock observation
is tracked separately in [#134](https://github.com/ineedbots/lc-headless/issues/134);
it remains a limitation of the recorded progress metrics, not evidence of an
actual player death or a failed fifteen-minute interval.

## Results

All **45 scenarios / 43 listed bots** completed at least fifteen uninterrupted
measured minutes without a script error or premature self-stop. Durations span
**915.3–936.5 seconds**. Every applicable bot has bank evidence;
the three focused checks above are explicitly separate from endurance.

`D/W` counts observed bank deposit/withdrawal operations, not whole trips. Initial
seeding is excluded. `n/a` means this scenario does not bank. Activities come
from the final progress report (bot counters can lag a server action).

| Bot / scenario | Measured wall time | Bank D/W | Final activity evidence |
|---|---:|---|---|
| CookBot | 15:20 | 14/14 | Cooked 379; Bank trips 13 |
| DartFletcher | 15:25 | n/a | Made 74940; XP 134892 |
| Firemaker | 15:25 | 0/13 | Fires 291; Trips 10 |
| FlaxAIO | 15:23 | 6/0 | Picked 196; Spun 168 |
| FlaxPicker | 15:22 | 11/0 | Picked 305; Trips 10 |
| FlaxSpinner | 15:22 | 11/12 | Spun 308; Bank trips 11 |
| GemCutter | 15:20 | 78/80 | Crafting xp 101250; Trips 75 |
| GnomeMagicChopper | 15:19 | 2/1 | Woodcutting xp 9250; Bank trips 1 |
| HerbCleaner | 15:19 | 156/157 | Cleaned 2250; Trips 150 |
| HerbloreSecondaries | 15:17 | 153/155 | Gathered 3994; Trips 148 |
| JiveBalls | 15:16 | 3/1 | Collected 81; Banked 81 |
| JiveCaskets | 15:15 | 537/101 | Opened 2716 |
| JiveCrafting | 15:25 | 11/23 | Made 143; Banked 130 |
| JiveEnchanter | 15:24 | 18/56 | Enchanted 446; Banked 442 |
| LeatherCrafter | 15:23 | 19/23 | Made 476; Crafting xp 17723 |
| NatureCrafter (master) | 15:22 | 7/0 | Crafted 200; Received 200; Trades 8 |
| NatureCrafter (runner) | 15:21 | 0/9 | Delivered 200; Trades 8 |
| PotionMaker | 15:20 | 78/236 | Herblore xp 26250; Batches 75 |
| RuneCrafter | 15:19 | 11/13 | Runecraft xp 1485; Air runes 297; Trips 11 |
| CoalTrucks | 15:26 | 5/1 | Banked 135; Mining xp 2700 |
| SmelterBot | 15:18 | 13/28 | Smelted 182; Bank trips 14 |
| SmithingBot | 15:17 | 8/10 | Bars used 222; Bank trips 9 |
| Superheater | 15:16 | 32/78 | Bars 403; Bank trips 32 |
| TannerBot | 15:15 | 25/27 | Tanned 486; Runs 18 |
| VialFiller | 15:17 | 20/21 | Filled 554; Trips 19 |
| ClimbingBoots | 15:22 | 2/12 | Bought 50; Trips 2 |
| BoneBurier | 15:25 | 0/18 | Buried 466; Trips 17 |
| BankFletcher | 15:26 | 17/19 | Long bow 444; Bank trips 17 |
| Woodcutter | 15:15 | 9/1 | Gathered 245; Banked 224; Trips 8 |
| Woodcutter (chop-and-burn) | 15:23 | 0/2 | Gathered 136; Fires 135 |
| Fisher | 15:20 | 15/1 | Gathered 74; Cooked 74; Banked 74 |
| Miner | 15:18 | 4/1 | Gathered 140; Banked 112 |
| GnomeCourse | 15:19 | n/a | Laps 20; Obstacles 144 |
| WildyAgility | 15:16 | 0/28 | Laps 13; Cleared 66 |
| EdgevilleMonkeyBars | 15:21 | 0/1 | Swings 149; Ate 14 |
| BrimhavenAgility | 15:24 | 1/3 | Tickets 6; Hops 76 |
| Thiever | 15:29 | 0/0; focused 2/1 | Steals 332; Bank trips 0 |
| ArdyCakes | 15:35 | 12/0 | Steals 95; Banked 112; Trips 4 |
| ArdyThiever | 15:33 | 0/0; focused 2/0 | Steals 190; Bank trips 0 |
| ArdyFighter | 15:34 | 8/0 | Kills 47; Bank trips 4 |
| WalkTo | 15:28 | n/a | 7 complete town-to-town legs |
| DoorOpener | 15:31 | n/a | Opens 3 |
| AIO Teleport | 15:36 | 0/0; focused 2/3 | Teleports 196; Law runes used 196 |
| ChaosDruidKiller | 15:32 | 10/2 | Kills 31; Looted 27; Banks 2 |
| HillGiant | 15:30 | 8/1 | Kills 13; Looted 14; Trips 6 |

Firemaker's `fire-loads.json` independently matches each 27-log withdrawal to
the following successful ignition messages. Its first full load has 27
ignitions after the bot reports a discovered 27-tile west-running lane; later
loads repeat the result. The tinderbox occupies the remaining pack slot.

## Checks and artifacts

- Windows x64 Release build passed.
- Full Release CTest: 1,035 selected tests, zero failed; optional real-cache
  checks skipped without cache environment variables.
- Separate revision-289 real-cache selection: 71 passed, seven checks needing
  other revisions' caches skipped, zero failed.
- Both focused runtime regression files passed; changed Python dialect lint and
  `git diff --check` passed. No C++ source changed.
- [Raw evidence archive](../validation/issue36-evidence.zip): client/server
  transcripts, source snapshots, exact fixture/settings manifests, conservative
  duration boundaries, bank mutations, fire-load matches and check logs.
  `file-manifest.json` records each archive entry's SHA-256 and length.
- Working artifacts remain under `build/issue36/`; the archive omits private
  RSA keys, real user credentials, player saves and databases.

This validates seeded behavior on the local 289 engine. It does not establish
organic new-account progression, revision-225/274 live behavior or fleet
throughput. Discovery failures, setup corrections, the excluded CookBot stall,
the WalkTo wrapper, focused banking checks and #134 remain identified above.
