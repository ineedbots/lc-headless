"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/gear.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.items import equipment, inventory

__all__ = ['held_id', 'worn_id', 'wear']


def held_id(id):
    return sum([item.count for item in [item for item in inventory.items() if item.id == id]])


def worn_id(id):
    return any([item.id == id for item in equipment.items()])


# Why: both halves of the priest suit render "Priest gown", so `Equipment.equip` reports the legs already on once the top is worn and never sends the second Wear.
def wear(item, log):
    """Wear by exact object id."""
    if worn_id(item.id):
        return True
    held = ([entry for entry in inventory.items() if entry.id == item.id] or [None])[0]
    if not held:
        log(f'no {item.name} (id {item.id}) in the pack to wear')
        return False
    op = ([action for action in held.actions() if ('wield' in action.lower() or 'wear' in action.lower() or 'equip' in action.lower())] or [None])[0]
    if not op or not (held.interact(op)):
        log(f'{item.name} (id {item.id}) offered no Wear')
        return False
    _result1 = yield from execution.delay_until(lambda: worn_id(item.id), 3000)
    return _result1
