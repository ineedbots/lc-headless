# Open work

Everything found open in this repository on 2026-11-01, for deciding what to do next. It collects items from their sources, which stay the place to update them: the README's TODO list, [BotApiParityStatus.md](BotApiParityStatus.md), the design documents and code comments. Missed test coverage has its own list in [ScriptCoverageBacklog.md](ScriptCoverageBacklog.md).

**GitHub:** no open issues. One open pull request, [#17](https://github.com/ineedbots/lc-headless/pull/17) (the coverage specs), with all 9 CI checks passing. No other unmerged branches or stashes.

## Main work

| Item | State | Source |
|---|---|---|
| Phase 18: the account leveler | Implemented; all 802 tests and the full export audit pass. Two-hour live acceptance is in progress | [BotApiParityDesign.md §12](BotApiParityDesign.md#12-phase-18-the-account-leveler) |
| Newer rs2b0t commits | Reviewed 17 commits from `32d52004` through `8b7db422` (2026-11-04); selected script, quest, navigation and content fixes applied. The quest recovery follow-up is implemented. Remaining multilocs, Cosmic runecrafting, three-tick fishing, MuleDepot work are recorded in [the review](Rs2b0tUpstreamReview.md) | README, upstream review |
| Play Tutorial Island rather than skipping it | Not started. `rs2004/tutorial.py` only asks the guide to skip | README |
| Stdlib test coverage, including phases 17a and 17e–17i | 84.89% with PR #17; 11,656 lines left | README, [ScriptCoverageBacklog.md](ScriptCoverageBacklog.md) |

## Bugs and failures

| Item | State | Source |
|---|---|---|
| JiveKQ stopped once on a third restock with "Could not buy a Shantay pass" | Cause unknown; log the shop's state when it recurs | Status page |
| A step failing while the character steps between two tiles never parks, as the tile reads as progress | Waiting for a quest to hit it | Status page |
| A wield swap changes the inventory, so the watchdog can't see a two-step loop (Ikov's melee picker had one) | Needs a watchdog rule when another quest hits it | Status page |
| A failing teleport cast is offered again for 5 repaths | Seen only on an account with a spell's quest set by varp | Status page |
| Radimus's conversation shuts after the first session, for a reason not found | The engine's next attempt carries on | Status page |
| The gilded totem's hand-in lost a minute on one run | Recovered on its next attempt | Status page |
| Regicide needs the spade it took through the pass, and no shop near Ardougne sells one | A death carrying the only one parks the quest, with the reason | Status page |
| Scavvo stocks one of each rune piece and doesn't restock | A second Hero's Quest partner needs the kit banked | Status page |
| A hard Kharazi trail's pack only just fits its kit and 15 sharks | An extra scroll or gift blocks it, with a log line. ClueSolver doesn't dress an account for the Saradomin Wizard | Status page |

## Tooling and tests

| Item | State | Source |
|---|---|---|
| `lint.py` has no rule for `None in some_set`, which raises in pocketpy | Caused phase 17i's casket crash | Status page |
| `ts2py.ts` and `lint.py` don't flag a generator returned from a conditional, `return (a(log) if c else b(log))` | Digsite and Ikov had it | Status page |
| rs2b0t tests that stub with `spyOn`: bank-chest, bank-id, bank-transfer, `StableClosedPoll`, JiveMarketDumper, MarketMaker's `tasks.test`, the Shilo trip's fixtures, and the rest of JiveDragons' and JiveKQ's | Not ported. The status page gives two answers: one row says they need a fake game state, another that `spec.py`'s `spy_on` makes them portable. `spy_on` exists, so the first looks out of date | Status page |
| `touristtrap.py` lines 2448 and 2484 | Probably dead code | [ScriptCoverageBacklog.md](ScriptCoverageBacklog.md#known-findings) |

## Live checks not done

| Item | State | Source |
|---|---|---|
| Phases 17h's and 17i's runs on a real-speed world | All ran at 100 ms ticks, so timing races (the throw, the wield, the crest) haven't been seen at 600 ms | Status page |
| Phase 11's bots for 15 minutes each | They ran for 12, so that checkbox stays unticked | [BotApiParityDesign.md](BotApiParityDesign.md), status page |
| A refused crossing with another way past, to show the walker routing round it | Waiting for one to be found; the Champions' Guild has none | Status page |
| Revision 225 and 274 live checks | 274's commit records a live run, without the CHAT `rights` or `MESSAGE_PRIVATE` checks its plan asks for. 225's commit records none. Either may have been done and not written down | [RevisionDesign.md](RevisionDesign.md), [Revision274Design.md](Revision274Design.md) |

## Revisions

| Item | State | Source |
|---|---|---|
| Audit content ids on 225 and 274 | Not started. The catalogs and `data/nav` come from 289's content, the catalog-name test runs against the 289 cache only, and no stdlib code reads `game.revision()` | [RevisionDesign.md §15](RevisionDesign.md#15-out-of-scope-and-risks), [Revision274Design.md §12](Revision274Design.md#12-out-of-scope-and-risks) |
| Download 225 maps over the wire | Optional phase 6. `DATA_*` packets are consumed and dropped, and stale squares only warn. `// TODO` at [SceneDecoder.cpp:135](../../src/Game/Decode/SceneDecoder.cpp#L135) | RevisionDesign §9.1 |
| A different revision per account | Would need one cache per revision in `Application` | RevisionDesign §15 |

## Deferred until needed

These wait on a trigger, and nothing is wrong today.

| Item | Trigger | Source |
|---|---|---|
| Replace the byte swap with `std::byteswap` | Moving to C++23; the build is on C++20. `// TODO` at [Endian.hpp:13](../../src/Utils/Endian.hpp#L13) | Code |
| A log file sink | The client running unattended | [LoggerDesign.md](LoggerDesign.md) |
| An IPv6 literal as `server.host` | A server needing one | [TransportDesign.md](TransportDesign.md) |
| A limit on the send queue | A stalled server becoming a problem | [TransportDesign.md](TransportDesign.md) |
| A JSON Schema for the config | The file growing | [ConfigDesign.md](ConfigDesign.md) |
| More walker data fixes for this engine | Each new quest route that needs one | Status page |

## Cosmetic

From the status page, all left as they are:

- `trail complete` is logged twice at a trail's end.
- GnomeMagicChopper's "Chopped" count stays 0, as rs2b0t counts it.
- JiveKBD's default Fire Strike kills nothing in 30 minutes. The bot runs and banks; this is a settings matter, as in rs2b0t.

## Out-of-date notes

These read as open but aren't, so they should be corrected or removed:

| Where | Why it's out of date |
|---|---|
| README TODO: "Phase 17 and 18" | Phase 17 is finished; only 18 is left |
| [tcp-protocol-289.md](tcp-protocol-289.md), "Known Gap" | It describes a `headless-client` protocol file that's no longer here. This client decodes `OBJ_ADD` |
| [BotApiParityDesign.md](BotApiParityDesign.md), 16a "Still open": empty ground spawns | Fixed in 17c, when `wait_if_missing` began to wait |

## What this doesn't cover

- The search covered GitHub, `TODO`, `FIXME`, `HACK`, `XXX`, `BUG` and `TBD` in tracked files, and open-item wording and unticked boxes in the docs. It wasn't a code review, so it won't list bugs nobody has written down.
- Design docs' "Not included" lists also name ideas that aren't marked as wanted, such as SOCKS4 and proxy chains. Only the ones marked `TODO` are listed here.
- The 13 quests' "stage N is not implemented" lines aren't missing work. They're the fallback for stage numbers that a quest's decision table doesn't name.
- The unticked boxes in BotApiParityDesign's sub-phase template and CONVENTIONS' new-project checklist are templates, not tasks.
