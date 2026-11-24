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

All four targets passed on fresh individual accounts at normal 600 ms ticks.
Each accepted account ran uninterrupted, returned to a bank and logged out.
The results span two client sessions: Trio uses a fresh account after its
original preparation failure, rather than a resumed timing.

| Quest | Account | Final QP | Result | Time taken |
|---|---|---|---|---|
| Nature Spirit | `d171a75d1ns` | 5 | PASS | 31m 39s |
| Shades of Mort'ton | `d171a75d1sm` | 9 | PASS | 23m 53s |
| Tai Bwo Wannai Trio | `d17a6a47dtw` | 7 | PASS | 1h 7m 34s |
| Shilo Village | `d171a75d1sv` | 7 | PASS | 40m 40s |

Every accepted result has a complete target journal, exactly one newly completed
quest, zero deaths, expected final QP, no initially completed target and a queue
with one done and zero stuck. Both native clients exited with code zero. The
original shared launcher correctly rejected its aggregate result because its
first Trio account failed; the three independent passing accounts are retained.
The separate fresh Trio launcher passed. These are four individual passes,
not a claim that the original four-account session passed as a whole.

Times run from each account's first `AIOQuester, queue:` to its passing
`E2E_RESULT`, including final banking and excluding seed/login staggering:

| Case | Queue start (UTC, 2026-11-24) | Passing result (UTC) | Exact seconds |
|---|---|---|---|
| `ns` | 03:16:47.937 | 03:48:26.944 | 1899.007 |
| `sm` | 03:16:50.950 | 03:40:44.330 | 1433.380 |
| `tw` | 03:37:31.128 | 04:45:04.734 | 4053.606 |
| `sv` | 03:16:53.922 | 03:57:34.152 | 2440.230 |

These timestamps fall on **November 23 locally (America/Regina)**.

Evidence and versions:

- Nature Spirit, Shades and Shilo: `build/e2e/phase17d-validation-20261123-v2`,
  seed `20261123T211440-seed-b1c0`, quest `20261123T211645-run-9313`.
  Prepared source `bccb2aca143888037ddbf6dd499fdf52b7a9e3e2`; quest-session
  source `3cf4c8f419c0a79ddd0a7719fc170383e6c5d1e9` adds the selection regression.
  Twenty-tick probes: 11,994–12,032 ms.
- Fresh Trio: `build/e2e/phase17d-trio-20261123`, seed
  `20261123T213523-seed-3466`, quest `20261123T213728-run-8ed4`.
  Prepared source `62b38e9fed9b7f5616c6a14a05754091772efdee`; quest-session
  source `3eaaa9d296293dbc33d8fdf98eee5c6af5c9944b` adds evidence documentation.
  Twenty-tick probes: 11,998–12,021 ms. `timings.json` and the quest session's
  `results.json` record its passing fresh run.
- Combined checked results and exact timings: `build/e2e/phase17d-final-results.json`.
  Original logs, seed acceptance, manifests, script hashes and session version
  files remain in the two run roots. Credentials remain ignored.
- Both runs use the same pinned client executable SHA-256:
  `45fe1bf80a17870b18c33eeb6517fd3ab3ac093f13b4c341706ab7db89a97ebe`.
  The supply fix changes external bot scripts, so no executable change was needed.
- Engine: `2395c968473333d13ff1454f5eff452a18a029b6`; content:
  `f32c62f66302f76b43c752ede3181de0c0d01369`. Server files remain unchanged by
  this validation. Preparation and its limits are documented in the suite guide.

The first attempt (`phase17d-validation-20261123`) was stopped shortly after
queue startup: Shades expanded to include Druidic Ritual through its Herblore
requirement. The corrected seed includes that unlock and matching QP. A
regression runs the real AIO quest selection against every prepared case and
requires exactly its target. No result or timing is accepted from that attempt.

The v2 Trio account `d171a75d1tw` failed before quest start (zero completed, one
stuck, QP 5, zero deaths). Shared supply preparation tried `skills.xp('supplies')`
while gathering seaweed. `62b38e9` restricts objective XP tracking to real skills,
retaining item counts and explicit prerequisite XP. Its runtime regression
reproduced the error before the fix and passes after it. The fresh Trio run
exercised seaweed gathering successfully and completed the quest. No failed
attempt contributes to its accepted time.

Validation: five launcher safeguards pass, changed scripts pass pocketpy lint,
the Release client builds, and the complete ported Python suite passes with
2,906 assertions. All eleven CI checks passed at `07f6e9a`; subsequent changes
in this evidence update are documentation only.

## Phase 17e

All 4 targets have fresh, uninterrupted **individual passes**, with
zero deaths, complete journals, exactly one completion per account, no stuck
queue entries, expected final QP, final bank return and clean logout. Tracks
[#158](https://github.com/ineedbots/lc-headless/issues/158) and
[PR #159](https://github.com/ineedbots/lc-headless/pull/159).

| Quest | Account | Result | Time taken | Final QP |
|---|---|---|---|---|
| The Tourist Trap | `e17989d00tt` | PASS, zero deaths | 27m 03s | 2 |
| Watch Tower | `e17713b4ewt` | PASS, zero deaths | 2h 46m 19s | 8 |
| Big Chompy Bird Hunting | `e17989d00cb` | PASS, zero deaths | 24m 16s | 2 |
| The Grand Tree | `e17989d00gt` | PASS, zero deaths | 36m 07s | 5 |

| Quest | Queue start (UTC) | Passing result (UTC) | Seconds |
|---|---|---|---|
| The Tourist Trap | 2026-11-24T11:43:43.765Z | 2026-11-24T12:10:46.750Z | 1622.985 |
| Watch Tower | 2026-11-24T13:03:07.121Z | 2026-11-24T15:49:25.741Z | 9978.620 |
| Big Chompy Bird Hunting | 2026-11-24T11:43:36.536Z | 2026-11-24T12:07:52.759Z | 1456.223 |
| The Grand Tree | 2026-11-24T11:43:40.733Z | 2026-11-24T12:19:47.927Z | 2167.194 |

Timings start at the first per-account queue entry and end at the passing
`E2E_RESULT`, including final banking and excluding seeding/login staggering.
The combined independently verified report is
`build/e2e/phase17ef-final-results.json`. Each accepted account has exactly one
quest session, one queue start, one final result and an unstarted target at seed
completion. Failed, interrupted and diagnostic attempts are excluded.

The three initial non-Watch-Tower accounts passed and logged out before the
original Watch Tower failure caused their shared client to exit 1. Thus these
are individual account passes; the original four-account launcher did not pass.
The fresh Watch Tower replacement's launcher passed with a clean process exit.

Preparation: [phase 17e guide](phase17e/README.md#preparation-and-limits).
Watch Tower seeds Druidic Ritual, Guam leaf, Bat bones and Gold bar; its fresh
replacement also seeds an ordinary Dragonfire shield. Dragon bones and all
quest-specific materials are obtained live. Other targets seed no completed
quest prerequisites or special materials. Standard prepared stats/supplies and
per-account infinite run apply. Normal 600 ms ticks were verified by 20-tick
probes taking 11.991–12.023 seconds initially and 11.997–12.010 seconds in the
Watch Tower replacement suite.

Original Watch Tower failure: one real death near Toban at
`2026-11-24T12:00:31.109Z`, with no food and repeated camp entry/approach retries,
followed later by a `deposit_all_matching` argument-count error in dragon-hunt
cleanup. The repair replenishes eight food below a four-item reserve, retries
pending Toban approaches within the same visit, and uses the bank API's single
predicate argument. The regression mock enforces that signature. Fresh Watch
Tower passed after those repairs; the failed original account is excluded.

Accepted evidence and versions:

- `build/e2e/phase17e-validation-20261124/`, session `20261124T054333-run-71ac`. Preparation source
  `9c8b946c3a16c3c8daea180dd38c031171f08bb5`, quest-session source
  `4fe2e0d4cc37602eb3e00952c097c790e860ade0`, binary SHA-256
  `45fe1bf80a17870b18c33eeb6517fd3ab3ac093f13b4c341706ab7db89a97ebe`.
- `build/e2e/phase17e-watchtower-20261124/`, session `20261124T070305-run-0967`. Preparation source
  `c65c005d9fc98d29af5ac540e6e45e775af1957a`, quest-session source
  `c65c005d9fc98d29af5ac540e6e45e775af1957a`, binary SHA-256
  `eda7edb173bf5b8b5a69066306feca356d6e98a5ca8618a50ea96b380e9f50c3`.

Engine `2395c968473333d13ff1454f5eff452a18a029b6`, content
`f32c62f66302f76b43c752ede3181de0c0d01369`; server implementation unchanged.
Local Release build, relevant launcher checks, focused runtime regressions,
dialect lint and full ported Python suite (2,906 native assertions) passed.
Regressions reproduced the old failures before the fixes. CI status belongs
to its checked commit; this evidence does not imply checks on a later commit.

## Phase 17f

All 5 targets have fresh, uninterrupted **individual passes**, with
zero deaths, complete journals, exactly one completion per account, no stuck
queue entries, expected final QP, final bank return and clean logout. Tracks
[#158](https://github.com/ineedbots/lc-headless/issues/158) and
[PR #159](https://github.com/ineedbots/lc-headless/pull/159).

| Quest | Account | Result | Time taken | Final QP |
|---|---|---|---|---|
| Elemental Workshop | `f17b5c196ew` | PASS, zero deaths | 22m 52s | 1 |
| Digsite Quest | `f17649fb3ds` | PASS, zero deaths | 44m 35s | 6 |
| Holy Grail | `f17649fb3hg` | PASS, zero deaths | 37m 27s | 8 |
| Family Crest | `f17378cd6fc` | PASS, zero deaths | 48m 25s | 1 |
| Horror from the Deep | `f17378cd6hd` | PASS, zero deaths | 1h 24m 04s | 2 |

| Quest | Queue start (UTC) | Passing result (UTC) | Seconds |
|---|---|---|---|
| Elemental Workshop | 2026-11-24T17:19:00.524Z | 2026-11-24T17:41:52.148Z | 1371.624 |
| Digsite Quest | 2026-11-24T11:43:54.520Z | 2026-11-24T12:28:29.935Z | 2675.415 |
| Holy Grail | 2026-11-24T11:44:07.131Z | 2026-11-24T12:21:34.143Z | 2247.012 |
| Family Crest | 2026-11-24T16:37:43.120Z | 2026-11-24T17:26:08.375Z | 2905.255 |
| Horror from the Deep | 2026-11-24T16:37:46.132Z | 2026-11-24T18:01:49.734Z | 5043.602 |

Timings start at the first per-account queue entry and end at the passing
`E2E_RESULT`, including final banking and excluding seeding/login staggering.
The combined independently verified report is
`build/e2e/phase17ef-final-results.json`. Each accepted account has exactly one
quest session, one queue start, one final result and an unstarted target at seed
completion. Failed, interrupted and diagnostic attempts are excluded.

The original phase 17f launcher correctly rejected the failed Elemental,
Family Crest and Horror accounts, although Digsite and Holy Grail passed and
logged out individually. The accepted replacements have separate clean launcher
passes: one for Elemental Workshop and one shared by Family Crest/Horror.
No aggregate pass is claimed for the original five-account launcher.

Preparation: [phase 17f guide](phase17f/README.md#preparation-and-limits).
Digsite seeds Druidic Ritual; Holy Grail seeds Merlin's Crystal. Family Crest
supplies five ordinary cooked fish and two Rubies, because its active Caleb
branch expects banked fish and the gem shop stocks one Ruby per restock.
Other quest materials are obtained live. Target progress and Horror's barcrawl
are not seeded. Standard prepared stats/supplies and infinite run apply;
no max-stat workaround was used. Normal 600 ms ticks were verified by 20-tick
probes: initial suite 11.983–11.996 seconds, survival replacements
11.987–12.010 seconds. The fresh Elemental v2 seed also passed its tick probes.

Failures and repairs retained as evidence:

- Initial Family Crest stopped on missing banked cooked fish; preparation was
  corrected. Its first replacement completed in 53m49s with a real death in the
  perfect-gold mine at `2026-11-24T12:20:07.111Z`. A 20-second ore wait skipped
  food upkeep despite carried food. The repair runs upkeep each tick, stops on
  runtime interruption/death, and enables melee protection for mine attackers.
  The accepted fresh replacement passed with the same combat profile.
- Initial Horror completed in 1h31m39s with a real death during the mother fight
  at `2026-11-24T13:00:27.507Z`. Shared melee prayer upkeep conflicted with the
  fight's missile protection. The fights now own their protection prayer; an
  empty food check also no longer suppresses every attack. The accepted fresh
  replacement passed both fights with zero deaths.
- Initial Elemental Workshop was blocked at the entrance. A focused live
  diagnostic on the stopped account reproduced the bad west stand and verified
  the corrected route: approach the wall from `(2709,3494,0)`, then the exact
  inside south stair stand `(2710,3496,0)`. The actual 2x2 stair is loc 3415 at
  `(2710,3497,0)`, angle 2; its rotated approach restriction forbids the west.
  Diagnostic log: `build/e2e/elemental-entrance-probe/client.log`.
- The first Elemental replacement was interrupted after the user spotted a full
  junk pack from generic crate searches. Searches now target only loc 3394
  (bowl), 3397 (leather) and 3395 (needle), approach before searching, reserve
  reward space, and bank cramped junk packs before more supplies/coal.
  Its disclosed diagnostic resumes banked the junk, repaired the bellows and
  completed with zero deaths at `2026-11-24T17:20:34.735Z`; those interrupted
  sessions are excluded from accepted timing. The separate fresh v2 passed.

Accepted evidence and versions:

- `build/e2e/phase17f-elemental-v2-20261124/`, session `20261124T111858-run-23e6`. Preparation source
  `2dca84eb067b7c96c24d90b100f7f444d395ab11`, quest-session source
  `ce7e02fb57af0595c015e3a7748d4b9157263c6b`, binary SHA-256
  `9f548464cbb02672694722469c4cea57c4b066ba6300661da7b57a12f3079546`.
- `build/e2e/phase17f-validation-20261124/`, session `20261124T054351-run-1ad4`. Preparation source
  `9c8b946c3a16c3c8daea180dd38c031171f08bb5`, quest-session source
  `4fe2e0d4cc37602eb3e00952c097c790e860ade0`, binary SHA-256
  `45fe1bf80a17870b18c33eeb6517fd3ab3ac093f13b4c341706ab7db89a97ebe`.
- `build/e2e/phase17f-survival-20261124/`, session `20261124T103741-run-db67`. Preparation source
  `aea870cb7eec475e5dd927cd7b522c2ba4358f40`, quest-session source
  `8d13c0a4d7423132b44437905e1cb6c4d382a744`, binary SHA-256
  `1e45cafa63d5ccc43e66d1b5d93773f1cbfcb1b1677ae18f541bf79bfaa63c07`.

Engine `2395c968473333d13ff1454f5eff452a18a029b6`, content
`f32c62f66302f76b43c752ede3181de0c0d01369`; server implementation unchanged.
Local Release build, relevant launcher checks, focused runtime regressions,
dialect lint and full ported Python suite (2,906 native assertions) passed.
Regressions reproduced the old failures before the fixes. CI status belongs
to its checked commit; this evidence does not imply checks on a later commit.

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

## Phase 17h

Fresh local-289 validation started on November 24, 2026, for
[#160](https://github.com/ineedbots/lc-headless/issues/160), in
[PR #161](https://github.com/ineedbots/lc-headless/pull/161).
Completion evidence is pending; startup and preparation are not passes.

| Quest | Account | Result | Time taken |
|---|---|---|---|
| Underground Pass | `h17270e59up` | Running | Pending |
| Regicide | `h176ebc68rg` | Fresh replacement preparing | Pending |

Both seed checks passed with unstarted targets, complete prerequisite journals,
ordinary supplies and correct initial QP (4 / 9). Each 20-tick probe took
11,999 ms. Quest session `20261124T130201-run-dad0` follows seed session
`20261124T130003-seed-e3c8`.
Evidence root: `build/e2e/phase17h-validation-20261124`.

The original Regicide account `h17270e59rg` did **not** complete. Its seeded
Underground Pass completion flag lacked the separate persistent gates in
`ibanmulti`, so cave entry repeatedly said to talk to King Lathas despite
Regicide being at stage 2. The affected account alone was stopped cleanly at
19:19:38 UTC, incomplete with zero deaths; Underground Pass continued without
interruption. The original launcher therefore cannot be an aggregate pass.
Preparation now includes prerequisite bits 5–8 (burned orbs), 11 (cave entry),
14–16 (paladin crests) and 18 (unicorn horn). No Regicide progress is seeded.
Seven phase 17h launcher tests and setup lint pass after the correction.

Fresh replacement root: `build/e2e/phase17h-regicide-v2-20261124`, prepared
from `4da00fd` on the same frozen binary. Both setup cases are seeded, but only
`rg` will run; its spare Underground Pass account is outside quest acceptance.

Preparation/runtime source: `914a7c85bc5a6a85625f47c7ae71d1014cd0b512`.
Frozen client: `build/e2e-binaries/phase17hi-initial.exe`, SHA-256
`9f548464cbb02672694722469c4cea57c4b066ba6300661da7b57a12f3079546`.
Engine/content: `2395c968473333d13ff1454f5eff452a18a029b6` /
`f32c62f66302f76b43c752ede3181de0c0d01369`, left unchanged.
See the [preparation limits and rerun instructions](phase17h/README.md).

## Phase 17i

Fresh Legends Quest validation started on November 24, 2026, under the same
issue and PR. Completion remains pending.

| Quest | Account | Result | Time taken |
|---|---|---|---|
| Legends Quest | `i179a9d20lq` | Running | Pending |

Evidence root: `build/e2e/phase17i-validation-20261124`.
The setup uses the same frozen binary, source and unchanged engine/content
versions as phase 17h. All 45 seeded completed quests, totaling 107 QP, are
listed in `phase17i/scripts/phase17i_cases.py`; the target is never advanced.
Seed session `20261124T130201-seed-0b5f` passed all 45 prerequisite journals,
107 initial QP and a 20-tick probe of 12,020 ms. Quest session
`20261124T130709-run-a174` selected only Legends Quest.
See the [preparation limits and rerun instructions](phase17i/README.md).

For both suites, acceptance requires a newly completed single-target AIO queue,
complete target journal, zero deaths, expected final QP and clean logout/process
exit. Time taken runs from the first per-account queue log to its passing result,
including final banking. Interrupted attempts and resumed diagnostic sessions
cannot supply uninterrupted timings. These suites cover quest completion;
Kharazi/Isafdar clue workflows are outside this request.

Release client/tests build, seven phase 17h and six phase 17i launcher tests, focused Underground
Pass/Regicide/Legends runtime specs and setup dialect lint passed.
