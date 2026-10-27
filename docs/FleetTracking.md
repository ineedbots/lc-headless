# Fleet tracking: experience, banks, inventories

The client can write what each account is earning and holding, per account, as JSON Lines. A small local
page reads those files. All of it is optional: each log writes to its own folder, and an empty folder turns
that log off. Nothing here changes how a script runs.

The files are per **account**, named after the account (the account file's name without `.jsonc`), so
several accounts in one process never collide and nothing depends on the world or the client's log file.

| Folder | One line per |
|---|---|
| `experience/<account>.jsonl` | skill sample, every `experienceIntervalMinutes` |
| `bank/<account>.jsonl` | bank open, listing what the bank held |
| `inventory/<account>.jsonl` | backpack change, at most every `inventoryIntervalSeconds` |
| `equipment/<account>.jsonl` | worn equipment change |

Each line is a complete JSON object, and the **last line is the current state**. Lines are appended, so a
file is also its history.

## Configuration

```jsonc
"scripting": {
    "experienceDirectory": "experience",
    "experienceIntervalMinutes": 1,
    "bankLogDirectory": "bank",
    "inventoryDirectory": "inventory",
    "inventoryIntervalSeconds": 5,
    "equipmentDirectory": "equipment"
}
```

| Key | Default | Meaning |
|---|---|---|
| `experienceDirectory` | `experience` | The folder. Empty turns the log off |
| `experienceIntervalMinutes` | `1` | Minutes between samples; `0` turns it off |
| `bankLogDirectory` | `bank` | The folder. Empty turns the log off |
| `inventoryDirectory` | `inventory` | The folder. Empty turns the log off |
| `inventoryIntervalSeconds` | `5` | The least time between two lines; `0` records every change |
| `equipmentDirectory` | `equipment` | The folder. Empty turns the log off |

## Experience

```json
{"time":"2026-10-27T13:25:49Z","account":"s18","skills":{"attack":{"level":31,"base":31,"xp":14848},"thieving":{"level":52,"base":52,"xp":943488},…}}
```

- All 19 skills, in the game's stat order, with the current level, base level and XP.
- The first sample is the baseline, written once the player is **settled** in game — placed, and a tick
  after the tick that placed them. The stats arrive a tick after the player, so a sample taken before
  that would record zeroes.
- Later samples follow every interval. The first of each run is a baseline; the client's log also names
  the skills that gained XP and their rate.

## Bank

```json
{"time":"2026-10-27T13:20:26Z","account":"s18","items":[{"id":995,"name":"Coins","qty":109},{"id":1891,"name":"Cake","qty":4856},…]}
```

- Written on the **closed → open** edge only. Deposits and withdrawals made while the bank stays open
  aren't re-recorded, so each line is the bank as it was when it opened, and the next open catches up.
- Items are grouped by id, in id order.

## Inventory and equipment

```json
{"time":"2026-10-27T13:19:52Z","account":"s18","bankOpen":false,"used":24,"free":4,"items":[{"id":1891,"name":"Cake","qty":16},{"id":2309,"name":"Bread","qty":6}]}
{"time":"2026-10-27T13:18:49Z","account":"s18","used":0,"items":[]}
```

- The backpack is rewritten when it changes, at most every `inventoryIntervalSeconds`, plus on the bank
  open and close edges. `bankOpen` marks the samples taken while the bank is open: the game swaps in the
  bank's own backpack then, and that is the one recorded. `free` comes from the cache's backpack size, so
  a packet holding only the filled slots can't report a full backpack.
- Items are grouped by id, in id order.
- Worn equipment is its own file and records only what is worn. It has no `free`: the equipment interface's
  grid has decorative cells that can never hold anything.

## The local page

```sh
python3 tools/fleet/server.py                  # http://127.0.0.1:8765
python3 tools/fleet/server.py --port 9000
```

Read-only, loopback only, and never started by the client. Ctrl+C ends it. It only reads the four folders
and starts or controls nothing.

- **Experience** — accounts down the side, skills across the top. Each cell shows the level and, beneath,
  the XP an hour. The rate is the newest sample minus the oldest sample of the newest continuous run (at
  most 15 minutes back); a relogin rewinds XP, so the run stops there rather than producing a negative
  rate. The metric selector switches to raw XP or XP an hour.
- **Bank** — every item summed across the latest bank snapshot of each account, with its id, total stock and
  how many accounts hold it. Click an item to see each account's share.
- **Inventory** — choose an account to see its backpack and worn equipment, the slot counts, whether a bank
  is open, and how old each snapshot is.

The page refreshes every ten seconds, shows how old each file is, and has a Refresh button per tab.

## Turning it off

| Want | Set |
|---|---|
| No experience log | `"experienceDirectory": ""` or `"experienceIntervalMinutes": 0` |
| No bank log | `"bankLogDirectory": ""` |
| No inventory log | `"inventoryDirectory": ""` |
| No equipment log | `"equipmentDirectory": ""` |
| No page | don't run `tools/fleet/server.py` |

The folders aren't in the repository's `.gitignore`. If you keep a fleet in a checkout, add
`experience/`, `bank/`, `inventory/` and `equipment/` to `.git/info/exclude` (local only) so the data never
ends up in a commit.
