# Hunting

`rs2004.hunting` is rs2b0t's boss and dragon framework (`api/combat/hunting/`): the dragon sites, the fight tasks that hold a safespot or chase a target, the walks in and out of a lair, the bank trip that restocks one, and the pure decisions under all of it. JiveDragons, JiveDemons and JiveKBD (`scripts/bots/`) are built on it. A script imports it:

```python
from rs2004.hunting import TAVERLEY_BLUE, Fight, Retreat, HoldSafespot, WalkToSpot, BankOpts, bank_routine, enter_lair
```

- [The host](#the-host)
- [Sites](#sites)
- [The tasks](#the-tasks)
- [Supplies and the lair](#supplies-and-the-lair)
- [Decisions](#decisions)
- [Loot under guard](#loot-under-guard)

## The host

The tasks and the supply walks don't keep state of their own about the run. They ask the bot, the **host**, which they're given. A host is any object with these:

| Member | For |
|---|---|
| `log(message)`, `vlog(message)` | Logging; `vlog`, for the traces a Verbose setting shows, is optional |
| `set_status(text)` | The status line |
| `park_for(reason)` | Stops the run where it stands, for a reason the operator must fix |
| `count_bank_trip()`, `count_kill()`, `count_burial()` | Counters |
| `style()` | `'melee'`, `'mage'` or `'range'` |
| `food_name()`, `food_withdraw()` | The food, and how many a trip takes |
| `weapon_name()`, `ammo_name()`, `spell_name()` | The gear |
| `pick_weapon(available)` | Optional: given the names on hand at the bank, settles the weapon before it's withdrawn |
| `keep_extra()` | Names the bank trip keeps on top of the gear and food |
| `leave_by_walk()` | Whether to walk out rather than teleport |
| `died`, `target_idx` | Attributes: whether a death is being recovered, and the npc index being fought or `None` |
| `hp_fraction()`, `panic_hp()`, `retreat_hp()` | Health, and the two lines as fractions |
| `has_food()`, `need_eat()`, `eat_once()` | Food; `eat_once` is **Wait** |
| `bury_bones()`, `bone_name()` | Whether to bury, and what |
| `safespot_index()`, `set_safespot_index(n)` | The safespot ladder's place |
| `fight` | Optional: the `Fight` task, so the others can interrupt it |
| `rotate_spawns()`, `shield_ready()` | Optional: whether melee moves between spawns, and whether the Dragonfire shield is on where it's needed |
| `arm_special()` | Optional, **Wait**: arms the special for the next swing |

A method on the bot class is the way to give each: pocketpy can't set a method on an instance. An attribute named like one of the methods hides it, so a bot keeps its own values under other names (`combat_style` for `style()`, `food_withdraw_count` for `food_withdraw()`).

## Sites

`DragonSite` holds everything about one lair. Every field defaults to `None`, so a site names only what it has:

| Field | Is |
|---|---|
| `key`, `label` | The setting's value, and its name |
| `target`, `also_hunt`, `bones` | The npc fought, any it fills the respawn time with, and the bones they drop |
| `safespots`, `melee_anchor`, `stands` | The ladder of tiles mage and range fight from, where melee waits, and numbered `DragonStand`s (`label`, `tiles`, `anchor`) for a site with several |
| `approach` | Tiles the walk in passes, one per obstacle |
| `gate`, `key_item` | A door (`loc_id`, `op`, `outside`, `inside`) and the key it takes (`name`, `id`) |
| `talk_gate`, `fee_gate` | An npc who lets you in (`npc`, `op`, `choose`, `stand`); one who charges (`npc`, `op`, `coins`, `stand`, `entrance`, and `paid_line` and `prepaid_line`, lower-case parts of the lines he says) |
| `exit`, `walk_out` | A loc that leaves (`loc_id`, `op`, `stand`); the tile the walk out ends on |
| `bank`, `escape_teleport_id` | The bank stand, and the catalog teleport that leaves |
| `ranged_threat`, `fire_at_range` | Whether the room hits a safespot anyway, and whether the dragons breathe from ten tiles |
| `antipoison`, `antifire`, `axe`, `coins`, `food`, `food_per_trip`, `loot_setting` | What a trip carries, and the setting that holds its loot list |

`in_area(tile)` is whether a tile is in the lair; `with_changes(**fields)` copies the site with some fields replaced. `in_box(min_x, max_x, min_z, max_z, level)` makes an area test for one.

| Name | Is |
|---|---|
| `TAVERLEY_BLUE`, `TAVERLEY_BLACK` | Taverley Dungeon's blue and black dragons, behind the dusty-key gate |
| `HEROES_BLUE` | The Heroes' Guild dragon, fought through its fence |
| `GUTANOTH_BLUE` | The Gu'Tanoth Enclave's blue dragons and greater demons, six stands |
| `BRIMHAVEN_IRON`, `BRIMHAVEN_STEEL` | Brimhaven Dungeon's metal dragons, which breathe at range, past Saniboch's fee |
| `DRAGON_SITES`, `SITE_OPTIONS` | The six by key, and their keys for a setting |
| `STAND_SITE_KEYS`, `MAX_STANDS` | The sites with several stands, and the most any has |
| `ENCLAVE_TARGET_OPTIONS`, `enclave_targets(site, mode='both')` | `'both'`, `'dragons'` or `'demons'`, and the Enclave site with that target; any other site as it is |
| `site_for(key)`, `stand_for(site, n)`, `hunt_names(site)`, `needs_shield(site, style)` | The site for a key (Taverley blue for an unknown one), its stand `n` from 1 (clamped), its target then fillers, and whether `style` wears the Dragonfire shield there |

## The tasks

Each takes the host and the site.

| Task | Does |
|---|---|
| `Fight(host, site)` | Picks a target in range of the safespot, or follows one into reach for melee, attacks and holds the fight until it dies, eating and arming the special through it. `blocks_loot()`, `has_chase_target()`, `reset()` and `interrupt_watch()` let the bot's other tasks work around it |
| `Retreat(host, site)` | Off the safespot and under `retreat_hp()`, or out of food, walks to the nearest safespot |
| `HoldSafespot(host, site)` | Rotates the ladder when a hit lands on it or nothing has been in sight for `SAFESPOT_BLIND_MS` |
| `WalkToSpot(host, site)` | Back to the fight tile from wherever the run is |

`anchor_for(site, style, index)` is the tile a style fights from, and `chases_target(site, style)` whether it follows the target.

## Supplies and the lair

The **Wait** functions take the host first.

| Name | Is |
|---|---|
| `BankOpts(...)` | What `bank_routine` restocks: `withdraw_food`, `deposit_inventory`, `rune_casts` and `rune_buffer`, `ammo`, `escape_stock` (spare escape casts), `heal_to` (a fraction), `potions` (boost `PotionPlan`s), `flasks` (`FlaskPlan`s), `wear`, `carry` and `leave`. All keyword, all optional |
| `bank_routine(h, site, opts)` | **Wait.** Leaves the lair, banks the loot, heals at the booth, restocks, and counts the trip once it has run to the end |
| `enter_lair(h, site)` | **Wait.** Walks in: the approach, the gate and key, the fee or the guard |
| `leave_lair(h, site)` | **Wait.** Out by the escape teleport, or the walk out when the cast won't fire |
| `teleport_out(h, site)` | **Wait.** Casts the escape teleport, up to three times: `None` once outside the lair, else why the cast won't fire |
| `walk_approach(h, site, stand=None)` | **Wait.** The approach legs from wherever the run is |
| `escape_runes_for(teleport_id)` | An `EscapeSpell`: `runes` as `(rune, count)` pairs, `level` and `label` |
| `FlaskPlan(flask, doses, want)`, `antipoison_plan(want)`, `prayer_plan(want)`, `antifire_plan(want)` | Flasks topped up by count |
| `dose_to_drink(count, doses=None)` | The smallest dose held, by `count(name)`; the antipoison doses by default |
| `ANTIPOISON_DOSES`, `PRAYER_DOSES`, `ANTIFIRE_DOSES` | Each potion's forms, (4) to (1) |
| `SHIELD`, `COINS`, `POISONED` | `'Dragonfire shield'`, `'Coins'`, and the poisoning line's lower-case part |
| `fee_prepaid(site)` | Whether the fee was paid on an attempt whose entrance didn't follow, so the next goes straight in |
| `in_cell()`, `leave_cell(h)`, `acquire_key(h, site)` | Velrak's jail: whether the run stands in it, getting out (**Wait**), and fetching the dusty key (**Wait**, `'held'`, `'bank'` or `'fetch'`) |
| `withdraw_to(name, target)` | **Wait.** Tops the pack up to `target`, and gives how many arrived |
| `wait_fed(cond, ms)` | **Wait.** Waits for `cond`, running the `sustain` hook every tick |

## Decisions

Pure functions, with the inputs rs2b0t passed in one object given positionally.

| Name | Is |
|---|---|
| `next_safespot(index, spots, hurt, blind_ms)`, `hurt_on_spot(ranged_threat, on_spot, last_hp, hp)` | The ladder's next index, and whether a hit says the tile is wrong |
| `retreat_due(in_lair, on_safespot, hp_frac, retreat_hp, has_food, spots)`, `hold_due(on_safespot, has_food)`, `loot_halts(hp_frac, panic_hp, retreat_hp)` | When to retreat, when to walk back, when to stop looting |
| `nearest_spot(from_, spots)`, `retreat_aim(rotated, from_, spots)` | The nearest safespot; `(index, next)` for a retreat, keeping a failed attempt's rotation |
| `body_origin(tile, size)`, `gap_to(from_, tile, size)` | A body's south-west tile, and the gap to its nearest face |
| `Sighting`, `note_sighting(prev, tile, now)`, `settled(s, now, ms)` | Whether a body has held its tile long enough to click |
| `attack_range_for(style)`, `engage_range_for(style)`, `loot_reach(fire_at_range)` | 1, 7, 10; one inside that; 10 or 14 |
| `chase_mode(style, fire_at_range)`, `prayer_for(style, fire_at_range)`, `prayer_sip_due(points, max_points)` | Melee on a site that breathes at range chases, prays Protect from Melee, and sips a Prayer potion at or under the higher of 8 points and 15% of the level |
| `shield_gate(style, fire_at_range, has_shield)`, `style_gate(style, fire_at_range)` | Why a run can't start, or `None` |
| `antifire_due(in_lair, tick, until)`, `antifire_lapsed(saw_shield, saw_potion)` | `ANTIFIRE_TICKS` from a sip, less `ANTIFIRE_MARGIN_TICKS`; a shield line with no potion line means the dose ran out. `SHIELD_ABSORBS` and `POTION_PROTECTS` are the lines, as lower-case parts for `game_messages` |
| `next_approach_index(stops, here)` | The approach stop to carry on from |
| `wants_drop(item, f)`, `is_clue_obj(id)` | A drop to take: `f` has `loot` (lower-case names), `bank_common`, `solve_clues`, `bury_bones` and `bone_name` |
| `key_status(held, banked)`, `keep_doses(potion_doses, antipoison_doses, carries)` | `'held'`, `'bank'` or `'fetch'`; the doses the key stop's deposit keeps |
| `site_tile_of(schema, bag, key, site)` | The site's tile, unless the setting under `key` has been moved off its schema default |

## Loot under guard

`guarded(drop, bodies, radius=4)` is whether a drop's tile is within `radius` (`LOOT_GUARD`) of any body, each with a `tile` and a `size`, so the loot walk leaves a pile at a demon's feet until it's gone.
