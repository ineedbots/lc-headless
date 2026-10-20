# Constants

Every constant a script has as a builtin, by area. Constants of [`rs2004.catalogs`](catalogs.md) are on that page.

## Inventories

Interface component ids, found in the server's cache at startup, so they're right for the revision in use. Print one to see its value. Use them with [`reader.inventory(com)`](game.md#reader) and to compare with [`InvItem.com`](items.md#invitem).

| Constant | Is |
|---|---|
| `INVENTORY` | The backpack |
| `EQUIPMENT` | The worn equipment |
| `BANK` | The bank's items |
| `BANK_INVENTORY` | The backpack beside the bank, while the bank is open |
| `INVENTORY_SIZE` | Backpack slots, 28 |

## Skills

The skill indexes, as [`skills.index(name)`](game.md#skills) and the `skill_xp` and `skill_level` [events](events.md#payload-events) give them.

| Constant | Value | Constant | Value |
|---|---|---|---|
| `ATTACK` | 0 | `FLETCHING` | 9 |
| `DEFENCE` | 1 | `FISHING` | 10 |
| `STRENGTH` | 2 | `FIREMAKING` | 11 |
| `HITPOINTS` | 3 | `CRAFTING` | 12 |
| `RANGED` | 4 | `SMITHING` | 13 |
| `PRAYER` | 5 | `MINING` | 14 |
| `MAGIC` | 6 | `HERBLORE` | 15 |
| `COOKING` | 7 | `AGILITY` | 16 |
| `WOODCUTTING` | 8 | `THIEVING` | 17 |
| | | `RUNECRAFT` | 20 |

`skills` functions take the lower-case names (`'woodcutting'`), not these numbers.

## Scenery layers

For [`Loc.layer`](world.md#loc), a query's `layer()`, and `locs.at(tile, layer)`.

| Constant | Value | Holds |
|---|---|---|
| `LAYER_WALL` | 0 | Walls, doors and gates |
| `LAYER_WALL_DECOR` | 1 | Things hung on walls |
| `LAYER_GROUND` | 2 | Most scenery: trees, rocks, booths, ladders |
| `LAYER_GROUND_DECOR` | 3 | Flat decoration on the ground |

## Combat

| Constant | Value | Meaning |
|---|---|---|
| `COMBAT_TICKS` | 8 | How many ticks after a hit `in_combat` stays true |
| `SA_MAX_ENERGY` | 1000 | A full special attack bar |
| `COMBAT_STYLE_OPTIONS` | `['attack', 'strength', 'controlled', 'defence']` | Melee training styles |
| `RANGE_STYLE_OPTIONS` | `['accurate', 'rapid', 'longrange']` | Ranged styles |
| `PRAYER_NAMES` | 15 names | See [prayer](side-tabs.md#prayer) |
| `AUTOCAST_SPELLS` | 16 names | See [autocast](side-tabs.md#autocast) |

## Dialogues

| Constant | Value | Meaning |
|---|---|---|
| `MAKE_X` | -1 | A make-menu button that asks for the count |
| `MAKE_ALL` | 0 | A make-menu button that makes all |

## Walking and messages

| Constant | Value |
|---|---|
| `NAV_PURE_WALK` | `{'use_teleport_catalog': False, 'policy': {'use_teleports': False}}` |
| `NAV_WITH_TELES` | `{'use_teleport_catalog': True, 'policy': {'use_teleports': True}}` |
| `CANT_REACH` | `"i can't reach that"`, a [message pattern](walking.md#game_messages) |
| `WRONG_SIDE` | A pattern function, not a string: true for "You can't do that from here." |

## Bank, shop and trade

| Constant | Value |
|---|---|
| `COMMON_BANK_LOOT` | `['uncut', 'sapphire', 'emerald', 'ruby', 'diamond', 'opal', 'jade', 'topaz', 'strange fruit', 'beer', 'kebab']` |
| `RANDOM_EVENT_CASKET_ID` | 405 |
| `NEARBY_BANK_RADIUS` | 14 |
| `PERIODIC_BANK_SETTINGS` | A settings schema fragment; see [periodic banking](bank.md#periodic-banking) |
| `SELL_STACK_STEP` | 10 |

## Settings

`settings` itself is a builtin: the script's [`SettingsBag`](settings.md#settingsbag).
