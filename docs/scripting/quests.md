# Quests: `rs2004.quests`

rs2b0t's quest engine, translated from its `api/ai/quests`. [The engine](#the-engine-rs2004questsengine) runs a queue of quests; each quest is [a module](#a-quest-rs2004questsdefs) whose `decide(snap)` names one [step](#steps-rs2004questsexecsteps) at a time. Under them are small steps of their own: talk to an NPC through its dialogue, walk to one across a ladder, act on a loc and answer what it asks. Bots outside quests use those too. Everything here is imported, not builtins, each module by its full name:

```python
from rs2004.quests.exec import talk_through, goto_npc, NpcStop, LadderHop
```

Each step takes a `log` function for its progress lines, such as a bot's `self.log`, and each that walks or clicks is a **Wait**. A step that takes a description of where to go, a stop, a hop or a door, reads its fields as attributes: use the classes below, or a [`Record`](catalogs.md#records), whose missing fields read as `None`, as rs2b0t's object literals translate.

## Talking: `rs2004.quests.exec`

| Function | Does |
|---|---|
| `talk_through(npc_name, prefer, log, gap_ms=None)` | **Wait.** `open_dialogue`, then `drive_dialog`. `True` once the dialogue closed |
| `open_dialogue(npc_name, log)` | **Wait.** Talks to the nearest NPC of that name with a Talk option, opening a door it stands behind. `True` once a dialogue is up |
| `drive_dialog(prefer, log, gap_ms=None)` | **Wait.** Clicks through the open dialogue, choosing the first option holding a `prefer` fragment, and the last option when none does, until the dialogue closes or stays quiet for `gap_ms` (1.5 seconds by default, `DIALOG_GAP_MS`). Stops when a random event is pending |
| `talk_strict(npc_name, prefer, log)` | **Wait.** Like `talk_through`, but stops instead of guessing when no option matches: several ogres offer "I have come to kill you" as the alternative |
| `talk_choosing_by(npc_name, rules, prefer, log)` | **Wait.** For a dialogue whose right answer depends on what the NPC said: the first `LineRule` whose `when_line` is in the NPC's last line picks the option, else `prefer` does, else it stops |
| `pick_preferred(options, prefer)` | The first option holding a preferred fragment, trying the fragments in order, by part and without regard to case, or `None` |
| `pick_by_line(lines, options, rules)` | The option the matching rule names, longest `when_line` first, ignoring colour tags and pipes, or `None` |
| `talk_op(actions)` | The first option starting "talk", or `None` |

`LineRule(when_line, choose)` is a rule: choose the option holding `choose` when the NPC's line holds `when_line`, in lower case.

```python
from rs2004.quests.exec import LineRule, talk_choosing_by

SKAVID = [LineRule('ar cur', 'Gor.'), LineRule('cur tanath', 'Bidith.')]
ok = yield from talk_choosing_by('Mad skavid', SKAVID, [], self.log)
```

## Getting to NPCs

| Function | Does |
|---|---|
| `goto_npc(stop, hops, log)` | **Wait.** Walks to an `NpcStop`: across a ladder in `hops` first when its anchor is on the other side of the ground, through its `approach` tiles, then to the anchor. `True` once the NPC is within its leash. Landing somewhere underground the anchor can't be reached from, it climbs back up to try the landing again, and gives `False` |
| `walk_with_hops(dest, radius, hops, log)` | **Wait.** Walks to `dest`, climbing the nearest ladder in `hops` first when `dest` is on the other side of the ground |
| `is_underground(t)`, `needs_hop(here, anchor)` | Whether a tile is underground (`z` 5000 and up), and whether two are on different sides |

| Class | Fields |
|---|---|
| `NpcStop(npc, anchor, leash, prefer, approach=None, gap_ms=None)` | The NPC's name; the tile it's found near and how far it wanders; the options to prefer when talking; tiles to walk through on the way; how long a lull in its dialogue may last, for a scene that walks it about |
| `LadderHop(stand, loc_name, op, arrive, open=None, walk=None)` | A ladder between the surface and underground: stand by it, use `op` on the `loc_name` loc within 3 tiles, and arrive. `open` is the option that opens it first, as a trapdoor's; `walk` a tile to walk to first when `stand` is behind a door the route can't pin |

```python
from rs2004.quests.exec import LadderHop, NpcStop, goto_npc, talk_through

HOPS = [
    LadderHop(Tile(3105, 3162, 0), 'Ladder', 'Climb-down', Tile(3104, 9576, 0), walk=Tile(3108, 3162, 0)),
    LadderHop(Tile(3104, 9576, 0), 'Ladder', 'Climb-up', Tile(3105, 3162, 0)),
]
SEDRIDOR = NpcStop('Sedridor', Tile(3103, 9572, 0), 8, ["I'm looking for the head wizard."])

arrived = yield from goto_npc(SEDRIDOR, HOPS, self.log)
if arrived:
    yield from talk_through(SEDRIDOR.npc, SEDRIDOR.prefer, self.log)
```

## Locs and doors

| Function | Does |
|---|---|
| `prompt_loc(step, log)` | **Wait.** Walks to a `LocPrompt`'s loc, uses its option, and answers whatever it raised, in either the chat box or the main modal, until `step.expect()` holds. `True` then. On failure it clears the boxes left standing, so a retry can click |
| `use_on_loc(item_id, loc, prefer, expect, log)` | **Wait.** Walks near a loc, uses the carried `item_id` on it, and answers what it raised until `expect()` holds. `loc` has a `name` and a `near` tile, and may have `within` (12 by default) and an `id` for when the name is shared |
| `cross_teleport_door(door)` | **Wait.** Crosses a `DoorCrossing`, a quest door whose Open teleports you through and shuts behind you. A game message after the click is a refusal; the far side is the only proof of a crossing |
| `drive_choice(prefer, log)` | **Wait.** Like `drive_dialog`, but stops on an option list none of `prefer` matches: a loc's prompt often offers the refusal first |
| `drive_until(expect, prefer, log, ms=30000)` | **Wait.** Keeps answering prompts until `expect()` holds or `ms` pass, holding the quest's protection prayer between them |
| `drive_boxes(expect, ms, prefer=None, log=None)` | **Wait.** Clicks a chain of message boxes away one at a time, in either widget, testing `expect()` before each, so the box carrying the answer is still readable |
| `clear_boxes(max_boxes=8)` | **Wait.** Dismisses every standing message box |
| `settle_scene()` | **Wait.** 2 ticks after a level or region change, as rs2b0t waits for its loc queries |
| `loc_near(name, op, within=12)` | The nearest loc of that name offering `op`, or `None` |
| `held_id(id)` | How many of the item id you carry |

| Class | Fields |
|---|---|
| `LocPrompt(name, op, near, expect, prefer=None, expect_ms=None, within=None, id=None, refused=None)` | Use `op` on the `name` loc near `near`, then answer with `prefer` until `expect()`, within `expect_ms` (20 seconds). `within` is how far from `near` to look (10), `id` picks a loc whose name is shared, and `refused` is a game message [pattern](walking.md#game_messages) the loc answers with when the option can't work yet |
| `DoorCrossing(id, stand, is_far, log, prefer=None, name=None, op=None, use_item=None, stand_radius=None)` | The door's loc id; the tile to click from, on the side you're leaving; `is_far()`, true once you're past it; the options for a door that asks something; its name and option when it isn't a Door offering Open; a key's item id for a locked door; and how far from `stand` counts as there, 0 for a door that tests your side by one coordinate |

```python
from rs2004.quests.exec import LocPrompt, prompt_loc

mark = game_messages.mark()
step = LocPrompt('Crate', 'Search', Tile(3208, 3210), lambda: game_messages.saw_since(mark, 'You find'))
found = yield from prompt_loc(step, self.log)
```

## Prayer: `rs2004.quests.prayer`

A quest declares the protection prayer it fights under as `{'protect': 'melee', 'magic' or 'missiles', 'potions': doses}`. `set_quest_prayer` points the upkeep at it, and `prayer_upkeep`, which `drive_until` calls between prompts, spends one tick on it when needed: raising the prayer in a fight, drinking a dose at the floor, and dropping the prayer when the fight ends.

| Name | Is |
|---|---|
| `set_quest_prayer(pray, log)` | Points the upkeep at a quest's prayer; `None` for one that declares none |
| `prayer_upkeep()` | **Wait.** At most one tick of upkeep. `True` when it acted |
| `prayer_upkeep_action(in_combat, protect_active, protect_available, points, doses)` | The one thing to do: `'none'`, `'protect'`, `'drink'` or `'drop'` |
| `PRAYER_FLOOR` | 25: the points at which a dose is drunk |
| `PROTECT_LEVEL`, `PROTECTION_NAME` | Each kind's Prayer level (37, 40, 43) and prayer name |
| `protection_name(pray)`, `protection_level(pray)` | The same, for a declaration |
| `PRAYER_POTION`, `PRAYER_POTION_IDS` | `'Prayer potion(4)'`, and the ids of every dose |
| `quest_prayer_state` | The running quest's `current` declaration, whether it `warned` that the level is too low, and its `log` |

## The engine: `rs2004.quests.engine`

`QuestEngine(host)` is a `Task`. AIOQuester (`bots/aio_quester.py`) is its host, and any bot can be: the host has `log(m)`, `verbose()`, `food_item()`, `picked_ids()` (the record ids to run), `skip_pending()`, `consume_skip()`, `consume_death()`, `note_state(rows, running_id, step_desc, no_progress, parked)` and `finish(reason)`.

AIOQuester expands selected prerequisites and quest-point requirements, respecting `-quest_id` exclusions.
Before a quest it can train missing skills and source supported food and supplies through child activities.
Preparation never starts another quest recursively: finish Druidic Ritual or Rune Mysteries first when their
skills are locked. Unavailable suppliers produce a blocked reason.

Automatic recovery refreshes stalled quest state, then tries a bank reset, then aborts that quest for the
session. Three deaths also abort it. The `restart` console command requests a bank reset. Preparation, Skip
and Restart restore the saved quest inventory and equipment before changing quests; an unsafe exit or
failed restoration stops with a reason. Carried Karamja rum and filled Legends bowls must be delivered first.

Custom engine hosts can opt into these paths with `automatic_recovery()`, `consume_restart()`,
`prepare(request)` (a Wait returning `'working'` or `'ready'`), `preparation_status()`, `stop_preparation()`
and `exit_preparation()`. `QuestModule.auto_retaliate` accepts a boolean or snapshot predicate; the engine
confirms the setting before executing a step. A deposit step can set `caps` to records of `id` and `qty` to
bank excess copies. Cooperative wait/custom steps set `cooperative=True`; a host's `waiting_for_partner(id)`
and `partner_progress_key(id)` keep active handoffs out of the ordinary stall counter while retaining a
ten-minute partnership deadline.

Each pass the engine:
1. reads the quest list and evaluates every quest (`rs2004.quests.eligibility`): `DONE`, `READY`, or `BLOCKED` with its reasons, such as `needs 12 quest points (have 10)`;
2. takes the first picked quest that's `READY`, in the list's order, which puts prerequisites first;
3. banks the pack to nothing before a quest that hasn't started, then banks whatever the quest won't use;
4. provisions it bank-first: the record's items, the coin float (`COIN_FLOAT`, 1000, unless the module says otherwise), the food float and prayer potions, and asks the module's `gather` for whatever the bank can't cover;
5. asks the module's `decide(snap)` for a step and runs it.

A quest that makes no progress for 8 steps (`NO_PROGRESS_PARK`), or that waits on the same `wait` step 15 times, is parked with its reason and the queue goes on; parked 3 times, it's given up for the session. A step counts as progress when anything the snapshot shows changes: the journal, the stage or its flags, the tile, the pack, what's worn, or combat xp. A finished quest walks back to a bank before the next starts.

| Module | Has |
|---|---|
| `quest_engine` | `QuestEngine`, `PROVISION_BANK`, `describe_step(step)` |
| `types` | `QuestSnapshot`, `QuestModule`, `QuestProgress`, `QuestPrayer`, `QuestSustain`, `quest_step(kind, ...)`, `held_id`, `banked_id`, `has_flag`, `flag_value` |
| `queue` | `next_quest`, `queue_rows`, `QueueRow` |
| `provisioning` | `plan_provisioning`, `deposit_plan`, `float_draw_plan`, `coin_float_plan`, `buy_purse_top_up`, `should_freshen_pack`, `gp_short`, `COIN_FLOAT` |
| `watchdog` | `progress_signature`, `ProgressWatchdog`, `NO_PROGRESS_WARN`, `NO_PROGRESS_PARK` |
| `trace` | `StepTracker`, `format_duration`, `format_tile`, `inv_delta` |

`rs2004.quests.data` has the records, `QUESTS` and `quest_record(id)`: all 63, generated from rs2b0t's `data/quests.ts`, so a prerequisite reads complete whether or not a module runs it yet.

## A quest: `rs2004.quests.defs`

A quest is `rs2004.quests.defs.<file>`, exporting a `QuestModule` of the same name, as rs2b0t's `defs/<file>.ts` does. `QUEST_DEFS` lists them in the queue's order, each with its record; `def_by_id(id)` loads a quest's module the first time it's asked for, so an account running one quest compiles one.

```python
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, quest_step

def decide(snap):
    if snap.journal == 'complete':
        return quest_step('done')
    if snap.journal == 'not_started':
        return quest_step('talk', stop=COOK)
    ...

cooksassistant = QuestModule(record=quest_record('cook'), bank=Tile(3093, 3243, 0), decide=decide, ...)
```

`decide(snap)` is a pure function of the snapshot, so a quest resumes from wherever it stopped, by a random event, a death or a client that ended. The snapshot has the journal status (`'not_started'`, `'in_progress'`, `'complete'` or `'unknown'`), the pack by lower-case name (`inv`) and by id (`inv_ids`), what's worn, the last bank read, the stage when the module reads one (`read_stage`, or `read_progress` for flags too), the tile, prayer, levels and free slots. `snap.with_fields({...})` copies it with fields changed.

A `QuestModule`'s other fields say what the engine should do for it: `bank`, `hops`, `grind`, `food`, `gather`, `tools`, `exit`, `owns_inventory`, `food_ready`, `sustain`, `pray`, `coin_float`, `warn_readiness`, `observe`, `on_start` and `resume_at(tile)`. The optional `recover(tile)` returns an exit step for a completed or interrupted quest area; the engine runs it before choosing another quest. Repeated failed recovery stops the queue. The optional resume predicate gives a started quest priority when a restarted queue is inside its one-way area, such as Dragon Slayer's maze or Crandor, or the witch's garden and shed. Generic banking waits until the quest leaves that area. See its docstring.

Ported so far: Cook's Assistant (`cooksassistant`), Sheep Shearer (`sheepshearer`), Rune Mysteries (`runemysteries`), The Restless Ghost (`restlessghost`), Witch's Potion (`hetty`), Black Knights' Fortress (`blackknight`) and Romeo & Juliet (`romeojuliet`), plus Demon Slayer (`demonslayer`), Doric's Quest (`doric`), Imp Catcher (`impcatcher`), Goblin Diplomacy (`goblindiplomacy`), Vampire Slayer (`vampireslayer`), The Knight's Sword (`knightssword`), Ernest the Chicken (`ernest`), Pirate's Treasure (`piratestreasure`), Prince Ali Rescue (`princeali`), Shield of Arrav (`shieldofarrav`) and Dragon Slayer (`dragonslayer`): all eighteen free-to-play quests.

Druidic Ritual (`druidicritual`, record id `druid`) and Monk's Friend (`monksfriend`, record id `drunkmonk`) are the first members' modules. Both expose pure `decide(snap)` functions and journal parsers. Druidic Ritual recovers missing meat bank-first and enchants one species at a time; Monk's Friend sources the blanket, water and logs and waits for the party to finish.

Four more members' modules expose `read_progress()` and a pure `decide(snap)`:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `gertrudescat` | `fluffs` | Sources milk and seasoned sardines, searches the six NPC crates and reunites Fluffs with her kitten. Retrieves a banked kitten before searching again |
| `junglepotion` | `junglepotion` | Requires Druidic Ritual. Picks and identifies the five exact herb ids, with mainland food and boat fares provisioned before departure |
| `clocktower` | `cog` | Collects and places the four cogs, including cooling the black cog and poisoning the rat pen. Leaves each sealed room through its own ladder |
| `hazeelcult` | `hazeelcult` | Runs the Carnillean side. Refuses a character already committed to the cult side with a reason, sets the valves, retrieves the armour and searches Jones' cupboard |

Their `parse_gertrudes_cat_journal`, `parse_jungle_journal`, `parse_clock_tower_journal` and `parse_hazeel_journal` functions return `QuestProgress` or `None`.

The remaining phase-17a modules are also registered:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `witchshouse` | `ball` | Reads journal rewinds, sources gloves and cheese, opens the mouse door, reads the diary, follows guarded garden crossings and casts Strikes through all four experiment forms |
| `fishingcontest` | `fishingcompo` | Sources the pass, garlic, rod, spade and worms; drives the gate conversation, stashes garlic at the pipe, catches carp and returns the trophy |
| `murder` | `murder` | Uses thread colour and exact evidence ids to match fingerprints, prove the suspect's poison story false and report to the guard |
| `seaslug` | `seaslug` | Repairs Holgart's boat, finds Kennith and Kent, lights a torch on the platform and operates the panel and crane |
| `priestperil` | `priestperil` | Uses temple doors, held keys and water to locate its phase, then supplies Drezel with essence, withdrawing banked essence or mining it with a held or banked pickaxe |
| `tribaltotem` | `totem` | Relabels the delivery crate, enters by Cromperty's teleport, solves the KURT lock from its displayed letters, investigates the stairs and retrieves the totem |

The four packages retain their upstream areas, journal and execution modules. Fishing Contest's journal reader returns a stage; Witch's House, Murder Mystery, Sea Slug and Tribal Totem return `QuestProgress`. Priest in Peril reads its phase through interactions and inventory. Its mining fallback needs Rune Mysteries completed and a held or banked pickaxe when no essence is banked. All twelve phase-17a quests have completed in one live queue, and FlourCollector and RoguesPurse have each banked a full load.

The phase-17b modules are registered too:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `dwarfcannon` | `mcannon` | Replaces the six railings, takes the remains from the watchtower, rescues the dwarf child from the goblin cave and repairs the cannon one named part at a time |
| `sheepherder` | `sheepherder` | Buys the plague suit, fetches the prod, prods each sheep into the enclosure along a route searched again from the sheep's tile every push, poisons it and burns its exact remains |
| `treegnome` | `tree` | Brings Montai the logs, fires the ballista at height 4, x 3, y 5, takes the orb from the stronghold chest and kills the Khazard warlord under Protect from Melee |
| `waterfall` | `waterfall` | Self-funds when the purse and bank are empty, reads the book, recovers Glarial's pebble, amulet and urn, solves the rune pillars and pours the ashes, bankless inside the falls |
| `scorpcatcher` | `scorpcatcher` | Requires the barcrawl card for the outpost. Reads which scorpions are caught from the cage's id, held or banked, and takes the dusty key, the dragon corridor and the monastery |
| `observatory` | `itgronigen` | Fetches sand, ore, planks and seaweed in map order, smelts the glass and bar in one furnace visit, kills the keep's guard for the lens mould and looks through the telescope |
| `fightarena` | `arena` | Wears the Khazard disguise, buys the Khali brew for the keys, fights the ogre, scorpion and Bouncer with Strikes from cover, or in the open under Protect from Melee when a beast won't come round the rock, and keeps the last stage it read |
| `merlinscrystal` | `arthur` | Talks to the knights, rides the crate into the fortress for Morgan's brief, makes the black candle, takes Excalibur from the Lady of the Lake and summons Thrantax to break the crystal |
| `lostcity` | `zanaris` | Reveals Shamus, sails to Entrana without restricted gear, kills the tree spirit with Strikes from the fungus safespot (`lostcity_combat`), crafts five Dramen staves and enters Zanaris |

Observatory Quest's goblin guard is fought with Troll Stronghold's `combat.fight` and `attackable`, so `rs2004.quests.defs.trollstronghold.combat` and `areas` were ported ahead of the quest itself. All nine phase-17b quests have completed in one live queue.

The phase-17c modules are registered too:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `deathplateau` | `death` | Asks Eohric and Harold about the night guard, buys Harold the ale and a Blurberry special, bets past his purse at dice until he writes the IOU, reads the combination and places the five stone balls; then Saba, Tenzing, Dunstan's spiked boots and Denulth's certificate, Tenzing's supplies, and the secret path scouted off the thrower trolls' approach |
| `trollstronghold` | `troll` | Needs Death Plateau complete. Wears the climbing boots and the loadout, fights Dad to his forfeit and a Troll General for the prison key under Protect from Melee, steals the cell keys (Thieving 30) or kills the woken guards, and frees Mad Eadgar before Godric |
| `eadgar` | `eadgar` | Needs Troll Stronghold and Mad Eadgar freed, and frees him first when the journal says he isn't. Catches the drunk parrot, hides it under the prison rack, gathers the scarecrow (logs, chickens, grain and a robe), brews the troll potion from a banked ranarr weed, fetches the fake man and the storeroom key and takes the goutweed; every Trollheim leg holds Protect from Missiles against the throwers |
| `plaguecity` | `elena` | Digs into the sewer from Edmond's garden after four pours, pulls the grill with the rope, follows Jethick, the Rehnisons and Milli, gets the clerk's audience with Bravek, makes his hangover cure and frees Elena with the warrant |
| `biohazard` | `biohazard` | Needs Plague City. Distracts the mourners with the pigeons, poisons their stew over the fence, takes the doctors' gown and the sick mourner's key for the distillator, sends the vials with the errand boys, crosses Varrock's east gate in the priest suit to Guidor and confronts King Lathas |

Each keeps rs2b0t's package. Plague City and Biohazard walk out of West Ardougne, the mourners' headquarters and the sewer before any bank leg, since none has a bank. Troll Stronghold and Eadgar's Ruse bank only below the stile; above it they wear what they carry and go on. Death Plateau's dice game reads the panel's buttons with `reader.modal_buttons` and presses them with `_core.click_component`, which sends a pause button's resume.

All five phase-17c quests have completed in one live queue. Eadgar's Ruse departs from rs2b0t in drawing two prayer potions for the Trollheim crossings, and Death Plateau in closing Harold's menu before it reads the IOU.

The phase-17d modules are registered too:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `druidspirit` | `druidspirit` | Needs The Restless Ghost and Priest in Peril. Wears the ghostspeak amulet before the first word, summons Filliman at the grotto door, shows him the mirror and his journal, blooms a fungus with his scroll and feeds the ritual stones, then casts a silver sickle at Al Kharid (bank first, else Dommik's mould, a pickaxe from Bob and a mined bar), has it blessed and kills three ghasts with the pouch, praying back up at Paterdomus |
| `mortton` | `mortton` | Needs Priest in Peril, and Nature Spirit started for the Mort Myre gate. Burns the Varrock log spawns for ashes, reads Herbi Flax's diary, brews serum 207 from the table's two tarromin, kills five shades for their remains, buys plank, brick and paste at Razmire's counters, rebuilds the Flamtaer temple from its transmitted meters, lights the altar, sanctifies the oil and cremates a shade |
| `tbwt` | `tbwt` | Needs Jungle Potion. Kits up at Ardougne across the ferry (a bow, arrows, armour, food, a spear and agility potions, bank first; the knife, pestle and tinderbox from Jiminua), then takes the brothers in the only order that closes: Lubufu's bait and apprenticeship, Tiadeche's catch, Tamayu's hunt with four doses and a Karambwan-poisoned spear, Tinsay's rum, sandwich and marinated Jogre bones, and Tiadeche's manual |
| `shilo` | `zombiequeen` | Needs Jungle Potion. Takes the coins, bones and food off the mainland, buys the tools from Jiminua in one visit, opens the mound into Ah Za Rhoon, reads both scrolls, buries Zadimus for the bone shard, searches the Bervirius dolmen, crafts the Beads of the Dead and the bone key, and fights the three Nazastarool forms in Rashiliyia's tomb before laying her remains in Bervirius' |

Each keeps rs2b0t's package, and each owns its inventory. Tai Bwo Wannai Trio reads its two transmitted varps (`tbwt_main`, `tbwt_tiadeche`) and opens the journal only for the other three brothers. Shades of Mort'ton reads the temple's three transmitted meters the same way. Every pocket the quests strand the bot in (the grotto, Ah Za Rhoon, the Bervirius tomb, Rashiliyia's tomb) is left before a step that acts outside it.

All four phase-17d quests have completed in one live queue. Nature Spirit departs from rs2b0t twice. Its sickle chain waits, with the reason, below the silver's Mining 20 or Smithing 20, which its record doesn't list and the server refuses in a message box. And it draws the melee kit before the ghasts, since a queue may leave a bow on with an empty quiver. Tai Bwo Wannai Trio needs Fishing 65 and Firemaking 30 beyond its record's levels, for the Karambwan and the Jogre bones.

The phase-17e modules are registered too:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `touristtrap` | `desertrescue` | Funds its 1,000 coins from the bank or by pickpocketing Men (`exec.fund_coins`), buys the desert outfit, waterskins and pass from Shantay, provokes the Mercenary Captain for the camp key, frees the slave for his clothes, trades Al Shabim the prototype dart it forges and fletches for a Tenti pineapple, and gets Ana out by barrel, lift, winch and mine cart. Its own water and food floors keep it alive in the desert, and every capture or jail is escaped before the stage is read |
| `watchtower` | `itwatchtower` | Draws its banked kit in one trip (the dragon bones, guam, bat bones and gold bar its record demands, plus whatever else the bank holds), helps Og, Toban and Grew for the relic parts, steals a rock cake for the battlement, answers the city guard's riddle with a death rune, learns the skavid words cave by cave, brews and has the ogre potion infused, dissolves the six shamans, takes the last two crystals and pulls the lever |
| `chompybird` | `chompybird` | Fletches twelve ogre arrows from achey logs, feathers and wolf-bone tips, with the knife and chisel from the bank or Bugs, takes the bellows from the ogre chest or the bank, inflates swamp toads for bait, borrows or buys the bow, shoots and plucks a chompy, carries all six seasonings and roasts it on the spit |
| `grandtree` | `grandtree` | Carries the bark sample to Hazelmere and the message back, goes through Glough's jail, glides to Karamja for the foreman's lumber order and rides Femi's cart back in, takes the invasion plans from Glough's chest with Anita's key, lays the four twigs on their pillars, kills the Black Demon below the trapdoor, and searches the roots for the Daconia rock |

Each keeps rs2b0t's layout: The Tourist Trap is one module, and the other three are packages. The Tourist Trap, Watch Tower and Big Chompy Bird Hunting own their inventories. Watch Tower's sealed pockets (the wizard floor, Grew's island, Toban's camp, the city-guard pocket, the lower city, the skavid caves and the enclave) are each left before a step that starts elsewhere, and The Grand Tree's legs own the unbaked climbs to Anita's floor and Glough's pillar floor. The Grand Tree reads its journal for the stage and keeps the furthest stage it has read, since a journal read opens a modal mid-fight. Big Chompy Bird Hunting departs from rs2b0t in waiting, with the reason, below Crafting 5, which its record doesn't list and the server refuses the chisel below in a message box.

The live run added more departures from rs2b0t:

- **The Tourist Trap**
    - It searches the jail window by its exact tile, since the nearest window answers "I can't reach that!".
    - Its `resume_at` covers the jails, the camp, the mine and the Bedabin tent, so a resumed queue gets out before generic banking.
    - A make-room deposit keeps the prototype's bar, feathers and hammer and the pass. Kebabs are kept only when no food is configured.
    - A pack holding only kept items banks food above the entry floor, one at a time, to make room for a quest item.
    - It makes room before it buys or withdraws the Shantay pass.
- **Watch Tower**
    - Its own inventory is left alone by the engine, so while it is still collecting its kit a full pack banks everything except quest items, food and prayer potions.
    - It fights Gorad, swinging and eating, rather than waiting for his tooth.
    - It asks Og, Toban and then Grew for replacement relic parts lost in a death. A part the wizard answers "I already have that part" is not offered again.
    - It buys the riddle's death rune from Aubury when Magic is under the Magic Guild's 66.
    - It draws no more enclave food than the pack has room for.


## Steps: `rs2004.quests.exec.steps`

`execute_step(step, hops, log)` runs one step. A step is a `Record` made by `quest_step(kind, ...)`, whose fields not set read as `None`:

| Kind | Fields | Does |
|---|---|---|
| `talk` | `stop` | Walks to the `NpcStop` and talks it through |
| `grab_ground` | `item`, `anchor`, `wait_if_missing` | Takes the item off the ground there; arriving at an empty spawn isn't a take. With `wait_if_missing` it waits up to 200 ticks for the spawn to come back, where rs2b0t paused 2 |
| `pick_loc` | `loc`, `op`, `item`, `anchor` | Picks from a loc until the item lands |
| `interact_loc` | `loc`, `op`, `anchor`, `expect_item` | Uses a loc |
| `use_on` | `item`, `target_kind` (`'npc'`, `'loc'` or `'item'`), `target`, `anchor`, `product` | Uses an item on a thing, and waits for the product |
| `equip` | `item` | Wears it |
| `scan_bank` | `bank` | Opens the bank, so the engine reads it |
| `withdraw` | `items` (dicts of `name`, `qty` and an optional `id`), `bank` | Withdraws them |
| `deposit` | `keep`, `keep_ids`, `exact_keep`, `bank` | Banks everything but what's kept |
| `mine_rock` | `rock`, `item`, `qty`, `anchor` | Mines one ore |
| `buy` | `item`, `qty`, `shop` (`npc`, `anchor`), `est_gp`, `bank` | Buys from the shop, drawing coins from the bank first when the purse is short |
| `custom` | `name`, `run(log)` | Runs the quest's own leg, a generator giving `True` when it worked |
| `wait` | `reason` | Waits two ticks |
| `done` | | Nothing |

The phase-17f modules are registered too:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `elementalworkshop` | `elemental_workshop` | Finds and reads the battered book, cuts its spine for the key, provisions from the Seers bank, starts the water wheel, stitches the bellows, lights the furnace with lava, kills the rock's Earth elemental for its ore, smelts it and smiths the shield. |
| `digsite` | `itexam` | Stamps the Examiner's letter, runs the three students' errands, sits the three exams, digs the level 3 site for the talisman, and works both shafts for the chemicals, the blast and the stone tablet. Every NPC, loc and object goes by id, since their names collide. |
| `holygrail` | `grail` | Talks to King Arthur and Merlin, strips for Entrana, takes the napkin from Galahad and the whistles from Draynor Manor, buys back or withdraws Excalibur, kills the Black Knight Titan, rings the bell to reach the Fisher King, frees Sir Percival and lifts the Grail. |
| `familycrest` | `crest` | Hands Caleb his fish, finds Avan through the gem trader and Boot, walks the lever chain to the perfect gold, crafts the ring and necklace, cures Johnathon and lands the four blasts on Chronozon from his safespot. |
| `horror` | `horror` | Builds the bridge, tours the barcrawl for Gunnjorn's key, gathers the tar and glass, repairs the lighthouse's light, loads the strange wall and fights the junior and the mother. |

Each keeps rs2b0t's package. Elemental Workshop, Digsite Quest, Family Crest and Horror from the Deep own their inventories. Holy Grail declares `resume_at` over the Fisher King's realm, which only the whistle leaves.

The live run added these departures from rs2b0t:

- **Family Crest** kills whatever else is hitting the account before it casts at Chronozon, since the lair is single-way and the server refuses the cast otherwise.
- **Horror from the Deep**
    - It reads its bridge flag off the open page's raw text, since `quests.journal` gives lines without colour tags.
    - It draws no more food than the pack has room for, and with a full pack banks what the stage has no use for.
    - Its dungeon load carries three prayer potions when the bank has them, and its fights drink one at the prayer floor.

`reach` also opens diagonal doors now, and the walker can climb out of the Elemental Workshop.

The phase-17g modules are registered too:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `heroquest` | `hero` | Gathers the kit, runs the gang's half of the armband with the partner (see "Hero's Quest and its partner"), fishes and cooks the lava eel, kills the Ice Queen for the ice gloves, takes the fire feather on Entrana, and hands all three in. |
| `ikov` | `ikov` | Fetches the boots of lightness and makes the bow and ice arrows, crosses the lava with the lever, kills the Fire Warrior, farms limpwurt roots from the hobgoblins for Winelda, then joins the Guardians of Armadyl and banishes Lucien. |
| `fremenniktrials` | `viking` | Wins the seven votes, from the Revellers' and the Bard's to the seer's riddles and the hunter's Draugen, and passes Thorvald's trial by letting Koschei's fourth form land the last blow. |

Hero's Quest and The Fremennik Trials own their inventories. All three declare `resume_at` over the pockets a walk can't leave. The Fremennik Trials warns below Prayer 70, since Koschei's forms outlast a lower pool under Protect from Melee, and Ikov's Fire Warrior needs about Ranged 70 for its 20 arrows.

The live run added these departures from rs2b0t:

- **Hero's Quest**
    - A short purse draws the difference from the bank before Scavvo, since the engine's own draw only tops up below a quarter of the price.
    - With the Ice Queen dead and no gloves on the floor, it waits up to five minutes for her respawn, since partners share her.
- **Temple of Ikov**
    - `past_south_gate` needs the temple too, as the half-plane alone holds the surface.
    - Armour found on at a shut south gate comes off, so the lever can be fetched across the bridge.
    - The bridge is one click, as a re-click from the far side carries the bot back.
    - The boots errand fetches its own knife.
    - A worn weapon stands unless something stocked beats it.
- **The Fremennik Trials** warns about Prayer as above, and `resume_at` covers its trial rooms.

The walker also has the Champions' Guild's staircase from inside the wall now.

A bank is the step's `bank`, or the nearest the walker can reach. `rs2004.quests.exec.legs` has the longer legs quests share: `open_container`, `climb`, `walk_and_talk`, `talk_and_close`, `talk_until` and `combine_by_id`; `rs2004.quests.exec.wool` gathers balls of wool. `rs2004.quests.exec.garlic.take_garlic(log)` climbs to Morgan's cupboard, opens it and searches for a clove; each climb or Open costs a pass, and it returns `True` once Garlic is held. Use it with `yield from`. `rs2004.quests.exec.fund_coins.fund_quest_coins(target, log, label=None)` earns pack coins up to `target` by pickpocketing Men: Varrock's only while the 10-coin Al Kharid toll is still owed, then Al Kharid's, buying and eating a Kebab from the seller beside him when Hitpoints fall below 3. It stops on a pending random event, or after two minutes without a coin, Thieving experience or a change in Hitpoints. `earn_quest_coins_step(target, label)` is a custom step that runs it.

Goblin Diplomacy's `tools` is a function returning the current keep list, including the configured food; the engine evaluates it before banking.

Before mining blurite, The Knight's Sword acquires a usable pickaxe even if its iron bars came from the bank. It also draws up to five banked Lobsters, Swordfish or Tuna when available; missing food does not block the quest, and it never leaves the cave to top food back up.

`rs2004.karamja_recovery.missing_boat_fare(from_, dest, coins, missing)` recognises a stranded traveller whose only missing route item is the 30-coin fare. `recover_boat_fare(dest, missing, log)` collects Luthas's payment, filling the plantation crate first when needed. `traversal.walk_to` calls it after an unfunded route fails, then retries the destination; available routes and teleports are tried first.

The phase-17h modules are registered too:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `upass` | `upass` | Starts with King Lathas, shoots the bridge rope with a fire arrow, crosses the spiked grid and the trapped corridor with the quest journal held open, burns the four orbs, crushes the unicorn, feeds the well three crests and the horn, builds the doll of Iban from its four elements, throws it into the pit, and follows Koftik out. |
| `regicide` | `regicide` | Takes the King's message and walks the pass again through the Well of Voyage, tracks King Tyras's camp through Isafdar's pockets, gathers the bomb's parts, distils naphtha at the Rimmington still, walks the pass a third time with the bomb, fires the catapult, and carries the letter past Arianwyn to King Lathas. |

Both own their inventories and declare `resume_at` over the pockets a walk can't leave. Underground Pass needs a melee kit banked, since it has no bank past the cave mouth and fights three paladins, three demons and Kalrag. Regicide needs a spade: no shop near Ardougne sells one, so the account must keep the one it took through the pass.

`quests.press_journal(name)` sends a journal's button without waiting, since an open modal suspends the pass's trap timers and the press has to land in its own tick. `reader.button_by_text(root, label)` finds the still's controls by their menu labels, as the packed component ids are the server's and not the client's.

The live run added these departures from rs2b0t:

- **Underground Pass**
    - A crossing sends its op to the loc cardinal to its stand, as a row of ledges ties by distance and the diagonal one refuses.
    - A crossing still landing is waited out, and a step back onto the walkable graph asks again whether the rest can be walked, so a tunnel door beside the target isn't taken by accident.
    - Fights renew a lapsed attack and eat as they go, since a second paladin engaging lapses the first attack.
    - A drop gets a few ticks to land, and a paladin who left no crest still owes one.
    - Making room for the robes drops the spade last, because Regicide needs it.
- **Regicide**
    - The first wait for the King's messenger logs in again, since his timer only starts at login and a queue that just finished the pass hasn't logged in since.
    - The walk through the pass settles after the well's teleport before asking which crossing is outstanding.

The phase-17i module is registered too:

| Module in `rs2004.quests.defs` | Record id | Behaviour |
|---|---|---|
| `legends` | `legends` | Stocks the bank from the Magic Guild and Jiminua's before asking Radimus for the quest, cuts into the Kharazi Jungle and maps its three thirds, trades a copy for the bull roarer, befriends Gujuo, forges and blesses the gold bowl, descends the trials for the Book of Binding, kills Nezikchened three times and the three Viyeldi guardians, fetches the sacred water, grows and carves the Yommi tree, and takes the gilded totem and four training sessions from Radimus |

It owns its inventory and declares `resume_at` over the jungle and both cave complexes. rs2b0t's recipe runs it at 70 in every skill. The bank has to hold what nothing sells: a rune axe, a lockpick, unpowered orbs, cosmic runes and the seven cut gems (or a chisel and a pickaxe, for the gem rocks), as well as coins, food, prayer potions and a melee kit. The trials swallow the pack's last slot, so each leg's food float is its own number.

AIOQuester's `legends_reward` names the skill Radimus's sessions train, one of the twelve he offers, and defaults to Prayer. `rs2004.traversal.execute_teleport_hop(transport, log)` casts or rubs one teleport hop of a route.

The live runs added these departures from rs2b0t:

- The wait after swinging the bull roarer counts ticks, eats, and kills what the noise set on the swinger, since a Jungle Savage killed a character standing through rs2b0t's wall-clock wait.
- A hat, shield or leg slot with nothing to wear no longer parks the quest, as a death can lose a piece nothing on the route sells. Only the body does.
- Radimus's conversation is driven to its end rather than waited on, since it shut after the first session on every run and the wait sat out its whole budget. The engine's next attempt talks to him again.

## Kit

| Module | Has |
|---|---|
| `rs2004.quests.weapons` | `MELEE_WEAPONS` and `PICKAXES` by tier, the dragon weapons' quest gates, and `best_held`, `best_banked`, `wielded_weapon`, `pack_weapon`, `live_best_weapon` |
| `rs2004.quests.armour` | `QUEST_ARMOUR` and `armour_choice(snap, slot)`: what's worn, else the best wearable in the pack, else in the bank |
| `rs2004.quests.strike` | `strike_spell(magic, count)` and `prepare_strikes(snap)`, the runes for 150 casts |
| `rs2004.quests.strike_combat` | Casting Strikes from cover: `ready_strikes`, `take_strike_cover`, `cast_strike`, `cast_from_cover` |
| `rs2004.quests.food`, `gear` | `quest_food.name`, `FOOD_FLOAT`, and `quest_loadout.current`, which AIOQuester sets |
| `rs2004.quests.journal_text` | `normalize_journal(lines)`, a journal as one line to search |


## Shield of Arrav and its supplier

AIOQuester offers `arrav_gang` (`random`, `phoenix` or `blackarm`), `arrav_partner` (the other character's name) and `arrav_certs` (default 2). `random` hashes the character's name so restarting keeps the same gang. The two partners meet at Varrock east bank to trade the weapon-store key, the Black Arm shield half and one certificate. The Phoenix partner mints before splitting; neither side redeems until it has paid what it owes. A solo character can redeem a banked certificate; otherwise the quest parks with the missing partner named in its reason.

`bots/arrav_supplier.py` is a separate certificate supplier. Start it on an unjoined character with coins banked and a Phoenix member named by `partner` to provide the first store key. It prepares Straven's mission before joining Black Arm, then uses the report on Straven to join Phoenix too. It collects both halves, mints and banks certificates until `cert_target` (default 10, minimum 2). It never redeems: redeeming would stop the supply. Proven mission and memberships are saved under `ArravSupplierState` for restarts.

`rs2004.partner_handoff.run_handoff(spec)` moves one exact item ID between two named characters, waits through both trade screens and checks the pack after the trade closes. Its `Record` fields are `partner`, `rendezvous`, `id`, `name`, `giving`, `label` and `log`. Use it with `yield from`.

## Hero's Quest and its partner

AIOQuester's `hero_partner` names the character running the other gang, since the master thief armband can't be earned alone. There is no gang setting: Grip refuses a Black Arm attacker and Katrine a Phoenix candlestick, so the gang is the one the character joined for Shield of Arrav.

Leave `arrav_partner` or `hero_partner` blank to pair automatically with an eligible opposite-gang
AIOQuester in the same process and configured world. Pairing requires mutual claims, expires stale peers
after fifteen seconds and preserves an active trade's partner. Explicit names override discovery and can
coordinate accounts in separate processes. The native message bus supplies discovery; browser
BroadcastChannel and cross-process automatic discovery are outside this port.

## The barcrawl

`bots/barcrawl.py` banks for coins, obtains Alfred Grimhand's card, visits all ten bars nearest first and hands the signed card to the Barbarian Outpost guard. It has no settings. `rs2004.quests.barcrawl.run_barcrawl.ensure_barcrawl(log, on_progress=None)` is the same tour for another bot or quest; `on_progress(signed, total)` reports the card's progress. The caller supplies coins (`BARCRAWL_GP` in `barcrawl_logic` includes travel money). `read_card(log=None)` returns a record with `remaining` bars and `done`, or `None` when unreadable. Both functions are generators. A completed card's refusal to Read because the character is too drunk counts as fully signed.


AIOQuester's `gather_wilderness_planks` boolean defaults to `true`. Set it to `false` to
prevent Dragon Slayer's supply gatherer from collecting Wilderness planks, including a
partial ship repair or later replacement. The delegated bot restores the previous gather
policy on stop. AccountLeveler forwards its Wilderness setting to this option.
Witch's House checks for a usable fire staff before buying Fire Strike runes, and preserves
fire staves while preparing inventory.

## Recovery and preparation invariants

All 63 quest definitions are implemented. `decide(snap)` chooses a leg from current state; resumable
progress and interrupt recovery must not depend solely on a suspended generator's locals. Quest-list
state and journals establish stage floors; unreadable/stale pages must not regress recognized progress,
while an authoritative not-started result may reset it. Runtime specs cover journal boundaries and
restart behavior.

Inventory preparation is bank-first and equipment-aware, with quest-specific item caps and bounded
preparation/retreat failure. An unselected sealed-area owner must not be abandoned; recover/exit the
current pocket before normal banking or quest selection. Deposits require backpack acknowledgement.
Combat preparation counts owned worn/carried/banked gear and provisions required spell runes and damage
budgets. Watchtower's quest-owned dragon hunt confirms its exit, cleans up on failure and refreshes bank
state before selection resumes. These rules also apply when resuming a partially completed quest.

The [stdlib runtime-spec guide](../Building.md#writing-stdlib-runtime-specs) explains the test fixture
and pocketpy constraints. Real-speed acceptance gaps and recurrence-based observations are maintained
in [GitHub issues](https://github.com/ineedbots/lc-headless/issues), including
[#34](https://github.com/ineedbots/lc-headless/issues/34) for phases 17h/17i.
