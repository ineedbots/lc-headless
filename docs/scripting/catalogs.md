# Catalogs and behaviours: `rs2004.catalogs`

rs2b0t's world data, its planners, and reusable tasks, in snake_case. Unlike everything else in this reference, they aren't builtins: import what you use.

```python
from rs2004.catalogs import pickaxe_req, has_all_tools, resolve_mining_location, ContinueDialog

camp = resolve_mining_location('Use Closest', game.tile())
if not has_all_tools([pickaxe_req()], skills.level, inventory.count):
    ...
```

Each part is also a module of its own, such as `rs2004.catalogs.tools`; `rs2004.catalogs` re-exports them all.

Item, NPC and scenery names in the tables are the 289 cache's, and a test checks every one against it. Something added after revision 225 or 274 doesn't exist on those servers.

- [Records](#records)
- [Tools](#tools)
- [Getting tools](#getting-tools)
- [Fishing and mining](#fishing-and-mining)
- [Gathering camps](#gathering-camps)
- [Other tables](#other-tables)
- [Combat](#combat)
- [Loadouts](#loadouts)
- [Trading partners](#trading-partners)
- [Tasks](#tasks)
- [Ported bots](#ported-bots)

### Callable arguments

Many planners take functions rather than values, so they can be tested and can read the bank as well as the backpack:

| Name in signatures | Pass | Such as |
|---|---|---|
| `skill_level`, `level` | `name -> int` | `skills.level` |
| `count`, `inv_count` | `name -> int`, what's carried | `inventory.count` |
| `bank_count` | `name -> int`, what's banked | `bank.count`, or a count you remembered |
| `worn` | `name -> bool` | `equipment.contains` |
| `available` | `name -> bool` | `lambda n: inventory.contains(n) or equipment.contains(n)` |

## Records

A table entry is a `Record`: its fields are attributes, nested dicts are records too, and a field the entry doesn't set reads as `None`.

| Member | Gives |
|---|---|
| `record.<field>` | The field, or `None` |
| `record.get(key, default=None)` | The field, or `default` when it's missing or `None` |
| `record.keys()` | The fields it sets |

## Tools

### Types

| Type | Fields |
|---|---|
| `ToolTier(name, level, attack_level=1)` | `name`; `level`, the skill level to use it; `attack_level`, to wield it |
| `ToolReq` | `kind`: `'tiered'` (with `skill`, `tiers` best first, `label`, `equip`) or `'exact'` (with `name`, `min`, `restock`, `equip`) |
| `ToolRestockStep` | `name`, `qty`, `equip`: one withdrawal |

### Data

| Constant | Value |
|---|---|
| `PICKAXES` | Rune (Mining 41, Attack 40), Adamant (31, 30), Mithril (21, 20), Steel (6, 5), Iron, Bronze (1, 1). Best first |
| `AXES` | Rune (Attack 40), Adamant (30), Mithril (20), Steel (5), Iron, Bronze. This revision gates axes on Attack only |
| `TINDERBOX`, `HAMMER`, `KNIFE`, `CHISEL`, `NEEDLE` | `'Tinderbox'`, `'Hammer'`, `'Knife'`, `'Chisel'`, `'Needle'` |

### Requirements

| Function | Gives |
|---|---|
| `pickaxe_req(equip=True)` | A tiered requirement for a pickaxe |
| `axe_req(equip=True)` | A tiered requirement for an axe |
| `exact_tool(name, min=1, restock=None, equip=False)` | An exact requirement: at least `min`, topped up to `restock` (`min` when `None`) |
| `tinderbox_req()` | `exact_tool('Tinderbox')` |
| `tool_attack_level(name)` | The Attack level to wield an axe or pickaxe; 1 for other tools |
| `can_wield_tool(name, attack_level)` | Whether that Attack level wields it |

### Checks

| Function | Gives |
|---|---|
| `has_tool_req(req, skill_level, count)` | Whether one requirement is met |
| `has_all_tools(reqs, skill_level, count)` | Whether all are |
| `missing_tool_labels(reqs, skill_level, count)` | Labels of the unmet ones |
| `tool_kit_label(reqs, skill_level, count)` | Text such as `'Rune axe + Tinderbox'`, with `'axe (bronze to rune)'` for a tier not held |
| `best_from_tiers(level, tiers, available)` | The best tier `level` can use that `available(name)` allows, or `None` |
| `best_pickaxe(mining_level, available)`, `best_axe(woodcutting_level, available)` | The same for each |
| `tool_keep_names(reqs)` | Every name that could meet the requirements, for a deposit's keep list |
| `best_held_tool_names(reqs, skill_level, count)` | The best tier held of each tiered requirement, and the exact tools held: what a deposit keeps |
| `surplus_held_tool_names(reqs, skill_level, count)` | Tiers held that are worse than the best held, such as a bronze axe beside a steel one |
| `tools_needing_equip(reqs, skill_level, count, worn)` | Tools to wield now: held, marked `equip`, not worn, and Attack high enough |
| `tool_restock_plan(reqs, skill_level, inv_count, bank_count)` | `ToolRestockStep`s to withdraw: the best owned tier when it's only in the bank, and exact tools short of their restock |
| `bank_has_better_gather_tool(reqs, skill_level, inv_count, bank_count)` | Whether the bank holds a better usable axe or pickaxe than the one carried |

```python
reqs = [axe_req(), tinderbox_req()]
keep = best_held_tool_names(reqs, skills.level, inventory.count)
yield from bank.deposit_all_matching(deposit_all_except(keep))
```

## Getting tools

Planning to buy, repair or smith a missing tool. Plans are pure: they read the world through an `AcquireWorld` and return what to do; your bot does it.

### Types

| Type | Fields |
|---|---|
| `ToolVendor` | `keeper` (the shopkeeper's name), `stand`, `bank_stand`; for one underground, `hop_from`, `hop_loc`, `hop_action` |
| `ShopOffer` | `name`, `cost`, `vendor` |
| `ToolAcquirePlan` | `kind`: `'repair'` (`broken_name`, `label`, `vendor`, `prefer`), `'buy'` (`name`, `cost`, `qty`, `vendor`, `equip`, `reason`) or `'smith'` (`name`, `bar`, `smith_level`, `vendor_bank`, `anvil_stand`, `equip`, `reason`) |
| `AcquireWorld(skill_level, held_count, inv_count, bank_count, worn)` | What the planners read, all functions. `held_count` counts backpack and worn |

### Data

| Constant | Value |
|---|---|
| `BOB_VENDOR` | Bob's Brilliant Axes, Lumbridge: axes, and repairs |
| `NURMOF_VENDOR` | Nurmof, Dwarven Mine: pickaxes, and repairs; reached through the trapdoor north of Falador |
| `GERRANT_VENDOR` | Gerrant, Port Sarim: fishing gear |
| `HARRY_VENDOR` | Harry, Catherby: fishing gear, bait and nets |
| `PICKAXE_SHOP_COSTS`, `AXE_SHOP_COSTS`, `FISHING_SHOP_COSTS` | Name to price |
| `AXE_SMITH_LEVEL`, `AXE_BAR_FOR` | Smithing level and bar for each axe |
| `GERRANT_ONLY_FISHING` | `['feather', 'fly fishing rod']` |
| `VARROCK_ANVIL_STAND`, `VARROCK_ANVIL_BANK` | Where to smith an axe |
| `COINS`, `BROKEN_AXE` | `'Coins'`, `'Broken axe'` |
| `TOOL_ACQUIRE_OPTIONS` | `['Off', 'Buy / repair']`, a setting's options |
| `TOOL_ACQUIRE_SETTING` | rs2b0t's ready-made [`SettingDef`](settings.md#settingdef) for them: a `'string'`, default `'Off'` |
| `FORGETFUL_BANK_ODDS` | 100 |
| `FORGETFUL_BANK_SETTING` | rs2b0t's `SettingDef` for wandering off after one bank visit in that many: a `'boolean'`, default `False` |

### Planners

| Function | Gives |
|---|---|
| `parse_tool_acquire_mode(raw)` | `'on'` or `'off'` from a setting's value |
| `plan_gather_tool_acquire(reqs, world, upgrade=False)` | A plan for the first tiered requirement that needs one, a broken tool first; or `None` |
| `plan_pickaxe_acquire(world, upgrade=False)` | Repair a broken pickaxe, or buy one when none is owned, or a better affordable one with `upgrade` |
| `plan_axe_acquire(world, upgrade=False)` | Repair a broken axe, or get one: Bob's shop up to steel, or smith one from a bar and hammer on hand, whichever is better |
| `plan_broken_tool_repair(held_or_worn)` | A repair plan for a held broken pickaxe or axe, or `None` |
| `plan_fishing_gear_buys(method, world, near=None, bait_qty=1000)` | Buy plans for each missing piece of a [`FishingMethod`](#fishing-and-mining)'s gear that's for sale and affordable. Bait and feathers are topped up to `bait_qty` |
| `plan_fishing_gear_acquire(method, world, near=None, bait_qty=1000)` | The first of those, or `None` |
| `fishing_gear_shop_cart(method, world, near=None, bait_qty=1000)` | The plans at the first plan's shopkeeper, so a fly rod and feathers are one visit |
| `fishing_vendor_for(name, near=None)` | Gerrant for feathers and fly rods; otherwise whichever is nearer `near`, or Harry for bait and big nets and Gerrant for the rest |
| `fishing_shop_cost(name)` | The price, or `None` |
| `best_owned_tier(level, tiers, count)` | The best usable tier owned |
| `pickaxe_shop_offers()`, `axe_shop_offers()` | `ShopOffer`s |
| `best_affordable_shop_tier(level, tiers, offers, coins, owned)` | The best usable, affordable offer better than `owned`, or `None` |
| `best_smithable_axe(woodcutting_level, smithing_level, owned, bar_count, has_hammer)` | `(name, bar, smith_level)` of the best axe a bar on hand can make, or `None` |
| `buy_plans_cost(plans)` | Their total cost |
| `coins_to_withdraw(need, inv_coins)` | Coins to take from the bank |
| `can_fund_plan(plan, inv_coins, bank_coins)` | Whether the coins cover it |
| `acquire_keep_names(plan, extra=None)` | What a deposit before the trip keeps: coins, the broken tool, or the bar and hammer |
| `shopable_missing_fishing_gear(gear, count)` | Names of missing pieces a shop sells |
| `is_fishing_bait_piece(piece)`, `with_bait_target(method, bait_qty)` | Bait helpers |
| `needs_tool_vendor_surface_hop(vendor, here)` | Whether an underground vendor's trapdoor is needed from `here` |
| `walk_to_tool_vendor(vendor, log=None)` | **Wait.** Walks to the vendor's stand, through Nurmof's trapdoor when above ground. `True` on arrival |

```python
def held_count(name):
    return inventory.count(name) + (1 if equipment.contains(name) else 0)

world = AcquireWorld(skills.level, held_count, inventory.count, lambda name: 0, equipment.contains)
plan = plan_gather_tool_acquire([pickaxe_req()], world)
if plan is not None and plan.kind == 'buy':
    yield from walk_to_tool_vendor(plan.vendor, log)
    opened = yield from shop.open(plan.vendor.keeper)
    if opened:
        yield from shop.buy(plan.name, plan.qty)
```

Here `lambda name: 0` says nothing is banked; pass a real count when you've looked in the bank.

## Fishing and mining

### Fishing

| Name | Is |
|---|---|
| `FishingGearPiece` | `name`, `min` (to fish at all), `restock` (what a bank trip tops up to) |
| `FishingMethod` | `name`, `op` (the spot's option), `pair` (the other option such a spot has, to tell spots apart; `''` for none), `gear` |
| `FISHING_METHODS` | Small net, bait rod (sardine/herring), fly fishing, bait rod (pike), big net, lobster cage, harpoon (tuna/swordfish), harpoon (sharks), oily rod |
| `FISHING_METHOD_OPTIONS` | Their names, for a setting |
| `ALL_FISHING_GEAR_NAMES` | Every gear name |
| `WHIRLPOOL_IDS` | `[403, 404, 405, 406]` |
| `resolve_fish_method(name)` | The method of that name, or the first, small net |
| `gear_keep_names(method)`, `gear_label(method)` | Its gear's names, and a label |
| `has_fishing_gear(method, count)`, `missing_fishing_gear(method, count)` | Whether the gear is carried, and which pieces aren't |
| `fishing_restock_plan(method, inv_count, bank_count)` | `[(name, qty)]` to withdraw |
| `spot_matches_method(actions, method)` | Whether a spot with these options is one the method fishes |

```python
method = resolve_fish_method(self.settings.method)
spot = npcs.query().name('Fishing spot').where(lambda n: spot_matches_method(n.actions(), method)).nearest()
```

### Mining

Every ore rock is named "Rocks", so ores differ only by id.

| Name | Is |
|---|---|
| `ROCK_OPTIONS` | `['Clay', 'Copper', 'Tin', 'Iron', 'Silver', 'Coal', 'Gold', 'Mithril', 'Adamantite', 'Runite']`, lowest tier first |
| `ROCK_TIER_ORDER` | The same list |
| `ROCK_TYPES` | Ore name to loc ids, such as `'Copper': [2090, 2091]` |
| `QUEST_ROCK_TYPES` | `'Blurite'` and `'Limestone'`, kept apart |
| `GAS_ROCK_IDS`, `GAS_ROCK_TICKS` | The exploding rocks of the gas random event, and how long they last |
| `BROKEN_PICKAXE` | `'Broken pickaxe'` |
| `resolve_rock_ids(names)` | The loc ids of the named ores, without regard to case; unknown names skipped |
| `rock_tier_by_id(id)` | The rock's tier, higher is better; -1 for one that isn't an ore rock |

```python
rock = locs.query().id(resolve_rock_ids(['Copper', 'Tin'])).within(10).nearest()
```

## Gathering camps

Fishing spots, mines and woods, each a `Record` with `name`, `spot` (a `Tile`), `bank_stand`, `booth_name`, `booth_op`, `resources`, `verified`, and where they apply `camp_radius`, `chase_radius`, `sweep`, `obstacles`, `notes`, `range_stand`, `range_name` and `recommended_combat`.

| Name | Is |
|---|---|
| `FISHING_LOCATIONS`, `MINING_LOCATIONS`, `WOODCUTTING_LOCATIONS` | The camps |
| `FISHING_LOCATION_OPTIONS`, `MINING_LOCATION_OPTIONS`, `WOODCUTTING_LOCATION_OPTIONS` | A setting's options: the special choices, then each camp's name |
| `MINING_LOCATION_OPTION_LABELS` | Labels with the recommended combat level |
| `USE_CLOSEST`, `USE_START_POSITION`, `USE_CUSTOM_POSITION` | `'Use Closest'`, `'Use Start Position'`, `'Use Custom Position'` |
| `DEFAULT_BOOTH_NAME`, `DEFAULT_BOOTH_OP` | `'Bank booth'`, `'Use-quickly'` |
| `DEFAULT_CAMP_RADIUS`, `DEFAULT_CHASE_RADIUS` | 64, 40 |
| `MAP_SQUARE` | 64 |
| `LOCAL_MINE_PREFER_RADIUS` | 12 |
| `SHILO_WATER_VENDOR` | The water vendor in Shilo Village |
| `ENT_NPC_IDS`, `ENT_LIFE_TICKS` | The ent random event's NPCs, which share trees' names, and how long they last |

| Function | Gives |
|---|---|
| `resolve_fishing_location(setting, start_tile)`, `resolve_mining_location(...)`, `resolve_woodcutting_location(...)` | The camp a setting names. `'Use Closest'` is the nearest in a straight line; `'Auto'` the nearest in the start tile's map square; the start and custom positions give `None` (work where you stand); a name matches without regard to case |
| `resolve_gathering_location(setting, start_tile, table)` | The same for any table |
| `location_options(table)` | A table's setting options |
| `booth_fields(loc)` | `(booth_name, booth_op)`, the defaults when `loc` is `None` or doesn't say |
| `mining_location_label(loc)` | `'Dwarven Mine (65 Combat recommended)'` and so on |
| `resolve_camp_radius(camp_radius, fallback=64)`, `resolve_chase_radius(chase_radius, fallback=40)` | A radius, or the fallback when `None` |
| `same_map_square(a, b)` | Same level of the same 64 × 64 map square |
| `bank_distance(start, tile)` | Straight-line distance, whatever the level |
| `pick_nearest_prefer_local(candidates, distance, prefer_radius=12)` | The nearest candidate, of those within `prefer_radius` when there are any |
| `pick_bucket_nearest(candidates, bucket, distance, prefer_radius=12)` | The nearest of the candidates in the best bucket, such as the best ore in camp |
| `is_ent_npc_id(id)`, `ent_npc_on_tile(npcs, tile)` | Ent checks |
| `should_cooldown_gather_tile(got_product, other_targets)` | Whether to leave a rock or tree alone for a while after a click that gave nothing |

## Other tables

### Cows and the Al Kharid toll

| Name | Is |
|---|---|
| `COW_LOCATIONS` | Records of `name`, `anchor`, `uses_al_kharid_toll`, and `bank_destination` (`name`, `tile`) |
| `COW_LOCATION_OPTIONS` | `'Auto'`, each field, `'Start tile'` |
| `DRAYNOR_BANK`, `FALADOR_EAST_BANK`, `ARDOUGNE_WEST_BANK`, `AL_KHARID_BANK` | Bank tiles |
| `TOLL_COIN_TARGET` | 20 |
| `resolve_cow_location(setting, start)` | `'Auto'` is the nearest field; `'Start tile'` is `None`; a name matches without regard to case |
| `nearest_cow_location(tile)` | The nearest field |
| `is_cow_field_loot_tile(anchor, leash_radius, tile)` | Whether loot on the tile is the field's |
| `needs_toll_coins(location, enabled)`, `should_bootstrap_toll_coins(location, start, coins, enabled)` | Toll checks |
| `cow_bank_destination(location, toll_enabled)` | `(name, tile)` of the bank to use |

### Runecrafting, thieving and herbs

| Name | Is |
|---|---|
| `RUNES` | Rune name to a record of `rune`, `talisman`, `level`, `bank`, `ruins` |
| `RUNE_OPTIONS`, `DEFAULT_RUNE` | The rune names; `'Air rune'` |
| `PICKPOCKET_TARGETS` | Records of `name` and `level`: Man and Woman (1) up to Hero (80) |
| `PICKPOCKET_TARGET_NAMES` | Their names |
| `ARDOUGNE_PICKPOCKET_TARGETS` | `['Guard', 'Knight of Ardougne', 'Paladin', 'Hero']` |
| `HERBS` | Records of `key`, `name`, `id`, `unid_id`, `level` |
| `HERB_OPTIONS` | Their names |

### Shops

| Function | Gives |
|---|---|
| `shop_db()` | The shop database by inventory name: each a dict of title, keepers, sell and buy rates, and items (`obj`, `name`, `baseline`, `restock_ticks`, `cost`, `stackable`, `members`). Loaded on first use |
| `shops_selling(item)` | `[(inventory name, shop)]` of the shops that stock the item, by name without regard to case |

The engine's prices (rs2b0t's `api/shop`). Each price climbs as stock leaves the shelf, so a full shelf costs far more than stock times cost. An item is a shop database item as a Record, and a shop a record with `sell` and `delta`:

| Function | Gives |
|---|---|
| `unit_price(item, shop, stock)` | What one costs with `stock` on the shelf |
| `shop_buy_price(base_cost, bought, sell_multiplier=100, delta=10)`, `buyout_cost(base_cost, stock, sell_multiplier=100, delta=10)` | The next one's price once `bought` have gone, and a whole shelf's |
| `expected_stock(item, seen, now_ms)` | The stock now, from what was `seen` (`count`, `at_ms`): it moves one towards the baseline every `restock_ticks` |
| `units_under_policy(policy, stock, baseline)` | How many to buy: everything for `{'kind': 'buyout'}`, down to `pct` percent of the baseline for `{'kind': 'floor', 'pct': ...}` |
| `buyout_plan(rec, stock, coins, chosen)` | What to buy of a shop's `chosen` items (lower-case names) with `coins`, the dearest first: Records of `obj`, `name`, `units` and `est_cost`. `stock` is `{obj: count}` |

### Walking destinations

| Name | Is |
|---|---|
| `WALK_DESTINATIONS` | Records of `name` and `tile`: Lumbridge, Varrock and other towns |
| `WALK_OPTIONS` | Their names |
| `resolve_destination(name)` | The record, or `None` |

### Cooking

| Name | Is |
|---|---|
| `COOK_LOCATIONS` | Records of `name`, `bank` (`name`, `tile`), `surface` (`stand`, `loc`, `loc_name`, `kind`, `arrive_radius`, `label`, or `None`), `obstacles`, `verified` |
| `COOK_LOCATION_OPTIONS` | `'Auto'`, each name, `'Custom'` |
| `COOKING_SURFACE_LOCS` | Every known range and fire: `x`, `z`, `level`, `name`, `kind` (`'oven'` or a fire) |
| `COOKING_RANGE_LOCS` | Range tiles |
| `CATHERBY_RANGE` | The Catherby range |
| `FISH_CAMP_COOK_PLANS` | Camp name to `{'pier': surface, 'bank': surface}` |
| `cook_location(name)` | The record, or `None` |
| `resolve_cook_location(setting, start, unlocked=None)` | `'Auto'` is the nearest bank whose location `unlocked(loc)` allows; `'Custom'` and unknown names are `None` |
| `nearest_cooking_range(origin, max_cheb=64)` | The nearest range on `origin`'s level, as a record of `stand`, `loc`, `loc_name`, `kind`, `label`, `notes`; or `None` |
| `nearest_cook_surface(origin, max_cheb=20)` | The nearest cooking surface, an oven before a fire |
| `cook_surface_for_fish_camp(camp_name, role='pier')` | A camp's curated surface: `'pier'` beside the spot, `'bank'` beside the bank |
| `resolve_fish_camp_cook_surface(camp_name, spot, max_cheb=64, role='pier')` | That, or else the nearest range to `spot` |
| `range_stand_from_loc(loc)` | The tile south of a range's corner |

### Firemaking

| Name | Is |
|---|---|
| `FIRE_SPOTS` | Name to a plot record: `bank`, and the rectangle `x0`, `x1`, `z0`, `z1` |
| `FIRE_SPOT_OPTIONS` | Their names |
| `LOG_LEVELS` | Log name to Firemaking level |
| `BURN_MODE_OPTIONS` | `['Off', 'Chop then burn']` |
| `parse_burn_mode(label)` | `'chop-then-burn'` or `'off'` |
| `logs_for_tree(tree_name)` | The logs a tree gives |
| `firemaking_level_for_logs(log_name)` | The level, or `None` |
| `resolve_fire_spot(name)`, `nearest_fire_spot(start)` | `(name, plot)`, or `None` |
| `local_fire_plot(origin, half=8)` | A plot centred on `origin` |
| `expand_local_fire_plot(plot, grow_by=4, max_half=24)` | The plot grown, or `None` past `max_half` |
| `in_fire_plot(tile, plot)` | Whether the tile is in it |
| `should_burn_full_load(mode, inventory_full, log_count, has_tinderbox)` | Whether to burn now |

#### Lanes

A full backpack burns best in a lane: a row of free tiles you light westward, stepping back a tile after each fire as the game does. `find_burn_lane` finds the best one in a plot, from the loaded scene's collision flags.

| Name | Is |
|---|---|
| `BURN_WEST`, `BURN_DIRS` | `(-1, 0)`, and the four directions, west first |
| `MAX_BURN_LANE` | 27 |
| `tile_key(tile)` | `'x,z'`, as the occupied sets hold tiles |
| `burn_lane_want(log_count)` | How many lights to want from one lane: the logs held, 1 to 27 |
| `run_in_dir(start, plot, direction, occupied, walkable, can_step, cap)`, `run_west(...)` | How many free tiles in a row from `start`, inside the plot, up to `cap`. Free is `walkable(tile)` and its key not in `occupied`; each step on must be `can_step(a, b)` |
| `find_burn_lane(plot, here, occupied, want, walkable, can_step, dirs=None)` | A record of `start`, `run` and `dir`, or `None`: a westward run that fits `want` logs, else the longest westward run, else any free tile, nearest first |
| `fire_reaction_ticks()` | Ticks between lights along a lane |
| `NoLightTiles()` | Tiles that answered "You can't light a fire here" this session: `add(tile)`, `has(tile)`, `size`, `merge(occupied)` (the occupied set with them added) and `clear()` |
| `light_fire(log_name)` | **Wait.** Lights the logs on your tile: `'lit'`, `'blocked'` (the game refused the tile) or `'stalled'` |

```python
refused = NoLightTiles()
plot = local_fire_plot(game.tile())
fires = {tile_key(l.tile()) for l in locs.query().name('Fire').within(20).results()}
lane = find_burn_lane(plot, game.tile(), refused.merge(fires), inventory.count('Logs'), reachability.walkable, reachability.can_step)
```

## Combat

### Food

| Name | Is |
|---|---|
| `FOOD_OPTIONS` | Food names for a setting, Shark down to Apple pie |
| `FOOD_FORMS` | Lower-case food to its partly eaten forms, such as cake, 2/3 cake, slice of cake |
| `FOOD_HEAL` | Lower-case form to hitpoints healed |
| `MIN_EAT_HP` | 5: always eat at or below this while food remains |
| `URGENT_HP_FRACTION` | 0.35 |
| `food_forms(food_name)` | Every form of the food |
| `is_food_item(name, food_name)` | Whether an item name is a form of the food |
| `is_edible_food(item, food_name)` | An unnoted item of the food |
| `food_count(items, food_name)` | How many bites the items hold |
| `food_heal_amount(food_name)` | What one bite heals; 8 for an unknown food |
| `eat_at_hp_threshold(max_hp, heal, min_hp=5)` | The hitpoints at or below which a bite heals in full |
| `should_eat_to_use_food(hp, max_hp, heal, count, min_hp=5)` | Eat when a bite heals in full, or at the floor |
| `should_eat_food(food_name, hp, max_hp, count, min_hp=5)` | The same, by food name |
| `should_hold_eat(attacked_this_tick, hp_fraction, urgent_at=0.35)` | Put eating off a tick: on the tick an attack started, unless health is urgent. Eating then would cost the swing |

```python
hp = skills.effective('hitpoints')
top = skills.level('hitpoints')
if should_eat_food('Lobster', hp, top, inventory.count('Lobster')) and not should_hold_eat(swing_started_this_tick(), skills.hp_fraction()):
    inventory.first('Lobster').interact('Eat')
```

### Attack timing

| Name | Is |
|---|---|
| `AttackClock` | Tracks the tick your attack animation started: `observe(animation, tick)` each tick, `attacked_this_tick(tick)`, `reset()` |
| `swing_started_this_tick()` | Whether your swing began this tick, from a shared clock |
| `bury_one_in_fight(bone_name)` | **Wait.** Buries one bone in a fight's cooldown, not on a swing's tick. `True` once it's gone |

### Potions

| Name | Is |
|---|---|
| `BoostPotion` | `skill`, `short` (a label), `flask` (the dose drawn when the loadout names none), `doses` (every form) |
| `PotionPlan` | `potion`, `flask`, `want` |
| `SUPER_ATTACK`, `SUPER_STRENGTH`, `SUPER_DEFENCE`, `RANGING_POTION` | The potions |
| `SUPER_SET` | The three supers |
| `BOOST_POTIONS` | Super attack and strength |
| `EMPTY_VIAL`, `BOOST_FLOOR` | `'Vial'`, 0.1 |
| `boost_faded(base, effective, floor=0.1)` | Whether a boost has worn down to within `floor` of base |
| `planned_potions(carry, potions=None)` | The dose form and count of each potion a loadout's carry list names |
| `ranging_plan(carry)` | The same for the ranging potion |
| `potion_to_sip(plans, held, levels)` | The potion to drink this tick, or `None`. `held(plan)` counts flasks; `levels(skill)` gives `(base, effective)` |

### Spells and keep lists

| Name | Is |
|---|---|
| `SPELL_DB` | Spell name (`'Wind Strike'`) to `ssb`, `level` and `runes` (`rune`, `count`) |
| `STAFF_RUNES` | Staff name to the runes it gives, such as `'Lava battlestaff'` to earth and fire |
| `runes_per_cast(spell_name, wielded)` | `[{'rune', 'count'}]` one cast takes, less what a wielded staff gives, or `None` for a spell the table lacks |
| `casts_available(spell_name, wielded, held)` | How many casts `held(rune)` pays for: `float('inf')` when a staff gives every rune, 0 for an unknown spell |
| `rune_withdraw_list(spell_name, wielded, casts)` | The runes to withdraw for that many casts |
| `spell_button_com(spell_name)` | The staff spell chooser's button for an autocast spell while the chooser is open, or -1. rs2b0t numbers it from the 289 interface; here it's found as [`autocast.arm`](side-tabs.md#autocast) finds it |
| `combat_keep_names(food, style, spell=None, ammo=None, weapon=None, extra=None)` | What a fight's deposit keeps: every form of the food, the spell's runes when `style` is `'mage'`, the ammo when `'range'`, the weapon, and `extra` |

### Gear

rs2b0t's `api/combat/equipment.ts`, `meleeWeapons.ts`, `ranged.ts` and `rangedSettings.ts`: the lists a fighting bot's settings offer, and the picks made from them.

| Name | Is |
|---|---|
| `BOWS`, `CROSSBOWS`, `DARTS` | The ranged weapons, Shortbow to Magic longbow, Crossbow to Karil's crossbow, Bronze to Rune dart |
| `ARROWS`, `BOLTS` | Bronze to Dragon arrow; Bronze to Rune bolts, then Broad and Bone bolts |
| `MELEE_WEAPONS` | One-handed melee weapons, so the shield slot stays free: the scimitars, swords, longswords and daggers, Dragon battleaxe and Dragon mace |
| `STAFFS` | Staff to the mystic staffs |
| `best_melee_weapon(available, attack, prefer_stab, unusable=None)` | The best of `available` (names) that `attack` can wield, or `None`: the highest tier, then the longsword's stab first when `prefer_stab` (the metal dragons are soft to it), a scimitar first otherwise. `unusable` is a set of names a wield already refused |
| `known_melee_weapon(names)` | The first of `names` that `MELEE_WEAPONS` knows, or `None` |
| `RANGED_WEAPONS`, `ROCK_CRAB_RANGED_WEAPONS` | `BOWS + DARTS` |
| `RangeLoadout` | `weapon`, `projectile` and `thrown` |
| `range_loadout_of(weapon, ammo)` | A dart is both the weapon and the projectile, and `thrown`; a bow fires `ammo` |
| `rock_crab_range_loadout(weapon, ammo)` | The same |
| `range_supply_empty(equipped, carried, ground)` | Whether all three counts are 0 |
| `CUSTOM_RANGED_SETTINGS` | `custom_bow` and `custom_ammo`, shown when `bow` or `ammo` is `'Other'`. Merge them into a schema that offers `'Other'` |
| `ranged_item(settings, key, fallback)` | The `bow` or `ammo` setting's item, or the custom name when it's `'Other'`. Raises `ValueError` when that name is empty |

```python
weapon = best_melee_weapon([i.name for i in bank.items()], skills.level('attack'), prefer_stab=False)
```

## Loadouts

A loadout is `{name, worn: {slot: item}, carry: [{item, qty}]}`. They're kept for every bot on the account in the account file's `script.settings["Loadouts"].sets`, through `loadouts`, rs2b0t's loadout store. A bot whose own `loadouts` setting holds a list uses that instead, and its `loadout` setting, `LOADOUT_SETTING`, names the one to use.

| Name | Is |
|---|---|
| `SLOTS` | `['hat', 'back', 'front', 'righthand', 'torso', 'lefthand', 'legs', 'hands', 'feet', 'ring', 'quiver']` |
| `CarryEntry(item, qty)` | One carried item |
| `Loadout(name, worn=None, carry=None)` | `name`, `worn` (slot to item name), `carry` (`CarryEntry`s) |
| `parse_loadouts(raw)` | Loadouts from a list of dicts or its JSON text, skipping what isn't one; never raises |
| `selected_loadout(settings)` | The loadout `settings.loadout` names, else the first; `None` when there are none |
| `food_of(loadout, fallback, is_food=None)` | The first carried item that's eaten, else `fallback` |
| `gear_of(loadout)` | The worn items' names |
| `supplies_of(loadout)` | The carry list |
| `weapon_of(loadout, fallback=None)` | The `righthand` item, or `fallback` |
| `script_food(settings, fallback)`, `script_foods(settings, fallback)` | The selected loadout's food, or foods |
| `upsert_loadout(loadouts, loadout)`, `remove_loadout(loadouts, name)`, `unique_name(loadouts, base)` | Editing helpers, returning new lists |
| `loadouts.all()`, `loadouts.names()`, `loadouts.by_name(name)` | The account's shared loadouts, their names, and one by name without regard to case |
| `loadouts.save(list)` | Saves the list into the account file, replacing what was there |
| `serialize_loadouts(list)` | The loadouts as JSON text, as `parse_loadouts` reads it |
| `LOADOUT_SETTING` | A [`SettingDef`](settings.md#settingdef) for a bot's `loadout`: a string chosen from the loadouts' names |
| `LOADOUTS_NAMESPACE`, `LOADOUTS_KEY` | `'Loadouts'` and `'sets'` |

```jsonc
"Cow killer": {
    "loadout": "Melee",
    "loadouts": [
        {"name": "Melee", "worn": {"righthand": "Bronze sword"}, "carry": [{"item": "Trout", "qty": 10}]}
    ]
}
```

## Places

| Name | Is |
|---|---|
| `ALTARS` | Records of `name`, `tile`, `loc` and, for the Monastery's, `requires` (Prayer 31) |
| `nearest_altar(start)` | The usable altar the shortest route reaches from `start`, or `None`, as rs2b0t ranks them by route cost; `None` too when a random event is pending. Not a wait: each route is planned at once |
| `TELEPORTS` | The standard teleports, lower-case name to a record of `name` and `fallback_com_id` |
| `resolve_teleport(name)` | The teleport a name means: `'varrock'`, `'Varrock teleport'` or the button's `'Cast @gre@Varrock teleport'`; `None` for an unknown one |
| `teleport_button_text(teleport)` | The magic tab button's text, `'Cast @gre@Varrock teleport'` |
| `resolve_teleport_component(teleport, find_button)` | `find_button(text)` gives a component or -1; the 289 interface's component when it doesn't find one |
| `in_ess_mine(x, z)` | Whether a tile is in the rune essence mine |
| `item_db()` | rs2b0t's item database, read on first use: item name to a record of `obj`, `id`, `name`, `cost`, `members`, and where they apply `slot` (`'hat'`, `'righthand'` and so on), `two_handed` and `consumable` (`'eat'` or `'drink'`) |
| `drop_db()` | Monster name to the item names its drop table can give, read on first use |

## The pack

rs2b0t's `packRules`.

| Name | Is |
|---|---|
| `matches_any(name, patterns)` | Whether the name holds any of the patterns, by part and without regard to case. Blank patterns match nothing |
| `count_matching(items, patterns)`, `slots_matching(items, patterns)` | How many matching items there are, stacks counted, and how many slots hold one |
| `should_bank(loot_slots, bank_at, inv_full)` | At `bank_at` slots of loot, or a full pack holding any |
| `should_restock(food_count, threshold)` | Fewer than `threshold` bites left |
| `should_eat(hp, max_hp, heal, food_count)` | As `should_eat_to_use_food` |
| `should_panic(hp_fraction, gate, food_count)` | Below the gate with no food left |

## Thieving

rs2b0t's `api/thieving`: Ardougne market's cake stall and its pickpocket targets.

| Name | Is |
|---|---|
| `STALL_TILE`, `STAND`, `STAND_ALT`, `FLEE_TILE` | The Baker's stall, the two tiles it's stolen from, and where to run when caught |
| `CAKE_ITEMS` | `['cake', 'bread', 'chocolate slice']`, matched by part |
| `LOCKOUT_TICKS`, `RESET_AFTER_REFUSALS` | 10 ticks after a fight before the stall can be stolen from; 3 refusals before swapping stands |
| `classify_steal(gained, combat, lockout_seen, attempt_seen)` | How a steal went: `'success'`, `'caught'`, `'lockout'`, `'refused'` (the Baker says no only overhead) or `'timeout'` |
| `should_reset(consecutive_refusals)` | Whether to swap stands |
| `carried_cakes()`, `needs_cake_restock(target)` | The stall's food in the backpack, and whether there's room and fewer than `target` |
| `steal_cakes(abort, set_status, log, fill_to=None, should_eat=None, locked_out_until=None, on_steal=None, on_reset=None)` | **Wait.** Steals until the backpack is full or holds `fill_to` of the stall's food: `'stocked'`, `'combat'`, `'aborted'` or `'no-progress'` after 90 seconds |
| `SPOTS`, `target_spot(target)` | Where each pickpocket target is worked: a record of `anchor` and `leash` |
| `required_thieving(target)` | The level a target needs |
| `HOSTILE_NAMES`, `is_hostile_attacker(candidate, max_distance)` | The market's guards and knights, and whether one is fighting you nearby |
| `choose_target(candidates_nearest_first, reachable)` | A record of `target`, the nearest reachable, and `blocked`, the nearest when none is |
| `THIEVER_BANKING_OPTIONS`, `auto_food_banking(mode)` | `['None', 'Auto']`, and whether the mode banks for food |
| `food_matches(name, keyword)`, `count_food(items, keyword)` | Food by part of its name, and how many |
| `should_restock_food(enabled, food_count, restock_at, bankable_pack_full)` | Bank at the food floor, or with a full pack |
| `safe_to_steal(hp_fraction, eat_at, food_count)`, `can_steal_now(food_count, hp, min_eat_hp, suicide)` | Whether to steal now; suicide mode steals on with no food |
| `STUN_COMBAT_TICKS` | 9: a pickpocket stun's movement lock. Retrying at 8 only turns the character |
| `next_withdraw_chunk(need)` | The next withdrawal toward `need`: `('op', 'Withdraw-1')`, `-5` or `-10`, `('x', count)` above 10, or `None` |
| `withdraw_to(name, target, count_in_inv=None)` | **Wait.** Withdraws until the backpack holds `target`; the units withdrawn |
| `close_bank_and_confirm_count(expected, count)` | **Wait.** Closes the bank and waits for `count()` to reach `expected` |

## Trading partners

For accounts that hand their haul to each other.

| Name | Is |
|---|---|
| `DEFAULT_TRADE_RANGE` | 2 |
| `MULE_MODE_OPTIONS` | `['Off', 'Gatherer', 'Mule', 'Cooker', 'Supplier']` |
| `parse_partner_list(raw)` | Names from a comma-separated setting |
| `names_match(a, b)`, `is_configured_partner(name, partners)` | Name checks, without regard to case |
| `count_offer_by_name(items, item_name)`, `count_offer_matching(items, test)` | Counts in a trade offer; each item counts at least 1 |
| `decide_receiver_offer_screen(partner_header, partners, my_offer_slots, their_product_count)` | On the offer screen, receiving: `('wait-header',)`, `('decline', reason)`, `('wait-offer',)` or `('accept',)` |
| `decide_giver_offer_screen(my_offer_slots)` | Giving: `'offer'`, then `'accept'` |
| `parse_mule_mode(raw)` | `'gatherer'`, `'mule'`, `'cooker'`, `'supplier'` or `'off'` |
| `mule_gatherer_handoff_active(mode, partners, power_mode)`, `mule_receiver_active(mode, partners)`, `mule_cooker_active(mode, partners)`, `mule_supplier_active(mode, partners, power_mode)`, `mule_non_gatherer_active(mode, partners)` | Which role is on: the mode matches and partners are configured |

Driving the trade (rs2b0t's `drivePartnerTrade.ts` and `PartnerHandoff.ts`):

| Name | Gives or does |
|---|---|
| `drive_active_partner_trade(role, partners, their_product_match, product_names_to_offer, set_status, log, on_complete=None, on_decline=None, inventory_metric=None, on_missing_partner=None, receiver_can_accept=None, my_offer_ready=None, baseline=None, verify_giver_partner=False, labels=None)` | **Wait.** One step of an open trade, as `'giver'` or `'receiver'`. The receiver accepts once a configured partner offers product (`their_product_match(name)`); the giver offers each of `product_names_to_offer()` with Offer All, then accepts; on the confirm screen both accept, and `on_complete(delta)` gets `inventory_metric()` (default `inventory.used()`) after less before, the before from `baseline()` when given. `on_missing_partner()` answers `'wait'` or `'decline'` while the partner's name hasn't shown, `receiver_can_accept(count)` a bool or `(ok, reason)`, and `labels` (a dict) renames the statuses. Call it every loop while `trade.active()` |
| `trade_screen_state()` | `'offer'`, `'confirm'` or `'closed'` |
| `stable_closed_poll(min_ms=600, now_fn=None)` | A condition that holds once the trade has been shut for `min_ms` without a break, since the swap between the screens reports neither for a moment |
| `run_handoff(partner, rendezvous, id, name, giving, label, log)` | **Wait.** Moves one object, by id, between this bot and `partner`, meeting at `rendezvous`, and proves it landed. `True` once it has |
| `decide_open_trade(trade_active, partner_near, now_ms, deadline_ms, next_request_at_ms)` | `'done'`, `'give-up'`, `'wait'` or `'request'`, for sending Trade with again until the window opens |

## Tasks

Ready-made [`Task`](script-structure.md#taskbot-and-task)s for a `TaskBot`. [`PeriodicBank`](bank.md#periodic-banking) is a builtin.

### `ContinueDialog(on_continue=None)`

Clicks through a dialogue page whenever one can be continued, calling `on_continue()` first. Put it first in the task list.

### `ItemNeed(name, count, source)` and `AcquireTask(bot, needs)`

An `ItemNeed` is a count of an item and where to get it: `source` is `('shop', keeper, near_tile)` or `('ground', tile)`. (`('gather',)` and `('make',)` are accepted but not done yet, and raise `NotImplementedError`.)

`AcquireTask` runs while any need is unmet: it walks to the shop and buys, or to the spawn and takes. `held(name)` and `has_all(needs)` are its checks.

```python
needs = [ItemNeed('Bucket', 1, ('shop', 'Shop keeper', Tile(3212, 3247)))]
self.add(AcquireTask(self, needs), ...)
```

### `DeathRecovery(bot, anchor, radius=6, needs=None, on_death=None, on_recovered=None, walk_back=None)`

After the `death` event, gets `needs` back (when given) and walks back within `radius` of `anchor`, or runs `walk_back()` instead. `on_death()` and `on_recovered()` are called at each end.

### Going back to camp

| Name | Is |
|---|---|
| `AnchorHost(anchor, leash_radius, log=None)` | What the helpers read |
| `create_return_to_anchor_task(host, slack=6, arrive_radius=8, timeout_ms=90000, long_range_tiles=0, suppress=None)` | A task that walks back within `arrive_radius` of the anchor once you're past the leash plus `slack`. Beyond `long_range_tiles` (when not 0) it uses `walk_resilient`. `suppress()` turns it off for a while |
| `beyond_leash(host, here, slack=0)`, `tile_within_leash(host, tile, slack=0)` | Leash checks |
| `resolve_run_anchor(here, location_spot)` | The camp's spot, or where you stand |
| `should_walk_home_to_gather_anchor(dist_to_anchor, arrive_radius=8)`, `should_soft_home_from_gather_miss(dist_to_anchor, leash=64)` | When a gatherer should head back |
| `HOME_ARRIVE_RADIUS` | 8 |

### `sustain`

Upkeep that a long wait must keep doing, such as eating: `sustain.set(hook)` once, then `yield from sustain.run()` inside your waits. `hook` may be a generator function; a run already in progress is skipped.

## Data source

The data comes from rs2b0t through `tools/catalogs/export_rs2b0t.ts`, run with Bun against an rs2b0t checkout. It writes the embedded catalog data in `src/Script/Stdlib/rs2004/catalogs/_data.py`, `_shops.py` and `_clues.py`.

## Ported bots

`scripts/bots/` has rs2b0t's bots translated with them, one file per bot as rs2b0t registers it. An account file names one as `bots/miner.py`, and another bot can import one, `from bots.miner import BOT`, to run it as a `ScriptActivity`.

| Kind | rs2b0t | Here |
|---|---|---|
| Gathering | Miner, Woodcutter, Fisher (GatheringBot) | `miner.py`, `woodcutter.py`, `fisher.py`, on the `bots/gathering/` package: cooking, chop-then-burn, tool buying and repair, the Desert Mining Camp, tick manipulation (off until rs2b0t ships it), the Fisher's mule hand-offs (gatherer, mule, cooker, supplier) and the Fishing Guild feather and Shilo supply runs |
| Gathering | CoalTrucks, EssMiner, FlaxPicker, FlaxAIO, GnomeMagicChopper | `coal_trucks.py`, `ess_miner.py`, `flax_picker.py`, `flax_aio.py`, `gnome_magic_chopper.py` |
| Skilling | BankFletcher, CookBot, DartFletcher, Firemaker, FlaxSpinner, GemCutter, HerbCleaner, HerbloreSecondaries, PotionMaker, LeatherCrafter, SmelterBot, SmithingBot, Superheater, TannerBot, VialFiller, BoneBurier, ClimbingBoots | `bank_fletcher.py` and the rest, each named as rs2b0t names it in snake_case |
| Jewellery and caskets | JiveBalls, JiveCaskets, JiveCrafting, JiveEnchanter | `jive_balls.py`, `jive_caskets.py`, `jive_crafting.py`, `jive_enchanter.py` |
| Runecrafting | RuneCrafter, NatureCrafter | `rune_crafter.py`, `nature_crafter.py`. NatureCrafter's paint button is the `gobank` console command |
| Agility | AgilityBot, WildyAgility, EdgevilleMonkeyBars, BrimhavenAgility | `gnome_course.py`, `wildy_agility.py`, `edgeville_monkey_bars.py`, `brimhaven_agility.py` |
| Thieving | ThievingBot, ArdyCakes, ArdyThiever, ArdyFighter | `thiever.py`, `ardy_cakes.py`, `ardy_thiever.py`, `ardy_fighter.py`. The three Ardougne bots solve the clues they pick up |
| Treasure Trails | ClueSolver | `clue_solver.py`: solves the clue or opens the casket in the pack, then banks the reward |
| Quests | ArravSupplier | `arrav_supplier.py`, its logic in `bots/arravsupplier/`: prepares the Phoenix mission, joins both gangs, banks certificates without redeeming |
| Quests | Barcrawl | `barcrawl.py`: obtains the card, visits all ten bars and hands it in |
| Quests | AIOQuester | `aio_quester.py`, its logic in `bots/aioquester/`: runs a queue of quests on [`rs2004.quests`](quests.md). Its paint's Skip button is the `skip` console command, and the paint is its progress report |
| Fighting | ChickenKiller, CowKiller, ChaosDruidKiller, HillGiant | `chicken_killer.py`, `cow_killer.py` (ChickenKiller with a cow field preset), `chaos_druid_killer.py`, `hill_giant.py` |
| Combat | MossGiant, BrimhavenMossGiants, FireGiant, GreenDragon, RockCrab, RangingGuild, AutoFighter, JiveChests | `moss_giant.py`, `brimhaven_moss_giants.py`, `fire_giant.py`, `green_dragon.py`, `rock_crab.py`, `ranging_guild.py`, `auto_fighter.py`, `jive_chests.py`, with their logic in `bots/firegiant/`, `bots/greendragon/`, `bots/rangingguild/`, `bots/autofighter/` and `bots/jivechests/`. GreenDragon, RockCrab and AutoFighter solve the clues they pick up, on [`rs2004.clues`](clues.md) |
| Bosses and dragons | JiveDragons, JiveDemons, JiveKBD | `jive_dragons.py`, `jive_demons.py`, `jive_kbd.py`, on [`rs2004.hunting`](hunting.md). JiveDragons solves the hard clues the dragons drop |
| Duel Arena | Duel Arena Combat Trainer (DuelArena) | `duel_arena.py`, its logic in `bots/duelarena/`: two accounts duel each other to train Attack, Strength and Defence |
| Movement and magic | WalkTo, DoorOpener, AIO Teleport, Alcher | `walk_to.py`, `door_opener.py`, `aio_teleport.py`, `alcher.py` |
| Shops and trading | ShopBuyout, ShopRunner, MarketMaker, JiveMarketDumper, MuleTrader | `shop_buyout.py`, `shop_runner.py`, `market_maker.py` (its logic in `bots/marketmaker/`), `jive_market_dumper.py`, `mule_trader.py` |
| Two-account | FlaxRunner, MuleCrafter | `flax_runner.py` (a runner picks, a spinner spins), `mule_crafter.py` (a crafter and its mules) |
| Four-account | JiveKQ | `jive_kq.py`, its parts in `bots/jivekq/`: four accounts in one client kill the Kalphite Queen together, talking over `send_bot_message` |
| Utility | BankSorter | `bank_sorter.py` |
| Gathering | FlourCollector | `flour_collector.py`: fills banked empty pots at Sinclair Mansion and banks the flour at Seers; requires Murder Mystery started |
| Herblore | RoguesPurse | `rogues_purse.py`, with `bots/roguespurse/logic.py`: searches, identifies and drops herbs by default; `mode=bank` banks full loads. Requires Herblore 3 and Jungle Potion at the Rogues purse stage |
| Event looting | WanderLooter | `wander_looter.py`, its logic and tasks in `bots/wanderlooter/`: wanders and picks up drops by exact name (Pumpkin by default), without fighting, and leaves alone drops where it took damage |

`scripts/examples/aio_thiever.py` joins three of them, ThievingBot, ArdyCakes and ArdyThiever, into one that trains Thieving from 1: Lumbridge's men and women to 5, East Ardougne's Baker's stall to 40, then the market's guards to 55 and its knights after that, eating the cakes it banked.
