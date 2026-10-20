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
| `FORGETFUL_BANK_ODDS` | 100 |

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
| `combat_keep_names(food, style, spell=None, ammo=None, weapon=None, extra=None)` | What a fight's deposit keeps: every form of the food, the spell's runes when `style` is `'mage'`, the ammo when `'range'`, the weapon, and `extra` |

## Loadouts

A script's `loadouts` setting is a list of `{name, worn: {slot: item}, carry: [{item, qty}]}`, and its `loadout` setting names the one to use.

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

```jsonc
"Cow killer": {
    "loadout": "Melee",
    "loadouts": [
        {"name": "Melee", "worn": {"righthand": "Bronze sword"}, "carry": [{"item": "Trout", "qty": 10}]}
    ]
}
```

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
