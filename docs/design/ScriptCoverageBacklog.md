# Script coverage backlog

What's left to test in the embedded stdlib, `src/Script/Stdlib/`, for anyone adding coverage. Script tests live in
`tests/Stdlib/`, and [Building.md](../Building.md#stdlib-script-coverage) describes the report these figures come from.
The figures are a snapshot: rerun the report rather than trusting them once tests have moved on.

**Snapshot:** 66,236 of 77,165 lines (85.84%), with 10,929 missed across 291 of 432 files.
Taken on Windows with no game caches, so the real-cache tests were skipped. Scripts under `scripts/` aren't measured.

| Area | Missed lines |
|---|---:|
| Quest legs, `quests/defs/` | 10,384 |
| Everything else, in [Shared code](#shared-code) | 545 |

Almost all of it is quest legs: `decide()` and the journal parsers are ported with rs2b0t's own tests, while the legs
that act on the game aren't. Each quest's legs need a runtime spec against fake facades.

## Writing a runtime spec

1. Put it in `tests/Stdlib/rs2b0t/quests/test_<quest>_<area>_runtime.py`. New files are picked up without a rebuild.
2. Build the world from `Scene` in `tests/Stdlib/rs2b0t/spec.py`, which fakes the pack, worn items, locs, NPCs, ground
   items, messages, chat, walking and the clock. A failed `delay_until` costs its whole timeout, so a leg's own deadlines
   expire as they do live.
3. Take each leg through its success and each of its failures, asserting on the outcome rather than only running the
   lines. `test_touristtrap_legs_runtime.py` and `test_legends_trials_runtime.py` are the models to follow.
4. Run the spec alone, then lint it:

   ```sh
   build/windows-script-coverage/Debug/Rs2004HeadlessTests.exe "rs2b0t's ported Python tests pass" -c test_<name>.py
   python -I tools/port/lint.py tests/Stdlib/rs2b0t/quests/test_<name>.py
   ```

To see one spec's coverage without a full run, set `RS2004_SCRIPT_COVERAGE_DIR` to an empty folder for that command, and
compare the JSON profiles it writes with `build/windows-script-coverage/script-coverage/manifest.json`.

Two pocketpy traps catch these specs:

- A closure captures an enclosing local when it's defined. A sibling function defined later is a `NameError`, and
  rebinding a local afterwards isn't seen, so define callees first and build effects in a helper for each object.
- Default arguments must be literals, so `stage=STAGE.STARTED` won't load.

## Known findings

Coverage work should report these rather than pin them in a test.

| Where | Finding |
|---|---|
| `grandtree/journal.py`, `read_grand_tree_stage` | A recognized older page returns its parsed stage even when `last_stage` holds a newer one. The cache stays ahead, but the returned stage can temporarily regress; an unreadable page then returns the newer cached stage again. |
| `holygrail/legs.py`, `ring_bell` | `RING_STAND` is 2 tiles from `CASTLE_LANDING` and the landing check allows 2, so 6 of the 9 tiles the walk can stop on pass before any teleport. The leg can log that it's inside, and set `inside_castle`, when it isn't. The spec tests from a tile where the check still tells the two apart. |
| `touristtrap.py`, lines 2448 and 2484 | `leave_camp` here looks unreachable, since `safe_recovery_route` has already answered for both camp areas. |

Some of what remains can't be reached by a test at all. `elementalworkshop/workshop.py` lines 129–130 and 657 are guards
on states the lines before them rule out, so 100% isn't the goal for every file.

## Quest legs

Largest gaps first. "Runtime spec" is any existing `*runtime*` spec naming the quest, which is the place to extend; some
of those cover a single fix or a part of the quest. Files missing fewer than 10 lines are listed together under each quest.

### Summary

| Quest | Missed | Covered | Runtime spec |
|---|---:|---:|---|
| [upass](#upass) | 1,626 | 51.5% | `upass_runtime` |
| [legends](#legends) | 1,274 | 62.9% | `legends_runtime`, `legends_trials_runtime` |
| [ikov](#ikov) | 930 | 45.2% | `ikov_runtime` |
| [watchtower](#watchtower) | 871 | 47.8% | none |
| [heroquest](#heroquest) | 719 | 54.0% | `heroquest_runtime` |
| [regicide](#regicide) | 670 | 60.7% | `regicide_runtime` |
| [digsite](#digsite) | 627 | 52.7% | none |
| [fremenniktrials](#fremenniktrials) | 551 | 61.1% | none |
| [horror](#horror) | 519 | 56.9% | none |
| [familycrest](#familycrest) | 514 | 56.5% | `familycrest_chronozon_runtime` |
| [chompybird](#chompybird) | 513 | 51.2% | none |
| [witchshouse](#witchshouse) | 163 | 78.2% | `witchshouse_runtime` |
| [hazeelcult](#hazeelcult) | 148 | 58.9% | none |
| [druidicritual](#druidicritual) | 96 | 65.2% | `druidicritual_and_monksfriend_runtime` |
| [elementalworkshop](#elementalworkshop) | 91 | 90.8% | `elementalworkshop_workshop_runtime` |
| [monksfriend](#monksfriend) | 87 | 62.7% | `druidicritual_and_monksfriend_runtime` |
| [fishingcontest](#fishingcontest) | 78 | 81.2% | `fishingcontest_runtime` |
| [seaslug](#seaslug) | 68 | 82.0% | `seaslug_runtime` |
| [deathplateau](#deathplateau) | 67 | 94.5% | `deathplateau_runtime` |
| [dragonslayer](#dragonslayer) | 65 | 96.3% | none |
| [treegnome](#treegnome) | 64 | 90.4% | `treegnome_runtime` |
| [waterfall](#waterfall) | 61 | 94.7% | `waterfall_runtime` |
| [fightarena](#fightarena) | 57 | 91.6% | `fightarena_runtime` |
| [junglepotion](#junglepotion) | 55 | 79.3% | none |
| [observatory](#observatory) | 39 | 92.8% | `observatory_runtime` |
| [lostcity](#lostcity) | 30 | 94.0% | `lostcity_runtime` |
| [murder](#murder) | 26 | 94.2% | `murder_runtime` |
| [sheepherder](#sheepherder) | 26 | 95.7% | `sheepherder_runtime` |
| [goblindiplomacy](#goblindiplomacy) | 25 | 95.4% | none |
| [holygrail](#holygrail) | 24 | 96.4% | `holygrail_legs_runtime` |
| [scorpcatcher](#scorpcatcher) | 24 | 96.1% | `scorpcatcher_runtime` |
| [dwarfcannon](#dwarfcannon) | 23 | 93.5% | `dwarfcannon_runtime` |
| [eadgar](#eadgar) | 21 | 98.0% | `eadgar_runtime` |
| [biohazard](#biohazard) | 20 | 97.8% | `biohazard_runtime` |
| [plaguecity](#plaguecity) | 20 | 97.9% | `plaguecity_runtime` |
| [lostcity_combat](#lostcity_combat) | 16 | 90.8% | `lostcity_runtime` |
| [merlinscrystal](#merlinscrystal) | 16 | 97.4% | `merlinscrystal_runtime` |
| [trollstronghold](#trollstronghold) | 16 | 97.8% | `trollstronghold_quest_runtime`, `trollstronghold_runtime` |
| [piratestreasure](#piratestreasure) | 14 | 97.3% | none |
| [touristtrap](#touristtrap) | 14 | 99.4% | `touristtrap_legs_runtime`, `touristtrap_rescue_runtime` |
| [vampireslayer](#vampireslayer) | 14 | 96.0% | none |
| [demonslayer](#demonslayer) | 12 | 96.4% | none |
| [knightssword](#knightssword) | 12 | 97.9% | none |
| [impcatcher](#impcatcher) | 11 | 96.0% | none |
| [mortton](#mortton) | 11 | 99.2% | `mortton_runtime` |

Also missing fewer than 10 lines each: shilo (9), princeali (8), druidspirit (5), priestperil (5), clocktower (4), doric (4), cooksassistant (3), ernest (3), gertrudescat (2), romeojuliet (2), shieldofarrav (2), tbwt (2), tribaltotem (2), blackknight (1), grandtree (1), hetty (1), restlessghost (1), sheepshearer (1).

### By file

#### upass

| File | Missed | Covered |
|---|---:|---:|
| `pass_.py` | 464 | 21.8% |
| `doll.py` | 248 | 18.4% |
| `bridge.py` | 186 | 27.1% |
| `area1.py` | 160 | 19.6% |
| `cavern.py` | 159 | 14.5% |
| `area2.py` | 123 | 25.5% |
| `railings.py` | 67 | 50.7% |
| `stall.py` | 59 | 66.9% |
| `cross.py` | 53 | 59.5% |
| `grid.py` | 37 | 61.5% |
| `supplies.py` | 29 | 88.0% |
| `__init__.py` | 16 | 90.2% |
| `journal.py` | 13 | 84.3% |

Under 10 each: `spent.py` (5), `areas.py` (4), `verdict.py` (3).

#### legends

| File | Missed | Covered |
|---|---:|---:|
| `viyeldi.py` | 279 | 21.6% |
| `shaman.py` | 252 | 22.0% |
| `jungle.py` | 186 | 28.2% |
| `guild.py` | 130 | 28.6% |
| `__init__.py` | 110 | 77.5% |
| `totem.py` | 96 | 19.3% |
| `fight.py` | 58 | 25.6% |
| `supplies.py` | 53 | 83.1% |
| `gather.py` | 46 | 43.9% |
| `scene.py` | 34 | 57.0% |
| `journal.py` | 20 | 79.4% |

Under 10 each: `areas.py` (9), `pockets.py` (1).

#### ikov

| File | Missed | Covered |
|---|---:|---:|
| `dungeon.py` | 335 | 21.9% |
| `fight.py` | 234 | 16.1% |
| `supplies.py` | 161 | 54.8% |
| `temple.py` | 126 | 13.7% |
| `__init__.py` | 40 | 77.8% |
| `gear.py` | 19 | 78.4% |
| `journal.py` | 15 | 70.0% |

#### watchtower

| File | Missed | Covered |
|---|---:|---:|
| `gutanoth.py` | 223 | 12.9% |
| `tower.py` | 158 | 17.7% |
| `tribes.py` | 157 | 14.2% |
| `caves.py` | 111 | 21.3% |
| `enclave.py` | 92 | 17.1% |
| `__init__.py` | 60 | 80.0% |
| `potion.py` | 39 | 27.8% |
| `journal.py` | 15 | 87.0% |
| `supplies.py` | 13 | 91.9% |

Under 10 each: `scene.py` (3).

#### heroquest

| File | Missed | Covered |
|---|---:|---:|
| `doors.py` | 165 | 11.3% |
| `eel.py` | 158 | 36.0% |
| `blackarm.py` | 140 | 31.4% |
| `feather.py` | 115 | 43.6% |
| `phoenix.py` | 81 | 38.6% |
| `partner.py` | 27 | 57.8% |
| `journal.py` | 17 | 79.8% |

Under 10 each: `shops.py` (5), `state.py` (5), `__init__.py` (4), `areas.py` (2).

#### regicide

| File | Missed | Covered |
|---|---:|---:|
| `bomb.py` | 259 | 19.3% |
| `pass_.py` | 121 | 40.1% |
| `isafdar.py` | 101 | 33.6% |
| `finish.py` | 80 | 23.8% |
| `__init__.py` | 53 | 77.7% |
| `pockets.py` | 32 | 81.4% |
| `journal.py` | 13 | 82.2% |

Under 10 each: `supplies.py` (8), `areas.py` (3).

#### digsite

| File | Missed | Covered |
|---|---:|---:|
| `caves.py` | 216 | 20.3% |
| `supplies.py` | 193 | 24.6% |
| `common.py` | 134 | 39.4% |
| `exams.py` | 36 | 64.4% |
| `__init__.py` | 28 | 88.7% |
| `journal.py` | 18 | 79.3% |

Under 10 each: `areas.py` (2).

#### fremenniktrials

| File | Missed | Covered |
|---|---:|---:|
| `seer.py` | 141 | 48.7% |
| `supplies.py` | 94 | 51.0% |
| `hunter.py` | 74 | 49.0% |
| `bard.py` | 65 | 49.2% |
| `warrior.py` | 47 | 46.0% |
| `navigator.py` | 46 | 39.5% |
| `reveller.py` | 44 | 52.7% |
| `journal.py` | 15 | 78.9% |
| `merchant.py` | 13 | 81.2% |

Under 10 each: `areas.py` (8), `__init__.py` (4).

#### horror

| File | Missed | Covered |
|---|---:|---:|
| `fight.py` | 165 | 27.3% |
| `lighthouse.py` | 114 | 18.0% |
| `dungeon.py` | 101 | 22.9% |
| `supplies.py` | 94 | 71.0% |
| `__init__.py` | 32 | 77.6% |

Under 10 each: `journal.py` (8), `barcrawl.py` (5).

#### familycrest

| File | Missed | Covered |
|---|---:|---:|
| `mine.py` | 240 | 22.6% |
| `chronozon.py` | 145 | 31.3% |
| `__init__.py` | 52 | 80.8% |
| `supplies.py` | 45 | 77.2% |
| `journal.py` | 30 | 61.0% |

Under 10 each: `areas.py` (2).

#### chompybird

| File | Missed | Covered |
|---|---:|---:|
| `hunt.py` | 235 | 12.3% |
| `dialogue.py` | 75 | 15.7% |
| `arrows.py` | 58 | 48.2% |
| `cook.py` | 57 | 40.6% |
| `__init__.py` | 50 | 75.6% |
| `supplies.py` | 19 | 82.1% |
| `journal.py` | 15 | 66.7% |

Under 10 each: `areas.py` (4).

#### grandtree

Runtime specs `grandtree_legs_runtime` and `grandtree_combat_runtime` cover all executable lines in `legs.py` (251) and `fight.py` (61).
Runtime spec `grandtree_state_runtime` covers all 55 executable lines in `journal.py`; the quest is 99.8% covered overall.

Under 10 each: `__init__.py` (1).

#### clocktower

Under 10 each: `clocktower.py` (4), now 98.9% covered. Runtime spec: `clocktower_legs_runtime`.

#### witchshouse

| File | Missed | Covered |
|---|---:|---:|
| `garden.py` | 76 | 67.2% |
| `house.py` | 45 | 75.0% |
| `patrol.py` | 23 | 84.0% |
| `journal.py` | 13 | 72.3% |

Under 10 each: `__init__.py` (6).

#### gertrudescat

Under 10 each: `gertrudescat.py` (2), now 99.4% covered. Runtime spec: `gertrudescat_legs_runtime`.

#### hazeelcult

| File | Missed | Covered |
|---|---:|---:|
| `hazeelcult.py` | 148 | 58.9% |

#### tribaltotem

Under 10 each: `tribaltotem.py` (2), now 99.3% covered. Runtime spec: `tribaltotem_legs_runtime`.

#### druidicritual

| File | Missed | Covered |
|---|---:|---:|
| `druidicritual.py` | 96 | 65.2% |

#### elementalworkshop

| File | Missed | Covered |
|---|---:|---:|
| `supplies.py` | 55 | 72.5% |
| `__init__.py` | 20 | 82.3% |
| `journal.py` | 13 | 76.4% |

Under 10 each: `workshop.py` (3).

#### monksfriend

| File | Missed | Covered |
|---|---:|---:|
| `monksfriend.py` | 87 | 62.7% |

#### fishingcontest

| File | Missed | Covered |
|---|---:|---:|
| `contest.py` | 34 | 74.6% |
| `supplies.py` | 28 | 71.4% |
| `journal.py` | 13 | 66.7% |

Under 10 each: `__init__.py` (3).

#### fightarena

| File | Missed | Covered |
|---|---:|---:|
| `fights.py` | 26 | 81.8% |
| `journal.py` | 19 | 71.6% |
| `__init__.py` | 11 | 93.1% |

Under 10 each: `legs.py` (1).

#### seaslug

| File | Missed | Covered |
|---|---:|---:|
| `legs.py` | 53 | 67.7% |
| `journal.py` | 13 | 78.3% |

Under 10 each: `__init__.py` (2).

#### deathplateau

| File | Missed | Covered |
|---|---:|---:|
| `__init__.py` | 64 | 89.6% |

Under 10 each: `journal.py` (2), `nav.py` (1).

#### dragonslayer

| File | Missed | Covered |
|---|---:|---:|
| `__init__.py` | 32 | 95.8% |
| `supplies.py` | 17 | 96.0% |
| `maze.py` | 12 | 97.1% |

Under 10 each: `journal.py` (4).

#### treegnome

| File | Missed | Covered |
|---|---:|---:|
| `supplies.py` | 39 | 71.9% |
| `journal.py` | 13 | 74.0% |

Under 10 each: `__init__.py` (5), `combat.py` (4), `areas.py` (3).

#### waterfall

| File | Missed | Covered |
|---|---:|---:|
| `waterfall.py` | 61 | 94.7% |

#### junglepotion

| File | Missed | Covered |
|---|---:|---:|
| `junglepotion.py` | 55 | 79.3% |

#### observatory

| File | Missed | Covered |
|---|---:|---:|
| `supplies.py` | 21 | 79.8% |
| `journal.py` | 13 | 64.9% |

Under 10 each: `__init__.py` (5).

#### lostcity

| File | Missed | Covered |
|---|---:|---:|
| `lostcity.py` | 30 | 94.0% |

#### murder

| File | Missed | Covered |
|---|---:|---:|
| `evidence.py` | 15 | 90.5% |

Under 10 each: `journal.py` (5), `poison.py` (5), `state.py` (1).

#### sheepherder

| File | Missed | Covered |
|---|---:|---:|
| `journal.py` | 13 | 75.9% |

Under 10 each: `herd.py` (8), `__init__.py` (2), `pen.py` (2), `herd_path.py` (1).

#### goblindiplomacy

| File | Missed | Covered |
|---|---:|---:|
| `goblindiplomacy.py` | 25 | 95.4% |

#### holygrail

| File | Missed | Covered |
|---|---:|---:|
| `journal.py` | 15 | 72.2% |

Under 10 each: `__init__.py` (8), `armour.py` (1).

#### scorpcatcher

| File | Missed | Covered |
|---|---:|---:|
| `journal.py` | 13 | 68.3% |

Under 10 each: `__init__.py` (8), `dungeon.py` (2), `areas.py` (1).

#### dwarfcannon

| File | Missed | Covered |
|---|---:|---:|
| `journal.py` | 13 | 82.2% |

Under 10 each: `__init__.py` (8), `repair.py` (2).

#### eadgar

Under 10 each: `supplies.py` (7), `__init__.py` (4), `parrot.py` (4), `trollheim.py` (4), `areas.py` (1), `journal.py` (1).

#### biohazard

| File | Missed | Covered |
|---|---:|---:|
| `__init__.py` | 10 | 94.0% |

Under 10 each: `areas.py` (2), `supplies.py` (2), `travel.py` (2), `varrock.py` (2), `west.py` (2).

#### plaguecity

Under 10 each: `__init__.py` (7), `supplies.py` (5), `travel.py` (5), `west.py` (2), `east.py` (1).

#### lostcity_combat

| File | Missed | Covered |
|---|---:|---:|
| `lostcity_combat.py` | 16 | 90.8% |

#### merlinscrystal

| File | Missed | Covered |
|---|---:|---:|
| `merlinscrystal.py` | 16 | 97.4% |

#### trollstronghold

| File | Missed | Covered |
|---|---:|---:|
| `__init__.py` | 12 | 97.1% |

Under 10 each: `combat.py` (2), `areas.py` (1), `journal.py` (1).

#### piratestreasure

Under 10 each: `karamja.py` (6), `__init__.py` (3), `journal.py` (3), `supplies.py` (2).

#### touristtrap

| File | Missed | Covered |
|---|---:|---:|
| `touristtrap.py` | 14 | 99.4% |

#### vampireslayer

| File | Missed | Covered |
|---|---:|---:|
| `vampireslayer.py` | 14 | 96.0% |

#### demonslayer

| File | Missed | Covered |
|---|---:|---:|
| `demonslayer.py` | 12 | 96.4% |

#### knightssword

Under 10 each: `supplies.py` (7), `__init__.py` (2), `dungeon.py` (2), `portrait.py` (1).

#### impcatcher

| File | Missed | Covered |
|---|---:|---:|
| `impcatcher.py` | 11 | 96.0% |

#### mortton

Under 10 each: `temple.py` (7), `shades.py` (2), `__init__.py` (1), `town.py` (1).

## Shared code

This code is already well tested and much of what's left is defensive branches, so a line here is usually harder to reach
and worth less than one in a quest leg. Paths are under `rs2004/`.

| File | Missed | Covered |
|---|---:|---:|
| `traversal.py` | 60 | 95.0% |
| `hunting/supply.py` | 39 | 95.1% |
| `clues/solve.py` | 37 | 95.1% |
| `hunting/combat.py` | 33 | 95.3% |
| `clues/executor.py` | 30 | 95.7% |
| `random_events.py` | 24 | 95.1% |
| `clues/guardian.py` | 20 | 95.8% |
| `game.py` | 18 | 95.3% |
| `banksort.py` | 17 | 96.6% |
| `catalogs/tool_acquire.py` | 17 | 95.2% |
| `routeplan.py` | 17 | 96.5% |
| `_runtime.py` | 16 | 95.3% |
| `quests/engine/quest_engine.py` | 16 | 97.4% |
| `random_solvers.py` | 13 | 96.7% |
| `catalogs/partner.py` | 11 | 96.6% |
| `quests/exec/steps.py` | 11 | 96.1% |
| `catalogs/tables.py` | 10 | 95.8% |
| `trade.py` | 10 | 96.9% |

Under 10 each: `clues/steps.py` (9), `entities.py` (9), `tabs.py` (9), `market/appraise.py` (8), `settings.py` (8), `reach.py` (7), `bank.py` (6), `catalogs/combat.py` (6), `market/catalog.py` (6), `clues/puzzle.py` (5), `duel.py` (5), `partner_handoff.py` (5), `catalogs/loadout.py` (4), `catalogs/thieving.py` (4), `clues/travel.py` (4), `quests/barcrawl/run_barcrawl.py` (4), `quests/exec/primitives.py` (4), `activity.py` (3), `catalogs/fishing.py` (3), `clues/acquire.py` (3), `events.py` (3), `market/categories.py` (3), `quests/exec/fund_coins.py` (3), `quests/exec/wool.py` (3), `catalogs/gathering.py` (2), `catalogs/tools.py` (2), `geometry.py` (2), `karamja_recovery.py` (2), `walkgeom.py` (2), `catalogs/firemaking.py` (1), `catalogs/places.py` (1), `catalogs/record.py` (1), `catalogs/tasks.py` (1), `dialogue.py` (1), `hunting/logic.py` (1), `market/_text.py` (1), `market/chat_protocol.py` (1), `messages.py` (1), `quests/engine/trace.py` (1), `quests/exec/legs.py` (1), `quests/strike_combat.py` (1).
