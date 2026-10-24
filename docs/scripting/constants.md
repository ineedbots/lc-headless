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
| `PROTECT_FROM_MAGIC`, `PROTECT_FROM_MISSILES`, `PROTECT_FROM_MELEE` | `'Protect from Magic'` and so on | The protection prayers, as `prayer.set` takes them |
| `PLAYER_FACE_BASE` | 32768 | Added to a player's index in a face target; see [`facing_player`](game.md#combat-styles) |
| `OVERHEAD_TICKS` | 5 | How long overhead text shows |

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
| `BANK_LOCATIONS` | Every known bank, as [`bank_locations()`](walking.md#banks) gives them |
| `CANT_REACH` | `"i can't reach that"`, a [message pattern](walking.md#game_messages) |
| `WRONG_SIDE` | A pattern function, not a string: true for "You can't do that from here." |
| `USE_MAGE_BANK`, `USE_ZANARIS_BANK` | `'use_mage_bank'` and `'use_zanaris_bank'`, the settings those banks need |
| `SPELL_MAX_WILDERNESS` | 20: the deepest Wilderness level spell teleports work at |
| `GLORY_MAX_WILDERNESS` | 30: the same for an amulet of glory |

## Bank, shop and trade

| Constant | Value |
|---|---|
| `COMMON_BANK_LOOT` | `['uncut', 'sapphire', 'emerald', 'ruby', 'diamond', 'opal', 'jade', 'topaz', 'strange fruit', 'beer', 'kebab']` |
| `RANDOM_EVENT_CASKET_ID` | 405 |
| `NEARBY_BANK_RADIUS` | 14 |
| `PERIODIC_BANK_SETTINGS` | A settings schema fragment; see [periodic banking](bank.md#periodic-banking) |
| `SELL_STACK_STEP` | 10 |
| `CATEGORY_ORDER` | The bank sorter's categories in order; see [sorting the bank](bank.md#sorting-the-bank) |
| `QUEST_JUNK` | The items finished quests leave behind, each `id`, `name` and `quest` |
| `BANK_INSERT_VARP` | 304, the bank's Swap/Insert setting |
| `ARRANGE_SWAP_COM`, `ARRANGE_INSERT_COM` | 8130 and 8131, the 289 bank's Swap and Insert buttons; `sort_bank` finds them by their labels instead |

## Settings

`settings` itself is a builtin: the script's [`SettingsBag`](settings.md#settingsbag). `GLOBAL_SETTINGS` is the schema of the [Global settings](settings.md#global-settings).
