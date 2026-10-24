# Bot API Parity: Status

Where [BotApiParityDesign.md](BotApiParityDesign.md)'s plan stands. Each phase's "As built" section there has the detail; this page is the summary and the list of what's still open.

## Phases

| Phase | What | State |
|---|---|---|
| 10 | Tooling (`coverage.py`, `ts2py.ts`, `lint.py`), runtime (Global settings, saving, pause, `ScriptActivity`), the public API's remainder | Done |
| 11 | The modules bots share, and 41 bots | Done, with the open items below |
| 12 | The walker's remainder: jewellery teleports, banking for a route, quest locks, the essence mine's session; EssMiner | Done |
| 13 | The economy: shops, mules, bank sorting, the market; 9 bots, and GatheringBot's mule hand-offs and feather buyout | Done |
| 14 | Combat: the gear lists, `rs2004.hunting`, `duel`; 13 fighters | Done, with the open items below |
| 15 | The clue engine and ClueSolver, wired into the seven bots that carry clues | Done, with the open items below |
| 16 | The quest engine and the free-to-play quests, in sub-phases 16a–16c ([BotApiParityQuestPhases.md](BotApiParityQuestPhases.md)) | Not started |
| 17 | The members' quests, in sub-phases 17a–17i | Not started |
| 18 | The account leveler | Not started |

## What's in place

- **Bots:** 68 files in `scripts/bots/`, one per rs2b0t bot, listed in [ScriptingApi.md](ScriptingApi.md#catalogs-and-behaviours). GatheringBot is the package `scripts/bots/gathering/`, with `miner.py`, `woodcutter.py` and `fisher.py` as its entries.
- **Tests:** 495 C++ test cases, the stdlib's Python tests in `tests/Stdlib/`, and 1,718 of rs2b0t's own tests in `tests/Stdlib/rs2b0t/`, on `spec.py`'s describe/test/expect. Those reading the walker's data (`nav/`) run with the real cache (`RS2004_CACHE_DIR`).
- **Live checks:** every phase 11 bot but ClimbingBoots has run against the local 289 engine without a script error, and each that banks has banked. Phase 12's: a glory Varrock to Draynor, Lumbridge to Karamja with no coins (it banks for the toll and fare), a quest-locked door left out of the route, EssMiner, and WildyAgility past its old stall. Phase 13's: BankSorter on a shuffled 200-item bank in insert mode, ShopBuyout buying Aubury's stock down and again after the restock, FlaxRunner's 8 hand-offs, Fisher's mule hand-off at Catherby, and MarketMaker selling iron ore and buying logs from a customer script over public chat. Phase 14's: every fighter for 30 minutes through a bank trip, JiveDragons at Taverley by range and under the shield and at Brimhaven under antifire and the shield, a range safespot never hit in 30 minutes, DuelArena's 14 duels between two accounts, and JiveKQ's four accounts killing the Kalphite Queen. Phase 15's: ClueSolver finishing easy, medium and hard trails, a hard one with a puzzle box and a dig guardian in one session, and one through the Duel Arena's pens beside a DuelArena clue helper.

## Open items

| Item | Where it goes |
|---|---|
| `karamjaRecovery.ts`: `missing_boat_fare`, `recover_boat_fare` (needs Pirate's Treasure's quest steps) | Phase 16 |
| A refused crossing with another way past, to show the walker routing round it live (the Champions' Guild has none) | When one is found |
| rs2b0t's tests that stub facades with `spyOn` (bank-chest, bank-id, bank-transfer, phase 13's `StableClosedPoll` with a window open, JiveMarketDumper's runtime, MarketMaker's `tasks.test`, the Shilo trip's fixtures): pocketpy ignores a method set on an instance | Needs a fake game state for Python tests, or C++ equivalents |
| JiveKQ: one account stopped on a third restock with "Could not buy a Shantay pass" after buying one each earlier trip; the log doesn't say why | When it recurs, with the shop's state logged |
| JiveKBD's default Fire Strike kills nothing in 30 minutes; the bot runs and banks | A settings matter, as rs2b0t's |
| The rest of JiveDragons' and JiveKQ's tests stub the client with `spyOn` | `spec.py`'s `spy_on` and fakes (phase 15) make them portable; JiveDragons' clue tests are ported |
| The walk into the Kharazi Jungle and across Isafdar, and rs2b0t's tirannwnTravel tests | Phase 17 (Legends' Quest's jungle code, Regicide's seams) |
| `trail complete` logged twice at a trail's end | Cosmetic |
| GnomeMagicChopper's "Chopped" count stays 0, as rs2b0t counts it | Cosmetic; left as rs2b0t's |
| ClimbingBoots not run live: needs Death Plateau | When a quested account exists (phase 17's quests) |
| Live runs were 12 minutes, not the plan's 15 | — |

## Working on it

- **Porting a module:** draft with `bun tools/port/ts2py.ts ../rs2b0t <file.ts> --stdlib`, finish by hand, then `python -I tools/port/lint.py src/Script/Stdlib scripts tests/Stdlib` and `python -I tools/port/coverage.py ../rs2b0t <module>`.
- **pocketpy's limits** are in [ScriptingApi.md](ScriptingApi.md#python-dialect); `lint.py` checks the ones that bite silently. The worst: a parameter without a default can't be passed by keyword, and a method set on an instance does nothing.
- **Live tests** run against `289server/engine` (`npx tsx src/app.ts`) from a scratch client config and accounts folder, never the user's `accounts/`. A harness bot sets stats and stock with the engine's cheats, then runs the bot under test as a `ScriptActivity`.
