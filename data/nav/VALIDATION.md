# Observatory reception ladder (issue #56)

On 2026-11-13, a local revision-289 run reproduced a world-walker route missing
from the Observatory reception to the cavern and telescope. Upstream disables
the reception ladder as being behind a runtime guard. The engine's guard only
shows the assistant's goblin warning before an unconditional descent; continuing
that conversation makes the crossing usable without a quest prerequisite.

| Field | Value |
|---|---|
| Client baseline | `97807d54cd856702cf4b15c43da2a8463fd8b18d` |
| Engine | `278bd51cc17cc0d093e1ea3895536a8054583f97` |
| Upstream export baseline | `27e57fa331656df5a0d9b7b1cd1f4ec0c44519bb` |
| Tick duration | 600 ms |
| Account | Scratch `navprobe56`, separate player saves and client configuration |
| Seeded prerequisites | Tutorial complete (`tutorial=1000`); default level-1 skills and 10 Hitpoints; no supplies |
| Quest states | `itgronigen=0` (not started), `itgronigen=7` (complete), set solely to exercise both warning branches |
| Start / ladder | `(2444,3192,0)` / loc 2187 at `(2444,3191,0)`, `Climb-down` |
| Actual landing | `(2420,9459,0)` |
| Full walk destination | `(2440,3160,0)`, adjacent to the telescope |

The engine behavior is in
`content/scripts/quests/quest_itgronigen/scripts/quest_itgronigen.rs2`,
`[oploc1,obs_dungeonladderdown]`: below quest completion, continue the assistant's
warning and the player's reply; then jump to `0_37_147_52_51`. Completed quests
skip the warning and use the same landing. No server transport behavior was changed.
The engine working tree had browser-client asset changes; this TCP run did not
use those assets or change the engine's game scripts.

## Reproduction

Use a separate local engine profile and scratch client/accounts directories as
described in [Building](../../docs/Building.md). The recorded run used TCP 19356,
web 18056 and management 18057, with the local engine's packed cache and RSA key.
The only engine harness changes seeded tutorial completion and a mainland login
position for this scratch username, and logged its game messages.

1. Set the scratch account's `itgronigen` to 0, and place it at `(2444,3192,0)`.
2. Disable teleports and request a route or `traversal.walk_to` to the dome at
   `(2440,3165,0)`. Before the correction, a 400,000-expansion route request
   exhausted its budget, and the walk returned `False`, `failed`, `unreachable`.
3. Click loc 2187's `Climb-down` and continue both warning pages. The engine
   reports `You climb down the ladder.` and places the player at `(2420,9459,0)`.
4. With regenerated data, walk from reception to `(2440,3160,0)` with radius 0,
   a 180,000 ms timeout, teleports disabled and no bank-item assumptions.
   Repeat with `itgronigen=7` to exercise the warning-free descent.

The telescope's own tile `(2440,3159,0)` is blocked. A radius-0 request there
correctly finishes `closest` on `(2440,3160,0)`; use the adjacent tile when
asserting exact arrival.

Both final live walks finished at the exact adjacent tile with teleports disabled:

```text
ISSUE56_WALK 0 True arrived None Tile(2440, 3160, 0)
ISSUE56_WALK 7 True arrived None Tile(2440, 3160, 0)
ISSUE56_PASS
```

Local artifacts are retained under `build/issue56/`: `before-client.log` contains
the failed route and manual descent; `client.log` contains the corrected walks;
`server.stdout.log` records tick duration, seeded login state and game messages.
`scripts/reproduce.py`, `scripts/validate.py` and `server.mts` contain the scratch
probes. Log timestamps use UTC (2026-11-14); the local test date was 2026-11-13.

## Regression checks

`tests/Stdlib/rs2b0t/nav/test_observatory_ladder_cache.py` runs as its own
cache-backed CTest case. Both route specs failed before regeneration and pass
afterward. They check exact arrival in the cavern and beside the telescope,
the reception hop's landing, and selection of its dialogue crossing only for
the matching destination.

The exporter adds one dungeon edge and one special crossing. Regeneration from
the upstream baseline preserves every existing edge and crossing and leaves
the other three JSON files unchanged. The crossing uses the existing dialogue
handler to continue the warning; the quest's explicit descent helper is unchanged.

Validation passed all 52 revision-289 walker-data CTest cases and all 6
`Navigation`-labelled cases in Windows Debug. The pinned C++ formatting check
and the new spec's pocketpy dialect check passed. A second export reproduced
all five JSON files byte for byte.

The Debug test target rebuilt successfully. Linking the ordinary application
was blocked by an existing client holding its executable/PDB open; that process
was left running. No native runtime implementation changed. The live probe used
the baseline Debug executable with the corrected external navigation data.
Revisions 225 and 274 were not re-audited by this validation.
