# Bot API Parity: Status

Where [BotApiParityDesign.md](BotApiParityDesign.md)'s plan stands. Each phase's "As built" section there has the detail; this page retains the implementation summary and validation history.

**Reviewed 2026-11-05:** all phases are implemented. The export audit against pinned upstream `8b7db422`
reports nothing missing. Remaining work is the follow-ups below, rather than an unfinished parity phase.
The latest saved coverage report has 76,822 / 78,503 executable lines covered (97.86%), with all 436 files
meeting the 95% floor; see [ScriptCoverageBacklog.md](ScriptCoverageBacklog.md) for scope and findings.

The [2026-11-04 upstream review](Rs2b0tUpstreamReview.md) records the selective port of newer commits from `32d52004` through `8b7db422`, including the completed quest and 2026-11-05 non-quest feature follow-ups, settings migrations and remaining live timing checks. It does not replace the original parity baseline; phase 18 is implemented and validated separately below.

## Phases

| Phase | What | State |
|---|---|---|
| 10 | Tooling (`coverage.py`, `ts2py.ts`, `lint.py`), runtime (Global settings, saving, pause, `ScriptActivity`), the public API's remainder | Done |
| 11 | The modules bots share, and 41 bots | Done, with the open items below |
| 12 | The walker's remainder: jewellery teleports, banking for a route, quest locks, the essence mine's session; EssMiner | Done |
| 13 | The economy: shops, mules, bank sorting, the market; 9 bots, and GatheringBot's mule hand-offs and feather buyout | Done |
| 14 | Combat: the gear lists, `rs2004.hunting`, `duel`; 13 fighters | Done, with the open items below |
| 15 | The clue engine and ClueSolver, wired into the seven bots that carry clues | Done, with the open items below |
| 16 | The quest engine and the free-to-play quests, in sub-phases 16a–16c ([BotApiParityQuestPhases.md](BotApiParityQuestPhases.md)) | 16a done (the engine, seven quests, AIOQuester), with the open items below; 16b done (nine more quests, garlic and Karamja fare recovery); 16c done (paired Arrav, Dragon Slayer, supplier, barcrawl and the fresh-account eighteen-quest queue) |
| 17 | The members' quests, in sub-phases 17a–17i | 17a done: all twelve quests completed in one live queue, and both gatherers banked full loads; 17b done: all nine quests completed in one live queue; 17c done: all five quests completed in one live queue, and ClimbingBoots ran live; 17d done: all four quests completed in one live queue; 17e done: all four quests completed in one live queue; 17f done: all five quests completed in one live queue; 17g done: two partners finished Hero's Quest and one queue finished the other two; 17h done: Underground Pass and Regicide completed in one live queue; 17i done: Legends Quest completed in one live queue, and ClueSolver finished a trail from the Kharazi Jungle and one from Isafdar |
| 18 | The account leveler | Done: tests and full export audit pass; two active hours on one fresh account across multiple child methods, in three measured sessions (see design for limits) |

## What's in place

- **Bots:** scripts in `scripts/bots/`, one entry per rs2b0t bot, listed in [scripting/README.md](../scripting/catalogs.md#ported-bots). GatheringBot is the package `scripts/bots/gathering/`, with `miner.py`, `woodcutter.py` and `fisher.py` as its entries.
- **Tests:** the latest feature validation records 809 registered CTest cases, plus the stdlib's Python specs in `tests/Stdlib/`, including rs2b0t ports in `tests/Stdlib/rs2b0t/` on `spec.py`'s describe/test/expect. The quest engine's and the quests' specs are in `quests/`. Those reading the walker's data (`nav/`) run with the real cache (`RS2004_CACHE_DIR`). One file runs alone with `Rs2004HeadlessTests "rs2b0t's ported Python tests pass" -c <file>`.
- **Live checks:** every phase 11 bot has run against the local 289 engine without a script error, and each that banks has banked. Phase 12's: a glory Varrock to Draynor, Lumbridge to Karamja with no coins (it banks for the toll and fare), a quest-locked door left out of the route, EssMiner, and WildyAgility past its old stall. Phase 13's: BankSorter on a shuffled 200-item bank in insert mode, ShopBuyout buying Aubury's stock down and again after the restock, FlaxRunner's 8 hand-offs, Fisher's mule hand-off at Catherby, and MarketMaker selling iron ore and buying logs from a customer script over public chat. Phase 14's: every fighter for 30 minutes through a bank trip, JiveDragons at Taverley by range and under the shield and at Brimhaven under antifire and the shield, a range safespot never hit in 30 minutes, DuelArena's 14 duels between two accounts, and JiveKQ's four accounts killing the Kalphite Queen. Phase 15's: ClueSolver finishing easy, medium and hard trails, a hard one with a puzzle box and a dig guardian in one session, and one through the Duel Arena's pens beside a DuelArena clue helper. Phase 16a's: AIOQuester taking a fresh account through all seven of its quests in one queue, resuming a quest after the client was ended mid-way, and skipping a quest it couldn't start with its reasons. Phase 16b's: all sixteen then-implemented quests on one fresh account. Phase 16c's: both Arrav partners completed, four supplier certificates banked, all ten barcrawl signatures, and a fresh account completing all eighteen quests for 39 quest points, with one automatically recovered death against Elvarg and development restarts to install fixes. Phase 17a's: all twelve short members' quests in one queue, and full loads from FlourCollector and RoguesPurse. Phase 17b's: all nine mid-length members' quests in one queue, with one automatically recovered death against Bouncer and development restarts to install fixes. Phase 17c's: all five quests in one queue, with three recovered deaths before the walker's route upkeep and door fixes, and ClimbingBoots buying and banking 224 boots. Phase 17d's: all four Morytania and Karamja quests in one queue, without a death, with development restarts to install Nature Spirit's skill gates and melee kit and the walker's way out of Bervirius' tomb. Phase 17f's: all five quests in one queue, with one recovered death each to Chronozon and the Dagannoth mother, and development restarts to install fixes. Phase 17g's: two partner accounts through Hero's Quest, then Temple of Ikov and The Fremennik Trials in one queue, with development restarts to install fixes, Prayer and Ranged raised to 70 during the run, and the second partner given the rune kit Scavvo had sold out of. Phase 17h's: Underground Pass and Regicide in one uninterrupted queue on a fresh account, without a death, with skills at 70. Phase 17i's: Legends Quest in one uninterrupted queue on a fresh account, without a death, with skills at 70, and ClueSolver finishing a trail from a Kharazi dig and, across restarts for sharks and a fix, one from an Isafdar dig.

## Open items

Remaining work is tracked in [GitHub issues](OpenWork.md), including live acceptance gaps,
trigger-based observations and optional improvements. That index links each migrated task;
issue bodies include scope, acceptance criteria and commit-pinned historical context.
The facade scenario audit is tracked in [#30](https://github.com/ineedbots/lc-headless/issues/30).

## Working on it

- **Porting a module:** draft with `bun tools/port/ts2py.ts ../rs2b0t <file.ts> --stdlib`, finish by hand, then `python -I tools/port/lint.py src/Script/Stdlib scripts tests/Stdlib` and `python -I tools/port/coverage.py ../rs2b0t <module>`.
- **pocketpy's limits** are in [scripting/README.md](../scripting/python-dialect.md#the-python-dialect); `lint.py` checks the ones that bite silently. The worst: a parameter without a default can't be passed by keyword, and a method set on an instance does nothing.
- **Live tests** run against `289server/engine` (`npx tsx src/app.ts`) from a scratch client config and accounts folder, never the user's `accounts/`. A harness bot sets stats and stock with the engine's cheats, then runs the bot under test as a `ScriptActivity`.


## Parity findings follow-up (2026-11-05)

The linter now rejects literal `None` membership in statically known sets (including local aliases and
set comprehensions), and follows conditional generator returns and imported wrapper chains. It conservatively
leaves unknown values, imported collections and shadowed `set` names alone; it is not an optional-value type
checker. Its regression tests run in CI alongside the port export collector tests.

Grand Tree journal reads retain the newest cached stage when an older page is recognized. A quest-list
`not_started` result still resets that floor. Tourist Trap's two unreachable `leave_camp` branches were removed;
recovery tests exercise both camp floors at both affected stages through `safe_recovery_route`.

Runtime facade ports now cover bank-chest/id/transfer, open-window and reopened `StableClosedPoll`,
JiveMarketDumper access selection, MarketMaker task outcomes, Shilo supply-trip interruption/retry and native
WordPack round trips of market replies. The bank scenarios exposed unsafe delegation after a chest failed to
open: access now retries three times and returns failure without using an unavailable bank action. Active Shilo
supply trips now keep gathering suspended while banking is retried.

The new JiveDragons runtime fixture covers ownership and kill settlement, scene rebuilds, movement rechecks,
loot order/capacity, food reclaim/retry budgets, bounded pickup failure, network targeting, adaptive stands, ammo acknowledgement and bank-only shield preparation. KQ runtime
ports cover food/equipment/prayer acknowledgement, same-tick combat inputs, valuable and arrow loot, entry gates,
upkeep, route interactions, search/pull, teammate gear recovery and death restocking. KQ sends special-attack toggles without delaying the next attack,
and a pending combat eat reserves its future loot slot before another food or vial is discarded. The remaining
scenario audit is tracked in [#30](https://github.com/ineedbots/lc-headless/issues/30); these additions
do not claim a complete one-for-one port of both bot suites.

Validation: Windows Debug and cache-backed Release each pass all 810 registered tests. The default Debug run
skips 27 cache-dependent tests; Release uses the 225, 274 and 289 caches. The full traced Debug run also passes
(76,822 / 78,503 lines, 97.86%; all 436 files above 95%). Later dragon/KQ scenario additions pass focused Debug
and Release runs. Full dialect lint is clean, the 11 port-tool unit tests pass, C++ formatting passes, and the
export audit against pinned `8b7db422` reports nothing missing. Live behavior was not remeasured in this follow-up.
