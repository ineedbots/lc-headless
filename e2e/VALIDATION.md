# Recorded live quest validation

These are measured acceptance results from November 23, 2026, on local revision
289. Quest execution used nominal 600 ms ticks, per-character infinite run and
the preparation disclosed by each suite. All cases below completed with zero
deaths during quest execution; seeded prerequisites are included in final QP.

**Time taken** is wall-clock elapsed time from that account's first
`AIOQuester, queue:` log entry to its passing `E2E_RESULT`, rounded to the nearest
second. It includes quest preparation/banking, retries, travel, random events and
the final bank return. It excludes account seeding and waiting for other accounts
to log in. Resumed cases include their offline/rebuild interval; these are
observations from one run, not expected runtimes or speed comparisons.

For the original phase 17g manual wrapper, the endpoint is its first script DONE
after quest completion instead of `E2E_RESULT`. Its cleanup limitations remain
disclosed below. Raw logs and credentials stay under ignored `build/`.

## Phase 16

[Suite](phase16/README.md) · [PR #148](https://github.com/ineedbots/lc-headless/pull/148)

Source `be0ea90`; artifacts `build/e2e/phase16-individual-20261123/sessions/20261123T103400-run-039f` (`batch-1/client.log` and `batch-2/client.log`). Nineteen individual accounts, both Arrav gangs, both clients exited zero. This table covers the independent run, not the optional two-account full queues.

| Case | Quest | Final QP | Result | Time taken |
|---|---|---|---|---|
| `ru` | Rune Mysteries Quest | 1 | PASS | 11m 20s |
| `do` | Doric's Quest | 1 | PASS | 7m 04s |
| `ks` | The Knight's Sword | 1 | PASS | 23m 20s |
| `sh` | Sheep Shearer | 1 | PASS | 10m 29s |
| `rg` | The Restless Ghost | 1 | PASS | 10m 16s |
| `co` | Cook's Assistant | 1 | PASS | 7m 44s |
| `im` | Imp Catcher | 1 | PASS | 45m 44s |
| `er` | Ernest the Chicken | 4 | PASS | 11m 25s |
| `wp` | Witch's Potion | 1 | PASS | 5m 49s |
| `rj` | Romeo & Juliet | 5 | PASS | 6m 10s |
| `pa` | Prince Ali Rescue | 3 | PASS | 23m 26s |
| `pt` | Pirate's Treasure | 2 | PASS | 13m 29s |
| `ph` | Shield of Arrav, Phoenix | 1 | PASS | 10m 35s |
| `ba` | Shield of Arrav, Black Arm | 1 | PASS | 10m 53s |
| `gd` | Goblin Diplomacy | 5 | PASS | 25m 57s |
| `de` | Demon Slayer | 3 | PASS | 17m 51s |
| `bk` | Black Knight's Fortress | 15 | PASS | 9m 18s |
| `vs` | Vampire Slayer | 3 | PASS | 14m 13s |
| `ds` | Dragon Slayer | 34 | PASS | 52m 36s |

## Phase 17a

[Suite](phase17a/README.md) · [PR #150](https://github.com/ineedbots/lc-headless/pull/150)

Source `829fce0`; artifacts `build/e2e/phase17a-validation-20261123-v2/sessions/20261123T115326-run-24e4/client.log`. All twelve fresh targets completed without quest-run restarts, with matching QP and clean logouts.

| Case | Quest | Final QP | Result | Time taken |
|---|---|---|---|---|
| `dr` | Druidic Ritual | 4 | PASS | 14m 13s |
| `mf` | Monk's Friend | 1 | PASS | 10m 59s |
| `gc` | Gertrude's Cat | 1 | PASS | 10m 38s |
| `jp` | Jungle Potion | 5 | PASS | 14m 07s |
| `ct` | Clock Tower | 1 | PASS | 12m 01s |
| `hc` | Hazeel Cult | 1 | PASS | 10m 17s |
| `wh` | Witch's House | 4 | PASS | 15m 13s |
| `fc` | Fishing Contest | 1 | PASS | 11m 16s |
| `mm` | Murder Mystery | 3 | PASS | 8m 09s |
| `ss` | Sea Slug Quest | 1 | PASS | 12m 40s |
| `pp` | Priest in Peril | 2 | PASS | 22m 32s |
| `tt` | Tribal Totem | 1 | PASS | 10m 12s |

## Phase 17b

[Suite](phase17b/README.md) · [PR #152](https://github.com/ineedbots/lc-headless/pull/152)

Sources `0ea1238` (first session) and `a8a3159` (Scorpion Catcher resume). Artifacts under `build/e2e/phase17b-validation-20261123/sessions`: `20261123T122354-run-30db/client.log` and `20261123T131153-run-85ae/client.log`. All nine targets completed, with matching QP and clean logouts. The first session was interrupted to rebuild the client; it records eight passes and an interrupted Scorpion Catcher. The resumed session records its pass. This is acceptance across two sessions. Setup ran at 100 ms; the quest run followed a measured twenty ticks in 12,005 ms after normal speed was restored.

| Case | Quest | Final QP | Result | Time taken |
|---|---|---|---|---|
| `dc` | Dwarf Cannon | 1 | PASS | 26m 18s |
| `sh` | Sheep Herder | 4 | PASS | 24m 55s |
| `tg` | Tree Gnome Village | 2 | PASS | 18m 04s |
| `wf` | Waterfall Quest | 1 | PASS | 23m 59s |
| `sc` | Scorpion Catcher | 1 | PASS | 1h 2m 35s |
| `ob` | Observatory Quest | 2 | PASS | 29m 43s |
| `fa` | Fight Arena | 2 | PASS | 20m 18s |
| `mc` | Merlin's Crystal | 6 | PASS | 28m 48s |
| `lc` | Lost City | 3 | PASS | 12m 40s |

Scorpion Catcher's table timing now comes from the fresh uninterrupted run at `build/e2e/phase17b-uninterrupted-20261123/sessions/20261123T134304-run-1fc1`, source `4b201aa`: zero deaths, no client restart or manual intervention, clean logout. The older resumed result remains historical evidence: 1h 7m 31s elapsed, 1h 6m 42s active, 19m 49s in its final session. No target progress or objective items were seeded during recovery.

## Phase 17g

[Suite](phase17g/README.md) · [PR #146](https://github.com/ineedbots/lc-headless/pull/146)

Original acceptance artifacts: `build/phase17g-live-20261122/{client,fremennik,ikov}.log` and `final-acceptance.md`. The Hero pair used source `699a205`; Ikov resumed with the web fix in `71e5f54`. Fremennik restarted its wrapper near the beginning; Ikov includes its client restarts. All returned to a bank and stopped their scripts. Hero and Fremennik logged out cleanly; Ikov needed a separate administrative cleanup after a later post-completion incident. That cleanup is excluded from timing and does not establish successful quest navigation. These rows describe the original manual acceptance, not later harness reruns.

| Case | Quest | Final QP | Result | Time taken |
|---|---|---|---|---|
| `ph` | Hero's Quest, Phoenix | 57 | PASS | 42m 01s |
| `ba` | Hero's Quest, Black Arm | 57 | PASS | 50m 07s |
| `ik` | Temple of Ikov, Guardians | 1 | PASS | 1h 18m 31s |
| `ft` | The Fremennik Trials | 3 | PASS | 52m 40s |

Ikov's table timing now comes from the fresh uninterrupted run at
`build/e2e/phase17g-uninterrupted-20261123/sessions/20261123T134304-run-20d6`,
source `4b201aa`: zero deaths, no client restart or manual intervention, clean
logout. Its original 1h 44m 40s resumed timing remains historical evidence.
The newer Ikov timing uses the standard `E2E_RESULT` endpoint; the original
manual-wrapper endpoint above applies to the two Hero's Quest rows.
The fresh run's Fremennik account completed but failed acceptance with one real
Koschei death, so its 58m 34s attempted timing does not replace the older row.
The shared two-account launcher correctly rejected that overall session; Ikov's
individual passing record and clean logout are retained independently.
A pre-run probe measured twenty ticks in 12,029 ms. The server's
`combat_viking_damage_player` checks for exactly zero remaining HP, so an
overkill bypasses its intended safe defeat. The user requested that the server
remain unchanged. The failed attempt remains recorded in
[#153](https://github.com/ineedbots/lc-headless/issues/153).

Fremennik's table timing now uses fresh account `g17505881ft`, source `3e697e4`,
artifacts `build/e2e/fremennik-retry-20261123/sessions/20261123T151055-run-09c2`.
It passed with one earned completion, 3 QP, zero deaths, no restart or manual
intervention, and a clean logout. Queue start was 21:10:57.107 UTC and passing
`E2E_RESULT` was 22:03:37.357 UTC. Koschei triggered the intended safe defeat
and returned the character to Thorvald's loft. A pre-run probe measured twenty
ticks in 12,025 ms; standard suite preparation and infinite run were retained.
The session records engine checkout `2395c968473333d13ff1454f5eff452a18a029b6`.
No server code was changed by this validation. The prior 59m 31s resumed timing
remains historical evidence. The successful retry does not resolve the server's
overkill condition in #153.
