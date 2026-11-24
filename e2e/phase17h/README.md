# Phase 17h on local 289

Run each target on a fresh scratch account through the real
`bots.aio_quester.AIOQuester`. Tracks [#160](https://github.com/ineedbots/lc-headless/issues/160).

| Case | Quest | Seeded completed prerequisites | Initial QP | Final QP |
|---|---|---|---|---|
| `up` | Underground Pass | Plague City, Biohazard | 4 | 9 |
| `rg` | Regicide | Plague City, Biohazard, Underground Pass | 9 | 12 |

Targets remain unstarted. Seeded prerequisite journals and their summed QP are
verified. Regicide preparation also sets Underground Pass's persistent
`ibanmulti` bits 5–8, 11, 14–16 and 18: burned orbs, cave entry, paladin crests
and unicorn horn. These prerequisite gates remain open after real completion;
the completed journal flag alone does not open them.
Regicide must wait for its messenger and traverse the pass itself;
no summons, target flags, trap solutions, quest items or bomb components are seeded.

## Prepare and run

Use the [local members server prerequisites](../phase17g/README.md#prerequisites).
Start a stopped server with `node --import tsx src/app.ts` from
`../289server/engine`, then wait for **World ready**. The launcher never changes
server files, tick speed or existing characters. From this repository root:

```powershell
python e2e/phase17h/run.py prepare --run-dir build/e2e/phase17h-night1 --operator-port 8131
python e2e/phase17h/run.py seed --run-dir build/e2e/phase17h-night1 --timeout-minutes 20
python e2e/phase17h/run.py run --run-dir build/e2e/phase17h-night1 --timeout-minutes 360
```

Preparation creates independent random credentials, snapshots scripts and records
source/binary hashes. It refuses existing run directories or character saves.
Seeding is one-shot: a failed setup requires fresh accounts. Credentials and raw
evidence remain under ignored `build/`.

## Preparation and limits

Skills are 75 melee, 85 hitpoints, 70 prayer, and 70 magic/ranged/mining/smithing/
cooking/crafting/fishing/woodcutting/firemaking/thieving/agility/herblore/fletching.
Banks receive one million coins, 1,000 lobsters, 100 prayer potions(3), rune melee
equipment, combat runes and ordinary tools. Each receives a shortbow and 500 bronze
arrows. Regicide also receives 1,000 sharks: its module carries and eats sharks.
Ropes, wool, coal and quest-specific items must be sourced live.

The seed's 20-tick probe must take approximately 12 seconds at normal 600 ms ticks.
Per-account infinite run is enabled unless `prepare --natural-run` is used.
This tests prepared quest completion rather than natural account progression.

## Results and monitoring

Use the [operator examples](../phase17g/README.md#observe-stop-and-resume) with
port 8131 and generated account names. `inspect` is read-only. `run --cases up`
or `run --cases rg` selects unfinished cases; disclose resumed attempts.
Quest-owned automatic relogging for Regicide's messenger remains part of its run.

Acceptance requires one newly completed target, its complete journal, no stuck
queue entries, zero deaths, expected final QP and clean logout/process exit.
Only a passing selected set produces the launcher's `results.json`.
Record **Time taken** from the first account `AIOQuester, queue:` log through its
passing `E2E_RESULT`, including final banking and excluding seeding/login stagger.
After a repair, use a fresh account for uninterrupted acceptance timing.
See [validation evidence](../VALIDATION.md#phase-17h).

```powershell
python -B -m unittest discover -s e2e/phase17h -p 'test_*.py'
```
