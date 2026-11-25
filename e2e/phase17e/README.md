# Phase 17e on local 289

Each fresh scratch account runs exactly one target through the real
`bots.aio_quester.AIOQuester`. Tracks [#158](https://github.com/ineedbots/lc-headless/issues/158).

| Case | Quest | Seeded completed prerequisites | Initial QP | Final QP |
|---|---|---|---|---|
| `tt` | The Tourist Trap | None | 0 | 2 |
| `wt` | Watch Tower | Druidic Ritual | 4 | 8 |
| `cb` | Big Chompy Bird Hunting | None | 0 | 2 |
| `gt` | The Grand Tree | None | 0 | 5 |

Watch Tower's fresh replacement passed uninterrupted in **2h 46m 19s** with
zero deaths after the food, dialogue and cleanup repairs. See the
[validation evidence](../VALIDATION.md#phase-17e) for individual results and limits.

Watch Tower's dragon hunt uses Protect from Melee when available, alongside its
dragonfire shield, and draws up to two available prayer potion flasks. Partial
flasks count toward that supply. Toban's cave entrance continuation is finished
before approaching him, so it cannot be mistaken for his dialogue. These follow-up
repairs are tracked in [#164](https://github.com/ineedbots/lc-headless/issues/164);
the historical completion time above predates them.

Grew conversations choose a reachable side away from the other island ogres,
hold that position rather than chasing distant attackers, and retry on the island for
up to four minutes. A closed chat box alone cannot complete the leg: the expected
journal flag or replacement reward must arrive. Low hitpoints without food and
pending random events stop the retry so normal recovery can take over.

Target quests remain unstarted after preparation. Druidic Ritual unlocks
Herblore where the actual AIO planner requires it. Prerequisite journals and QP
are verified; the planner regression requires exactly one selected target.

## Prepare and run

Use the [local members server prerequisites](../phase17g/README.md#prerequisites).
The launcher does not alter server files or existing saves. Start a stopped server
with `node --import tsx src/app.ts` from `../289server/engine`, then wait for
**World ready**. From this repository root:

```powershell
python e2e/phase17e/run.py prepare --run-dir build/e2e/phase17e-night1 --operator-port 8115
python e2e/phase17e/run.py seed --run-dir build/e2e/phase17e-night1 --timeout-minutes 15
python e2e/phase17e/run.py run --run-dir build/e2e/phase17e-night1 --timeout-minutes 240
```

Preparation snapshots scripts, client/engine revisions and the binary hash,
generates independent random credentials, and refuses existing run directories
or saved accounts. Raw evidence and credentials stay beneath ignored `build/`.
Seeding is one-shot: wait for PASS before running; failed seeds need fresh accounts.

## Preparation and limits

Skills are 75 melee, 85 hitpoints, 70 prayer, 60 magic/ranged, 65 fishing,
50 cooking, 35 herblore and 40 mining/smithing/crafting/woodcutting/firemaking/
thieving/agility/fletching. Banks hold one million coins, 1,000 lobsters,
100 prayer potions(3), rune melee equipment, combat runes and ordinary tools.
Watch Tower additionally receives one Guam leaf, Bat bones and Gold bar:
its module has no world source for these inputs. It also receives an ordinary
Dragonfire shield for its melee dragon hunt. Dragon bones must be obtained
live, along with all relics, crystals, potion intermediates and quest materials.
The Tourist Trap must make its prototype dart and rescue Ana; Chompy must make
its arrows, obtain bait and hunt; The Grand Tree must acquire its quest items
and kill the demon. No target quest flags or target reward items are seeded.

A 20-tick probe must take approximately 12 seconds. Keep normal 600 ms ticks.
Per-account infinite run is enabled by default; `prepare --natural-run` omits it.
This measures prepared quest completion, rather than natural account progression.

## Results and monitoring

Each account emits `E2E_RESULT` and logs out after its queue ends. Acceptance
requires the complete target journal, exactly one newly completed quest, no stuck
entries, zero deaths, expected final QP and clean process exit. Only a passing
selected set produces the launcher's `results.json`.

Use the [shared operator examples](../phase17g/README.md#observe-stop-and-resume)
with port 8115 and generated account names. Inspect is read-only. Resume only
unfinished cases using `run --cases <case>`; disclose any resumed runs.

Record **Time taken** from the first per-account `AIOQuester, queue:` log to the
passing `E2E_RESULT`, including final banking and excluding seeding/login staggering.
Fresh uninterrupted reruns are required after fixes for accepted uninterrupted
timings. Pending runs and interrupted attempts are not passes.
The Watchtower shaman action keeps all six dissolves and Dalgroth mining in one
enclave visit. It still retreats when its food, health or inventory reserve is
exhausted, and stops for pending interruptions. Older binaries returned after
each shaman, causing area recovery to leave the enclave and consume another
nightshade on each entry. Single-visit live validation of this change is pending.
Tower entry continues the guard's permission page, crystal hand-in waits for
dialogue and journal confirmation, and the lever finishes the reward dialogue.
Live validation of these continuation fixes is pending.
See [recorded validation](../VALIDATION.md#phase-17e).

```powershell
python -B -m unittest discover -s e2e/phase17e -p 'test_*.py'
```
