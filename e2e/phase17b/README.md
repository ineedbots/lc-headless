# Phase 17b on local 289

Nine fresh scratch characters each run one members quest through the real
`bots.aio_quester.AIOQuester`. This suite tracks
[#151](https://github.com/ineedbots/lc-headless/issues/151).

See the [recorded validation table](../VALIDATION.md#phase-17b) for all nine results
and measured time taken, including Scorpion Catcher's resumed run.

| Case | Quest | Expected final QP |
|---|---|---|
| `dc` | Dwarf Cannon | 1 |
| `sh` | Sheep Herder | 4 |
| `tg` | Tree Gnome Village | 2 |
| `wf` | Waterfall Quest | 1 |
| `sc` | Scorpion Catcher, including the barcrawl | 1 |
| `ob` | Observatory Quest | 2 |
| `fa` | Fight Arena | 2 |
| `mc` | Merlin's Crystal | 6 |
| `lc` | Lost City | 3 |

## Prepare and run

Use the client build, Python 3.12+, Node and local server described in the
[phase 17g prerequisites](../phase17g/README.md#prerequisites). The development
server must have members content enabled, `node.production=false` and
`login.enabled=false`. Start it if needed:

```powershell
cd ../289server/engine
node --import tsx src/app.ts
```

Wait for **World ready**, then run from the headless repository root:

```powershell
python e2e/phase17b/run.py prepare --run-dir build/e2e/phase17b-night1 --operator-port 8099
python e2e/phase17b/run.py seed --run-dir build/e2e/phase17b-night1
python e2e/phase17b/run.py run --run-dir build/e2e/phase17b-night1 --timeout-minutes 240
```

`prepare` generates nine credentials with a random prefix and the table's
suffixes, copies the scripts, and records client/server commits and file hashes.
It refuses existing run directories and matching saved characters. All nine
accounts fit in one client process; use a free operator port when running other
suites. Configuration, credentials, logs and results stay under ignored `build/`.

Seeding is one-shot. Wait for `seed` to print `PASS` before starting `run`.
A failed seed requires a new directory and fresh characters. Existing saves are
never cleared to repeat acceptance.

## Preparation and limits

Every target must be unstarted before and after preparation. Each character
starts with zero quest points. No completed quest prerequisites or barcrawl
progress are seeded. Scorpion Catcher must obtain and complete its own card.

Preparation supplies combat levels (75 melee, 85 hitpoints, 70 prayer, 60 magic),
40 mining/smithing/crafting/fishing/woodcutting/firemaking/thieving/agility and
50 cooking. Banks receive coins, lobsters, prayer potions, rune melee equipment,
runes and ordinary tools. Bank contents are verified. Quest keys, the cage,
orb, lens mould, Glarial's items, black candle, Dramen staves and other quest
objective items and supplies must be obtained by the quest bot.

The normal server tick is 600 ms. The wrapper enables per-character infinite
run by default; pass `--natural-run` to `prepare` to omit it. These are prepared
quest acceptance runs, with boosted skills and consumables.

## Results, monitoring and resume

The launcher prints the session's `client.log` path. Each account emits
`E2E_RESULT` and logs out when its queue ends. A pass requires the target's
journal to be complete, one newly completed quest, no stuck queue entries,
zero deaths, the table's expected QP and a clean client exit. Already completed
characters cannot pass another acceptance run. Successful sessions save
`results.json`; seeding also saves `seed-complete.json`.

Monitor the operator API on the configured port and use the shared `inspect`
script command for diagnostics; see the
[operator examples](../phase17g/README.md#observe-stop-and-resume).
Ctrl+C requests a graceful shutdown and cleans up the owned client process.
To resume an unfinished case, preserving progress:

```powershell
python e2e/phase17b/run.py run --run-dir build/e2e/phase17b-night1 --cases sc
```

Use a fresh run for a complete rerun of all nine quests. To check host-side
configuration safeguards without starting the server:

```powershell
python -B -m unittest discover -s e2e/phase17b -p 'test_*.py'
```
