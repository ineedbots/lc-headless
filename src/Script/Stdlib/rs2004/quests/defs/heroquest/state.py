"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/state.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.game import reader
from rs2004.items import inventory
from rs2004.quests.food import quest_food

__all__ = ['held_id', 'banked_id', 'anywhere', 'worn_id', 'live_item', 'modal_said', 'food_name', 'held_food']

# Why: Key, Herb, Chest and Door each name more than one object, so a name lookup silently accepts the wrong one.
def held_id(snap, id):
    _v1 = (snap.inv_ids.get(id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


# Why: Keep unread bank state distinct from an empty bank.
def banked_id(snap, id):
    if not snap.bank_known or snap.bank_ids is None:
        return 0
    return snap.bank_ids.get(id, 0)


def anywhere(snap, id):
    return held_id(snap, id) + banked_id(snap, id) + (1 if worn_id(snap, id) else 0)


def worn_id(snap, id):
    return snap.worn_ids is not None and id in snap.worn_ids


def live_item(id):
    _v3 = ([item for item in inventory.items() if item.id == id] or [None])[0]
    return (_v3 if _v3 is not None else None)


# Why: `~objbox` and `~mesbox` build a main modal, not a chat line, so their text never reaches `GameMessages`.
def modal_said(text):
    """Whether the open main modal says something, as a lower-case part of a line."""
    return any([text in line.lower() for line in reader.main_modal_texts()])


# Why: `QuestFood.name` is the host's setting and is only correct at decide time, never at import.
def food_name():
    """The food the host chose, or the lobsters this quest defaults to."""
    return (quest_food.name if quest_food.name is not None else 'Lobster')


def held_food(snap):
    """How much of it is carried. `snap.inv` is keyed by lower-cased display name."""
    _v4 = snap.inv.get(food_name().lower())
    return (_v4 if _v4 is not None else 0)
