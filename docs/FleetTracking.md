# Fleet tracking: account data, experience, banks, inventories

The client stores all five fleet streams in a local SQLite database. The default is
`data/fleet.sqlite`; logging is enabled by default, including for accounts without scripts. No script
behavior changes. Setting `fleetDatabasePath` to an empty string disables all fleet streams.

The database stores account identity and stream/timestamp/sequence metadata separately from typed stream
tables. Account data and experience have explicit columns; bank, backpack and equipment snapshots use
child item rows, and experience snapshots use child skill rows. The sequence orders records
deterministically when timestamps share a second. Client processes sharing one database must use unique
account names unless they intentionally represent the same logical account. SQLite indexes support
latest-state lookups and bounded per-account history. A snapshot and all its child rows commit in one
transaction, so it cannot be partially written.

`fleet_accounts` stores account names; `fleet_records` stores the sequence, account reference, stream
reference, and `recorded_at` as whole Unix seconds. The stream name is stored once in `fleet_streams`.
State, target-kind, and skill names are likewise stored once in `fleet_states`, `fleet_target_kinds`, and
`fleet_skills`, with integer references in the typed rows. The stream data lives in `fleet_account_data`,
`fleet_experience`, `fleet_bank`, `fleet_inventory`, and `fleet_equipment`. Skills and items live in
`fleet_experience_skills` and the corresponding `*_items` child tables. Item names are stored once in
`fleet_item_names`; each snapshot keeps its item ID and a reference to the name used by that snapshot.
The experience-skill and item child tables use their composite primary keys without a separate rowid.
Public records still expose UTC timestamps in the existing `YYYY-MM-DDTHH:MM:SSZ` format. There is no
generic JSON payload column.

Schema version 5 is created for new databases. Earlier database schemas, including pre-release version 4,
are not migrated; the client rejects them without modifying them. Back up any history you need and configure a new
database path. Existing generic-payload databases and JSONL files are not migrated or imported.
Unversioned databases are also rejected without being modified.

The database uses WAL mode, `synchronous=NORMAL`, and a 25 ms busy timeout. Reads can proceed while clients
write. Within a client process, `AccountRunner` shares one background writer per normalized database path.
The account loop enqueues records and observes their completion without waiting on SQLite. The writer
collects up to 64 records for a transaction, waiting at most 5 ms to fill a batch; it accepts at most 256
outstanding writes per database. A full queue rejects the new write, which the stream reports and retries
using its existing pending/coalescing policy. Each batch is one transaction, so all of its records commit
together or all fail; a snapshot and its child rows remain atomic. A failed write is reported once, retried
with the stream's pending/coalescing policy, and does not advance successful sampling state or publish an
event. Each logger retains up to 256 deferred session transitions or bank-open snapshots; a new event
that exceeds that limit is explicitly warned and rejected. Deferred session/status transitions are written
in order, while coalescible gameplay and inventory changes keep their existing latest-sample policies.
Completion handling and event publication stay on the account loop and happen only after commit.
On normal runner shutdown, each started account's final state is sampled and accepted writes are drained
before the event publisher stops. SQLite still serializes writers across client processes, so a busy batch
can fail after the 25 ms wait and rely on the stream retry policy. SQLite is intended for a local
filesystem, not a network share. WAL is checkpointed automatically; see [maintenance](#log-maintenance).

The five streams keep their existing live-event JSON shape:

| Stream | Record trigger |
|---|---|
| `account-data` | Account data change, at most every `accountDataIntervalSeconds`; session changes immediately |
| `experience` | Settled skill sample every `experienceIntervalMinutes`, plus status changes |
| `bank` | Bank open, listing what the bank held |
| `inventory` | Backpack change, at most every `inventoryIntervalSeconds` |
| `equipment` | Worn equipment change |

Invalid UTF-8 bytes in item names are replaced with the Unicode replacement character before storage and
event publication.

## Configuration

```jsonc
"scripting": {
    "fleetDatabasePath": "data/fleet.sqlite",
    "accountDataLogEnabled": true,
    "experienceLogEnabled": true,
    "bankLogEnabled": true,
    "inventoryLogEnabled": true,
    "equipmentLogEnabled": true,
    "experienceIntervalMinutes": 1,
    "inventoryIntervalSeconds": 5,
    "accountDataIntervalSeconds": 5
}
```

| Key | Default | Meaning |
|---|---|---|
| `fleetDatabasePath` | `data/fleet.sqlite` | One database file for all enabled streams; empty disables fleet logging |
| `accountDataLogEnabled` | `true` | Store account state/session changes |
| `experienceLogEnabled` | `true` | Store skill samples and status changes |
| `experienceIntervalMinutes` | `1` | 0 to 1440 minutes between samples; `0` turns experience logging off |
| `bankLogEnabled` | `true` | Store bank snapshots |
| `inventoryLogEnabled` | `true` | Store backpack changes |
| `inventoryIntervalSeconds` | `5` | 0 to 86400 seconds between lines; `0` records every change |
| `equipmentLogEnabled` | `true` | Store worn equipment changes |
| `accountDataIntervalSeconds` | `5` | 0 to 86400 seconds between changes; `0` records every observed change |

These keys are also listed in the [configuration reference](Configuration.md#fleet-tracking-settings)
and [sample config](../client.jsonc.sample). They apply to every account, including idle accounts. Paths
are relative to the client's working directory. The fleet page reads the default database, or the database
paths in `--config` files, or explicit `--database` paths.

Legacy `*Directory` settings are ignored; set `fleetDatabasePath` and the desired `*LogEnabled` options
explicitly. Existing JSONL history remains untouched and is not read by the new fleet page.

## Account data

```json
{"time":"2026-11-14T13:20:26Z","account":"s18","state":"ingame","settled":true,"pid":42,"tile":{"x":3200,"z":3201,"level":0},"destination":null,"target":{"kind":"npc","index":17},"hp":{"current":25,"base":30},"energy":80,"prayer":{"current":12,"base":20},"specialAttack":{"energy":750,"armed":false},"running":true,"moving":false,"inCombat":false,"weight":5,"tick":123}
```

- Records changed account data, including idle accounts without a script. Changes during the interval
  are coalesced into the latest observed state. An unchanged account writes no extra records.
- Session state and settled changes bypass the interval. Gameplay fields are null until settled in
  game, and become null on logout or disconnection, so old positions and targets aren't reported as current.
- Tiles use absolute `x`, `z`, and `level`. `destination` is the client's outstanding walk destination,
  or null when none remains.
- `target` is the **server facing target**, not the last requested interaction. It is null, an `npc` or
  `player` with its entity `index`, or a `tile` with its tile. Entity facing takes priority over coordinate
  facing. Coordinate facing is rounded down from half-tile coordinates; the server provides no object ID.
  Facing can persist after an interaction has ended.
- HP and prayer include current and base levels. Run `energy` is 0–100; special attack energy uses
  0–1000, matching the scripting API. `specialAttack` is null until its energy varp has arrived
  (including servers/revisions without that bar). `weight` uses the game's run-weight units.
- `pid` is the current server player index. `tick` is the client tick count at observation; changes to
  the tick alone do not trigger a record.
- Failed writes warn once, retry at the configured interval, and publish no event until a transaction commits.

## Experience

```json
{"time":"2026-10-27T13:25:49Z","account":"s18","state":"ingame","settled":true,"skills":{"attack":{"level":31,"base":31,"xp":14848},"thieving":{"level":52,"base":52,"xp":943488},…}}
```

- `state` is the client's own: `connecting`, `ingame`, `logging out`, `logged out` or `disconnected`.
  A record is written whenever it changes, so the latest record says where the account is.
- `settled` is true once the player is placed and the stats for that tick have arrived. Only settled
  in-game lines are used for rates; a status line or a logged-out one has no XP run.
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

- Captured on the **closed → open** edge, once the bank inventory has arrived. If the interface opens
  first, an info log notes that the logger is waiting for its inventory while it stays open. Deposits
  and withdrawals made after that snapshot aren't re-recorded; the next open catches them. Failed
  database writes retry from the pending snapshot on later account steps and don't require another
  bank opening.
- Items are grouped by id, in id order.

## Inventory and equipment

```json
{"time":"2026-10-27T13:19:52Z","account":"s18","bankOpen":false,"used":24,"free":4,"items":[{"id":1891,"name":"Cake","qty":16},{"id":2309,"name":"Bread","qty":6}]}
{"time":"2026-10-27T13:18:49Z","account":"s18","used":0,"items":[]}
```

- The backpack is rewritten when it changes, at most every `inventoryIntervalSeconds`, including bank
  open and close changes subject to that same interval. `bankOpen` marks samples taken while the bank is
  open: the game swaps in the bank's own backpack then, and that is the one recorded. `free` comes from the cache's backpack size, so
  a packet holding only the filled slots can't report a full backpack.
- Items are grouped by id, in id order.
- Worn equipment records only what is worn. It has no `free`: the equipment interface's
  grid has decorative cells that can never hold anything.

## WebSocket events

The operator WebSocket endpoint `/api/v1/events` publishes a live event after each
successfully committed fleet record:

| Event | Journal |
|---|---|
| `fleet.account-data` | Account data and session changes |
| `fleet.experience` | Experience samples and account state changes |
| `fleet.bank` | Bank snapshots on opening |
| `fleet.inventory` | Backpack samples, with the configured interval |
| `fleet.equipment` | Worn equipment changes |

```json
{"version":1,"type":"subscribe","id":"fleet","events":["fleet.account-data","fleet.experience","fleet.bank","fleet.inventory","fleet.equipment"],"accounts":["s18"]}
```

Each event's `payload` is the complete JSON object from the corresponding typed
record, including its `time` and `account`; it is serialized only for event
publication, not stored as a database payload. Events are published only after the
typed snapshot transaction commits. The envelope's `account` is the account config
name. Omit `accounts` to receive all accounts. These events need no script,
are live only, and are not retained in subscription snapshots or replayed after
reconnect. Disabled streams and failed commits produce no events.

The existing event size limit is 8192 bytes per envelope. Fleet records reserve
1024 bytes for envelope metadata, so records exceeding 7168 bytes of JSON are
omitted from the event stream; their full payloads are still stored.
See [live events](Running.md#live-progress-events) for listener setup, acknowledgements,
ordering and reconnect behavior.

## The local page

```sh
python3 tools/fleet/server.py                  # http://127.0.0.1:8765
python3 tools/fleet/server.py --port 9000
python3 tools/fleet/server.py --database data/fleet.sqlite
```

Read-only, loopback only, and never started by the client. Ctrl+C ends it. By default it reads
`data/fleet.sqlite`; repeat `--database PATH` to combine databases. With `--config`, it reads the
database paths in those client configurations and enables client control.

- **Accounts** — the latest state of each account: session status, PID, tile, destination, server facing
  target, HP and prayer (current/base), run energy, special attack energy and armed state, running,
  moving, combat, weight and tick. Filter by account name. Gameplay values are blank while unsettled
  or offline. Recorded age is the last account-data change, not a connection heartbeat.
  The server exposes these latest records at `/api/account-data` as an `accounts` object keyed by account.
- **Experience** — accounts down the side, skills across the top. Each cell shows the level and, beneath,
  the XP an hour. The rate is the newest sample minus the oldest sample of the newest continuous run (at
  most 15 minutes back); a relogin rewinds XP, so the run stops there rather than producing a negative
  rate. The metric selector switches to raw XP or XP an hour.
- **Bank** — every item summed across the latest bank snapshot of each account, with its id, total stock and
  how many accounts hold it. Click an item to see each account's share.
- **Inventory** — choose an account to see its backpack and worn equipment, the slot counts, whether a bank
  is open, and how old each snapshot is.

The page refreshes every ten seconds, shows how old each record is, and has a Refresh button per tab.

The server uses CPython 3 and its standard library. `--port` overrides `FLEET_PORT`, whose default is
`8765`. `--config CLIENT_JSONC ...` enables the optional controls described below. Client control uses
POSIX process groups and Linux `/proc` for adoption; use the page read-only on Windows.

## Starting and stopping the client

The page is read-only unless it is given client configs:

```sh
python3 tools/fleet/server.py --config client_w1.jsonc client_w2.jsonc client_w3.jsonc
```

One process handles at most **16 scripted accounts**: `ScriptRuntime::MAX_VMS` is 16 and pocketpy's own
VM table is `pk_all_vm[16]`. A larger fleet is run as one process per config — 45 accounts as three
processes of 15 — and the page treats them as one fleet.

A bar above the tabs then has **Launch client** and **Stop client**:

| State | Launch | Stop |
|---|---|---|
| idle | enabled | disabled |
| running | disabled | enabled |
| during launch or stop | disabled | disabled |

- **Launch** finds the built client (beside the repository, in a preset build folder, then `PATH`) and runs
  `Rs2004Headless <config> --raw-console` for **each** config, with output appended to
  `logs/fleet-<config>.log`. It refuses while any is running.
- **Stop** sends SIGINT to every process, the client's graceful Ctrl+C path: scripts get `killGraceSeconds`,
  then accounts log out. A second SIGINT follows after ten seconds to log every account out at once if the
  server is refusing a logout in combat, and SIGKILL only for a process that outlives both (forty seconds).
- The status line shows the clients and the accounts: `running · 3/3 clients · 45/45 in game`. The account
  count is the latest status record in the experience stream, so it follows logins and logouts without polling
  the clients.
- The running pids are written to `logs/fleet.pid`, so restarting the page adopts the clients it launched and
  Stop still works. A client started any other way is not adopted and is never signalled.

This is not the in-client script control described above: Launch starts **new** client processes, and Stop
shuts them down. Switching scripts means stopping and launching again.

Without `--config` the page cannot start or stop anything: the bar is hidden, and `/api/launch` and
`/api/stop` answer 403.

## Turning it off

| Want | Set |
|---|---|
| No account data log | `"accountDataLogEnabled": false` |
| No experience log | `"experienceLogEnabled": false` or `"experienceIntervalMinutes": 0` |
| No bank log | `"bankLogEnabled": false` |
| No inventory log | `"inventoryLogEnabled": false` |
| No equipment log | `"equipmentLogEnabled": false` |
| No page | don't run `tools/fleet/server.py` |

The default database and its WAL sidecars, `logs/` (including `fleet.pid`) and Python `__pycache__/`
folders are ignored by Git. If you choose a custom database path, add it to `.git/info/exclude` or `.gitignore`.

## Log maintenance

Fleet history is pruned automatically per account and stream according to the
`scripting.fleetRetention` limits. After each write batch, once an account's
stream reaches its configured maximum, the oldest records by insertion sequence
are deleted in prune-sized batches. If a batch overshoots the maximum by more
than one prune amount, enough oldest records are removed to bring the count below
the maximum. Related snapshot and child rows are removed by foreign-key cascade
in the same transaction as the write.
The defaults retain up to 10,000 account-data and experience records, 1,000 bank
and equipment records, and 5,000 inventory records per account. Each pruning
amount is 10% of its stream's maximum. Set both `maxRecords` and
`pruneRecords` to `0` for a stream to disable pruning.
Limits count parent records, not child rows or bytes, so snapshots of different
sizes still consume different amounts of storage. The writer checks only the
account/stream pairs touched by a write batch; a changed limit takes effect the
next time that account writes to the stream.

Pruning limits retained rows but does not necessarily shrink the SQLite file
immediately: SQLite can reuse the freed pages. The compactor can checkpoint the
WAL and optionally run `VACUUM` to reclaim free pages from the main database.
Stop all writers before manual maintenance:

```sh
python3 tools/fleet/compact_logs.py --database data/fleet.sqlite --dry-run
python3 tools/fleet/compact_logs.py --database data/fleet.sqlite --console-mb 20
python3 tools/fleet/compact_logs.py --database data/fleet.sqlite --vacuum
```

`--dry-run` reports the database action without writing. Checkpointing truncates the WAL file after
committed records are copied into the database. `--vacuum` additionally reclaims free pages in the main
database; it may take time and needs temporary disk space. `--console-mb` sets the number of MiB retained
per `logs/*.log` file (default `20`). Back up the database together with any active `-wal` sidecar, or use
SQLite's online backup API; do not copy only the main file while a client is writing.

## Performance and storage behavior

The database is written synchronously from the account loop; no background queue is used. Each transaction
stores one complete snapshot, with a 25 ms SQLite busy timeout and retry on the next eligible sampling step.
WAL plus `synchronous=NORMAL` favors concurrent readers and lower write latency; it can lose the newest
committed transactions on sudden power loss, while preserving database consistency. `synchronous=FULL` can
be selected only by changing the storage implementation and measuring the tradeoff.

The [synthetic benchmark](../tools/fleet/benchmark_storage.py) compares JSONL with the normalized schema
and production fleet-server query functions. Earlier numbers measured the generic payload schema and no
longer apply. For a repeatable local comparison, run
`python -B tools/fleet/benchmark_storage.py --accounts 45 --records 20 --queries 10`.
It measures the Python storage path, not the live C++/SQLiteCpp writer; use results only for the tested
workload, filesystem and runtime.
