# Refused-crossing live acceptance (#37)

[Issue #37](https://github.com/ineedbots/lc-headless/issues/37) is demonstrated by
[the client transcript](issue37-client.txt) and [the server transcript](issue37-server.txt).
The run arrived at the exact destination after one refusal and one replan in **4,249 ms**.
No client or navigation-data changes were needed.

## Environment

- Run: **2026-11-13 18:52:15–18:52:26 America/Regina**, corresponding to
  2026-11-14 00:52 UTC in the client log.
- Client: `f3df934ca57a2bb9914fe0fed1322b5bd107cff0`, Windows x64 Debug,
  built with `cmake --build --preset windows-debug --parallel`.
- Revision 289 engine: `278bd51cc17cc0d093e1ea3895536a8054583f97`.
- Content: `f32c62f66302f76b43c752ede3181de0c0d01369`.
- Node.js 24.21.0; normal **600 ms** server tick, without acceleration.
- Separate engine working directory under `build/issue37/engine`, separate saves,
  TCP port 19337, web port 18037, management port 18038. Login service and live
  reload were disabled; packed cache and assets were linked from the local engine.
- Scratch account `navprobe37`, development staff access, members world; no key,
  quest, skill, inventory or bank prerequisites. The ordinary tutorial skip ran
  before the script on the account's first login. The setup staff teleport ends
  before timing begins; the walk itself disables teleports and bank funding.
- Engine/content source files were not edited. Existing engine web-asset changes
  were unrelated to this TCP run. Existing accounts and configs were not used.
- Client startup paths in the transcript are replaced with `<repo>` and `<engine>`.

## Route and result

Positions use `(x,z,level)`. Loc ID and coordinate together identify the crossing
placement; the graph does not assign a separate crossing ID.

| Stage | Crossing / route | Evidence (UTC) |
|---|---|---|
| Initial | `(3217,3218,0)` → `(3216,3218,0)`; Open Large door **1516** at `(3217,3218,0)`; cost 4, 2 waypoints | 00:52:22.043 |
| Refusal | Server sends **`The door is locked.`** without opening the primary door | Server epoch ms 1794617542605; client receipt 00:52:22.607 |
| Exclusion | `quest-locked Large door at 3217,3218, leaving it out` | 00:52:22.615 |
| Replan | `(3217,3218,0)` → `(3217,3219,0)` → `(3216,3219,0)` → `(3216,3218,0)`; Open Large door **1519** at `(3217,3219,0)`; cost 6, 4 waypoints | 00:52:22.635, `repath 1` |
| Cross alternate | `through the Large door at 3217,3219` | 00:52:25.047 |
| Arrive | `True`, outcome `arrived`, exact tile `(3216,3218,0)`, excludes `[[3217,3218]]`, **4,249 ms** | 00:52:26.272 |

`WALK path:` lines are the actual traversal's logs. `ROUTE_PROBE` lines are separate,
read-only navigator searches at those points using the traversal's exclusion list,
to expose the loc IDs and waypoints. They do not replace or modify traversal
requests, route results or transport handlers.

## Deliberate refusal

[refuse_crossing.mts](refuse_crossing.mts) starts the ordinary engine, then wraps
its Open-loc packet handler for just account `navprobe37`, loc 1516 at `(3217,3218,0)`.
That placement returns a real game-message packet without opening. Other operations,
including the alternate crossing, use the original handler. The refusal stays
active throughout the run.

The two leaves of Lumbridge castle's entrance are separate graph crossings. The
alternate leaf's normal server script opens the double door and the player walks
through it. This demonstrates exclusion and arrival via an alternate crossing;
it does not demonstrate independent entrances or a particular quest's lock condition.

[refused_crossing.py](refused_crossing.py) is a pocketpy account script. It teleports
the scratch account to the start, waits for placement, and calls the ordinary
`traversal.walk_to` with zero arrival radius and the default follow policy.
It asserts the refusal, crossing IDs, exactly two route probes, exclusion and exact
arrival, logs `PASS issue37`, and logs the account out. A missing refusal fails.

## Repeat locally

Follow [Building](../../docs/Building.md), [Configuration](../../docs/Configuration.md)
and [Running](../../docs/Running.md), with a matching packed development 289 engine.
Create this separate working directory; directory links suffice for shared assets:

```text
build/issue37/engine/
    data/config/world.json       copied engine config, overridden below
    data/config/private.pem      copy of the local engine key
    data/config/public.pem       copy of the local engine key
    data/pack                    link to engine/data/pack
    data/raw                     link to engine/data/raw
    data/players/                empty; do not link existing saves
    public                       link to engine/public
    view                         link to engine/view
```

Override these fields in the copied `world.json`, retaining other engine defaults:

```json
{
    "easyStartup": false,
    "web": {"port": 18037, "managementPort": 18038},
    "node": {"port": 19337, "profile": "issue37", "production": false, "members": true},
    "login": {"enabled": false},
    "friend": {"enabled": false},
    "logger": {"enabled": false},
    "build": {"startup": false, "liveReload": false, "srcDir": "<absolute content path>"}
}
```

Use unoccupied ports if these are unavailable. In a separate PowerShell terminal,
starting at the repository root:

```powershell
$repoPath = (Get-Location).Path
$enginePath = (Resolve-Path ../289server/engine).Path
$loaderUri = ([System.Uri]"$enginePath/node_modules/tsx/dist/loader.mjs").AbsoluteUri
Set-Location build/issue37/engine
node --import $loaderUri "$repoPath/tools/live/refuse_crossing.mts" $enginePath
```

Wait for `World ready`. In the repository-root terminal, create a scratch client
config from `client.jsonc.sample`: TCP `127.0.0.1:19337`, revision 289, the engine's
RSA public modulus/exponent, its packed cache, and `data/nav`.
Set `scripting.scriptsDirectory` to the absolute `tools/live` path, account/output
directories under `build/issue37`, and `client.logFile` to
`build/issue37/repeat-client.log`. RSA values must be the public `n` and `e`
corresponding to the copied private key.

Create `build/issue37/account.jsonc`:

```json
{
    "username": "navprobe37",
    "password": "scratch37",
    "randomEvents": false,
    "runAuto": false,
    "script": {"file": "refused_crossing.py"}
}
```

Then run:

```powershell
cmake --build --preset windows-debug --parallel
./build/windows-msvc/Debug/Rs2004Headless.exe build/issue37/client.jsonc --account build/issue37/account.jsonc --raw-console
```

Expect the refusal, one replan through loc 1519, and `PASS issue37` followed by
logout. Restart the scratch engine before repeating to restore closed doors.
Stop it afterwards. Keep keys, saves and configs under the ignored build directory.

## Validation and limits

The Debug build, embedded standard-library tests (1,477 assertions), quest-lock
phrase tests (7 assertions), six navigation cases, 21 world-pathfinder cases,
and the pocketpy dialect lint passed. The deterministic workflow in `tests/Stdlib/test_transport_crossings.py`
checks refusal → excluded request → alternate door → exact arrival.

The first East Ardougne candidate was rejected: the door at `(2572,3305,1)` refused
naturally, but the planned ladder detour returned to the original side. It was
not used as arrival evidence. Its ladder approach/landing behavior remains
uninvestigated; this work does not establish a fix for that separate candidate.
The accepted Lumbridge run found no defect in refusal exclusion/replanning.
Revisions 274/225 and other crossings were not live-tested.
