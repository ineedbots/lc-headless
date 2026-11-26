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

Fresh local-289 acceptance completed on November 24, 2026, for
[#160](https://github.com/ineedbots/lc-headless/issues/160), in
[PR #161](https://github.com/ineedbots/lc-headless/pull/161).
Both quests passed on fresh replacement accounts after the repairs below.

| Quest | Account | Result | Time taken | Final QP |
|---|---|---|---|---|
| Underground Pass | `h174f033fup` | PASS, zero deaths | 41m 40s | 9 |
| Regicide | `h176ebc68rg` | PASS, zero deaths | 1h 20m 47s | 12 |

Each accepted account had exactly one selected target, one newly completed quest,
a complete journal, queue done 1 / stuck 0 / total 1, expected QP, final banking
and clean logout. Each selected launcher passed and exited cleanly. These are
**two uninterrupted individual runs in separate sessions**; the original two-account
phase 17h launcher failed and is excluded. Spare accounts used only for preparation
are outside quest acceptance. No manual pauses, resumes or restarts occurred in
the accepted runs; Regicide's quest-owned messenger relog is part of its workflow.

| Quest | Queue start (UTC, November 24) | Passing result (UTC) | Seconds |
|---|---|---|---|
| Underground Pass | 19:38:36.240 | 20:20:15.825 | 2499.585 |
| Regicide | 19:22:30.234 | 20:43:17.038 | 4846.804 |

Time taken includes quest preparation performed by AIO and final banking, from
its first per-account queue log through `E2E_RESULT`. It excludes seeding and
login staggering. Whole-second labels round the measured elapsed seconds.

Accepted evidence:

- Underground Pass: `build/e2e/phase17h-upass-v2-20261124`, seed
  `20261124T133635-seed-b6fc`, quest `20261124T133834-run-f1b8`.
  Prepared/session source `5c92c41ce3c3791b94edffd1249365a375913c7e`.
  Target unstarted with 4 initial QP; 20 ticks took 11,988 ms.
  Frozen client `build/e2e-binaries/phase17h-brew.exe`, SHA-256
  `830cb5de5384d7c304db9faae6416c7221de38662ca10121b6b3ac0281132712`.
  Clean logout at 20:20:16.442 UTC.
- Regicide: `build/e2e/phase17h-regicide-v2-20261124`, seed
  `20261124T132028-seed-d0a8`, quest `20261124T132228-run-0bf9`.
  Prepared source `4da00fd384148a0a1ba80e92e934a1c22b468c60`, session source
  `fdc0b686c47f2be83cbb6ee8bb9a4bc4aadbd5b6` (documentation-only difference).
  Target unstarted with 9 initial QP; 20 ticks took 11,997 ms.
  Frozen client `build/e2e-binaries/phase17hi-initial.exe`, SHA-256
  `9f548464cbb02672694722469c4cea57c4b066ba6300661da7b57a12f3079546`.
  Clean logout at 20:43:17.637 UTC.

The [setup guide](phase17h/README.md) discloses stats, ordinary supplies,
infinite run and completed prerequisites. Regicide additionally receives sharks
and Underground Pass's persistent `ibanmulti=379360` gates: bits 5–8 (burned
orbs), 11 (cave entry), 14–16 (paladin crests) and 18 (unicorn horn).
These represent completed prerequisite progress; no Regicide progress or quest
items are seeded. The Underground Pass target receives none of these bits.

Failed attempts and repairs:

- Original `h17270e59rg` reached Regicide stage 2 but could not enter the cave:
  its completed Underground Pass journal flag alone did not open the separate
  persistent gates. Only that account was stopped at 19:19:38 UTC, incomplete
  with zero deaths. Fix `4da00fd` supplies the prerequisite gate bits and adds
  a regression for cave, orb-well and paladin-door requirements.
- Original `h17270e59up` reached stage 7 but stood at `(2327,9801,0)` outside
  the brew hut. Its three-tile arrival radius accepted a stand through the north
  wall, so bucket use repeatedly failed. Bounded retries and safe-exit recovery
  ended the account at 19:31:11 UTC, incomplete with zero deaths and 4 QP.
  Fix `5c92c41` walks to `(2326,9799,0)`, inside the hut, via the existing door
  route. The runtime regression fails before the change and passes after it.

Original evidence: `build/e2e/phase17h-validation-20261124`, seed
`20261124T130003-seed-e3c8`, failed quest session `20261124T130201-run-dad0`.
Neither original account contributes an accepted completion time.

A focused live brew leg on the stopped original account opened/crossed the door
at `(2325,9801,0)`, filled the bucket and logged out cleanly. Its 6.001-second
result at 19:35:35.623–19:35:41.624 UTC is **leg-only**, excluded from full-quest
timing. No quest flags, positions or items were seeded for this diagnostic.
Evidence: `build/e2e/upass-brew-probe-20261124` and
`build/upass-brew-leg-stdout.log`.

Engine/content remained unchanged at
`2395c968473333d13ff1454f5eff452a18a029b6` /
`f32c62f66302f76b43c752ede3181de0c0d01369`. Normal 600 ms ticks were verified.
Release build, seven phase 17h launcher tests, changed-file dialect lint, focused
runtime regression and full ported Python suite (2,906 native assertions) passed.

## Phase 17i

Fresh Legends Quest acceptance completed on November 24, 2026, under the same
issue and PR, in its original uninterrupted session.

| Quest | Account | Result | Time taken | Final QP |
|---|---|---|---|---|
| Legends Quest | `i179a9d20lq` | PASS, zero deaths | 1h 46m 36s | 111 |

The account selected only Legends Quest, recorded one newly completed quest,
a complete journal, queue done 1 / stuck 0 / total 1 and expected 111 QP.
It completed the final bank return and logged out cleanly at 20:53:48.239 UTC;
the selected launcher passed and exited cleanly. No manual intervention, pause,
resume or restart occurred. Queue start: 19:07:11.643 UTC; passing result:
20:53:47.643 UTC; elapsed: **6396.000 seconds**. Timing follows phase 17h's
queue-to-result convention.

Evidence: `build/e2e/phase17i-validation-20261124`, seed
`20261124T130201-seed-0b5f`, quest `20261124T130709-run-a174`.
Prepared source `914a7c85bc5a6a85625f47c7ae71d1014cd0b512`, session source
`383325e8366ad3e6215b8c469de829d30bab1929` (documentation-only difference).
Frozen client `build/e2e-binaries/phase17hi-initial.exe`, SHA-256
`9f548464cbb02672694722469c4cea57c4b066ba6300661da7b57a12f3079546`.
Engine/content versions match phase 17h and were left unchanged.

Preparation verified all 45 completed prerequisite/QP-gate journals, totaling
107 initial QP, with Legends unstarted. The 20-tick probe took 12,020 ms.
The [setup guide](phase17i/README.md) and `scripts/phase17i_cases.py` list all
preparation, including ordinary gems, lockpicks, orbs, cosmic runes and rune axe.
No target quest flags or target quest items were seeded. Six phase 17i launcher
tests, focused runtime checks and setup dialect lint passed.

All three accepted launchers retain `results.json`, `version.json`, client logs
and per-root `timings.json`. An independent audit checked result/queue/QP fields,
exactly one queue/result per account, matching snapshots and binary hashes,
clean logout, launcher PASS and empty launcher stderr. Combined report:
`build/e2e/phase17hi-final-results.json`. The failed original phase 17h launcher
is not an aggregate pass. All quest accounts are now logged out.
These suites cover prepared quest completion; Kharazi/Isafdar clue workflows
from historical issue #34 are outside this request.

## Grand concurrent run

The November 24, 2026 grand run launched all 65 individual cases concurrently
at normal 600 ms ticks. **62 cases passed; three failed after real deaths:**
Phoenix Heroes, Regicide, and Legends. All accounts have stopped. The last
passing result was Watch Tower at 23:52:23.633 UTC. The aggregate grand run
**failed**; later replacements do not erase its failures.

Source: `767b558ca8b3736b74cae7f93ef5dbe768005e48`. Frozen binary SHA-256:
`830cb5de5384d7c304db9faae6416c7221de38662ca10121b6b3ac0281132712`. Evidence: `build/e2e/grand-20261124`,
including `provenance.json`, `results.json`, and per-phase session logs.
Each account started its queue once, without manual intervention, pause, resume
or restart. Optional phase 16 two-account full queues were excluded. Time taken
is queue start through result, including the final bank return for passing cases;
failed-case time ends at its failure result. Exact seconds are retained in JSON.
Mixed phase 17g/h client groups and phase 17i have failed launcher outcomes;
their individually passing cases are not aggregate phase passes.

| Phase | Quest | Account | Result | Time taken | Final QP | Deaths |
|---|---|---|---|---|---|---|
| 16 | Rune Mysteries Quest | `f16ac6b5cru` | PASS | 11m 23s | 1 | 0 |
| 16 | Doric's Quest | `f16ac6b5cdo` | PASS | 6m 41s | 1 | 0 |
| 16 | The Knight's Sword | `f16ac6b5cks` | PASS | 24m 12s | 1 | 0 |
| 16 | Sheep Shearer | `f16ac6b5csh` | PASS | 10m 25s | 1 | 0 |
| 16 | The Restless Ghost | `f16ac6b5crg` | PASS | 10m 14s | 1 | 0 |
| 16 | Cook's Assistant | `f16ac6b5cco` | PASS | 7m 47s | 1 | 0 |
| 16 | Imp Catcher | `f16ac6b5cim` | PASS | 19m 02s | 1 | 0 |
| 16 | Ernest the Chicken | `f16ac6b5cer` | PASS | 11m 27s | 4 | 0 |
| 16 | Witch's Potion | `f16ac6b5cwp` | PASS | 5m 49s | 1 | 0 |
| 16 | Romeo & Juliet | `f16ac6b5crj` | PASS | 6m 10s | 5 | 0 |
| 16 | Prince Ali Rescue | `f16ac6b5cpa` | PASS | 23m 21s | 3 | 0 |
| 16 | Pirate's Treasure | `f16ac6b5cpt` | PASS | 13m 23s | 2 | 0 |
| 16 | Shield of Arrav (Phoenix) | `f16ac6b5cph` | PASS | 10m 12s | 1 | 0 |
| 16 | Shield of Arrav (Black Arm) | `f16ac6b5cba` | PASS | 10m 30s | 1 | 0 |
| 16 | Goblin Diplomacy | `f16ac6b5cgd` | PASS | 21m 23s | 5 | 0 |
| 16 | Demon Slayer | `f16ac6b5cde` | PASS | 17m 43s | 3 | 0 |
| 16 | Black Knight's Fortress | `f16ac6b5cbk` | PASS | 9m 23s | 15 | 0 |
| 16 | Vampire Slayer | `f16ac6b5cvs` | PASS | 14m 05s | 3 | 0 |
| 16 | Dragon Slayer | `f16ac6b5cds` | PASS | 54m 46s | 34 | 0 |
| 17a | Druidic Ritual | `a179fbc34dr` | PASS | 14m 23s | 4 | 0 |
| 17a | Monk's Friend | `a179fbc34mf` | PASS | 10m 53s | 1 | 0 |
| 17a | Gertrude's Cat | `a179fbc34gc` | PASS | 11m 14s | 1 | 0 |
| 17a | Jungle Potion | `a179fbc34jp` | PASS | 14m 06s | 5 | 0 |
| 17a | Clock Tower | `a179fbc34ct` | PASS | 11m 58s | 1 | 0 |
| 17a | Hazeel Cult | `a179fbc34hc` | PASS | 11m 07s | 1 | 0 |
| 17a | Witch's House | `a179fbc34wh` | PASS | 14m 59s | 4 | 0 |
| 17a | Fishing Contest | `a179fbc34fc` | PASS | 11m 19s | 1 | 0 |
| 17a | Murder Mystery | `a179fbc34mm` | PASS | 8m 09s | 3 | 0 |
| 17a | Sea Slug Quest | `a179fbc34ss` | PASS | 12m 46s | 1 | 0 |
| 17a | Priest in Peril | `a179fbc34pp` | PASS | 35m 55s | 2 | 0 |
| 17a | Tribal Totem | `a179fbc34tt` | PASS | 10m 09s | 1 | 0 |
| 17b | Dwarf Cannon | `b17129a5bdc` | PASS | 25m 01s | 1 | 0 |
| 17b | Sheep Herder | `b17129a5bsh` | PASS | 25m 33s | 4 | 0 |
| 17b | Tree Gnome Village | `b17129a5btg` | PASS | 17m 46s | 2 | 0 |
| 17b | Waterfall Quest | `b17129a5bwf` | PASS | 23m 56s | 1 | 0 |
| 17b | Scorpion Catcher | `b17129a5bsc` | PASS | 50m 17s | 1 | 0 |
| 17b | Observatory Quest | `b17129a5bob` | PASS | 29m 22s | 2 | 0 |
| 17b | Fight Arena | `b17129a5bfa` | PASS | 19m 41s | 2 | 0 |
| 17b | Merlin's Crystal | `b17129a5bmc` | PASS | 28m 39s | 6 | 0 |
| 17b | Lost City | `b17129a5blc` | PASS | 13m 35s | 3 | 0 |
| 17c | Death Plateau | `c17a36543dp` | PASS | 32m 07s | 1 | 0 |
| 17c | Troll Stronghold | `c17a36543ts` | PASS | 15m 31s | 2 | 0 |
| 17c | Eadgar's Ruse | `c17a36543er` | PASS | 1h 28m 21s | 7 | 0 |
| 17c | Plague City | `c17a36543pc` | PASS | 33m 26s | 1 | 0 |
| 17c | Biohazard | `c17a36543bh` | PASS | 25m 39s | 4 | 0 |
| 17d | Nature Spirit | `d170e1029ns` | PASS | 31m 01s | 5 | 0 |
| 17d | Shades of Mortton | `d170e1029sm` | PASS | 24m 08s | 9 | 0 |
| 17d | Tai Bwo Wannai Trio | `d170e1029tw` | PASS | 1h 10m 29s | 7 | 0 |
| 17d | Shilo Village | `d170e1029sv` | PASS | 39m 03s | 7 | 0 |
| 17e | The Tourist Trap | `e17ad30bdtt` | PASS | 23m 59s | 2 | 0 |
| 17e | Watch Tower | `e17ad30bdwt` | PASS | 2h 12m 04s | 8 | 0 |
| 17e | Big Chompy Bird Hunting | `e17ad30bdcb` | PASS | 29m 26s | 2 | 0 |
| 17e | The Grand Tree | `e17ad30bdgt` | PASS | 39m 53s | 5 | 0 |
| 17f | Elemental Workshop | `f176837d7ew` | PASS | 20m 38s | 1 | 0 |
| 17f | Digsite Quest | `f176837d7ds` | PASS | 39m 41s | 6 | 0 |
| 17f | Holy Grail | `f176837d7hg` | PASS | 36m 46s | 8 | 0 |
| 17f | Family Crest | `f176837d7fc` | PASS | 48m 56s | 1 | 0 |
| 17f | Horror from the Deep | `f176837d7hd` | PASS | 1h 25m 37s | 2 | 0 |
| 17g | Hero's Quest (Phoenix) | `g178f773bph` | FAIL | 42m 26s | 56 | 1 |
| 17g | Hero's Quest (Black Arm) | `g178f773bba` | PASS | 40m 49s | 57 | 0 |
| 17g | Temple of Ikov | `g178f773bik` | PASS | 1h 7m 38s | 1 | 0 |
| 17g | The Fremennik Trials | `g178f773bft` | PASS | 57m 34s | 3 | 0 |
| 17h | Underground Pass | `h17178307up` | PASS | 40m 39s | 9 | 0 |
| 17h | Regicide | `h17178307rg` | FAIL | 58m 16s | 9 | 1 |
| 17i | Legends Quest | `i17da08c3lq` | FAIL | 1h 26m 14s | 107 | 1 |

The fresh full-quest replacement results follow below.

## Death prevention full-quest reruns

After fixing the three grand-run death causes, fresh full-quest replacements
ran with both Hero gang partners together. All four full cases passed with zero
deaths, one newly completed quest, complete journals, queue done 1 / stuck 0 /
total 1, expected final QP, final banking and confirmed clean logout. All three
selected launchers passed and exited cleanly. No manual pause, resume, restart
or script reload occurred. Each full character began at target stage 0 and
logged exactly one queue start and one result. Times include all automatic
travel retries and the final bank return.

| Quest | Fresh account | Result | Time taken | Final QP |
|---|---|---|---|---|
| Hero's Quest (Phoenix) | `g176daadbph` | PASS, zero deaths | 43m 38s | 57 |
| Hero's Quest (Black Arm) | `g176daadbba` | PASS, zero deaths | 41m 39s | 57 |
| Regicide | `h17600dcbrg` | PASS, zero deaths | 1h 29m 18s | 12 |
| Legends Quest | `i17243641lq` | PASS, zero deaths | 1h 42m 04s | 111 |

| Account | Queue start (UTC) | Passing result (UTC) | Elapsed seconds |
|---|---|---|---|
| `g176daadbph` | 2026-11-24T23:50:31.461Z | 2026-11-25T00:34:09.235Z | 2617.774 |
| `g176daadbba` | 2026-11-24T23:50:28.423Z | 2026-11-25T00:32:07.441Z | 2499.018 |
| `h17600dcbrg` | 2026-11-24T23:44:42.222Z | 2026-11-25T01:14:00.227Z | 5358.005 |
| `i17243641lq` | 2026-11-24T23:47:25.432Z | 2026-11-25T01:29:29.627Z | 6124.195 |

Fix source: `07f50a4f` on PR #163. Every full session used the same frozen
client, SHA-256 `2f43faa167f2eeee8006bf738c998d78af1ebb7f8b7126cb5f290976393b40c8`.
The Regicide session records base `fce88a0b` because its identical fixed binary
was built and launched from the working tree before that tree was committed as
`07f50a4f`. Session binary hashes were independently checked against the frozen
file. Other full sessions record `07f50a4f`. Engine/content stayed unchanged at
`2395c968473333d13ff1454f5eff452a18a029b6` /
`f32c62f66302f76b43c752ede3181de0c0d01369`; normal 600 ms seed probes passed.

Evidence: `build/e2e/full-heroes-deathfix-20261124`,
`build/e2e/full-regicide-deathfix-20261124`, and
`build/e2e/full-legends-deathfix-20261124`. Each root retains its manifest,
script snapshots, one seed/run session, launcher results and exact `timings.json`.
Combined independent audit: `build/e2e/death-prevention-report.json`.
The original failed grand-run accounts and evidence were preserved.

The fixes address missing prayer supplies in Hero's Quest, unarmoured and
unprotected combat in Regicide, and ledge overshoots and blocked prayer upkeep
in Legends Quest.
Regicide defeated the soldier without spending its seven remaining sharks and
crossed the original quarry death location at 84% HP with six sharks. Both
Hero accounts obtained their gloves and completed the feather chain. Legends
restored prayer through the guardian fights and completed the remaining quest.

Validation: embedded stdlib suite passed 4,496 native assertions across four
test cases; the focused death-prevention specs also passed after adding the
complete-armour preparation assertion. All 18 phase 17g/h/i host-side launcher
tests, changed-file pocketpy dialect lint and whitespace checks passed. All 11
CI checks on fix commit `07f50a4f` passed.

## Watchtower Grew interruption recovery

On November 25, 2026, the grand run's Watchtower account repeatedly bought a
rope, entered Grew's island, had its dialogue interrupted by aggressive ogres,
and left without progressing. Closing a chat box had been accepted as success.
The corrected leg chooses a reachable side of Grew away from other ogres,
holds that position while clearing attackers, and retries on the island until
the expected journal flag or replacement reward arrives. It stops for unsafe
hitpoints without food, pending random events, or its local retry limit.

| Validation | Account | Result | Time taken |
|---|---|---|---|
| Grew introduction, resumed at stage 2 | `e17148d46wt` | PASS, journal-confirmed; proceeded to Gorad | 3m 14s |

The leg ran from `2026-11-25T19:16:19.813Z` to
`2026-11-25T19:19:33.612Z` (**193.799 seconds**, including travel). The account
crossed onto the island once, cleared two attackers, finished the introduction,
and restocked food before selecting "knock out one of Gorad's teeth" at
`19:20:21.006Z`. Food fell from five lobsters to three; deaths stayed zero.
Evidence: `build/e2e/watchtower-grew-position-20261125`, session
`20261125T131345-run-f478`, source `fdba399`, binary SHA-256
`e1c5e9af1df48b2b05f2d6a18cd96400b79ae1e4739946597d3e4e26bb3734e7`.

This is a resumed leg result. Applying the fix interrupted the original grand
account at the bank at `19:00:42Z`; its original timing is not an uninterrupted
pass. The first clearing-only diagnostic exhausted its retry budget as ogres
respawned; preserve `build/e2e/watchtower-grew-resume-20261125` as failed evidence.
Both diagnostics used the existing save without reseeding target progress.

The earlier fresh pilot `e17ae4679wt` exposed prayer flasks being deposited
again during Dusty key preparation. Its failed dragon hunt and deliberate stop
at the bank remain under `build/e2e/watchtower-prayer-dialogue-20261125`.
The keep list now preserves every prayer dose form through that bank stop.
A fresh full run of the prayer, Toban and Grew fixes used `e176371cawt` under
`build/e2e/watchtower-all-fixes-20261125`, source `ab4bc87`, binary SHA-256
`d2f2ff78fc6df27af3b7b449cfd3687f672a746240eefa6a06f9de8e9c3b56f5`.
Its seed passed the 600 ms tick probe. It completed without interruption, but
exposed the enclave and tower inefficiencies described below; it predates those
follow-up fixes.

| Validation | Account | Result | Time taken |
|---|---|---|---|
| Resumed remainder after Grew fix | `e17148d46wt` | PASS, 8 QP, zero deaths, clean logout | 1h 9m 29s |
| Fresh full quest, source `ab4bc87` | `e176371cawt` | PASS, 8 QP, zero deaths, clean logout | 2h 13m 53s |

The resumed remainder ran from `19:13:48.022Z` to `20:23:17.414Z`
(4169.392 seconds). The fresh run ran from `19:20:43.215Z` to
`21:34:36.615Z` (8033.400 seconds), including final banking, and logged out
cleanly at `21:34:37.222Z`. These are distinct results; neither replaces the
original interrupted grand-run result.
No server files were changed for these fixes. See
[PR #165](https://github.com/ineedbots/lc-headless/pull/165) and
[issue #164](https://github.com/ineedbots/lc-headless/issues/164).

### Watchtower repeated enclave visits

The fresh `ab4bc87` run above exposed an inefficient shaman circuit. Its log
records six `dissolve the ogre shamans` actions, from `21:04:52.816Z` to
`21:18:16.814Z`, followed by another entry to mine Dalgroth at `21:19:52.215Z`.
Each dissolve action returned success after one target. Before the next planner
decision, the engine's area recovery left the enclave; the outside planner then
acquired another nightshade and refilled food as needed. These were planned
exits, not reserve-exhaustion retreats.

The action now continues through the remaining shaman positions and mines the
rock after receiving the shaman crystal. Food, health, space and interruption
checks remain active. Runtime regression coverage exercises one nightshade
entry, six distinct dissolves and both crystals without leaving; incomplete
circuits and safety exits do not claim completion. Later live runs completed
the quest but still needed two or three circuits; the single-visit objective
remains unmet. See the completion audit below. The original completed full run
retained its frozen older binary throughout.

### Watchtower tower continuations

The same fresh run repeatedly failed to climb from the ground floor, retried
the crystal hand-in, and was then sent downstairs by area recovery before
another attempt. It eventually advanced to stage 11 at `21:32:52.207Z`.
Read-only revision-289 server inspection confirms that the ground ladder opens
a guard permission continuation before climbing; the client was waiting only
for a level change. The crystal use-on also drove dialogue immediately, with a
short page-gap timeout that could expire during approach to the wandering
wizard. The lever timed out while its reward dialogue was still waiting.

The ladder now continues the permission page before waiting for the floor
change, and the top-floor arrival settles the scene. Crystal hand-in waits for
the initial dialogue and requires journal advancement; lever activation drives
the reward continuation before checking completion. Runtime regressions cover
permission-gated climbing, delayed hand-in dialogue, unchanged journal state,
and reward dialogue gating completion. Both later full runs passed crystal
hand-in and lever activation on their first attempts; the completed `ab4bc87`
run remains evidence of the original behavior.

A fresh combined validation uses account `e17f863a2wt` under
`build/e2e/watchtower-tower-20261125`, source `ca5f972`, frozen binary SHA-256
`f956d9ee9cd3f35ae14bd8861ace88992bdd63e1ace6f82674152eb83718c8a9`.
Seeding passed in session `20261125T153852-seed-f880`, including the normal
600 ms tick probe and clean logout. The full quest rerun passed uninterrupted;
the shaman single-visit objective remains unmet.

### Watchtower Og interruption recovery

The `ca5f972` run above exposed another interrupted tribal introduction:
`talk to Og` retried 46 times from `21:48:55.846Z` to `21:55:05.446Z`
(6m 9.600s), finally receiving Toban's key and proceeding to the chest. Many
closed dialogues had been reported as successful without journal or inventory
progress. The run recovered without intervention and completed uninterrupted;
it was not restarted to apply the Og follow-up.

Og now uses the same reachable-side selection and targeted attacker clearing
as Grew. A bounded local retry requires the introduction flag and key, the
gold hand-in flag, or an actual replacement item gain. Its preferred menu
answer matches the request; replacement-key requests no longer prefer the
competing "I have your gold" answer. Runtime regressions cover interruptions,
gold hand-in, replacement key/part requests, unrelated players' ogres, safer
positioning, the retry deadline and safety stops. The later live run passed
both the introduction and gold hand-in, including clearing an attacking ogre.

A separate fresh validation uses `e176054eewt` under
`build/e2e/watchtower-og-20261125`, source `7870570`, binary SHA-256
`cf18a4d3db01e71ab7415777c87f516525a34f531793abfb797e4c556c323940`.
It uses the normal phase 17e preparation, with no target quest flags or rewards
seeded. The earlier `e17f863a2wt` run completed separately on its frozen binary.
Seeding passed in session `20261125T155635-seed-8f77`, including the 600 ms
tick probe and clean logout. The fresh full quest passed uninterrupted.

### Watchtower continuation completion audit

Both full reruns completed on November 25, 2026, with a complete journal,
exactly one newly completed quest, 8 QP, zero deaths, no stuck queue entries,
and clean logout. Times include final banking and exclude seeding.

| Account | Source | Result | Time taken |
|---|---|---|---|
| `e17f863a2wt` | `ca5f972` | PASS, uninterrupted; predates Og fix | 1h 39m 16s |
| `e176054eewt` | `7870570` | PASS, uninterrupted; includes Og fix | 1h 55m 37s |

The first ran from `21:40:57.618Z` to `23:20:13.841Z` (5956.223 seconds),
session `20261125T154055-run-5273`, and logged out at `23:20:14.415Z`.
The second ran from `21:58:37.856Z` to `23:54:14.453Z` (6936.597 seconds),
session `20261125T155835-run-ee64`, and logged out at `23:54:15.020Z`.
Artifact roots and frozen binary hashes are recorded above.

On the Og-fix account, introduction passed in 52.784 seconds. Gold hand-in
passed in 130.227 seconds, including clearing attacker 4790, consuming one
lobster, and receiving relic part 1. Crystal hand-in and lever activation each
completed in one announced action on both accounts, without the old tower
retry loop.

The enclave improvement is partial: `ca5f972` required two shaman actions;
`7870570` required three. A bounded circuit sometimes exhausted its positions
before receiving the crystal, causing an exit and another nightshade trip.
The final successful circuit also mined Dalgroth before leaving, but a complete
single-visit circuit has not been demonstrated. Keep this limitation open;
these passing quest results do not establish that acceptance criterion.

All 11 CI checks passed on test follow-up `a295a71` (run `45713964464`),
including native and stdlib coverage. Full local script coverage passed all
443 file floors, with `tribes.py` at 321/329 (97.57%) and overall coverage at
79,136/80,873 (97.85%). All 134,954 local assertions passed; 78 cache-dependent
cases skipped without configured cache data. No server files were changed.

### Watchtower live shaman targeting

The preceding runs exhausted their fixed stand positions while some shamans
were still more than four tiles away. The corrected action approaches visible
shamans at their actual positions, remembers confirmed NPC indices to avoid
respawns, and uses the old positions to search for unloaded targets. The visit
still has a four-minute budget and checks food, health, space and interruptions.

| Validation | Account | Result | Time taken |
|---|---|---|---|
| Seeded shaman leg, source `f6ae9cf` | `e17285fb7wt` | PASS: one entry, six dissolves, both crystals, zero deaths | 1m 16s |

The diagnostic ran from `2026-11-26T00:14:04.222Z` to
`2026-11-26T00:15:20.436Z`, reporting 76,213 ms internally. It explicitly seeded
target stage 10, zero shaman kills, an enchanted potion and one nightshade;
this is a leg result, not full-quest completion. All six different NPC indices
(2330, 2335, 2342, 2347, 2348, 2343) were confirmed dissolved before mining
Dalgroth. No reserve retreat or re-entry occurred.

Evidence: `build/e2e/watchtower-shaman-leg-20261125/leg-client.log`;
standard seed session `20261125T181143-seed-4452` passed the 600 ms tick probe.
Frozen binary SHA-256:
`a244dde443b5b0a6dd242af63546ab2b2f8e9e8ec351f602b03246a86bc43353`.
The diagnostic script and rerun instructions are in `e2e/phase17e`.

A separate full-quest account `e17b0e516wt` is running under
`build/e2e/watchtower-shamans-full-20261125`, with the same source and frozen
binary. Its normal seed session `20261125T181305-seed-6d09` passed and did not
set target flags or rewards. Full completion remains pending. Earlier failed
circuits and timings above remain preserved; no server files were changed.
