"""Ported from rs2b0t's src/bot/api/ai/quests/defs/chompybird/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.chompybird.areas import BOB_AXES, CB_ID, CB_NAME, CB_TILE, GERRANT
from rs2004.quests.food import quest_food

__all__ = ['ARROW_TARGET', 'FOOD_TARGET', 'COIN_TARGET', 'held_id', 'banked_id', 'selected_food', 'scan_bank', 'withdraw', 'keep_list', 'held_axe', 'make_space', 'loadout_step', 'tool_step', 'tools_held', 'feathers_step']

ARROW_TARGET = 12
FOOD_TARGET = 6
COIN_TARGET = 2000
COIN_FLOOR = 300
AXES = ['Rune axe', 'Adamant axe', 'Mithril axe', 'Black axe', 'Steel axe', 'Iron axe', 'Bronze axe']


def held_id(snap, id):
    count = None if snap.inv_ids is None else snap.inv_ids.get(id)
    return count if count is not None else 0


def banked_id(snap, id):
    count = None if snap.bank_ids is None else snap.bank_ids.get(id)
    return count if count is not None else 0


def held(snap, name):
    count = snap.inv.get(name.lower())
    return count if count is not None else 0


def banked(snap, name):
    count = None if snap.bank is None else snap.bank.get(name.lower())
    return count if count is not None else 0


def selected_food():
    food = (quest_food.name.strip() if quest_food.name is not None else None)
    return (food if food else None)


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': CB_TILE.YANILLE_BANK})


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': CB_TILE.YANILLE_BANK})


def keep_list():
    """Everything this quest carries; anything else is spillover."""
    food = (selected_food().lower() if selected_food() is not None else None)
    return [n.lower() for n in list([a.lower() for a in AXES]) + [CB_NAME.KNIFE, CB_NAME.CHISEL, CB_NAME.FEATHER, CB_NAME.COINS, CB_NAME.ACHEY_LOGS, CB_NAME.SHAFT, CB_NAME.FLIGHTED, CB_NAME.WOLF_BONES, CB_NAME.ARROWTIPS, CB_NAME.ARROW, CB_NAME.BOW, CB_NAME.TOAD, CB_NAME.RAW_CHOMPY, CB_NAME.SEASONED_CHOMPY, CB_NAME.POTATO, CB_NAME.ONION, CB_NAME.CABBAGE, CB_NAME.TOMATO, CB_NAME.DOOGLE, CB_NAME.EQUA, 'ogre bellows', 'scimitar', 'longsword', 'battleaxe', 'mace', 'sword', 'chainbody', 'platebody', 'platelegs', 'plateskirt', 'full helm', 'med helm', 'kiteshield', 'sq shield'] + list((([food] if food else [])))]


def held_axe(snap):
    _v1 = ([name for name in AXES if held(snap, name) > 0] or [None])[0]
    return (_v1 if _v1 is not None else None)


def banked_axe(snap):
    _v2 = ([name for name in AXES if banked(snap, name) > 0] or [None])[0]
    return (_v2 if _v2 is not None else None)


def make_space(snap, slots):
    """Bank the junk this quest has no use for, so a withdrawal has somewhere to land."""
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    keep = keep_list()
    spillover = any([not any([(k in name) for k in keep]) for name in list(list(snap.inv.keys()))])
    if not spillover:
        return None
    return Record({'kind': 'deposit', 'keep': keep, 'bank': CB_TILE.YANILLE_BANK})


# Why: `ownsInventory` retires the engine's provisioning, so coins, food and the axe are this module's own bank trip.
def loadout_step(snap, want_axe=True):
    """Coins, food and, when `wantAxe`, an axe. Null once the pack is dressed."""
    if not snap.bank_known:
        return scan_bank()
    space = make_space(snap, 4)
    if space:
        return space
    wants = []
    # Why: Withdraw all available kit before the separate Lumbridge axe trip.
    for tool in [Record({'name': CB_NAME.KNIFE, 'id': CB_ID.KNIFE}), Record({'name': CB_NAME.CHISEL, 'id': CB_ID.CHISEL})]:
        if held_id(snap, tool.id) == 0 and banked_id(snap, tool.id) > 0:
            wants.append({'name': tool.name, 'qty': 1, 'id': tool.id})
    coins = held(snap, CB_NAME.COINS)
    if coins < COIN_FLOOR:
        take = min(COIN_TARGET - coins, banked(snap, CB_NAME.COINS))
        if take > 0:
            wants.append({'name': CB_NAME.COINS, 'qty': take})
    food = selected_food()
    if food and held(snap, food) == 0:
        take = min(FOOD_TARGET, banked(snap, food))
        if take > 0:
            wants.append({'name': food, 'qty': take})
    if want_axe and held_axe(snap) is None:
        from_bank = banked_axe(snap)
        if from_bank:
            wants.append({'name': from_bank, 'qty': 1})
    if len(wants) > 0:
        return withdraw(wants)
    if want_axe and held_axe(snap) is None:
        # Why: No nearby shop sells an axe, and achey trees cannot be chopped without one.
        return Record({'kind': 'buy', 'item': 'Bronze axe', 'qty': 1, 'shop': BOB_AXES, 'est_gp': 100})
    return None


# Why: Bugs only sells the pair while the quest sits at stage 5, so every later leg relies on the account's own knife and chisel.
def tool_step(snap):
    """A knife and a chisel from the bank. Null when both are held, or when the bank has neither."""
    missing = [tool for tool in [Record({'name': CB_NAME.KNIFE, 'id': CB_ID.KNIFE}), Record({'name': CB_NAME.CHISEL, 'id': CB_ID.CHISEL})] if held_id(snap, tool.id) == 0]
    if len(missing) == 0:
        return None
    if not snap.bank_known:
        return scan_bank()
    stored = [tool for tool in missing if banked_id(snap, tool.id) > 0]
    if len(stored) < len(missing):
        return None
    return withdraw([{'name': tool.name, 'qty': 1, 'id': tool.id} for tool in stored])


def tools_held(snap):
    return held_id(snap, CB_ID.KNIFE) > 0 and held_id(snap, CB_ID.CHISEL) > 0


def feathers_step(snap, want):
    """Feathers up to `want`: the bank first, then Gerrant's counter in Port Sarim."""
    have = held_id(snap, CB_ID.FEATHER)
    if have >= want:
        return None
    if not snap.bank_known:
        return scan_bank()
    space = make_space(snap, 1)
    if space:
        return space
    short = want - have
    from_bank = min(short, banked_id(snap, CB_ID.FEATHER))
    if from_bank > 0:
        return withdraw([{'name': CB_NAME.FEATHER, 'qty': from_bank, 'id': CB_ID.FEATHER}])
    return Record({'kind': 'buy', 'item': CB_NAME.FEATHER, 'qty': short, 'shop': GERRANT, 'est_gp': short * 4})
