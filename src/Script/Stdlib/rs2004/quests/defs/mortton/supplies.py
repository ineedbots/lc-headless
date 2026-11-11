"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import _core
import math
from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items
from rs2004.items import inventory
from rs2004.quests.defs.mortton.areas import SM_ID, SM_LOC, SM_LOC_ID, SM_NAME, SM_STAGE, SM_TILE, VARROCK_GENERAL
from rs2004.quests.exec.prompts import settle_scene, use_on_loc
from rs2004.quests.food import quest_food
from rs2004.traversal import traversal

__all__ = ['COIN_TARGET', 'COIN_LOW', 'FOOD_TARGET', 'FOOD_LOW', 'DOSES_PER_VIAL', 'SM_TOOLS', 'held_id', 'banked_id', 'SERUM_BY_DOSE', 'PERM_SERUM_BY_DOSE', 'serum_doses', 'perm_serum_doses', 'serum_vials', 'serum_vial_id', 'perm_serum_vial_id', 'recover_pyre_supplies', 'doses_needed', 'serums_short', 'recover_serum', 'ashes_short', 'logs_short', 'kit', 'make_ashes', 'fill_vial']

COIN_TARGET = 30000
COIN_LOW = 5000
# Why: 6 is what the temple loadout can spare; the shopping trip fills 15 slots and Morytania has no bank to trim against.
FOOD_TARGET = 6
# Why: the only bank inside Morytania is Canifis, 200 tiles north of the temple, so a restock only happens when the last food has gone.
FOOD_LOW = 1
DOSES_PER_VIAL = 3
TINDERBOX_GP = 100
# Why: a fire burns 100-200 ticks before it drops its ashes and the spawn has its own timer, so 2 burns is minutes.
BURN_BUDGET_MS = 420000
SM_TOOLS = [
    'coins',
    'tinderbox',
    'hammer',
    'logs',
    'ashes',
    'diary',
    'vial',
    'herb',
    'tarromin',
    'unfinished potion',
    'serum 207',
    'loar remains',
    'olive oil',
    'sacred oil',
    'pyre logs',
    'plank',
    'limestone brick',
    'swamp paste',
]


def held_id(snap, id):
    count = None if snap.inv_ids is None else snap.inv_ids.get(id)
    return count if count is not None else 0


def banked_id(snap, id):
    count = None if snap.bank_ids is None else snap.bank_ids.get(id)
    return count if count is not None else 0


SERUM_BY_DOSE = [[SM_ID.SERUM4, 4], [SM_ID.SERUM3, 3], [SM_ID.SERUM2, 2], [SM_ID.SERUM1, 1]]
PERM_SERUM_BY_DOSE = [[SM_ID.SERUM_PERM4, 4], [SM_ID.SERUM_PERM3, 3], [SM_ID.SERUM_PERM2, 2], [SM_ID.SERUM_PERM1, 1]]


def doses(snap, table):
    return sum([held_id(snap, id) * per for id, per in table])


def serum_doses(snap):
    return doses(snap, SERUM_BY_DOSE)


def perm_serum_doses(snap):
    return doses(snap, PERM_SERUM_BY_DOSE)


def serum_vials(snap):
    """Vials of serum 207 held, whatever their dose."""
    return sum([held_id(snap, id) for id, _dose in SERUM_BY_DOSE])


def first_held(table):
    for id, _dose in table:
        if inventory.count_by_id(id) > 0:
            return id
    return None


def serum_vial_id():
    return first_held(SERUM_BY_DOSE)


def perm_serum_vial_id():
    return first_held(PERM_SERUM_BY_DOSE)


scan_bank = Record({'kind': 'scan_bank'})


# Why: a dose is spent per villager conversation the quest still owes, and each conversation is gated on a stage, so what is left to brew falls out of where the quest is.
def doses_needed(stage):
    """Doses of serum the rest of the quest still spends from this stage on."""
    doses = 1
    if stage < SM_STAGE.KILL_SHADES:
        doses += 1
    if stage < SM_STAGE.SHADES_TO_RAZMIRE:
        doses += 1
    if stage < SM_STAGE.ULSQUIRE_TEMPLE:
        doses += 1
    return doses


# Why: counting a half-brewed vial as a vial stops the chain on the unfinished potion and leaves the last conversation unpayable.
def serums_short(snap, stage):
    """Serums still to brew for the rest of the quest, at 3 doses a vial."""
    have = serum_doses(snap) + perm_serum_doses(snap)
    return max(0, math.ceil((doses_needed(stage) - have) / DOSES_PER_VIAL))


def kept(name, keep):
    lower = name.lower()
    return any([k in lower for k in keep])


def recover_serum(snap, stage):
    if stage < SM_STAGE.READ_DIARY or serums_short(snap, stage) == 0:
        return None
    if not snap.bank_known:
        return scan_bank
    ingredients = [
        Record({'id': SM_ID.TARROMIN_UNF, 'name': 'Unfinished potion'}),
        Record({'id': SM_ID.TARROMIN, 'name': 'Tarromin'}),
        Record({'id': SM_ID.UNID_TARROMIN, 'name': 'Herb'}),
    ]
    serums = []
    if stage >= SM_STAGE.MADE_SERUM:
        serums = [Record({'id': id, 'name': f'Serum 207(p) ({dose})'}) for id, dose in PERM_SERUM_BY_DOSE]
        serums = serums + [Record({'id': id, 'name': f'Serum 207 ({dose})'}) for id, dose in SERUM_BY_DOSE]
    brewing = any([held_id(snap, item.id) > 0 for item in ingredients])
    candidates = serums + ([] if brewing else ingredients)
    item = ([item for item in candidates if banked_id(snap, item.id) > 0] or [None])[0]
    if not item:
        return None
    if snap.free_slots == 0:
        keep = ['coins', 'serum 207', 'pyre logs', 'loar remains', 'sacred oil', 'olive oil']
        expendable = any([count > 0 and not kept(name, keep) for name, count in snap.inv.items()])
        return (Record({'kind': 'deposit', 'keep': keep}) if expendable else Record({'kind': 'wait', 'reason': 'no pack room for serum recovery'}))
    return Record({'kind': 'withdraw', 'items': [{'id': item.id, 'name': item.name, 'qty': 1}]})


# Why: nothing inside Morytania sells or spawns logs and no axe is carried, so the 2 spawns beside the Varrock east bank feed both the ashes and the pyre.
def ashes_short(snap, stage):
    """Ashes still to burn: one per serum this quest has yet to brew."""
    return max(0, serums_short(snap, stage) - held_id(snap, SM_ID.ASHES))


# Why: After `logs_on_pyre`, the log has been consumed and should not trigger another swamp trip.
def logs_short(snap, stage):
    """Logs the pack still needs: one per outstanding burn, plus the one the pyre consumes."""
    spent = stage >= SM_STAGE.LOGS_ON_PYRE or (stage >= SM_STAGE.CREATED_PYRE_LOGS and held_id(snap, SM_ID.PYRE_LOGS) > 0)
    return max(0, ashes_short(snap, stage) + ((0 if spent else 1)) - held_id(snap, SM_ID.LOGS))


# Why: `ownsInventory` opts this quest out of the engine's coin and food withdrawal, so both are drawn here.
# Why: the tinderbox and the logs ride the same trip, since the ashes leg burns them at the Varrock spawn on the way east.
def kit(snap, stage):
    """Coins, food, tinderbox and logs, bank first. Null once the approach pack is ready."""
    food_name = (quest_food.name.strip() if quest_food.name is not None else None)
    food_held = 0
    if food_name:
        count = snap.inv.get(food_name.lower())
        food_held = count if count is not None else 0
    need_coins = held_id(snap, SM_ID.COINS) < COIN_LOW
    need_food = bool(food_name) and food_held < FOOD_LOW
    need_tinderbox = held_id(snap, SM_ID.TINDERBOX) == 0
    need_logs = logs_short(snap, stage) > 0
    if not need_coins and not need_food and not need_tinderbox and not need_logs:
        return None
    if not snap.bank_known:
        return scan_bank
    items = []
    _v7 = (snap.bank.get('coins') if snap.bank is not None else None)
    banked_coins = (_v7 if _v7 is not None else 0)
    if need_coins and banked_coins > 0:
        items.append({'name': SM_NAME.COINS, 'qty': min(COIN_TARGET, banked_coins), 'id': SM_ID.COINS})
    if need_food and food_name:
        _v8 = (snap.bank.get(food_name.lower()) if snap.bank is not None else None)
        banked = (_v8 if _v8 is not None else 0)
        if banked > 0:
            items.append({'name': food_name, 'qty': min(FOOD_TARGET - food_held, banked)})
    if need_tinderbox and banked_id(snap, SM_ID.TINDERBOX) > 0:
        items.append({'name': SM_NAME.TINDERBOX, 'qty': 1, 'id': SM_ID.TINDERBOX})
    if need_logs and banked_id(snap, SM_ID.LOGS) > 0:
        items.append({'name': SM_NAME.LOGS, 'qty': logs_short(snap, stage), 'id': SM_ID.LOGS})
    if len(items) > 0:
        return Record({'kind': 'withdraw', 'items': items})
    if need_tinderbox:
        return Record({'kind': 'buy', 'item': SM_NAME.TINDERBOX, 'qty': 1, 'shop': VARROCK_GENERAL, 'est_gp': TINDERBOX_GP})
    return None


def burn_one(log):
    """Light one held log and take the ashes the fire leaves behind."""
    tinder = ([i for i in inventory.items() if i.id == SM_ID.TINDERBOX] or [None])[0]
    logs = ([i for i in inventory.items() if i.id == SM_ID.LOGS] or [None])[0]
    if not tinder or not logs:
        log('burnOne: no tinderbox or no logs in the pack')
        return False
    before = inventory.count_by_id(SM_ID.ASHES)
    if not (tinder.use_on(logs)):
        return False

    # Why: the fire burns 100-200 ticks before `obj_addall` drops its ashes, so the wait is minutes.
    def ashes_near():
        return ground_items.query().where(lambda g: g.id == SM_ID.ASHES).within(3).nearest() is not None

    _w10 = yield from execution.delay_until(ashes_near, 180000)
    if not (_w10):
        log('burnOne: the fire never left any ashes')
        return False
    ash = ground_items.query().where(lambda g: g.id == SM_ID.ASHES).within(3).nearest()
    if not ash or not (ash.interact('Take')):
        return False
    _result11 = yield from execution.delay_until(lambda: inventory.count_by_id(SM_ID.ASHES) > before, 8000)
    return _result11


# Why: the spawn is 2 logs at a time on its own timer, so the loop burns whatever is spare as it goes.
def make_ashes(ashes, logs):
    """Take logs from the Varrock spawns, burning them until the pack holds the ashes and the pyre log."""

    def _fn12(log):
        if bank.is_open():
            yield from bank.close()
        _w13 = yield from traversal.walk_resilient(SM_TILE.VARROCK_LOGS, radius=2, attempts=3, timeout_ms=180000, log=log)
        if not (_w13):
            return False
        yield from settle_scene()
        deadline = _core.step_time() + BURN_BUDGET_MS
        while _core.step_time() < deadline:
            burns_left = max(0, ashes - inventory.count_by_id(SM_ID.ASHES))
            held = inventory.count_by_id(SM_ID.LOGS)
            if burns_left == 0 and held >= logs:
                return True
            if burns_left > 0 and held > logs:
                _w14 = yield from burn_one(log)
                if not (_w14):
                    return False
                continue
            spawn = ground_items.query().where(lambda g: g.id == SM_ID.LOGS).within(8).nearest()
            if not spawn:
                # Both spawns are taken; they come back on their own timer.
                yield from execution.delay_ticks(4)
                continue
            if spawn.interact('Take'):
                yield from execution.delay_until(lambda: inventory.count_by_id(SM_ID.LOGS) > held, 8000)
        log(f'makeAshes: gave up holding {inventory.count_by_id(SM_ID.ASHES)} ashes and {inventory.count_by_id(SM_ID.LOGS)} logs')
        return False
    return _fn12


def fill_vial(log):
    """Fill an empty vial at the Mort'ton sink."""
    before = inventory.count_by_id(SM_ID.VIAL_WATER)
    return use_on_loc(SM_ID.VIAL_EMPTY, Record({'name': SM_LOC.SINK, 'near': SM_TILE.SINK, 'id': SM_LOC_ID.SINK, 'within': 8}), [], lambda: inventory.count_by_id(SM_ID.VIAL_WATER) > before, log)


def recover_pyre_supplies(snap, need_logs, need_oil, need_remains):
    if not need_logs and not need_oil and not need_remains:
        return None
    if not snap.bank_known:
        return scan_bank
    items = []
    if need_logs and banked_id(snap, SM_ID.PYRE_LOGS) > 0:
        items.append(Record({'name': SM_NAME.PYRE_LOGS, 'id': SM_ID.PYRE_LOGS, 'qty': 1}))
    elif need_oil:
        oil = ([id for id in [
            SM_ID.SACRED_OIL4,
            SM_ID.SACRED_OIL3,
            SM_ID.SACRED_OIL2,
            SM_ID.OLIVE_OIL4,
            SM_ID.OLIVE_OIL3,
            SM_ID.OLIVE_OIL2,
        ] if banked_id(snap, id) > 0] or [None])[0]
        if oil is not None:
            items.append(Record({'name': ('Olive oil' if oil <= SM_ID.OLIVE_OIL2 else 'Sacred oil'), 'id': oil, 'qty': 1}))
    if need_remains and banked_id(snap, SM_ID.REMAINS) > 0:
        items.append(Record({'name': SM_NAME.REMAINS, 'id': SM_ID.REMAINS, 'qty': 1}))
    if len(items) == 0:
        return None
    if ((snap.free_slots if snap.free_slots is not None else len(items))) < len(items):
        keep = list(SM_TOOLS) + list((([quest_food.name.lower()] if quest_food.name else [])))
        expendable = any([count > 0 and not any([(k in name.lower()) for k in keep]) for name, count in list(snap.inv.items())])
        return (Record({'kind': 'deposit', 'keep': keep}) if expendable else Record({'kind': 'wait', 'reason': 'no pack room for pyre recovery'}))
    return Record({'kind': 'withdraw', 'items': items})
