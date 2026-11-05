# Open work

Reviewed against local code, tests and saved validation reports on 2026-11-05. Linked documents retain
implementation details and historical acceptance evidence. GitHub issues, pull requests and upstream's
current tip were not queried during this review.

All original Bot API parity phases (10–18), including all 63 quests and AccountLeveler, are implemented.
The export audit against pinned rs2b0t `8b7db422` reports nothing missing. The newer quest recovery,
multiloc, Cosmic/JiveRC, three-tick fishing, MuleCrafter and MuleDepot ports are also implemented.
Every embedded stdlib file meets the 95% coverage floor; additional coverage is optional follow-up.

## Implementation and tooling

| Item | Remaining work | Source |
|---|---|---|
| Play Tutorial Island | Implement the tutorial sequence; `rs2004/tutorial.py` currently designs the character and asks the guide to skip | README |
| Later upstream commits | Review changes after pinned `8b7db422`; this cleanup makes no claim about upstream's current tip | [Upstream review](Rs2b0tUpstreamReview.md) |
| Pocketpy lint: set membership | Detect unsafe `None in some_set`, or audit relevant sets; the specific clue casket crash is fixed | [Parity status](BotApiParityStatus.md#open-items) |
| Pocketpy lint: returned generators | Detect conditional generator returns such as `return (a(log) if c else b(log))`; the specific Digsite/Ikov call sites are fixed | Parity status |
| Remaining upstream facade tests | Port bank-chest/id/transfer, open-window `StableClosedPoll`, JiveMarketDumper runtime, MarketMaker tasks, Shilo supply-trip fixtures, WordPack chat echo, and remaining JiveDragons/JiveKQ suites. Class/module `spy_on` and fakes are available; instance method replacement remains unsupported | Parity status |
| Grand Tree journal | Investigate returning an older parsed stage despite a newer cached stage | [Coverage findings](ScriptCoverageBacklog.md#known-findings) |
| Tourist Trap recovery | Confirm/remove the two suspected unreachable `leave_camp` branches following `safe_recovery_route` | Coverage findings |
| Cache-backed Debug navigation test budget | The aggregate walker-data suite exceeded CTest's 300-second limit during the WildyAgility follow-up; split its registration or review the budget. The full cache-backed Release suite and default Debug suite pass | [Validation](Rs2b0tUpstreamReview.md#wildyagility-follow-up-2026-11-05) |

## Live validation

| Item | Evidence still needed | Source |
|---|---|---|
| New feature workflows | Cosmic travel/trading, coordinated MuleDepot transfers, MuleCrafter meeting/banking modes and real-speed three-tick fishing throughput | [Upstream review](Rs2b0tUpstreamReview.md#remaining-work) |
| Multilocs with real content | Local 289 cache has varbits but no multiloc loc definitions; transitions/collision currently use synthetic fixtures | Upstream review |
| Phases 17h/17i at real speed | Repeat timing-sensitive quest/clue runs at 600 ms; recorded acceptance used 100 ms ticks | [Parity status](BotApiParityStatus.md#open-items) |
| AccountLeveler beyond its acceptance run | Real-speed behavior, high-level dragon progression and optional player-market trading. The completed two-hour run used low-level methods at 100 ms across restarts | [Design, phase 18](BotApiParityDesign.md#as-built-18) |
| Phase 11 duration | Most bots ran 12 minutes; the plan's 15-minute acceptance checkbox remains open | [Design, phase 11](BotApiParityDesign.md#5-phase-11-the-modules-bots-share) |
| Refused crossing with an alternative | Demonstrate the walker routing around one live; the Champions' Guild crossing has no alternative | Parity status |
| Revision 225/274 live evidence | Confirm/document planned checks. The old audit found a 274 live-run record without CHAT `rights`/`MESSAGE_PRIVATE` evidence and no 225 live-run record; these remain unverified | [RevisionDesign.md](RevisionDesign.md), [Revision274Design.md](Revision274Design.md) |

## Bugs and limitations awaiting a trigger

These are retained observations, not newly reproduced failures.

| Item | Next step or trigger | Source |
|---|---|---|
| JiveKQ Shantay-pass purchase stopped on a third restock | Capture the shop state if it recurs | [Parity status](BotApiParityStatus.md#open-items) |
| Tile oscillation counts as watchdog progress | Add a rule when another failing quest reproduces it | Parity status |
| Wield swaps hide two-step loops from the watchdog | Add a rule when another quest reproduces it; Ikov's specific picker loop is fixed | Parity status |
| Failed teleport offered for five repaths | Revisit when a real account hits it; observed with quest progress seeded by varp | Parity status |
| Radimus conversation closes after its first session | Investigate if retry recovery stops being sufficient | Parity status |
| Gilded totem hand-in lost a minute once | Investigate if it recurs or recovery fails | Parity status |
| Regicide death can lose its only spade | Add a source when needed; currently parks with a reason | Parity status |
| Scavvo's rune kit does not restock | Bank a second kit for paired Hero's Quest runs without a harness | Parity status |
| Hard Kharazi pack capacity and Saradomin Wizard kit | Extra items can block a 15-shark load; ClueSolver logs shortages but does not dress its account | Parity status |
| Unexplained clue bank stall | One historical account stalled before kit logging existed; investigate if it recurs | [Design, phase 17i](BotApiParityDesign.md#as-built-17i) |

## Revisions and deferred maintenance

| Item | Remaining work or trigger | Source |
|---|---|---|
| Content ids on 225/274 | Audit revision-specific content: catalogs/nav are generated from 289, and catalog-name checks target 289 | [RevisionDesign.md §15](RevisionDesign.md#15-out-of-scope-and-risks), [Revision274Design.md §12](Revision274Design.md#12-out-of-scope-and-risks) |
| Download 225 maps over the wire | Optional phase 6; `DATA_*` payloads are consumed/dropped and stale squares only warn | [RevisionDesign.md](RevisionDesign.md) |
| A revision per account | Requires a cache per revision in `Application` | RevisionDesign §15 |
| `std::byteswap` | When moving from C++20 to C++23 | `src/Utils/Endian.hpp` |
| IPv6 literal server host | When a server needs one | [TransportDesign.md](TransportDesign.md) |
| Send queue limit | When a stalled server makes it necessary | TransportDesign |
| Config JSON Schema | When configuration growth warrants it | [ConfigDesign.md](ConfigDesign.md) |
| Walker data adjustments | When a new quest route exposes an engine-specific mismatch | Parity status |
| Obsolete protocol implementation notes | `tcp-protocol-289.md` still points to an absent `headless-client` and describes `OBJ_ADD` as missing; this client already decodes it | [Protocol notes](tcp-protocol-289.md#headless-client-implementation-notes) |

## Cosmetic and optional coverage

- Duplicate `trail complete` logging and GnomeMagicChopper's zero "Chopped" counter remain cosmetic.
- JiveKBD's default Fire Strike yielded no kills in its recorded 30-minute run; adjust settings as needed.
- Black Knights' Fortress re-listens at the grill after a restart because `listened` is process-local.
- Further coverage opportunities are in [ScriptCoverageBacklog.md](ScriptCoverageBacklog.md). Its latest saved
  report is 97.85%, with every file meeting 95%; phase 17 runtime specs are no longer an outstanding floor requirement.

Completed items have been removed from this index, including phase 18, the old coverage-floor work,
empty-ground-spawn waiting and the log file sink (`src/Console/LogFile.cpp`, configured by `client.logFile`).
Historical phase checklists and test counts remain in the design documents as evidence. Template checkboxes,
unsupported stage-number fallbacks and deliberately excluded browser features are not pending tasks.
