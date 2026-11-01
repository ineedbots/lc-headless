"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.loadout import gear_of, weapon_of
from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.items import equipment, inventory
from rs2004.quests.defs.fremenniktrials.areas import FT_ID, FT_TILE
from rs2004.quests.exec.primitives import open_dialogue
from rs2004.quests.exec.prompts import drive_until
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout
from rs2004.traversal import traversal

__all__ = ['held_count', 'held', 'worn', 'banked', 'held_id', 'food_names', 'scan_bank', 'from_bank', 'gather_knife', 'gather_axe', 'gather_tinderbox', 'gather_shark', 'gather_coins', 'planned_gear', 'wear_all', 'combat_kit', 'walk_to', 'talk_until', 'combine']

def held_count(snap, name):
    return snap.inv.get(name.lower(), 0)


def held(snap, name):
    return held_count(snap, name) > 0


def worn(snap, name):
    return (name.lower() in snap.worn)


def banked(snap, name):
    return snap.bank.get(name.lower(), 0) if snap.bank is not None else 0


def held_id(snap, id):
    return snap.inv_ids.get(id, 0) if snap.inv_ids is not None else 0


def banked_id(snap, id):
    return snap.bank_ids.get(id, 0) if snap.bank_ids is not None else 0


COMBAT_FOODS = ['Lobster', 'Swordfish', 'Tuna', 'Salmon', 'Trout']


def food_names():
    configured = (quest_food.name.strip() if quest_food.name is not None else None)
    names = []
    seen = set()
    for name in [configured] + list(COMBAT_FOODS):
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def food_held(snap):
    return sum([held_count(snap, name) for name in food_names()])


def food_in_bank(snap):
    _v1 = ([name for name in food_names() if banked(snap, name) > 0] or [None])[0]
    return (_v1 if _v1 is not None else None)


FOOD_TARGET = 8


def scan_bank():
    return (Record({'kind': 'scan_bank', 'bank': FT_TILE.SEERS_BANK}))


def withdraw_step(items):
    return (Record({'kind': 'withdraw', 'items': items, 'bank': FT_TILE.SEERS_BANK}))


def from_bank(snap, wants):
    """Top the pack up from the Seers' Village bank. Null when everything is carried or the bank has none of it."""
    if not snap.bank_known:
        return scan_bank()
    missing = []
    for w in wants:
        has = held_count(snap, w.name) if w.id is None else held_id(snap, w.id)
        stock = banked(snap, w.name) if w.id is None else banked_id(snap, w.id)
        if has < w.qty and stock > 0:
            missing.append({'name': w.name, 'qty': w.qty, 'id': w.id})
    return (withdraw_step(missing) if len(missing) > 0 else None)


# Why: the 2 tools the quest can't buy near Rellekka both have a permanent ground spawn inside the town's map squares.
def gather_knife(snap):
    """Bank first, then the spawn north-east of Rellekka."""
    if held(snap, 'Knife'):
        return None
    _v2 = from_bank(snap, [Record({'name': 'Knife', 'qty': 1})])
    return (_v2 if _v2 is not None else Record({'kind': 'grab_ground', 'item': 'Knife', 'anchor': FT_TILE.KNIFE_SPAWN}))


def gather_axe(snap):
    if held(snap, 'Bronze axe') or worn(snap, 'Bronze axe') or any_axe(snap):
        return None
    _v3 = from_bank(snap, [Record({'name': 'Bronze axe', 'qty': 1})])
    return (_v3 if _v3 is not None else Record({'kind': 'grab_ground', 'item': 'Bronze axe', 'anchor': FT_TILE.AXE_SPAWN}))


AXES = ['bronze axe', 'iron axe', 'steel axe', 'black axe', 'mithril axe', 'adamant axe', 'rune axe']


def any_axe(snap):
    return any([(name in snap.inv) or (name in snap.worn) for name in AXES])


def gather_tinderbox(snap):
    """Arhein's Catherby stall is the closest tinderbox to Rellekka."""
    if held(snap, 'Tinderbox'):
        return None
    _v4 = from_bank(snap, [Record({'name': 'Tinderbox', 'qty': 1})])
    return (_v4 if _v4 is not None else Record({
        'kind': 'buy',
        'item': 'Tinderbox',
        'qty': 1,
        'shop': Record({'npc': 'Arhein', 'anchor': FT_TILE.ARHEIN}),
        'est_gp': 200,
    }))


# Why: No practical nearby shop stocks raw shark, and catching one requires Fishing 76.
def gather_shark(snap):
    """Bank first, then Rufus in Canifis, the only restocking raw shark in the game."""
    if held_id(snap, FT_ID.RAW_SHARK) > 0:
        return None
    _v5 = from_bank(snap, [Record({'name': 'Raw shark', 'qty': 1, 'id': FT_ID.RAW_SHARK})])
    return (_v5 if _v5 is not None else Record({
        'kind': 'buy',
        'item': 'Raw shark',
        'qty': 1,
        'shop': Record({'npc': 'Rufus', 'anchor': FT_TILE.RUFUS}),
        'est_gp': 4000,
    }))


# Why: the bank is a 50s walk from Rellekka and the quest spends coin in 5 places, so a lump costs 1 trip where change for each costs 5.
COIN_LUMP = 20000


def gather_coins(snap, need):
    if held_count(snap, 'Coins') >= need:
        return None
    if not snap.bank_known:
        return scan_bank()
    available = banked(snap, 'Coins')
    if available + held_count(snap, 'Coins') < need:
        return Record({'kind': 'wait', 'reason': f'need {need} gp and the bank cannot cover it'})
    return withdraw_step([{'name': 'Coins', 'qty': min(available, max(need, COIN_LUMP))}])


TIERS = ['rune', 'adamant', 'mithril', 'black', 'steel', 'iron', 'bronze']
# Why: the Draugen's melee defences are all 100, so only the tier matters.
# Why: chainbody leads the body slot because rune platebody also wants Dragon Slayer, and `Equipment.equip` refuses it silently.
GEAR_SLOTS = [
    ['2h sword', 'longsword', 'scimitar', 'battleaxe', 'warhammer', 'mace', 'sword'],
    ['chainbody', 'platebody'],
    ['platelegs', 'plateskirt'],
    ['full helm', 'med helm'],
    ['kiteshield', 'sq shield'],
]


def wearing_slot(snap, kinds):
    for name in snap.worn:
        if any([name.endswith(kind) for kind in kinds]):
            return True
    return False


def best_in_bank(snap, kinds):
    for tier in TIERS:
        for kind in kinds:
            name = f'{tier} {kind}'
            if banked(snap, name) > 0 or held(snap, name):
                return name[0].upper() + name[1:]
    return None


def planned_gear(snap):
    """The declared loadout, or the best the bank holds when nothing is declared."""
    declared = gear_of(quest_loadout.current)
    names = (declared if len(declared) > 0 else [name for name in [best_in_bank(snap, kinds) for kinds in [kinds for kinds in GEAR_SLOTS if not wearing_slot(snap, kinds)]] if name is not None])
    return [name for name in names if not worn(snap, name)]


def wear_all(names):
    def _fn6(log):
        for name in names:
            _c7 = equipment.contains(name)
            if not _c7:
                _w8 = yield from equipment.equip(name)
                _c7 = (_w8)
            if _c7:
                continue
            log(f'cannot wear {name} — banking it and moving on')
        return True
    return Record({'kind': 'custom', 'name': f"wear {', '.join(names)}", 'run': _fn6})


def combat_kit(snap):
    """Dress and feed for the Draugen. Null once the kit is on. Missing armour is survivable, a missing weapon isn't."""
    if not snap.bank_known:
        return scan_bank()
    food = food_in_bank(snap)
    if food_held(snap) < FOOD_TARGET and food is not None:
        return withdraw_step([{'name': food, 'qty': FOOD_TARGET - food_held(snap)}])
    wanted = [name for name in planned_gear(snap) if banked(snap, name) > 0 or held(snap, name)]
    to_withdraw = [name for name in wanted if not held(snap, name)]
    if len(to_withdraw) > 0:
        return withdraw_step([{'name': name, 'qty': 1} for name in to_withdraw])
    to_wear = [name for name in wanted if held(snap, name)]
    if len(to_wear) > 0:
        return wear_all(to_wear)
    weapon = weapon_of(quest_loadout.current)
    if len(snap.worn) == 0 and weapon is None:
        return Record({'kind': 'wait', 'reason': 'no loadout gear and nothing worn — the Draugen hits back'})
    return None


WALK_ATTEMPTS = 4
WALK_MS = 300000


def walk_to(tile, radius, log):
    here = game.tile()
    if here and here.level == tile.level and tile.distance_to(here) <= radius:
        return True
    _result9 = yield from traversal.walk_resilient(tile, radius=radius, attempts=WALK_ATTEMPTS, timeout_ms=WALK_MS, log=log)
    return _result9


# Why: a conversation opened on the tick the walk lands sometimes drives to nothing; a re-open costs 1s where the engine's retry costs the step's budget again.
def talk_until(npc, near, prefer, expect, log, ms=60000):
    """Walk to an NPC and keep re-opening the conversation until the goal lands."""
    _w11 = yield from walk_to(near, 2, log)
    if not (_w11):
        return False
    deadline = _core.step_time() + ms
    while _core.step_time() < deadline and not expect():
        yield from execution.delay_ticks(2)
        _w12 = yield from open_dialogue(npc, log)
        if not (_w12):
            continue
        yield from drive_until(expect, list(prefer), log, min(30000, deadline - _core.step_time()))
    return expect()


def _combine(item_id, target_id, product_id, label, log):
    item = ([i for i in inventory.items() if i.id == item_id] or [None])[0]
    target = ([i for i in inventory.items() if i.id == target_id] or [None])[0]
    if not item or not target:
        log(f'{label}: missing {(item_id if not item else target_id)} in the pack')
        return False
    before = inventory.count_by_id(product_id)
    if not (item.use_on(target)):
        return False
    _result14 = yield from execution.delay_until(lambda: inventory.count_by_id(product_id) > before, 10000)
    return _result14


def combine(item_id, target_id, product_id, label):
    """Use a held item on another held item and wait for the product id to land."""
    return Record({'kind': 'custom', 'name': label, 'run': lambda log: _combine(item_id, target_id, product_id, label, log)})
