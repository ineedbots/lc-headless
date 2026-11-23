# Phase 17a on local 289

Twelve fresh scratch characters each run one members quest through the real
`bots.aio_quester.AIOQuester`. This suite tracks
[#149](https://github.com/ineedbots/lc-headless/issues/149).

See the [recorded validation table](../VALIDATION.md#phase-17a) for per-quest results
and measured time taken.

| Case | Quest | Seeded completed prerequisites | Expected final QP |
|---|---|---|---|
| `dr` | Druidic Ritual | None | 4 |
| `mf` | Monk's Friend | None | 1 |
| `gc` | Gertrude's Cat | None | 1 |
| `jp` | Jungle Potion | Druidic Ritual (4 QP) | 5 |
| `ct` | Clock Tower | None | 1 |
| `hc` | Hazeel Cult, Carnillean side | None | 1 |
| `wh` | Witch's House | None | 4 |
| `fc` | Fishing Contest | None | 1 |
| `mm` | Murder Mystery | None | 3 |
| `ss` | Sea Slug | None | 1 |
| `pp` | Priest in Peril | Rune Mysteries (1 QP), for essence mining | 2 |
| `tt` | Tribal Totem | None | 1 |

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
python e2e/phase17a/run.py prepare --run-dir build/e2e/phase17a-night1 --operator-port 8097
python e2e/phase17a/run.py seed --run-dir build/e2e/phase17a-night1
python e2e/phase17a/run.py run --run-dir build/e2e/phase17a-night1 --timeout-minutes 240
```

`prepare` generates twelve credentials with a random prefix and the table's
suffixes, copies the scripts, and records client/server commits and file hashes.
It refuses existing run directories and matching saved characters. All twelve
accounts fit in one client process; use a free operator port when running other
suites. Configuration, credentials, logs and results stay under ignored `build/`.

Seeding is one-shot. Wait for `seed` to print `PASS` before starting `run`.
A failed seed requires a new directory and fresh characters. Existing saves are
never cleared to repeat acceptance.

## Preparation and limits

Every target must be unstarted before and after preparation. The only completed
quest flags set are the two prerequisite cases disclosed above; their journal
completion and initial QP are checked before logout. Jungle Potion's account
does not wait for the separate Druidic Ritual account.

Preparation supplies combat levels (75 melee, 85 hitpoints, 70 prayer, 60 magic),
40 mining/smithing/crafting/fishing/woodcutting/firemaking/thieving/agility and
50 cooking. Jungle Potion also receives 35 herblore. Banks receive coins,
lobsters, prayer potions, rune melee equipment, runes and ordinary tools. The
bank contents are verified. Meat, herbs, cogs, evidence, keys, essence, the
totem and other quest objective items must be obtained by the quest bot.
Priest in Peril therefore exercises its essence mining fallback.

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
python e2e/phase17a/run.py run --run-dir build/e2e/phase17a-night1 --cases pp
```

Use a fresh run for a complete rerun of all twelve quests. To check host-side
configuration safeguards without starting the server:

```powershell
python -B -m unittest discover -s e2e/phase17a -p 'test_*.py'
```
