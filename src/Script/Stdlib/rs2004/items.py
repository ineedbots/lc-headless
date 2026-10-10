"""The backpack and worn equipment. Mirrors rs2b0t's api/inventory/Inventory.ts, InvItem and
api/equipment/Equipment.ts (MIT, see third_party/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.entities import GroundItem, Loc, Npc, Player, op_index, present_ops

__all__ = ['InvItem', 'inventory', 'equipment']

EQUIP_OPTIONS = ('Wield', 'Wear', 'Equip')
REMOVE_OPTION = 1
EQUIP_TIMEOUT_MS = 3000


class InvItem:
    """One slot of an inventory: name, id, slot, count, noted, and com, the inventory it's in. Its actions
    are its own, such as 'Eat', in the backpack, and its inventory's, such as 'Withdraw 5', in the bank and
    other interfaces, as the right-click menu shows them."""

    def actions(self):
        return present_ops(self._ops)

    def interact(self, action):
        """Uses the option named action, such as 'Eat' or 'Withdraw 5'. False when it has no such option."""
        op = op_index(self._ops, action)
        if op == -1:
            return False
        if self._button:
            return _core.inv_button(self, op)
        return _core.item_op(self, op)

    def use_on(self, target):
        """Uses the item on another item, an NPC, a player, scenery or a ground item."""
        if isinstance(target, InvItem):
            return _core.use_item_on_item(self, target)
        if isinstance(target, Npc):
            return _core.use_item_on_npc(self, target)
        if isinstance(target, Player):
            return _core.use_item_on_player(self, target)
        if isinstance(target, Loc):
            return _core.use_item_on_loc(self, target.id, target._x, target._z)
        if isinstance(target, GroundItem):
            return _core.use_item_on_ground_item(self, target)
        raise TypeError(f'an item is used on an InvItem, Npc, Player, Loc or GroundItem, not {type(target).__name__}')

    def __repr__(self):
        return f'InvItem(id={self.id}, name={self.name}, count={self.count}, slot={self.slot})'


def _named(items, name):
    wanted = name.strip().lower()
    return [item for item in items if item.name is not None and item.name.lower() == wanted]


class _Inventory:
    """The backpack. Names match whole, without regard to case."""

    def items(self):
        return _core.get_inventory(INVENTORY)

    def first(self, name):
        found = _named(self.items(), name)
        return found[0] if found else None

    def contains(self, name):
        return self.first(name) is not None

    def count(self, name):
        """The total quantity, across stacks and slots."""
        return sum([item.count for item in _named(self.items(), name)])

    def count_by_id(self, id):
        return sum([item.count for item in self.items() if item.id == id])

    def used(self):
        return INVENTORY_SIZE - _core.get_empty_slots()

    def free(self):
        return _core.get_empty_slots()

    def is_full(self):
        return _core.get_empty_slots() == 0


class _Equipment:
    """What you wear."""

    def items(self):
        return _core.get_equipment()

    def contains(self, name):
        return len(_named(self.items(), name)) > 0

    def equip(self, name):
        """Wields, wears or equips the item from the backpack, and waits for it to be worn. Use with yield from."""
        item = inventory.first(name)
        if item is None:
            return False
        options = item.actions()
        for option in EQUIP_OPTIONS:
            if option in options:
                if not item.interact(option):
                    return False
                worn = yield from execution.delay_until(lambda: self.contains(name), EQUIP_TIMEOUT_MS)
                return worn
        return False

    def unequip(self, name):
        """Removes the worn item into the backpack, and waits for it to come off. Use with yield from."""
        found = _named(self.items(), name)
        if not found:
            return False
        if not _core.inv_button(found[0], REMOVE_OPTION):
            return False
        removed = yield from execution.delay_until(lambda: not self.contains(name), EQUIP_TIMEOUT_MS)
        return removed


inventory = _Inventory()
equipment = _Equipment()
