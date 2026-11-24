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

## Phase 17c

[Suite](phase17c/README.md) · [PR #155](https://github.com/ineedbots/lc-headless/pull/155)

All five fresh accounts passed in one uninterrupted quest session, with no
restarts or manual quest intervention. These timings supersede the earlier
phase 17c observations below. Every target journal was complete, exactly one
quest was newly completed per account, no queue entries were stuck, all final
QP totals matched, and all accounts logged out before the client exited zero.

| Quest | Case | Final QP | Result | Time taken |
|---|---|---|---|---|
| Death Plateau | `dp` | 1 | PASS, 0 deaths | 32m 23s |
| Troll Stronghold | `ts` | 2 | PASS, 0 deaths | 14m 54s |
| Eadgar's Ruse | `er` | 7 | PASS, 0 deaths | 1h 28m 32s |
| Plague City | `pc` | 1 | PASS, 0 deaths | 35m 04s |
| Biohazard | `bh` | 4 | PASS, 0 deaths | 25m 19s |

Source `11dd4b1de72388bfd467f4bbaa1baa2dde887b16`; pinned executable SHA-256
`45fe1bf80a17870b18c33eeb6517fd3ab3ac093f13b4c341706ab7db89a97ebe`.
Artifacts: `build/e2e/phase17c-uninterrupted-20261123`, quest session
`sessions/20261123T190816-run-df48`, seed session
`sessions/20261123T190616-seed-52a4`. The root's `timings.json` records each
account's queue/result timestamps and unrounded elapsed seconds; `results.json`
in the quest session records the passing outcomes. Timings include the final
bank return, excluding seeding and login staggering. The run occurred on
November 23, 2026 local time (November 24 UTC).

Each target began unstarted. Preparation used the suite's boosted skills,
ordinary equipment/consumables, prerequisite completions/QP, one raw ranarr weed
for Eadgar and ten bread/trout for Death Plateau. Completed Death Plateau also
requires its scouted-path state (`death_map=8`) for Tenzing's door. Mad Eadgar was
left imprisoned so the handler had to free him. Per-character infinite run was
enabled. Normal 600 ms ticks were checked before execution: twenty-tick probes
measured 11,970–12,028 ms. Engine `2395c968473333d13ff1454f5eff452a18a029b6` and
content `f32c62f66302f76b43c752ede3181de0c0d01369` remained unchanged.

The fresh full run exercised explicit HQ leaf closure at `(2547,3325,0)` and
Eadgar's excess-food deposit (`lobster 8→6`), followed by quest completion.
The full ported stdlib suite passed after both fixes (2,899 native assertions),
as did four suite safeguard tests and changed-script lint. All 11 CI checks
passed on the tested source `11dd4b1`.

Earlier diagnostic runs remain separate. Plague City/Biohazard used `794a2ed`
in `build/e2e/phase17c-validation-20261123-v2/sessions/20261123T180249-run-f2f5`;
Death Plateau/Troll Stronghold used `f380a40` in
`build/e2e/phase17c-validation-20261123-v3/sessions/20261123T181719-run-1f6b`.
Their per-account zero-death passes took 35m 14s / 29m 43s / 31m 46s / 14m 14s
respectively; aggregate launchers correctly rejected other failed cases.
These older timings are superseded by the fresh five-account table above.

Earlier v1 journal verification and v2 food/path setup failures are not passes.
Eadgar's v3 stage-60 run filled its pack at nine grain because its smaller food
float did not bank surplus food. `160e9df` added food quantity caps; its first
resume (`20261123T190019-run-d6da`) then exposed a shared cap executor bug using
normal inventory actions instead of the bank side panel. `8727343` corrected
cap clicks and acknowledgements. Both regressions failed before and passed
after their fixes, including mixed food, committed mountain travel, stale normal
counts, rejected/unchanged deposits and a zero cap. The next saved-progress
resume (`20261123T190309-run-aca4`) successfully banked two lobsters and collected
the tenth grain, but was stopped at the user's request to start the fresh run.
Neither interrupted Eadgar attempt supplies a completion time.

## Phase 17d

[Suite](phase17d/README.md) · [PR #157](https://github.com/ineedbots/lc-headless/pull/157)
· [Issue #156](https://github.com/ineedbots/lc-headless/issues/156)

Live validation is in progress; no completion timings are accepted yet.

| Quest | Account | Result | Time taken |
|---|---|---|---|
| Nature Spirit | `d1723575dns` | Pending | — |
| Shades of Mort'ton | `d1723575dsm` | Pending | — |
| Tai Bwo Wannai Trio | `d1723575dtw` | Pending | — |
| Shilo Village | `d1723575dsv` | Pending | — |

Run root: `build/e2e/phase17d-validation-20261123`, prepared from
`bad8f350237c29608b46ad06499d02c36dea109b`. Client binary SHA-256:
`45fe1bf80a17870b18c33eeb6517fd3ab3ac093f13b4c341706ab7db89a97ebe`.
Engine: `2395c968473333d13ff1454f5eff452a18a029b6`; content:
`f32c62f66302f76b43c752ede3181de0c0d01369`. Preparation and its limits are
documented in the suite guide. Server files remain unchanged by this validation.

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
A pre-run probe measured twenty ticks in 12,029 ms. The earlier attribution of
the real death to fourth-form overkill was unproven: those logs did not record
the NPC form. The server checks for exactly zero remaining HP, but its fourth
form's configured Strength 5 and default strength bonus produce a maximum hit
of 1. The equality check alone therefore does not reproduce overkill under
these parameters. The user requested that the server remain unchanged.
The failed attempt and corrected diagnosis remain recorded in
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
remains historical evidence. The successful retry does not establish reliability
of the earlier foodless client strategy; phase-aware food support is tracked
in #153 and PR #152.

### Focused Koschei food regression

Fresh scratch account `klegf692a4ft`, client source `ec29f3e`, passed the warrior
leg alone at normal 600 ms ticks (pre-run probe: twenty ticks in 12,041 ms).
Other six votes and Thorvald-started were explicitly seeded; Thorvald-done was
absent. Attack/Strength/Defence 75, HP85, Prayer43, 100 banked lobsters and infinite
run were used. The real AIOQuester handled equipment cleanup, withdrew eight
lobsters and ran the combat leg; the temporary wrapper only observed and stopped
it on the safe loft return. No server code was edited.

| Form | Lowest HP | Lobsters eaten |
|---|---|---|
| 1 | 85 | 0 |
| 2 | 85 | 0 |
| 3 | 68 | 3 |
| 4 | 1 | 0 |

| Scope | Result | Real deaths | Time taken |
|---|---|---|---|
| Warrior leg, including preparation and banking | PASS | 0 | 12m 21s |
| Fight step through safe-return result | PASS | 0 | 6m 19s |

Queue start: 22:33:54.112 UTC; fight step: 22:39:56.534 UTC; passing result:
22:46:15.128 UTC. All four forms were observed, food remained unused in form 4,
the character reached `(2667,3692,L1)` and logged out, and the client exited zero.
The quest remained incomplete as intended. This does not replace the full-quest
timing above. Engine checkout `2395c968473333d13ff1454f5eff452a18a029b6`, content
checkout `f32c62f66302f76b43c752ede3181de0c0d01369`; artifacts:
`build/e2e/koschei-leg-20261123-v5/sessions/20261123T163352-run-e4d6`.
Temporary setup/rerun instructions are in `build/koschei-leg/README.md`.

The first combat attempt (`koschei-leg-20261123-v4`, source `02636ff`) stalled on
the third-form transition and was stopped as a failed attempt. Shared sustain
dropped prayer outside combat while the combat loop re-enabled it, preventing
reengagement. `ec29f3e` restricts shared sustain to combat and has a failing-before,
passing-after runtime regression. The accepted v5 attempt used a fresh account
with no restart or manual quest intervention. Earlier v1–v3 seed-verification
failures occurred before combat and remain separate artifacts.


## Focused Biohazard HQ exit regression

The phase 17c v2 account repeatedly repathed while leaving the headquarters:
the downstairs door at `(2546,3325,0)` opens onto `(2547,3325,0)`, blocking the
corridor beside the furniture. The exit leg now crosses to `(2547,3326,0)`, closes
that specific open leaf, verifies closure and continues to the scripted HQ exit.
The regression fails before the change and passes after it, including refused
or unchanged closure and an unrelated upstairs leaf.

| Scope | Result | Time taken |
|---|---|---|
| HQ upstairs to West Ardougne, including explicit leaf closure | PASS | 15s |

On November 23, 2026 (local time), spare prepared account `c1762b0d8bh` was placed
at `(2550,3326,1)` and ran the real `biohazard.travel.leave_hq` handler with normal
600 ms ticks. No door state was seeded. It opened/crossed the inner door, logged
explicit closure at 00:25:58.334 UTC on November 24, and emitted a passing
`HQ_EXIT_RESULT` at 00:26:04.903 UTC at `(2551,3320,0)`. The start was
00:25:49.903 UTC. The character logged out and the process ended.

This is **leg-only** validation, not a Biohazard completion or full quest timing.
The spare account came from v3 preparation and never ran the full quest. The
ongoing v2/v3 quest clients continued on their original binary, without restart;
they do not execute this new fix. The focused client was built separately as
`Rs2004Headless-hq-test.exe` from parent `f380a40` plus the HQ fix. Runtime source
SHA-256: `30e876535dbdfb328c58e5179ea27a2b87b26dac68b9babc7a648f3d9af04c88`.
Binary SHA-256: `e0bc1defada67cb31967ddd30fd9679cad77470ab4c4cc1a1f2c73c0ded21017`.
Engine/content remained `2395c968` / `f32c62f6`, unchanged. Raw setup, logs and
provenance: `build/e2e/biohazard-hq-20261123`.
