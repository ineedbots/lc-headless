"""Ported from rs2b0t's src/bot/api/ai/quests/defs/treegnome/supplies.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.loadout import gear_of
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import locs
from rs2004.items import equipment, inventory
from rs2004.quests.defs.treegnome.areas import LOGS_WANTED, TG_ITEM, TG_NPC, TG_TILE
from rs2004.quests.exec.prompts import settle_scene
from rs2004.quests.food import FOOD_FLOAT, quest_food
from rs2004.quests.gear import quest_loadout
from rs2004.traversal import traversal

__all__ = ['AXES', 'FOOD_LOW', 'FOOD_TARGET', 'has_axe', 'scan_bank', 'source_axe', 'top_up_food', 'chop_logs', 'arm_for_the_warlord']

AXES = [
    Record({'id': 1359, 'name': 'Rune axe'}),
    Record({'id': 1357, 'name': 'Adamant axe'}),
    Record({'id': 1361, 'name': 'Black axe'}),
    Record({'id': 1355, 'name': 'Mithril axe'}),
    Record({'id': 1353, 'name': 'Steel axe'}),
    Record({'id': 1349, 'name': 'Iron axe'}),
    Record({'id': 1351, 'name': 'Bronze axe'}),
]
SHOP_AXE = 'Iron axe'
SHOP_AXE_GP = 300
FOOD_LOW = 3
FOOD_TARGET = FOOD_FLOAT


def has_axe(snap):
    return any([((snap.inv_ids.get(axe.id) if snap.inv_ids.get(axe.id) is not None else 0)) > 0 or (((axe.id in snap.worn_ids) if (axe.id in snap.worn_ids) is not None else False)) for axe in AXES])


def scan_bank():
    return (Record({'kind': 'scan_bank', 'bank': TG_TILE.BANK}))


def source_axe(snap):
    """Bank first, Aemad second; an unread bank may hold one."""
    if has_axe(snap):
        return None
    if snap.bank_known != True:
        return scan_bank()
    in_bank = ([axe for axe in AXES if ((snap.bank_ids.get(axe.id) if snap.bank_ids.get(axe.id) is not None else 0)) > 0] or [None])[0]
    if in_bank:
        return Record({
            'kind': 'withdraw',
            'items': [{'name': in_bank.name, 'qty': 1, 'id': in_bank.id}],
            'bank': TG_TILE.BANK,
        })
    return Record({
        'kind': 'buy',
        'item': SHOP_AXE,
        'qty': 1,
        'shop': Record({'npc': TG_NPC.AEMAD, 'anchor': TG_TILE.AXE_SHOP}),
        'est_gp': SHOP_AXE_GP,
    })


def top_up_food(snap):
    """Top the pack back up before a fight the engine's one-shot food withdrawal cannot cover."""
    name = quest_food.name.strip()
    if not name:
        return None
    key = name.lower()
    _v1 = snap.inv.get(key)
    if ((_v1 if _v1 is not None else 0)) >= FOOD_LOW:
        return None
    if snap.bank_known != True:
        return scan_bank()
    _v2 = snap.bank.get(key)
    stock = (_v2 if _v2 is not None else 0)
    if stock == 0:
        return None
    _v3 = snap.inv.get(key)
    want = min(FOOD_TARGET - ((_v3 if _v3 is not None else 0)), stock)
    return Record({'kind': 'withdraw', 'items': [{'name': name, 'qty': want}], 'bank': TG_TILE.BANK})


CHOP_MS = 25000
CHOP_RADIUS = 9
STUMP_PATIENCE = 30


def chop_logs(log):
    _w4 = yield from traversal.walk_resilient(TG_TILE.TREES, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w4):
        return False
    yield from settle_scene()
    stumped = 0
    while inventory.count_by_id(TG_ITEM.LOGS.id) < LOGS_WANTED:
        tree = locs.query().name('Tree').action('Chop down').within(CHOP_RADIUS).nearest()
        if not tree:
            # Why: a felled tree is a stump for a few seconds, and the cluster is small enough that all of it can be down at once.
            stumped += 1
            if stumped >= STUMP_PATIENCE:
                log('every Tree around the battlefield chop stand is a stump')
                return False
            yield from execution.delay_ticks(2)
            continue
        stumped = 0
        before = inventory.count_by_id(TG_ITEM.LOGS.id)
        if not (tree.interact('Chop down')):
            return False
        yield from execution.delay_until(lambda: inventory.count_by_id(TG_ITEM.LOGS.id) > before, CHOP_MS)
        yield from sustain.run()
    return True


TIERS = ['rune', 'adamant', 'mithril', 'black', 'steel', 'iron', 'bronze']
# Why: the warlord's config carries no per-style defence, so the fastest weapon wins and the slot list is plain best-available melee.
GEAR_SLOTS = [
    Record({'kinds': ['scimitar', 'longsword', 'sword', 'mace', 'battleaxe', 'warhammer']}),
    Record({'kinds': ['platebody', 'chainbody']}),
    Record({'kinds': ['platelegs', 'plateskirt']}),
    Record({'kinds': ['full helm', 'med helm']}),
    Record({'kinds': ['kiteshield', 'sq shield']}),
]
unwearable = set()


def wearing_kind(snap, kinds):
    return any([any([name.endswith(kind) for kind in kinds]) for name in list(snap.worn)])


def best_available(snap, kinds):
    for tier in TIERS:
        for kind in kinds:
            name = f'{tier} {kind}'
            if (name in unwearable):
                continue
            _v5 = snap.bank.get(name)
            if ((_v5 if _v5 is not None else 0)) > 0 or ((snap.inv.get(name) if snap.inv.get(name) is not None else 0)) > 0:
                return name[0].upper() + name[1:]
    return None


def planned_gear(snap):
    declared = gear_of(quest_loadout.current)
    names = (declared if len(declared) > 0 else [name for name in [best_available(snap, slot.kinds) for slot in [slot for slot in GEAR_SLOTS if not wearing_kind(snap, slot.kinds)]] if name is not None])
    return [name for name in names if not (name.lower() in unwearable) and not (name.lower() in snap.worn)]


def wear_all(names, log):
    for name in names:
        _c6 = equipment.contains(name)
        if not _c6:
            _w7 = yield from equipment.equip(name)
            _c6 = (_w7)
        if _c6:
            continue
        log(f'cannot wear {name} — level or quest requirement; moving on without it')
        unwearable.add(name.lower())
    return True


def arm_for_the_warlord(snap):
    """Wield the best melee kit the bank and pack can offer, or null when dressed."""
    if snap.bank_known != True:
        return scan_bank()
    wanted = planned_gear(snap)
    if len(wanted) == 0:
        return None
    missing = [name for name in wanted if ((snap.inv.get(name.lower()) if snap.inv.get(name.lower()) is not None else 0)) == 0]
    if len(missing) > 0:
        return Record({
            'kind': 'withdraw',
            'items': [({'name': name, 'qty': 1}) for name in missing],
            'bank': TG_TILE.BANK,
        })
    return Record({'kind': 'custom', 'name': f"wear {', '.join(wanted)}", 'run': lambda log: wear_all(wanted, log)})
