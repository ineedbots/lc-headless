# Phase 17i on local 289

Run Legends Quest on its own fresh scratch account through the real
`bots.aio_quester.AIOQuester`. Tracks [#160](https://github.com/ineedbots/lc-headless/issues/160).

| Case | Quest | Seeded completed prerequisites | Initial QP | Final QP |
|---|---|---|---|---|
| `lq` | Legends Quest | Required ancestors plus explicit QP-gate preparation | 107 | 111 |

The complete preparation list is the `FLAGS` table in
[phase17i_cases.py](scripts/phase17i_cases.py). Its 45 completed quests sum to
107 QP; each journal and the total are verified before the target runs. The list
includes Hero's Quest, Family Crest, Shilo Village, Underground Pass, Waterfall
Quest and their ancestors. Legends remains unstarted throughout preparation.

## Prepare and run

Use the [local members server prerequisites](../phase17g/README.md#prerequisites).
Start a stopped server with `node --import tsx src/app.ts` from
`../289server/engine`, then wait for **World ready**. The launcher never changes
server files, tick speed or existing characters. From this repository root:

```powershell
python e2e/phase17i/run.py prepare --run-dir build/e2e/phase17i-night1 --operator-port 8133
python e2e/phase17i/run.py seed --run-dir build/e2e/phase17i-night1 --timeout-minutes 20
python e2e/phase17i/run.py run --run-dir build/e2e/phase17i-night1 --timeout-minutes 360
```

Preparation snapshots scripts, source/binary hashes and independent random
credentials. Existing run directories and character saves are refused. Seeding
is one-shot; failed preparation requires a fresh account. Raw logs, configurations
and credentials stay under ignored `build/`.

## Preparation and limits

Skills are 75 melee, 85 hitpoints, 70 prayer, and 70 magic/ranged/mining/smithing/
cooking/crafting/fishing/woodcutting/firemaking/thieving/agility/herblore/fletching.
Banks hold one million coins, 1,000 lobsters, 100 prayer potions(3), rune melee
equipment, combat runes and ordinary tools. Legends also receives a rune axe,
five lockpicks, five unpowered orbs, 100 cosmic runes, and one each of the seven
cut gems (opal, jade, red topaz, sapphire, emerald, ruby and diamond).
These are ordinary inputs; no map, bull roarer, golden bowl, binding book,
crystals, quest potions, Yommi seeds or totems are seeded. Gold, other runes and
shop supplies must be obtained live.

The seed's 20-tick probe must take approximately 12 seconds at 600 ms ticks.
Per-account infinite run is enabled unless `prepare --natural-run` is used.
This measures prepared quest completion rather than natural progression or
the earlier Kharazi/Isafdar clue workflows mentioned in historical issue #34.

## Results and monitoring

Use the [operator examples](../phase17g/README.md#observe-stop-and-resume) with
port 8133 and the generated account name. `inspect` is read-only.
Acceptance requires exactly one newly completed quest, a complete journal,
zero deaths, no stuck queue entries, 111 final QP and clean logout/process exit.
Only a passing selected set produces the launcher's `results.json`.

Record **Time taken** from the first account `AIOQuester, queue:` log through its
passing `E2E_RESULT`, including final banking and excluding seeding/login stagger.
Disclose interruptions and resumed attempts; use fresh accounts after repairs
for accepted uninterrupted timing. See [validation evidence](../VALIDATION.md#phase-17i).

```powershell
python -B -m unittest discover -s e2e/phase17i -p 'test_*.py'
```
