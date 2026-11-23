# Phase 17c on local 289

Five fresh scratch accounts each run one quest through the real
`bots.aio_quester.AIOQuester`. Tracks [#154](https://github.com/ineedbots/lc-headless/issues/154).

| Case | Quest | Seeded completed prerequisites | Initial QP | Final QP |
|---|---|---|---|---|
| `dp` | Death Plateau | None | 0 | 1 |
| `ts` | Troll Stronghold | Death Plateau | 1 | 2 |
| `er` | Eadgar's Ruse | Death Plateau, Troll Stronghold, Druidic Ritual | 6 | 7 |
| `pc` | Plague City | None | 0 | 1 |
| `bh` | Biohazard | Plague City | 1 | 4 |

## Prepare and run

Use the [phase 17g prerequisites](../phase17g/README.md#prerequisites): a built
Release client, Python 3.12+, Node and the local members development server with
`node.production=false` and `login.enabled=false`. Start the server if stopped:

```powershell
cd ../289server/engine
node --import tsx src/app.ts
```

Wait for **World ready**, then run from the headless repository root:

```powershell
python e2e/phase17c/run.py prepare --run-dir build/e2e/phase17c-night1 --operator-port 8107
python e2e/phase17c/run.py seed --run-dir build/e2e/phase17c-night1 --timeout-minutes 15
python e2e/phase17c/run.py run --run-dir build/e2e/phase17c-night1 --timeout-minutes 240
```

Preparation records source commits and hashes, snapshots scripts and generates
five random credentials. Existing run directories and saved characters are
refused. All credentials and raw evidence stay under ignored `build/`.
Seeding is one-shot: wait for `PASS` before running quests. After a failed seed,
prepare fresh characters in a new directory. Server files and user saves are
never modified by the launcher.

## Preparation and limits

Each target is unstarted before and after preparation. Only the table's
prerequisite completion flags and matching QP are set. Eadgar remains imprisoned
on his case so the handler must free him; no target progress is seeded.

Skills are 75 melee, 85 hitpoints, 70 prayer, 60 magic, 50 cooking and 40
mining/smithing/crafting/fishing/woodcutting/firemaking/thieving/agility. Eadgar
also receives 35 herblore and one banked raw ranarr weed, because its handler
requires a banked herb or unfinished potion. It must mix its own potion and
obtain thistle, parrot, scarecrow ingredients, keys and goutweed.

Banks contain coins, lobsters, prayer potions, rune melee equipment, combat
runes and ordinary tools. No climbing/spiked boots, iron bar, quest drinks,
IOU, balls, map, certificate, keys, gas mask, plague samples, gown or priest
outfit are seeded. The scripts must obtain these themselves. Bank contents and
prerequisite journals are verified. A 20-tick probe requires approximately
12 seconds before seed acceptance. Use normal 600 ms server ticks.

Per-character infinite run is enabled by default; `prepare --natural-run`
omits it. These prepared quest runs do not measure natural progression.

## Results and monitoring

Each account emits `E2E_RESULT` and logs out after its queue ends. Acceptance
requires a complete target journal, exactly one newly completed quest, no stuck
queue entries, zero deaths, expected final QP and a clean process exit. The
launcher writes `results.json` only when all selected cases pass.

Use the [shared operator examples](../phase17g/README.md#observe-stop-and-resume)
with port 8107 and the generated account names. The read-only `inspect` script
command reports dialogue, location, inventory, prayer and nearby NPCs.

To resume only unfinished accounts, preserving progress:

```powershell
python e2e/phase17c/run.py run --run-dir build/e2e/phase17c-night1 --cases er ts
```

Disclose interruptions and include restart gaps when recording time taken. Use
fresh accounts for an uninterrupted rerun. Measure from the first per-account
`AIOQuester, queue:` to its passing `E2E_RESULT`, including the bank return.
The validation table must include **Time taken**; pending runs are not passes.

Check suite safeguards without a running server:

```powershell
python -B -m unittest discover -s e2e/phase17c -p 'test_*.py'
```
