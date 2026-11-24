# Phase 17f on local 289

Each fresh scratch account runs exactly one target through the real
`bots.aio_quester.AIOQuester`. Tracks [#158](https://github.com/ineedbots/lc-headless/issues/158).

| Case | Quest | Seeded completed prerequisites | Initial QP | Final QP |
|---|---|---|---|---|
| `ew` | Elemental Workshop | None | 0 | 1 |
| `ds` | Digsite Quest | Druidic Ritual | 4 | 6 |
| `hg` | Holy Grail | Merlin's Crystal | 6 | 8 |
| `fc` | Family Crest | None | 0 | 1 |
| `hd` | Horror from the Deep | None | 0 | 2 |

Target quests remain unstarted after preparation. Druidic Ritual unlocks
Herblore where the actual AIO planner requires it. Prerequisite journals and QP
are verified; the planner regression requires exactly one selected target.

## Prepare and run

Use the [local members server prerequisites](../phase17g/README.md#prerequisites).
The launcher does not alter server files or existing saves. Start a stopped server
with `node --import tsx src/app.ts` from `../289server/engine`, then wait for
**World ready**. From this repository root:

```powershell
python e2e/phase17f/run.py prepare --run-dir build/e2e/phase17f-night1 --operator-port 8117
python e2e/phase17f/run.py seed --run-dir build/e2e/phase17f-night1 --timeout-minutes 15
python e2e/phase17f/run.py run --run-dir build/e2e/phase17f-night1 --timeout-minutes 240
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
Family Crest additionally receives one cooked Swordfish, Bass, Tuna, Salmon and
Shrimps, plus two Rubies. Caleb's active decision branch requires banked cooked
fish; the gem shop has only one Ruby per restock. The initial account stopped
on missing fish and is excluded from accepted completion timings. A fresh
replacement must run uninterrupted with the corrected preparation.
Elemental Workshop must source
its supplies and make the shield; Digsite must pass all exams and obtain its
chemicals/tablet; Holy Grail must reclaim Excalibur and defeat the Titan; Family
Crest must make its perfect jewellery and source its spells; Horror must repair the bridge,
complete its own barcrawl, repair the lighthouse and defeat both bosses.
No barcrawl, target quest flags or target quest items are seeded.

A 20-tick probe must take approximately 12 seconds. Keep normal 600 ms ticks.
Per-account infinite run is enabled by default; `prepare --natural-run` omits it.
This measures prepared quest completion, rather than natural account progression.

## Results and monitoring

Each account emits `E2E_RESULT` and logs out after its queue ends. Acceptance
requires the complete target journal, exactly one newly completed quest, no stuck
entries, zero deaths, expected final QP and clean process exit. Only a passing
selected set produces the launcher's `results.json`.

Use the [shared operator examples](../phase17g/README.md#observe-stop-and-resume)
with port 8117 and generated account names. Inspect is read-only. Resume only
unfinished cases using `run --cases <case>`; disclose any resumed runs.

Record **Time taken** from the first per-account `AIOQuester, queue:` log to the
passing `E2E_RESULT`, including final banking and excluding seeding/login staggering.
Fresh uninterrupted reruns are required after fixes for accepted uninterrupted
timings. Pending runs and interrupted attempts are not passes.
See [recorded validation](../VALIDATION.md#phase-17f).

```powershell
python -B -m unittest discover -s e2e/phase17f -p 'test_*.py'
```
