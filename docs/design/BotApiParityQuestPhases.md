# Bot API Parity: the quest phases

[BotApiParityDesign.md](BotApiParityDesign.md) §10 and §11 plan phases 16 and 17: the quest engine and all 63 of rs2b0t's quests. Together they're about 75,000 lines of rs2b0t, against phase 15's 3,900. This file splits them into sub-phases, each small enough to port, test and run live before the next one starts. The design doc's decisions still hold: `rs2004.quests` is a stdlib package, each quest is `rs2004/quests/defs/<id>.py` or a package of that name, and `decide(snap)` stays a pure function of the snapshot.

Sizes were measured at rs2b0t `4417d0b7` (2026-10-23), in lines of TypeScript. As with every phase, each sub-phase starts by measuring again at rs2b0t's tip.

---

## 1. Order

| Sub-phase | What | rs2b0t lines, bots included | Bots |
|---|---|---|---|
| 16a | The engine, and seven short free-to-play quests | ≈4,600 | AIOQuester |
| 16b | Nine more free-to-play quests | ≈5,600 | |
| 16c | Shield of Arrav, Dragon Slayer and the barcrawl; then all 18 free-to-play quests in one queue | ≈3,900 | ArravSupplier, Barcrawl |
| 17a | Short members' quests with no members' prerequisites, and Jungle Potion | ≈6,650 | FlourCollector, RoguesPurse |
| 17b | Mid-length members' quests: Merlin's Crystal, Lost City, Waterfall and others | ≈7,700 | |
| 17c | Plague City and Biohazard; Death Plateau, Troll Stronghold and Eadgar's Ruse | ≈6,900 | |
| 17d | Morytania and Karamja: Nature Spirit, Shades of Mortton, Tai Bwo Wannai Trio, Shilo Village | ≈6,400 | |
| 17e | The Grand Tree, Big Chompy Bird Hunting, Watch Tower, The Tourist Trap | ≈7,300 | |
| 17f | Elemental Workshop, Digsite, Holy Grail, Family Crest, Horror from the Deep | ≈8,000 | |
| 17g | Hero's Quest, Temple of Ikov, The Fremennik Trials | ≈6,700 | |
| 17h | Underground Pass and Regicide | ≈6,800 | |
| 17i | Legends' Quest, and the clue walks into the Kharazi Jungle and across Isafdar | ≈5,000 | |

Each sub-phase only needs quests from earlier ones. The members' quests' prerequisites (from rs2b0t's `data/quests.ts`):
- Jungle Potion needs Druidic Ritual, which 17a also has.
- Biohazard needs Plague City.
- Troll Stronghold needs Death Plateau; Eadgar's Ruse needs Druidic Ritual and Troll Stronghold.
- Nature Spirit needs The Restless Ghost and Priest in Peril, and Shades of Mortton needs Priest in Peril.
- Tai Bwo Wannai Trio and Shilo Village need Jungle Potion.
- Holy Grail needs Merlin's Crystal.
- Hero's Quest needs 55 quest points, Lost City, Dragon Slayer, Merlin's Crystal and Shield of Arrav.
- Underground Pass needs Biohazard, and Regicide needs Underground Pass.
- Legends' Quest needs Hero's Quest, Family Crest, Shilo Village, Underground Pass and Waterfall Quest.

This replaces the design doc's three batches (17a to 17c there), which put 26, 15 and 4 quests in a batch.

---

## 2. What every sub-phase does

- **Read before porting.** rs2b0t's `docs/decisions/quest-pitfalls-*.md` (38 files, plus `-engine` and `-habits`) and `docs/reference/quest-harness-recipes-*.md` for each quest in it. The pitfalls are what broke the quest live; the recipes are how rs2b0t set up an account to test it.
- **Port** with `ts2py.ts`, then by hand for pocketpy's dialect. A quest's tests in `test/api/ai/quests/defs/` port beside it into `tests/Stdlib/rs2b0t/quests/`, and those that read the walker's data into `nav/`.
- **Generated data.** `data/quests.ts`'s records are generated in 16a. A sub-phase that adds a quest checks every item, NPC and loc name its module uses against the cache, as the real-cache tests do now.
- **Live.** Against the local engine, AIOQuester runs the sub-phase's quests in one queue, on a scratch account (see the memory on live testing):
    - prerequisites done with `~cq`, then a second login, since `~cq` only reads complete on the next one;
    - skills set by `setstat` to each quest's requirement, not above it, so a missed skill check shows;
    - `~cq` leaves some sub-stage varbits unset, as phase 15 found with Watchtower's market. One that a quest reads is set with `setvar` and recorded under the sub-phase's "As built" in the design doc.

  A quest that parks gives its reason. It's fixed, or recorded with that reason in the design doc.
- **Docs and stubs.** `scripts/typings/rs2004/quests/`, `docs/scripting/quests.md`, scripting/python-dialect.md's porting table and BotApiParityStatus.md, with each sub-phase.

---

## 3. Phase 16a: the engine

`exec/primitives.ts`, `exec/prompts.ts` and `prayer.ts` already came with phase 15, since the clue engine imports them. The rest of the engine:

| Part | rs2b0t | Lines |
|---|---|---|
| The engine | `engine/`: `QuestEngine.ts`, `queue.ts`, `provisioning.ts`, `watchdog.ts`, `trace.ts`, `types.ts`; and the root's `types.ts` | 1,310 |
| Execution | `exec/steps.ts`, `legs.ts`, `wool.ts` | 550 |
| Requirements | `EligibilityEvaluator.ts`, `RequirementChecker.ts`, `ItemChecker.ts`, `data/quests.ts` (generated) | 760 |
| Kit | `gear.ts`, `armour.ts`, `weapons.ts`, `food.ts`, `strike.ts`, `strikeCombat.ts`, `journalText.ts` | 350 |
| The quest list | `defs/index.ts`: every quest's entry, each module loaded the first time the queue needs it | 90 |

The quests, the shortest free-to-play ones, chosen to cover each kind of step without a quest boss:

> Cook's Assistant, Sheep Shearer (with `wool.ts`), Rune Mysteries, The Restless Ghost, Witch's Potion, Black Knights' Fortress, Romeo & Juliet

**AIOQuester** (617 lines): its queue, food, prayer and settings. Its settings for Shield of Arrav's gang, Hero's Quest's partner and Legends' reward come with those quests (16c, 17g, 17i); until then they aren't offered.

**Tests.**
- `test/api/ai/quests/engine/` (11 files), `exec/` less what phase 15 ported, and the root's: `data`, `eligibility-evaluator`, `requirement-checker`, `item-checker`, `armour`, `questWeapons`, `questPrayer`, `strike*`, `quest-banks`, `quest-gather`, `driveDialogGap`.
- The seven quests' tests.
- `test/scripts/AIOQuester/` less `arravSettings` (16c) and the paint test.
- The clue engine's `hard-tier` test, which phase 15 left for the quest list.

- **Done when:**
    - [x] Those tests are ported and pass, less the cases that wait for later quests (see the design doc's "As built: 16a").
    - [x] Live, AIOQuester takes a fresh account off Tutorial Island through all seven quests in one queue. Black Knights' Fortress needs 12 quest points, which the other six don't make, so two came from Doric's Quest and Imp Catcher set complete by varp. It also took fixes to the walker's data and combat stats for its banquet hall.
    - [x] Stopped mid-quest by ending the client, and started again, it picks the quest up where it stopped.
    - [x] A quest whose requirement isn't met is skipped with its reason, and the queue goes on.

---

## 4. Phase 16b: nine more free-to-play quests

> Demon Slayer, Doric's Quest, Imp Catcher, Goblin Diplomacy, Vampire Slayer (with `exec/garlic.ts`), The Knight's Sword, Ernest the Chicken, Pirate's Treasure, Prince Ali Rescue

These bring the first fights (Delrith, Count Draynor), the first items gathered across the map, and Karamja's boat. Pirate's Treasure's `karamja.ts` also lets phase 11's `karamjaRecovery` test port.

- **Done when:**
    - [x] Their tests are ported and pass, and `karamjaRecovery`'s.
    - [x] Live, AIOQuester finishes all nine in one queue, on an account with 16a's quests done.

---

## 5. Phase 16c: Shield of Arrav, Dragon Slayer and the barcrawl

| Part | rs2b0t | Lines |
|---|---|---|
| Shield of Arrav | `defs/shieldofarrav/` | 1,256 |
| Dragon Slayer | `defs/dragonslayer/` | 1,948 |
| The barcrawl | `barcrawl/` | 326 |

- **Shield of Arrav** needs two accounts, one in each gang, who trade their halves of the shield (`partner.ts`). AIOQuester gains the gang and partner settings.
- **Dragon Slayer** has its own tests at the root: `dragonslayerDecide`, `Journal`, `Maze`, `MazeRun` and `Supplies`.
- **The barcrawl** comes now because Scorpion Catcher (17b) and Horror from the Deep (17f) need the card.

**Bots:** ArravSupplier (296 lines), built on Shield of Arrav's gang legs and hand-off, and Barcrawl (90).

**Tests:** the three parts', `arravSettings`, and the walker's `shieldOfArravTiles`.

- **Done when:**
    - [x] Those tests are ported and pass.
    - [x] Live, two accounts finish Shield of Arrav as partners, one in each gang, and an account finishes Dragon Slayer.
    - [x] ArravSupplier banks a certificate from both gangs, and Barcrawl gets a card signed at every bar.
    - [x] AIOQuester takes a fresh account off Tutorial Island through all 18 free-to-play quests in one queue, with skills set by debugproc. This was phase 16's live check in the design doc.

---

## 6. Phase 17a: short members' quests

> Druidic Ritual, Gertrude's Cat, Monk's Friend, Witch's House, Fishing Contest, Clock Tower, Hazeel Cult, Murder Mystery, Priest in Peril, Tribal Totem, Sea Slug Quest, Jungle Potion

None needs a members' quest except Jungle Potion, which needs Druidic Ritual from this batch.

**Bots:** FlourCollector (88 lines), which imports Murder Mystery's areas, and RoguesPurse (445), which imports Jungle Potion's stages.

All twelve quest modules and both bots are implemented, with lazy queue registration, upstream tests, runtime integration checks, cache checks and stubs. Live verification is in progress. See the design doc's "As built: 17a" for the current scope.

- **Done when:**
    - [x] Their tests are ported and pass, and RoguesPurse's.
    - [ ] Live, AIOQuester finishes all twelve in one queue.
    - [ ] FlourCollector and RoguesPurse each bank a load.

---

## 7. Phase 17b: mid-length members' quests

> Sheep Herder, Tree Gnome Village, Waterfall Quest, Scorpion Catcher, Dwarf Cannon, Observatory Quest, Fight Arena, Merlin's Crystal, Lost City

They bring Fight Arena's fights, Lost City's tree spirit (`lostcityCombat.ts`), and Zanaris.

- **Done when:**
    - [ ] Their tests are ported and pass.
    - [ ] Live, AIOQuester finishes all nine in one queue.

---

## 8. Phase 17c: Plague City and Biohazard; the trolls

> Plague City, Biohazard, Death Plateau, Troll Stronghold, Eadgar's Ruse

Two chains: Plague City then Biohazard in West Ardougne, and Death Plateau, Troll Stronghold and Eadgar's Ruse in the mountains.

**Tests:** the quests', and the walker's `script-travel-corpus`, which reads Troll Stronghold's areas.

- **Done when:**
    - [ ] Those tests are ported and pass.
    - [ ] Live, AIOQuester finishes all five in one queue.
    - [ ] ClimbingBoots runs live, on an account with Death Plateau done (an open item since phase 13).

---

## 9. Phase 17d: Morytania and Karamja

> Nature Spirit, Shades of Mortton, Tai Bwo Wannai Trio, Shilo Village

Morytania's first two, then Karamja's jungle after Jungle Potion. rs2b0t's `shilo-gear-lifecycle` engine test, which needs Shilo Village's module, ports here.

- **Done when:**
    - [ ] Their tests are ported and pass, and `shilo-gear-lifecycle`'s.
    - [ ] Live, AIOQuester finishes all four in one queue.

---

## 10. Phase 17e: the gnomes, the ogres and the desert

> The Grand Tree, Big Chompy Bird Hunting, Watch Tower, The Tourist Trap (with `exec/fundCoins.ts`)

Each is long and keeps to one region. Watch Tower is the quest whose market stage `~cq` left unset in phase 15; an account that does it here needs no `setvar`.

- **Done when:**
    - [ ] Their tests are ported and pass.
    - [ ] Live, AIOQuester finishes all four in one queue.

---

## 11. Phase 17f: Elemental Workshop to Horror from the Deep

> Elemental Workshop, Digsite Quest, Holy Grail, Family Crest, Horror from the Deep

Each has puzzles or machinery of its own, and Holy Grail, Family Crest and Horror from the Deep end in a boss fight.

- **Done when:**
    - [ ] Their tests are ported and pass.
    - [ ] Live, AIOQuester finishes all five in one queue.

---

## 12. Phase 17g: Hero's Quest, Temple of Ikov and the Fremennik Trials

> Hero's Quest, Temple of Ikov, The Fremennik Trials

- **Hero's Quest** needs two accounts, one of each gang, as Shield of Arrav did: `partner.ts` again. AIOQuester gains its partner setting.
- **Temple of Ikov** brings the walker's `ikovTiles` test.

- **Done when:**
    - [ ] Their tests are ported and pass, and `ikovTiles`'s.
    - [ ] Live, two partner accounts finish Hero's Quest, and AIOQuester finishes the other two in one queue.

---

## 13. Phase 17h: Underground Pass and Regicide

| Quest | rs2b0t | Lines | Its root tests |
|---|---|---|---|
| Underground Pass | `defs/upass/` (21 files) | 4,494 | `upass*`, 13 files |
| Regicide | `defs/regicide/` (11 files) | 2,304 | `regicide*`, 5 files |

The longest two after Legends'. Regicide's `seams.ts` and `pockets.ts` are the Isafdar crossings the clue engine's walk across Tirannwn uses; 17i wires them in.

- **Done when:**
    - [ ] Those tests are ported and pass.
    - [ ] Live, AIOQuester finishes Underground Pass and then Regicide in one queue.

---

## 14. Phase 17i: Legends' Quest, and the clue walks

`defs/legends/` (15 files, 4,959 lines), the longest quest, needing all of 17d, 17f, 17g and 17h. AIOQuester gains its reward setting.

**The clue walks.** Phase 15 left `walk_across_kharazi` and `walk_across_tirannwn` failing with a log line. With Legends' `jungle.ts` and `areas.ts`, and Regicide's pockets and seams:
- `walk_across_kharazi` uses `enter_jungle` and `leave_jungle`, as rs2b0t's `kharaziTravel.ts` does;
- `walk_across_tirannwn` uses `travel_tirannwn`, as rs2b0t's `tirannwnTravel.ts` does, and `tirannwnStage` comes off coverage.py's not-ported list;
- rs2b0t's `tirannwnTravel` test and the walking parts of `kharaziJungle`'s port.

- **Done when:**
    - [ ] Legends' tests and the clue walks' are ported and pass.
    - [ ] Live, AIOQuester finishes Legends' Quest.
    - [ ] Live, ClueSolver finishes a clue in the Kharazi Jungle and one in Isafdar, on an account with Legends' Quest and Regicide done.
    - [ ] `coverage.py` reports nothing missing in `api/ai/quests`.
