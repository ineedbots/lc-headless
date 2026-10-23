# Items: backpack, equipment and InvItem

## `inventory`

The backpack. Names match whole, without regard to case, and surrounding spaces are ignored.

| Method | Gives |
|---|---|
| `inventory.items()` | An [`InvItem`](#invitem) per occupied slot |
| `inventory.first(name)` | The first item with that name, or `None` |
| `inventory.contains(name)` | Whether there's one |
| `inventory.count(name)` | The total quantity across every stack and slot |
| `inventory.count_by_id(id)` | The same, by item id |
| `inventory.used()` | Occupied slots |
| `inventory.free()` | Empty slots |
| `inventory.is_full()` | Whether no slot is free |

`backpack_capacity()` is rs2b0t's: how many slots the backpack has, `INVENTORY_SIZE`. rs2b0t reads 0 until its pack interface loads; here the size is known from the start.

```python
if inventory.is_full():
    for item in inventory.items():
        if item.name == 'Copper ore':
            item.interact('Drop')
            yield from execution.delay(100)
```

## `equipment`

What you wear.

| Method | Gives |
|---|---|
| `equipment.items()` | The worn items, as `InvItem`s; `slot` is the equipment slot |
| `equipment.contains(name)` | Whether an item with that name is worn |
| `equipment.equip(name)` | **Wait.** Uses the backpack item's Wield, Wear or Equip option, whichever it has, then waits up to 3 seconds for it to be worn. Gives `True` once it is; `False` when it isn't in the backpack, has no such option, or didn't go on in time |
| `equipment.unequip(name)` | **Wait.** Removes the worn item into the backpack and waits up to 3 seconds. Gives `True` once it's off |

```python
if not equipment.contains('Bronze pickaxe'):
    yield from equipment.equip('Bronze pickaxe')
```

The weapon is the item whose `slot` is 3; [`special.wielded()`](side-tabs.md#special) gives its name.

## `InvItem`

One slot of any inventory: the backpack, the worn equipment, the bank, a shop's stock, a trade offer. A snapshot, like the world's things.

| Field | Meaning |
|---|---|
| `id` | The item id |
| `name` | Its name, or `None` |
| `count` | The stack size |
| `slot` | Its slot in the inventory, from 0 |
| `noted` | Whether it's a banknote |
| `com` | The interface component of the inventory it's in, such as [`INVENTORY`](constants.md#inventories) or `BANK` |

| Method | Does |
|---|---|
| `actions()` | The options its right-click menu shows. In the backpack these are the item's own, with "Drop" where its type has nothing in that slot. In the bank, a shop, the worn equipment and other interfaces, they're the inventory's, such as "Withdraw 5", "Buy 1" or "Remove" |
| `interact(action)` | Uses the option, by text (without regard to case) or number 1 to 5: `item.interact('Eat')`, `item.interact('Withdraw 5')`. `False` when it has no such option |
| `use_on(target)` | Uses the item on another `InvItem`, an [`Npc`](world.md#npc), a [`Player`](world.md#player), a [`Loc`](world.md#loc) or a [`GroundItem`](world.md#grounditem). Walks to a world target first. Anything else raises `TypeError` |
| `move_to(slot)` | Drags it to another slot of its inventory, as rearranging the bank does |

None of these wait; they queue the click and return.

```python
knife = inventory.first('Knife')
logs = inventory.first('Logs')
if knife is not None and logs is not None:
    knife.use_on(logs)
    yield from chat_dialog.make_x('Short', 27)

range_ = locs.query().name('Range').within(5).nearest()
inventory.first('Raw shrimps').use_on(range_)
```

## Other inventories

`reader.inventory(com)` gives the `InvItem`s of any inventory the server has sent, such as `reader.inventory(BANK)`. The [bank](bank.md), [shop and trade](shops-and-trades.md) facades find theirs for you.
