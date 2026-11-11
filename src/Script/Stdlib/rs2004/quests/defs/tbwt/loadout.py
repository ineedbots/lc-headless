"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tbwt/loadout.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.catalogs.combat import food_forms
from rs2004.catalogs.record import Record
from rs2004.quests.defs.tbwt.areas import FOOD_TARGET, KARAMBWAN_BAIT, TB_ID, TB_LUBUFU, TB_MAIN, TB_POTIONS, TB_SPEARS, TB_TAMAYU, TB_TIADECHE, TB_TINSAY
from rs2004.quests.defs.tbwt.journal import TB_FLAG
from rs2004.catalogs.tables import item_db
ITEM_DB = item_db()
from rs2004.quests.engine.types import flag_value, has_flag
from rs2004.quests.food import quest_food

__all__ = ['TB_FOODS', 'food_names', 'food_forms_for_quest', 'loadout', 'retain_loadout']

TB_FOODS = ['Lobster', 'Swordfish', 'Tuna', 'Trout', 'Salmon', 'Cake']


def food_names(configured=None):
    if configured is None:
        configured = quest_food.name
    forbidden = set(['banana', 'sliced banana', 'raw karambwan', 'karambwan', 'poorly cooked karambwan'])
    return list(list({_k: _v for _k, _v in [[name.strip().lower(), name.strip()] for name in [name for name in [configured] + list(TB_FOODS) if bool((name.strip() if name is not None else None)) and not (name.strip().lower() in forbidden)]]}.values()))


def food_forms_for_quest(configured=None):
    if configured is None:
        configured = quest_food.name
    _flat1 = []
    for _x in food_names(configured):
        _flat1.extend(food_forms(_x))
    return list(set(_flat1))


def loadout(snap):
    def stage(flag):
        return (flag_value(snap.progress, flag) if flag_value(snap.progress, flag) is not None else 0)

    def held(id):
        return ((snap.inv_ids.get(id) if snap.inv_ids is not None else None) if (snap.inv_ids.get(id) if snap.inv_ids is not None else None) is not None else 0)

    lubufu = stage(TB_FLAG.LUBUFU)
    tiadeche = stage(TB_FLAG.TIADECHE)
    tamayu = stage(TB_FLAG.TAMAYU)
    tinsay = stage(TB_FLAG.TINSAY)
    _v2 = (snap.progress.stage if snap.progress is not None else None)
    _v3 = (_v2 if _v2 is not None else snap.stage)
    phase = ('reward' if ((_v3 if _v3 is not None else 0)) >= TB_MAIN.ALL_BROTHERS else ('lubufu' if lubufu < TB_LUBUFU.COMPLETE else ('tiadeche' if tiadeche < TB_TIADECHE.REQUEST_MANUAL else ('tamayu' if tamayu < TB_TAMAYU.COMPLETE else ('rum' if tinsay < TB_TINSAY.GIVEN_RUM else ('sandwich' if tinsay < TB_TINSAY.GIVEN_SANDWICH else ('bones' if tinsay < TB_TINSAY.COMPLETE else 'manual')))))))
    spear = phase == 'tamayu' and not has_flag(snap.progress, TB_FLAG.SPEAR)
    potions = phase == 'tamayu' and not has_flag(snap.progress, TB_FLAG.AGILITY)
    poisoned = any([held(s.kp_id) > 0 for s in TB_SPEARS])
    poison = held(TB_ID.KARAMBWAN_POISON_PASTE) > 0
    fish = held(TB_ID.RAW_KARAMBWAN) + held(TB_ID.POORLY_COOKED_KARAMBWAN) > 0
    fishing = spear and not poisoned and not poison and not fish
    banked_fish = any([(((snap.bank_ids.get(id) if snap.bank_ids is not None else None) if (snap.bank_ids.get(id) if snap.bank_ids is not None else None) is not None else 0)) > 0 for id in [TB_ID.RAW_KARAMBWAN, TB_ID.POORLY_COOKED_KARAMBWAN, TB_ID.KARAMBWAN_POISON_PASTE]])
    tools = []
    if (phase == 'lubufu' and lubufu < TB_LUBUFU.GIVEN_KARAMBWANJI) or (phase == 'tiadeche' and tiadeche < TB_TIADECHE.CAUGHT and not held(TB_ID.VESSEL_LOADED) and not held(TB_ID.RAW_KARAMBWANJI)) or (fishing and not banked_fish and held(TB_ID.RAW_KARAMBWANJI) < KARAMBWAN_BAIT) or (phase == 'bones' and not any([held(id) for id in [TB_ID.RAW_KARAMBWANJI, TB_ID.KARAMBWANJI_PASTE, TB_ID.PASTY_JOGRE_BONES, TB_ID.MARINATED_JOGRE_BONES]])):
        tools.append(TB_ID.NET)
    if phase == 'rum' and not held(TB_ID.SLICED_BANANA) and not held(TB_ID.RUM_SLICED):
        tools.append(TB_ID.KNIFE)
    if (spear and not poisoned and not poison) or (phase == 'bones' and not any([held(id) for id in [TB_ID.KARAMBWANJI_PASTE, TB_ID.PASTY_JOGRE_BONES, TB_ID.MARINATED_JOGRE_BONES]])):
        tools.append(TB_ID.PESTLE)
    if phase == 'bones' and not any([held(id) for id in [TB_ID.BURNT_JOGRE_BONES, TB_ID.PASTY_JOGRE_BONES, TB_ID.MARINATED_JOGRE_BONES]]):
        tools.append(TB_ID.TINDERBOX)
    if phase == 'sandwich' and not held(TB_ID.SANDWICH):
        tools.append(TB_ID.SEAWEED)
    caps = {_k: _v for _k, _v in [[TB_ID.COINS, float('inf')]] + list([[id, 1] for id in tools])}

    def keep(ids, qty=1):
        for id in ids:
            caps[id] = qty

    if tiadeche < TB_TIADECHE.COMPLETE:
        keep([TB_ID.VESSEL, TB_ID.VESSEL_LOADED, TB_ID.CRAFTING_MANUAL])
    if phase == 'lubufu':
        caps[TB_ID.RAW_KARAMBWANJI] = max(0, TB_LUBUFU.GIVEN_KARAMBWANJI - max(lubufu, TB_LUBUFU.FETCH_KARAMBWANJI))
    elif phase == 'tiadeche' or phase == 'bones':
        caps[TB_ID.RAW_KARAMBWANJI] = 1
    else:
        if fishing:
            caps[TB_ID.RAW_KARAMBWANJI] = KARAMBWAN_BAIT
    if tamayu < TB_TAMAYU.COMPLETE and not has_flag(snap.progress, TB_FLAG.SPEAR):
        keep([TB_ID.RAW_KARAMBWAN], 2)
        keep([TB_ID.POORLY_COOKED_KARAMBWAN, TB_ID.KARAMBWAN_POISON_PASTE])
        if spear:
            _v4 = (([s for s in TB_SPEARS if held(s.kp_id)] or [None])[0].kp_id if ([s for s in TB_SPEARS if held(s.kp_id)] or [None])[0] is not None else None)
            selected = (_v4 if _v4 is not None else (([s for s in TB_SPEARS if held(s.id)] or [None])[0].id if ([s for s in TB_SPEARS if held(s.id)] or [None])[0] is not None else None))
            if selected:
                keep([selected])
    if potions:
        remaining = 4
        for potion in TB_POTIONS:
            qty = min(held(potion.id), math.ceil(remaining / potion.doses))
            if qty > 0:
                caps[potion.id] = qty
            remaining = max(0, remaining - qty * potion.doses)
    if tinsay < TB_TINSAY.GIVEN_RUM:
        keep([TB_ID.BANANA, TB_ID.SLICED_BANANA, TB_ID.RUM, TB_ID.RUM_SLICED])
    if tinsay < TB_TINSAY.GIVEN_SANDWICH:
        keep([TB_ID.MONKEY_CORPSE, TB_ID.MONKEY_SKIN, TB_ID.SANDWICH])
    if tinsay < TB_TINSAY.COMPLETE:
        keep([
            TB_ID.JOGRE_BONES,
            TB_ID.BURNT_JOGRE_BONES,
            TB_ID.PASTY_JOGRE_BONES,
            TB_ID.MARINATED_JOGRE_BONES,
            TB_ID.KARAMBWANJI_PASTE,
        ])
    catch_held = held(TB_ID.RAW_KARAMBWANJI)
    deliver_catch = phase == 'lubufu' and lubufu >= TB_LUBUFU.FETCH_KARAMBWANJI and lubufu < TB_LUBUFU.GIVEN_KARAMBWANJI and catch_held > 0 and (catch_held >= TB_LUBUFU.GIVEN_KARAMBWANJI - lubufu or ((snap.free_slots if snap.free_slots is not None else 28)) <= 1)
    compact = (phase == 'rum' and (held(TB_ID.RUM_SLICED) > 0 or (held(TB_ID.SLICED_BANANA) > 0 and held(TB_ID.RUM) > 0) or (held(TB_ID.BANANA) > 0 and held(TB_ID.KNIFE) > 0))) or (phase == 'sandwich' and (held(TB_ID.SANDWICH) > 0 or (held(TB_ID.MONKEY_SKIN) > 0 and held(TB_ID.SEAWEED) > 0))) or (phase == 'bones' and held(TB_ID.MARINATED_JOGRE_BONES) > 0) or (phase == 'tamayu' and tamayu >= TB_TAMAYU.WATCHED_CUTSCENE and ((any([held(p.id) for p in TB_POTIONS]) if potions else poisoned)))
    min_free = (0 if deliver_catch or compact else (max(1, KARAMBWAN_BAIT - catch_held) + ((0 if held(TB_ID.VESSEL) or held(TB_ID.VESSEL_LOADED) else 1)) + 2 if fishing and not banked_fish else (2 if phase == 'rum' or phase == 'sandwich' or phase == 'bones' else 1)))
    plan = Record({
        'phase': phase,
        'tools': tools,
        'caps': None,
        'food': FOOD_TARGET,
        'min_free': min_free,
        'spear': spear,
        'potions': potions,
        'deliver_catch': deliver_catch,
        'compact': compact,
    })
    plan.caps = caps
    return plan


equipment = {_k: _v for _k, _v in [[item.id, item] for item in [item for item in ITEM_DB if item.slot]]}


def retain_loadout(snap, inventory, configured):
    ids = {}
    for item in inventory:
        if not item.noted:
            _v5 = ids.get(item.id)
            ids[item.id] = ((_v5 if _v5 is not None else 0)) + item.count
    plan = loadout(snap.with_fields({'inv_ids': ids}))
    foods = set(food_forms_for_quest(configured))
    keep_ids = []
    caps = []
    names = {_k: _v for _k, _v in [[item.id, (item.name.lower() if item.name is not None else None)] for item in inventory]}
    occupied = set([item.slot for item in [item for item in ITEM_DB if item.slot and (((item.id in snap.worn_ids) if snap.worn_ids is not None else None) or (item.name.lower() in snap.worn))]])
    retained = {}
    slots = 0
    for id, count in ids.items():
        _v7 = names.get(id)
        if ((_v7 if _v7 is not None else '') in foods):
            continue
        gear = equipment.get(id)
        spare_spear = any([s.id == id or s.kp_id == id for s in TB_SPEARS])
        _v8 = plan.caps.get(id)
        limit = (_v8 if _v8 is not None else (((float('inf') if gear.slot == 'quiver' else 1) if (gear.slot if gear is not None else None) and not (gear.slot in occupied) and not spare_spear else 0)))
        qty = min(count, limit)
        if qty <= 0:
            continue
        retained[id] = qty
        slots += (1 if id == TB_ID.COINS or (gear.slot if gear is not None else None) == 'quiver' else qty)
        if (gear.slot if gear is not None else None):
            occupied.add(gear.slot)
    food = min(plan.food, max(0, 28 - slots - plan.min_free))
    for id, count in ids.items():
        _v9 = names.get(id)
        edible = ((_v9 if _v9 is not None else '') in foods)
        qty = (min(count, food) if edible else (retained.get(id) if retained.get(id) is not None else 0))
        if edible:
            food -= qty
        if qty > 0:
            keep_ids.append(id)
        if qty < count and qty > 0:
            caps.append(Record({'id': id, 'qty': qty}))
    return Record({'keep_ids': keep_ids, 'caps': caps})
