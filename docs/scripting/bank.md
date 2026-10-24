# The bank: `bank`, `banking` and deposit rules

- [`bank`](#bank): the bank interface once it's open, and opening one nearby
- [`banking`](#banking): a whole trip, walking to a bank across the map when none is near
- [Deposit rules](#deposit-rules)
- [Periodic banking](#periodic-banking)

```python
opened = yield from banking.open()
if opened:
    yield from bank.deposit_all_matching(deposit_all_except(['Bronze pickaxe']))
    yield from bank.withdraw_x('Lobster', 10)
    yield from bank.close()
```

Item names match whole, without regard to case. Option names match without regard to case, and a hyphen counts as a space, so rs2b0t's `'Withdraw-1'` works as well as `'Withdraw 1'`.

## `bank`

### Reading

| Method | Gives |
|---|---|
| `bank.is_open()` | The bank interface is the main interface |
| `bank.ready()` | It's open, and its items and the backpack beside it have arrived |
| `bank.wait_ready(timeout_ms=4000)` | **Wait.** Waits for the items. Gives `ready()` |
| `bank.loaded()` | rs2b0t's: the bank's item list isn't empty |
| `bank.snapshot_ready()` | rs2b0t's: open, with its item list sent |
| `bank.snapshot_generation()` | rs2b0t's: which update of the bank's item list this is, as the tick it came on, or -1 while it's shut. Take it before an action, and `wait_snapshot_after` waits for the action's answer |
| `bank.wait_snapshot_after(generation, timeout_ms=4000)` | **Wait.** Waits for the item list to update after `generation`. `False` when it doesn't or the bank shuts |
| `bank.normal_backpack_snapshot()` | The backpack's items while the bank is shut, to compare with its side view once it opens; `None` while it's open |
| `bank.backpack_ready(expected=None, log=None)` | **Wait.** Waits for the backpack beside the open bank, and given a `normal_backpack_snapshot()`, for it to hold the same items in the same slots |
| `bank.root()` | The bank interface's id |
| `bank.items()` | The bank's items as [`InvItem`](items.md#invitem)s, whose actions are the bank's options ("Withdraw 1" ... "Withdraw X"). `[]` when closed |
| `bank.side_items()` | The backpack beside the bank, whose actions deposit. `[]` when closed |
| `bank.count(name)`, `bank.count_by_id(id)` | How many of the item the bank holds |

### Withdrawing

| Method | Gives or does |
|---|---|
| `bank.withdraw(name, op='Withdraw 1')` | Uses the option on the bank item once. Doesn't wait. `False` without the item or option |
| `bank.withdraw_by_id(id, op='Withdraw 1')` | The same by id |
| `bank.withdraw_x(name, count)` | **Wait.** Withdraws `count`, or all there is if fewer. Uses Withdraw 1, 5 or 10 when `count` is one of those, otherwise Withdraw X and answers the count dialog. Waits up to 4 seconds for the items to land (or for the backpack to fill). `True` when they did |
| `bank.withdraw_x_by_id(id, count, lands_as_id=None)` | **Wait.** The same by id. In note mode the backpack receives the note, which has a different id: pass that as `lands_as_id` |
| `bank.withdraw_load(name)` | **Wait.** Fills the backpack from one item, by name or id: Withdraw All where it has one, else X for the free slots. Waits up to 4 seconds for the whole load to land. `True` straight away, without a click, when the backpack is already full |
| `bank.set_note_mode(on)` | **Wait.** Withdraws as notes (`True`) or items (`False`). Opening the bank resets this to items, so set it after opening |

### Depositing

| Method | Gives or does |
|---|---|
| `bank.deposit(name, op='Deposit 1')` | Uses the option on the backpack item beside the bank once. Doesn't wait |
| `bank.deposit_inventory()` | **Wait.** Deposits everything |
| `bank.deposit_all_matching(matches)` | **Wait.** Deposits each stack for which `matches(name, id)` is true, a stack at a time with its Deposit All option, waiting up to 2 seconds for each to go. A nameless item is passed as `''`. Handles up to 32 stacks a call |

`matches` is usually one of the [deposit rules](#deposit-rules):

```python
yield from bank.deposit_all_matching(deposit_all_except(['Rune pickaxe', 'Coins']))
yield from bank.deposit_all_matching(lambda name, id: name.endswith(' ore'))
```

### Opening a nearby bank

All are **Waits** that give `True` once the bank is open and ready. A dialogue that comes before the bank is continued.

| Method | Does |
|---|---|
| `bank.open_nearest(booth_name='Bank booth', op='Use-quickly')` | Uses the nearest booth in the loaded area, stepping beside it when a try from here fails. Up to 6 tries. `False` when there's no booth. When the booth lacks `op`, the first option starting "Use" or "Bank" is used |
| `bank.open_booth(stand, booth_name='Bank booth', op='Use-quickly')` | The same, walking to `stand` when a try fails. Up to 4 tries |
| `bank.open_nearest_access(access)` | Opens a bank by its access, a dict: `{'name': 'Bank chest', 'op': 'Use', 'open_first': {'name': 'Closed chest', 'op': 'Open'}}`. `open_first` is something to open before it can be used, and is optional |
| `bank.open_npc_access(access)` | Opens a bank through a banker: `{'name': 'Banker', 'op': 'Bank', 'choose': None}`. `choose` is the dialogue option to pick, for a banker who talks first. Up to 3 tries |
| `bank.close(timeout_ms=3000)` | Closes the bank, so the backpack's own options work again, and waits for it to go. `True` when closed, or when it wasn't open |

None of these walk across the map. For that, use `banking`.

## `banking`

### `banking.open(stand=None, booth_name='Bank booth', booth_op='Use-quickly', obstacles=None, destination=None, prefer_nearby=True, nearby_radius=14, log=None)`

**Wait.** Opens a bank, wherever you are, choosing the way as rs2b0t does with [`resolve_bank_open_route`](#helpers):

1. A booth in the loaded area within `nearby_radius`, unless `prefer_nearby` is `False`.
2. A known bank within `nearby_radius` of you, when `stand` isn't that near: walked to and opened as that bank says, by a banker, a chest or a booth. Starting beside Draynor's bank doesn't walk to a camp's Edgeville stand.
3. The booth at `stand`, walked to with [`traversal.walk_resilient`](walking.md#traversal), or with [`walk_opening`](walking.md#walking-through-doors-walk_opening) when `obstacles` names doors or gates to open on the way. A bank near the stand with a chest or a banker, such as Shantay's, is opened that way.
4. Without a stand, a booth anywhere in the loaded area, else `destination`, one of [`bank_locations()`](walking.md#banks), or else the [`nearest_bank_reachable`](walking.md#banks), walked to and opened as that bank says.

A bank the account can't use, such as Zanaris's without `use_zanaris_bank`, is skipped, and a `stand` at one gives `False`. `log` is given its choices. Gives `True` once the bank is open.

### `banking.bank_nearest(deposit, common_junk=True, destination=None, return_to=None, booth_name='Bank booth', booth_op='Use-quickly', after_deposit=None, log=None)`

**Wait.** A whole bank trip: opens a bank as `open()` does, deposits every item for which `deposit(name)` is true (plus [common bank loot](#deposit-rules) when `common_junk`), runs `after_deposit()` (which may be a generator, to withdraw supplies), then walks back to `return_to` when given. Gives `True` when it banked.

```python
yield from banking.bank_nearest(lambda name: name == 'Cowhide', return_to=FIELD_CENTRE)
```

## Deposit rules

rs2b0t's rules for what a deposit takes.

| Function or constant | Gives |
|---|---|
| `deposit_all_except(keep)` | A matcher for `deposit_all_matching` that deposits every named item except those in `keep`, by whole name without regard to case |
| `deposit_matcher(own, include_common)` | A matcher that deposits what `own(name)` picks, plus common bank loot when `include_common` |
| `matches_common_bank_loot(name, id=-1)` | Whether the item is common loot: its name contains a word of `COMMON_BANK_LOOT`, or its id is `RANDOM_EVENT_CASKET_ID` |
| `is_disposable_gather_junk(name, id=-1)` | Common bank loot, or random-event leftovers such as fliers and half-eaten pies |
| `withdraw_op(ops, amount)` | The withdraw option for `amount` (`'all'`, `'10'`, `'5'`, `'1'`, `'x'` or `'any'`) among an item's options, or `None` |
| `COMMON_BANK_LOOT` | `['uncut', 'sapphire', 'emerald', 'ruby', 'diamond', 'opal', 'jade', 'topaz', 'strange fruit', 'beer', 'kebab']` |
| `RANDOM_EVENT_CASKET_ID` | `405` |
| `NEARBY_BANK_RADIUS` | `14`, the tiles within which a bank counts as here |

## Periodic banking

Banking loot every so often, so a death doesn't lose it all.

### `PeriodicBank(strategy, items_threshold, minutes_threshold, count_loot, deposit, after_deposit=None, common_junk=None, return_to=None, log=None, destination=None, set_status=None)`

A [`Task`](script-structure.md#taskbot-and-task) for a `TaskBot`, labelled `'periodic bank'`. Every argument is a **callable**, so it reads the current settings each time:

| Argument | Returns |
|---|---|
| `strategy()` | `'off'`, `'items'`, `'time'` or `'either'` |
| `items_threshold()` | Bank once `count_loot()` reaches this |
| `minutes_threshold()` | Bank once this many minutes have passed since the last bank |
| `count_loot()` | How much loot is held now |
| `deposit(name)` | Whether to deposit an item |
| `after_deposit()` | Optional, run after depositing; may be a generator |
| `common_junk()` | Optional, whether to deposit common loot too; `True` when not given |
| `return_to()` | Optional, a `Tile` to walk back to |
| `destination()` | Optional, one of `bank_locations()` to bank at |
| `log(message)` | Optional, given progress lines |
| `set_status(text)` | Optional, told `'periodic bank run'` when a run starts |

It never runs while you're in combat or with no loot. When no bank can be reached it waits 3 minutes before trying again.

```python
self.add(
    PeriodicBank(
        lambda: parse_bank_strategy(self.settings.bank_strategy),
        lambda: self.settings.bank_every_items,
        lambda: self.settings.bank_every_minutes,
        lambda: inventory.count('Cowhide'),
        lambda name: name == 'Cowhide',
        common_junk=lambda: self.settings.bank_common_junk,
        return_to=lambda: FIELD_CENTRE,
    ),
    ...
)
```

### Helpers

| Function or constant | Gives |
|---|---|
| `PERIODIC_BANK_SETTINGS` | A [settings schema](settings.md#schemas) fragment: `bank_strategy` (`'Off'`, `'Loot count'`, `'Time'` or `'Either'`, default `'Off'`), `bank_every_items` (1 to 27, default 15), `bank_every_minutes` (1 to 120, default 10) and `bank_common_junk` (default `True`) |
| `parse_bank_strategy(label)` | `'off'`, `'items'`, `'time'` or `'either'`, from that setting's label |
| `should_bank_now(strategy, state)` | Whether to bank, from `state`'s `loot_count`, `minutes_since_last_bank`, `items_threshold` and `minutes_threshold` (a dict or an object). Never with no loot |
| `resolve_bank_open_route(bank_open=False, here=None, stand=None, nearby_booth_dist=None, nearest=None, prefer_nearby=True, nearby_radius=14)` | How `banking.open` would get a bank open, as rs2b0t decides it: `'already-open'`, `'scene-booth'` (a booth within `nearby_radius`), `'local-bank'` (a known bank that near, when the preset `stand` isn't), `'preset-stand'` or `'nearest-fallback'`. `nearest` is a bank from [`bank_locations()`](walking.md#banks) |
| `open_bank_access(dest, fallback, log=None)` | **Wait.** Opens the bank `dest` names, a `bank_locations()` entry: through its banker when it has `npcAccess`, else by its `access`, else by `fallback` (`{'name': ..., 'op': ...}`) |
| `purge_pack_at_bank(keep, stand=None, destination=None, prefer_nearby=None, booth_name='Bank booth', booth_op='Use-quickly', obstacles=None, log=None)` | **Wait.** rs2b0t's start-of-run cleanup: banks everything but the `keep` names, so a bot can start with a pack of junk. `True` when nothing needed banking or the backpack is clear; `False` when the bank couldn't be opened or junk is left |
| `bank_pace_ticks(rand=None)` | rs2b0t's pause between bank actions: 2 ticks about a third of the time, else 1, so an open, a scan and a close never land on one tick. `rand` stands in for `random.random` |
| `bank_pace(log=None)` | **Wait.** Pauses that long |
| `wait_bank_ready(log=None)` | **Wait.** Waits up to 7 ticks for the open bank's items, pacing as rs2b0t does. `False` once it's closed |
| `withdraw_coins(need, inv_coins, bank_coins, coin_name='Coins', log=None)` | **Wait.** With the bank open, withdraws coins until the backpack holds `need`. `False` when the bank has none or the withdraw fails |

## Sorting the bank

rs2b0t's bank sorter: it files every item into a category, coins first and junk last, places each within its category (ores copper to rune, weapons dragon to bronze, runes combat then elemental, herbs in identify order, and the rest by price, dearest first), and drags the bank into that order in as few moves as it can.

```python
opened = yield from banking.open()
if opened:
    result = yield from sort_bank(log)
    log(result.reason, result.moves)
```

| Function or constant | Gives or does |
|---|---|
| `sort_bank(log=None, category_overrides=None)` | **Wait.** Sorts the open bank, four drags a tick and planning again each round, using the bank's Swap or Insert setting, whichever needs fewer drags, and putting the setting back after. Gives a result with `sorted`, `moves` (drags sent), `mode`, `unmatched` (ids no rule files) and `reason`: `'sorted'`, `'bank not open'`, `'snapshot not ready'`, `'bank closed'`, `'arrange mode stuck'`, `'no progress'` or `'round limit'`. `category_overrides` files ids by hand, `{id: category}` |
| `plan_bank_sort(items, overrides=None, force=None)` | The plan alone, for items with `slot`, `id`, `name` and `cost`: `mode` (`'swap'` or `'insert'`, or `force`'s), `moves` (each `from_` and `to`), `layout` (the ids in sorted order) and `unmatched`. The slots must run 0 to n-1, as the server keeps them; otherwise nothing is planned |
| `sortable_bank_items()` | The open bank's items as the planner reads them, with the cache's value as their cost |
| `CATEGORY_ORDER` | `coins`, `runes`, `staves`, `ammunition`, `weapons`, `armour`, `rangedArmour`, `food`, `potions`, `jewellery`, `herbs`, `oresBarsGems`, `logs`, `supplies`, `tools`, `teleports`, `questLive`, `questObsolete`, `junk`: rs2b0t's names |
| `QUEST_JUNK`, `find_quest_junk(banked, status_of)` | The items finished quests leave behind (`id`, `name`, `quest`), and those among `banked`, each with its quest's `status_of(quest)` and `droppable`: the quest is complete |
| `BANK_INSERT_VARP` | 304, the bank's Swap/Insert setting: 1 inserts |

The server goes by the bank's own Swap/Insert setting, not the drag packet's mode, so `sort_bank` presses the Swap or Insert button (found by its label) and waits for the varp before it drags. [`InvItem.move_to(slot, insert=False)`](items.md#invitem) drags one item. `rs2004.banksort` also has the rules themselves: `category_of(item)`, `is_unmatched(item)`, `rank_within(category, item)`, `longest_increasing_subsequence(values)`, `apply_move(order, move, mode)` and `set_arrange_mode(mode)`.
