# Bot API Parity: Status

Where [BotApiParityDesign.md](BotApiParityDesign.md)'s plan stands. Each phase's "As built" section there has the detail; this page is the summary and the list of what's still open.

The [2026-11-04 upstream review](Rs2b0tUpstreamReview.md) records the selective port of newer commits from `32d52004` through `8b7db422`, including the remaining feature and quest work. It does not replace the original parity baseline or close phase 18.

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
| 18 | The account leveler | Not started |

## What's in place

- **Bots:** scripts in `scripts/bots/`, one entry per rs2b0t bot, listed in [scripting/README.md](../scripting/catalogs.md#ported-bots). GatheringBot is the package `scripts/bots/gathering/`, with `miner.py`, `woodcutter.py` and `fisher.py` as its entries.
- **Tests:** 800 C++ test cases, the stdlib's Python tests in `tests/Stdlib/`, and about 2,000 of rs2b0t's own tests in `tests/Stdlib/rs2b0t/`, on `spec.py`'s describe/test/expect; the quest engine's and the quests' are in `quests/`. Those reading the walker's data (`nav/`) run with the real cache (`RS2004_CACHE_DIR`). One file runs alone with `Rs2004HeadlessTests "rs2b0t's ported Python tests pass" -c <file>`.
- **Live checks:** every phase 11 bot has run against the local 289 engine without a script error, and each that banks has banked. Phase 12's: a glory Varrock to Draynor, Lumbridge to Karamja with no coins (it banks for the toll and fare), a quest-locked door left out of the route, EssMiner, and WildyAgility past its old stall. Phase 13's: BankSorter on a shuffled 200-item bank in insert mode, ShopBuyout buying Aubury's stock down and again after the restock, FlaxRunner's 8 hand-offs, Fisher's mule hand-off at Catherby, and MarketMaker selling iron ore and buying logs from a customer script over public chat. Phase 14's: every fighter for 30 minutes through a bank trip, JiveDragons at Taverley by range and under the shield and at Brimhaven under antifire and the shield, a range safespot never hit in 30 minutes, DuelArena's 14 duels between two accounts, and JiveKQ's four accounts killing the Kalphite Queen. Phase 15's: ClueSolver finishing easy, medium and hard trails, a hard one with a puzzle box and a dig guardian in one session, and one through the Duel Arena's pens beside a DuelArena clue helper. Phase 16a's: AIOQuester taking a fresh account through all seven of its quests in one queue, resuming a quest after the client was ended mid-way, and skipping a quest it couldn't start with its reasons. Phase 16b's: all sixteen then-implemented quests on one fresh account. Phase 16c's: both Arrav partners completed, four supplier certificates banked, all ten barcrawl signatures, and a fresh account completing all eighteen quests for 39 quest points, with one automatically recovered death against Elvarg and development restarts to install fixes. Phase 17a's: all twelve short members' quests in one queue, and full loads from FlourCollector and RoguesPurse. Phase 17b's: all nine mid-length members' quests in one queue, with one automatically recovered death against Bouncer and development restarts to install fixes. Phase 17c's: all five quests in one queue, with three recovered deaths before the walker's route upkeep and door fixes, and ClimbingBoots buying and banking 224 boots. Phase 17d's: all four Morytania and Karamja quests in one queue, without a death, with development restarts to install Nature Spirit's skill gates and melee kit and the walker's way out of Bervirius' tomb. Phase 17f's: all five quests in one queue, with one recovered death each to Chronozon and the Dagannoth mother, and development restarts to install fixes. Phase 17g's: two partner accounts through Hero's Quest, then Temple of Ikov and The Fremennik Trials in one queue, with development restarts to install fixes, Prayer and Ranged raised to 70 during the run, and the second partner given the rune kit Scavvo had sold out of. Phase 17h's: Underground Pass and Regicide in one uninterrupted queue on a fresh account, without a death, with skills at 70. Phase 17i's: Legends Quest in one uninterrupted queue on a fresh account, without a death, with skills at 70, and ClueSolver finishing a trail from a Kharazi dig and, across restarts for sharks and a fix, one from an Isafdar dig.

## Open items

| Item | Where it goes |
|---|---|
| A refused crossing with another way past, to show the walker routing round it live (the Champions' Guild has none) | When one is found |
| rs2b0t's tests that stub facades with `spyOn` (bank-chest, bank-id, bank-transfer, phase 13's `StableClosedPoll` with a window open, JiveMarketDumper's runtime, MarketMaker's `tasks.test`, the Shilo trip's fixtures): pocketpy ignores a method set on an instance | Needs a fake game state for Python tests, or C++ equivalents |
| JiveKQ: one account stopped on a third restock with "Could not buy a Shantay pass" after buying one each earlier trip; the log doesn't say why | When it recurs, with the shop's state logged |
| JiveKBD's default Fire Strike kills nothing in 30 minutes; the bot runs and banks | A settings matter, as rs2b0t's |
| The rest of JiveDragons' and JiveKQ's tests stub the client with `spyOn` | `spec.py`'s `spy_on` and fakes (phase 15) make them portable; JiveDragons' clue tests are ported |
| `trail complete` logged twice at a trail's end | Cosmetic |
| GnomeMagicChopper's "Chopped" count stays 0, as rs2b0t counts it | Cosmetic; left as rs2b0t's |
| Live runs were 12 minutes, not the plan's 15 | — |
| Black Knights' Fortress re-listens at the grill after a restart (rs2b0t keeps `listened` in memory) | Harmless; a stage oracle would fix it |
| A step failing while the character steps between two tiles never parks, as the tile reads as progress (rs2b0t's watchdog) | When a quest hits it |
| The walker's data needed fixes for this engine at Black Knights' Fortress (`STAIR_FIXES`, `CROSSING_ADDITIONS` in `tools/nav/export_rs2b0t.ts`), Bervirius' tomb and the Elemental Workshop (`EDGE_ADDITIONS`), and the Champions' Guild (`STAIR_FIXES`) | More may turn up with each quest sub-phase |
| Runtime specs for phases 17f's and 17g's game legs, as 17c and 17d have (17e lacks them too; 17g has them only for legs fixed live) | A coverage follow-up, listed in [ScriptCoverageBacklog.md](ScriptCoverageBacklog.md) |
| Scavvo stocks one of each rune piece and doesn't restock, so a second Hero's Quest partner needs the kit banked | When a pair runs it without a harness |
| A wield swap changes the inventory, so the no-progress watchdog can't see a two-step loop (Ikov's melee picker had one) | A rule in the watchdog, when another quest hits it |
| Regicide needs the spade it took through the pass, and no shop near Ardougne sells one, so a death carrying the only one parks it with the reason | When a quest needs a spade source |
| Phase 17h's live runs were all at 100 ms ticks; its timing races (the throw, the wield, the crest) haven't been seen on a 600 ms world | When a run at real speed is due |
| Phase 17i's live runs were at 100 ms ticks too, and Radimus's conversation shuts after the first session for a reason not found; the engine's next attempt carries on | When a run at real speed is due |
| The gilded totem's hand-in lost a minute on one run, in the shape the training had, and recovered on its next attempt | When it costs more |
| A failing teleport cast is offered again for 5 repaths (an account with a spell's quest set by varp shows it) | When a real account hits it |
| A hard Kharazi trail's pack only just fits its kit and 15 sharks, so an extra scroll or gift blocks it, though now with a log line; ClueSolver doesn't dress an account for the Saradomin Wizard | When an account hits it |
| `None in some_set` raises in pocketpy (phase 17i's casket crash); `lint.py` has no rule for it | A rule, or a check of the stdlib's sets |
| A generator returned from a conditional, `return (a(log) if c else b(log))`, isn't flagged by `ts2py.ts` or `lint.py` (Digsite's `talk_to_npc_id` and Ikov's `fetch_ikov_lever` had it) | A rule alongside the generator-call one |

## Working on it

- **Porting a module:** draft with `bun tools/port/ts2py.ts ../rs2b0t <file.ts> --stdlib`, finish by hand, then `python -I tools/port/lint.py src/Script/Stdlib scripts tests/Stdlib` and `python -I tools/port/coverage.py ../rs2b0t <module>`.
- **pocketpy's limits** are in [scripting/README.md](../scripting/python-dialect.md#the-python-dialect); `lint.py` checks the ones that bite silently. The worst: a parameter without a default can't be passed by keyword, and a method set on an instance does nothing.
- **Live tests** run against `289server/engine` (`npx tsx src/app.ts`) from a scratch client config and accounts folder, never the user's `accounts/`. A harness bot sets stats and stock with the engine's cheats, then runs the bot under test as a `ScriptActivity`.
