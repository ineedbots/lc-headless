# Phase 16: all eighteen F2P quests

Run the real AIOQuester against local revision 289 with two fresh scratch accounts.
Both accounts run the full eighteen-quest queue. `ph` joins the Phoenix gang and
`ba` joins Black Arm; they earn and exchange Shield of Arrav items through the
client's normal partner coordination. Keep them in the same client process.

| Quest | Record ID | QP |
|---|---|---|
| Rune Mysteries Quest | `runemysteries` | 1 |
| Doric's Quest | `doric` | 1 |
| The Knight's Sword | `squire` | 1 |
| Sheep Shearer | `sheep` | 1 |
| The Restless Ghost | `priest` | 1 |
| Cook's Assistant | `cook` | 1 |
| Imp Catcher | `imp` | 1 |
| Ernest the Chicken | `haunted` | 4 |
| Witch's Potion | `hetty` | 1 |
| Romeo & Juliet | `romeojuliet` | 5 |
| Prince Ali Rescue | `prince` | 3 |
| Pirate's Treasure | `hunt` | 2 |
| Shield of Arrav | `blackarmgang` | 1 |
| Goblin Diplomacy | `gobdip` | 5 |
| Demon Slayer | `demon` | 3 |
| Black Knight's Fortress | `blackknight` | 3 |
| Vampire Slayer | `vampire` | 3 |
| Dragon Slayer | `dragon` | 2 |

The queue uses the bot's built-in order. Its earlier quests earn the 12 QP needed
for Black Knight's Fortress and 32 QP needed for Dragon Slayer. Each fresh account
finishes with **39 QP** on this revision. No members quests are selected.

## Requirements and server startup

Use the client build, cache, navigation data, Python 3.12+, Node and local server
requirements in the [phase 17g prerequisites](../phase17g/README.md#prerequisites).
This suite supports a local development world with members content disabled too;
the F2P quest selection does not require changing an existing members world.
Developer commands must be available, `node.production` must be false, and
`login.enabled` must be false. The launcher refuses production/login-server setups.

Build from the repository root, following [Building](../../docs/Building.md):

```powershell
cmake --preset windows-msvc
cmake --build --preset windows-release --target Rs2004Headless --parallel 4
```

Start a stopped engine in a separate terminal and wait for **World ready**:

```powershell
cd ../289server/engine
node --import tsx src/app.ts
```

Keep nominal 600 ms ticks. The launcher connects only to `127.0.0.1`, derives the
public RSA parameters from the engine's actual decryption key, and does not change
world settings or start/stop an existing server. Private key material is not
copied into run artifacts.

## Prepare, seed, run

From the headless repository root:

```powershell
python e2e/phase16/run.py prepare --run-dir build/e2e/phase16-night1 --operator-port 8093
python e2e/phase16/run.py seed --run-dir build/e2e/phase16-night1
python e2e/phase16/run.py run --run-dir build/e2e/phase16-night1 --timeout-minutes 720
```

If Python is managed through uv, substitute
`uv run --python 3.12 --no-project python` for `python`.
Allow several hours: walking, imp drops, combat and random events run live.
The explicit twelve-hour timeout accommodates this; the shared launcher's default
is four hours. Timeout or Ctrl+C requests a graceful quit and fails the invocation.

`prepare` makes random names (`g16` plus six random hex digits plus `ph`/`ba`) and
separate passwords. `--prefix g16night1` sets readable names instead. Prefixes
start with a lowercase letter and contain at most ten lowercase letters/digits.
Existing run folders and matching server saves are refused. Never delete or reset
the user's characters to rerun this suite: choose a fresh directory and prefix.

Paths default to `../289server/engine`, `data/cache`, `data/nav` and the platform's
Release executable. Preparation accepts `--server-dir`, `--cache-dir`, `--nav-dir`,
`--client` and `--server-port`. Linux defaults use `build/linux-clang/Release`.
Use a distinct `--operator-port` when another test client is running. The phase 17g
suite can run separately on its own accounts and operator port.

Preparation copies the current bot scripts, the shared acceptance wrapper and
phase-specific seed script into the run directory. Generated passwords, account
configs, script snapshots, fleet databases and logs stay under ignored `build/`.
`manifest.json` records engine/client SHAs, executable and script hashes, account
names and preparation settings. Each execution records its current versions too.

## What is seeded

`seed` first checks that every target quest is `not_started` and QP is zero. It
lets the client handle Tutorial Island, deposits the starter inventory, and seeds:

- Attack, Strength and Defence 75; Hitpoints 85; Prayer 70; Magic 60.
- Mining, Smithing, Crafting, Fishing and Woodcutting 40; Cooking 50.
- 1,000,000 coins and 1,000 lobsters, plus the retained tutorial supplies.
- Rune chainbody, platelegs and longsword; iron chainbody and bronze med helm for
  the fortress disguise; bronze pickaxe/axe, knife, tinderbox, hammer, shears,
  spade, bucket and pot.
- 2,000 mind, 4,000 air and 6,000 fire runes.

The seed checks supplies in the bank and repeats the zero-QP/unstarted assertions
before reporting `E2E_SEEDED` and logging out. Seeding is one-shot: a failed or
interrupted seed requires fresh characters, not rerunning the seed on saved progress.

All quest objectives are earned: beads, wool, ores, dyes, blurite and its sword,
the portrait and manor puzzles, rum delivery, disguising/rescuing Ali, both Arrav
gang paths and handoffs, Silverlight, the vampire fight, Melzar's Maze, map pieces,
ship repairs, the dragonfire shield and Elvarg. Tools and ordinary combat supplies
are banked; no quest flags, QP, objective items or reward certificates are seeded.

By default the wrapper enables per-character infinite run energy using the local
developer command. Pass `--natural-run` to **prepare** to omit it. This is quest
acceptance with seeded preparation, not training, resource scarcity or run-energy
endurance evidence. Testing F2P quests on a members world does not prove every
nonmembers-world restriction; record which world settings were used.

## Monitor, stop and resume

The launcher prints its session directory. Follow that session's log:

```powershell
Get-Content build/e2e/phase16-night1/sessions/<session>/client.log -Wait -Tail 40
Invoke-RestMethod http://127.0.0.1:8093/api/v1/status
```

The normal operator console supports the wrapper's `inspect` command for account
state. See [phase 17g diagnostics](../phase17g/README.md#observe-stop-and-resume)
for console submission examples. Watch blocked/parked reasons, repeated steps,
partner waits, deaths and exceptions. An active process alone is not a pass.

Ctrl+C stops this launcher's client and marks the invocation interrupted. The
shutdown helper verifies the operator listener's account names before sending
`quit`, so another client on a conflicting port is not quit. Avoid duplicate
logins or force-killing characters in dangerous areas.

To resume after fixing a client issue, preserve server saves and the run directory:

```powershell
python e2e/phase16/run.py run --run-dir build/e2e/phase16-night1 --cases ph ba --timeout-minutes 720 --client build/windows-msvc/Release/Rs2004Headless.exe
```

Keep both partners selected while Arrav is unfinished. Once both have completed
Arrav, `--cases ph` or `--cases ba` can resume a single remaining account. Do not
seed again. The script snapshot is preserved: a rebuilt executable updates native
and embedded stdlib behavior, but changes under `scripts/bots` require a fresh
preparation for a reproducible full rerun.

## Passing evidence

For each account, the shared wrapper requires every selected journal entry complete,
all queue rows DONE with no stuck rows, zero deaths in the invocation, the expected
39 QP and an earned completion count matching the number unfinished at login.
It records `E2E_RESULT`, then logs the account out automatically. The launcher also
requires exit code zero and matching successful records for both selected names
before writing `results.json` and printing PASS.

`initial_done` makes resumed progress explicit. An account already finished at
login cannot pass as a new completion. A resumed pass proves the remaining work
in that invocation; inspect earlier session logs for prior interruptions or deaths.
A clean full acceptance needs both initial lists empty and eighteen newly completed
quests per account in an uninterrupted run. Preserve all sessions when reporting
recovery evidence.

## Fast checks without a server

```powershell
python -B -m unittest discover -s e2e/phase16 -p 'test_*.py'
python -B -m unittest discover -s e2e/phase17g -p 'test_*.py'
python -I tools/port/lint.py e2e/scripts e2e/phase16/scripts e2e/phase17g/scripts
```

These checks cover fresh setup, partner/queue configuration, expected quest points,
snapshot contents, save protection, suite mismatches and completion-result rejection.
CI runs them; live execution remains a separate acceptance step.
