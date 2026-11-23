# Phase 17g on local 289

Reproduce the live acceptance behind [#145](https://github.com/ineedbots/lc-headless/issues/145)
and [PR #146](https://github.com/ineedbots/lc-headless/pull/146). Four fresh scratch
characters run the actual `bots.aio_quester.AIOQuester`:

The [recorded validation table](../VALIDATION.md#phase-17g) backfills time taken
from the original manual acceptance logs, with its restart and cleanup limits.

| Case | Quest | Preparation | Expected final QP |
|---|---|---|---|
| `ph` | Hero's Quest, Phoenix | Phoenix gang and completed prerequisite quests | 57 |
| `ba` | Hero's Quest, Black Arm | Black Arm gang and completed prerequisite quests | 57 |
| `ik` | Temple of Ikov | Unstarted, Guardians route | 1 |
| `ft` | The Fremennik Trials | Unstarted, all seven votes | 3 |

Keep both Hero accounts in the same client process: partner coordination uses
the client's account messaging. The other two cases can run alongside them.

## Prerequisites

- A checkout/build containing PR #146's web fix (`71e5f54`) or its merge. Without
  it, a carried knife can satisfy route planning but fail the web's Slash action.
- Build the client following [Building](../../docs/Building.md). From the repo root:

  ```powershell
  cmake --preset windows-msvc
  cmake --build --preset windows-release --target Rs2004Headless Rs2004HeadlessTests --parallel 4
  ```

  Linux uses `linux-clang` and `linux-release` instead. The launcher selects the
  corresponding Release executable by default; `--client` overrides its location.
- Python 3.12+ for `run.py` (standard library only), plus Node 24+ for the server
  and extraction of its **public** RSA parameters. If Python is managed through uv,
  replace `python` below with `uv run --python 3.12 --no-project python`.
- A working revision-289 engine/content installation, its existing packed cache,
  and dependencies installed as described in that server's README. Defaults expect
  `../289server/engine`, client cache `data/cache`, and walker data `data/nav`.
  Override these with `--server-dir`, `--cache-dir` and `--nav-dir` when preparing.
- The local server must have `node.production=false`, `login.enabled=false` and
  members content enabled. Developer commands must be available. These are the
  settings used by the original run; the harness does not edit server settings,
  restart an existing server, alter the tick rate, or change user saves.

In a separate terminal, start the server if it is stopped:

```powershell
cd ../289server/engine
node --import tsx src/app.ts
```

Wait for **World ready**. The original engine SHA was
`868f012f652fbdd8da0918b5960b536a07785772`, with nominal 600 ms ticks.
The launcher always connects to `127.0.0.1`, using WebSocket port 80 by default;
use `--server-port` for another local port. It derives public RSA parameters from
the engine's `data/config/private.pem`, the same key the server decrypts with;
the original install's separate `public.pem` was inconsistent. No private key
material is copied into run artifacts, and no RSA key is hard-coded here.

## Prepare, seed, run

Run these commands from the headless repository root:

```powershell
python e2e/phase17g/run.py prepare --run-dir build/e2e/phase17g-night1
python e2e/phase17g/run.py seed --run-dir build/e2e/phase17g-night1
python e2e/phase17g/run.py run --run-dir build/e2e/phase17g-night1
```

`prepare` creates a random account prefix and four credentials in a **new** run
directory. `--prefix g17night1` chooses readable names (`g17night1ph`, etc.);
prefixes are lowercase letters/digits, start with a letter and have at most ten
characters. Existing run folders and matching character saves are refused.
Preparation copies the current `scripts/bots` and these two runtime scripts into
the run folder, avoiding platform-specific symlinks and keeping a reproducible
script snapshot. Use a fresh folder and prefix for another full acceptance run.

`seed` logs in all four characters, lets the client handle the tutorial, seeds the
preparation below, verifies supplies and logs all four out. It must exit with
`PASS` before `run`. Seeding is **one-shot**: a started or partially failed setup
cannot be repeated on those characters. Keep its logs and prepare a new set.
The harness never clears completed quests on an existing account.

`run` starts the four real quest bots and waits for their results. Allow several
hours: the original Ikov root farm took most of its approximately 85-minute
final session, and random events and drops change timing. The default timeout
is 240 minutes; `--timeout-minutes` changes it. The wrapper emits a structured
result and requests account logout when a queue stops, including blocked queues.
This avoids leaving completed scripts logged in overnight.

A `PASS` requires the selected accounts to finish their one-quest queues with no
blocked/parked rows, one recorded completion, complete quest journals and zero
deaths, plus a clean client exit. A zero exit without result records is a failure;
an already completed account is not accepted as a fresh completion. A timeout,
interruption, failed script or forced disconnect is not a pass. Preserve the logs
when diagnosing any failure.

## Preparation and scope

The exact commands live in [scripts/seed.py](scripts/seed.py). The effective bank
setup follows the successful run, with two setup corrections: the Fremennik
starting tile is the walkable Seers bank stand, and Ikov candles use the valid
`unlit_candle` server name. The original invalid candle name caused the quest bot
to buy one; this prepared rerun supplies ordinary candles directly.

- Attack/Strength/Defence 75, Hitpoints 85, Ranged 75, Prayer 70, Magic 60,
  Mining 55, Fishing/Cooking 65, Herblore 35, Agility/Thieving/Crafting 50,
  Woodcutting 60 and Fletching 65.
- Each bank receives 1m coins, 1,000 lobsters, 100 prayer potions(3), rune
  chainbody/platelegs/longsword, bronze pickaxe/axe, knife and tinderbox.
- Hero's server setup chooses the correct gang, completes Shield of Arrav,
  Dragon Slayer, Lost City and Merlin's Crystal, and provides ordinary fishing
  ingredients and Black Arm disguise. **Its ice gloves are dropped and verified
  absent**, requiring a real Queen fight. Supporting completion flags listed in
  `seed.py` maintain 56 QP across logins; Hero remains at stage 0.
- Hero receives an oak longbow, 500 steel arrows and fishing bait. Ikov receives
  a yew shortbow, coif, dragonhide gear, candles and mundane bow ingredients;
  its body may be refused without Dragon Slayer, as in the original run, and
  the quest handles that refusal. Fremennik receives two raw sharks.
- The wrapper enables **per-character infinite run** at login, matching the
  original acceptance. `prepare --natural-run` omits it; that variant has not
  been accepted by the original evidence and takes longer.

Armbands, keys, eels, gloves, feathers, Ikov pendants/boots/lever/ice arrows,
twenty hobgoblin roots and Fremennik trial items must be earned by the quest
scripts. There are no seeded quest completions for the selected target quests.
This does not test natural skill training, energy endurance, both Ikov alignments,
or [#46's depleted Scavvo provisioning](https://github.com/ineedbots/lc-headless/issues/46).

## Observe, stop and resume

The launcher prints the session directory. Each invocation retains its own
`sessions/<id>/client.log`, `console.log`, `fleet.sqlite`, `version.json` and,
on success, `results.json`. `manifest.json` records the initial engine/client
SHAs, executable hash, copied Python hashes, account names and run mode; each
session records its actual executable/Python hashes and source SHAs again.
Progress reports are in `progress/`.
Credentials remain under the ignored run directory; do not commit them.

The local operator listener defaults to port 8091 (`prepare --operator-port` or
`seed/run --operator-port` overrides it). While the client is running:

```powershell
Invoke-RestMethod http://127.0.0.1:8091/api/v1/status
Invoke-RestMethod http://127.0.0.1:8091/api/v1/console/commands -Method Post -ContentType 'application/json' -Body '{"command":"inspect"}'
Invoke-RestMethod http://127.0.0.1:8091/api/v1/console/commands -Method Post -ContentType 'application/json' -Body '{"command":"quit"}'
```

Prefix a command with `@<generated-account-name>` to target one character. The
`inspect` command prints the visible dialogue, health, prayer, inventory,
equipment, nearby NPCs and ground items. It is available only while the quest
script is active. Ctrl+C or timeout asks this session's client to quit and allows
45 seconds for logout; the launcher checks the listener's account set before
sending a quit, so it does not stop an unrelated operator process.

For a client fix, stop the affected client, rebuild, then resume unfinished cases
from their saved progress **without seeding again**:

```powershell
python e2e/phase17g/run.py run --run-dir build/e2e/phase17g-night1 --cases ik --client build/windows-msvc/Release/Rs2004Headless.exe
```

Use `--cases ph ba` for the Hero pair, or `--cases ft` for Fremennik. Do not log
the same character into two clients. Separate concurrent clients need distinct
operator ports, for example `--operator-port 8093`. If editing bot Python rather
than the embedded stdlib, explicitly update the affected files in the run's copied
`scripts/bots` tree and record the change; preparing another folder creates new
characters instead of resuming old ones.
Result records describe each session. Review earlier sessions when reporting
cumulative deaths or failures; a resumed pass does not erase an earlier failed
attempt. Use fresh characters for an uninterrupted acceptance rerun.

## Validation of this reproduction package

Host-side safety/result checks and pocketpy syntax checks:

```powershell
python -m unittest discover -s e2e/phase17g -p "test_*.py"
python -I tools/port/lint.py e2e/scripts e2e/phase17g/scripts
```

The original live acceptance completed Phoenix at 57 QP, Black Arm at 57 QP,
Fremennik at 3 QP and Ikov at 1 QP, with zero deaths during all four quest runs.
Its supporting checks passed 4,482 stdlib assertions and all eleven CI jobs on
`71e5f54`. Server messages, journal state, queue DONE and bank return established
completion; a healthy client process alone did not.

The launcher and acceptance wrapper are shared with phase 16 through `e2e/harness.py`
and `e2e/scripts/`. Existing phase 17g commands and saved run directories still work.
