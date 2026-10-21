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

### `banking.open(stand=None, booth_name='Bank booth', booth_op='Use-quickly', obstacles=None, destination=None, prefer_nearby=True, nearby_radius=14)`

**Wait.** Opens a bank, wherever you are. In order:

1. A booth in the loaded area, when it's within `nearby_radius`, or `prefer_nearby` is `False`, or neither `stand` nor `destination` is given.
2. Otherwise a banker (an NPC with a Bank option) by the same rule.
3. Otherwise, when `stand` is given, walks there with [`traversal.walk_resilient`](walking.md#traversal) and opens the booth there.
4. Otherwise walks to `destination`, one of [`bank_locations()`](walking.md#banks), or else the [`nearest_reachable_bank`](walking.md#banks), and opens it as that bank says: a banker, a chest, or a booth.

`obstacles` is accepted for rs2b0t compatibility and not used. Gives `True` once the bank is open.

### `banking.bank_nearest(deposit, common_junk=True, destination=None, return_to=None, booth_name='Bank booth', booth_op='Use-quickly', after_deposit=None)`

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

### `PeriodicBank(strategy, items_threshold, minutes_threshold, count_loot, deposit, after_deposit=None, common_junk=None, return_to=None, log=None, destination=None)`

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
