"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/loadout.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.combat import food_forms
from rs2004.catalogs.record import Record
from rs2004.quests.defs.watchtower.areas import CRYSTALS, RELIC_PARTS, WT_ITEM as I, WT_TILE, watchtower_area
from rs2004.catalogs.tables import item_db
ITEM_DB = item_db()
from rs2004.quests.engine.types import flag_value, has_flag
from rs2004.quests.food import quest_food

__all__ = ['WATCHTOWER_FOODS', 'food_names', 'edible_names', 'food_count', 'phase_items', 'retain_watchtower_loadout', 'clear_space', 'fit_supplies']

WATCHTOWER_FOODS = ['Lobster', 'Swordfish', 'Tuna', 'Trout', 'Salmon', 'Cake']


def food_names(configured=None):
    if configured is None:
        configured = quest_food.name
    return list(list({_k: _v for _k, _v in [[name.lower(), name] for name in [name for name in [configured] + list(WATCHTOWER_FOODS) if bool((name.strip() if name is not None else None))]]}.values()))


def edible_names(configured=None):
    if configured is None:
        configured = quest_food.name
    _flat1 = []
    for _x in food_names(configured):
        _flat1.extend(food_forms(_x))
    return list(set(_flat1))


def food_count(snap):
    return sum([((snap.inv.get(name) if snap.inv.get(name) is not None else 0)) for name in edible_names()])


def phase_items(snap):
    def held(item):
        return ((snap.inv_ids.get(item.id) if snap.inv_ids is not None else None) if (snap.inv_ids.get(item.id) if snap.inv_ids is not None else None) is not None else 0)

    def owned(item):
        return held(item) + (((snap.bank_ids.get(item.id) if snap.bank_ids is not None else None) if (snap.bank_ids.get(item.id) if snap.bank_ids is not None else None) is not None else 0))

    _v2 = (snap.stage if snap.stage is not None else (snap.progress.stage if snap.progress is not None else None))
    stage = (_v2 if _v2 is not None else 0)
    area = watchtower_area(snap.tile)
    cave_kit = [I.SKAVID_MAP, I.LIT_CANDLE]
    if stage == 2 and not owned(I.OGRE_RELIC):
        if not has_flag(snap.progress, 'helped-og'):
            return [I.TOBAN_KEY, I.STOLEN_GOLD]
        if not has_flag(snap.progress, 'helped-toban'):
            return [I.DRAGON_BONES]
        if not has_flag(snap.progress, 'helped-grew'):
            return [I.ROPE, I.OGRE_TOOTH]
        return list(RELIC_PARTS) + list((([I.ROPE] if owned(I.JANGERBERRIES) < 2 else [])))
    if stage == 2 or stage == 3:
        return [I.OGRE_RELIC]
    if stage == 5:
        return [I.DEATH_RUNE]
    if stage == 6:
        return cave_kit
    if stage == 7:
        return list((([] if held(I.NIGHTSHADE) else cave_kit))) + [I.NIGHTSHADE]
    if stage == 9 or (stage == 10 and ((flag_value(snap.progress, 'shamans-left') if flag_value(snap.progress, 'shamans-left') is not None else 6)) > 0 and not held(I.MAGIC_OGRE_POTION)):
        potion = ([item for item in [I.MAGIC_OGRE_POTION, I.OGRE_POTION, I.GUAM_JANGER_VIAL, I.GUAM_VIAL] if owned(item)] or [None])[0]
        if potion == I.MAGIC_OGRE_POTION or potion == I.OGRE_POTION:
            return [potion]
        return list((([potion] if potion else [I.GUAM_LEAF, I.VIAL_WATER]))) + list((([] if potion == I.GUAM_JANGER_VIAL else [I.JANGERBERRIES]))) + list((([I.GROUND_BAT_BONES] if owned(I.GROUND_BAT_BONES) else [I.BAT_BONES, I.PESTLE])))
    if stage == 10:
        _v3 = flag_value(snap.progress, 'shamans-left')
        left = (_v3 if _v3 is not None else 6)
        if left > 0 or not owned(I.CRYSTAL3) or not owned(I.CRYSTAL4):
            return list((([I.MAGIC_OGRE_POTION] if left > 0 else []))) + list((([I.PICKAXE] if not owned(I.CRYSTAL4) else []))) + list((([] if area == 'enclave' else list((([] if held(I.NIGHTSHADE) else cave_kit))) + [I.NIGHTSHADE])))
        if not owned(I.CRYSTAL1):
            return [I.ROPE]
        if not owned(I.CRYSTAL2):
            return cave_kit
        return list(CRYSTALS)
    return []


db = {_k: _v for _k, _v in [[item.id, item] for item in ITEM_DB]}


def retain_watchtower_loadout(snap, inventory, configured=None, reserve=2):
    if configured is None:
        configured = quest_food.name
    ids = {}
    for item in inventory:
        if not item.noted:
            _v4 = ids.get(item.id)
            ids[item.id] = ((_v4 if _v4 is not None else 0)) + item.count
    state = snap.with_fields({'inv_ids': ids})
    _v6 = (snap.stage if snap.stage is not None else (snap.progress.stage if snap.progress is not None else None))
    stage = (_v6 if _v6 is not None else 0)
    caps = {_k: _v for _k, _v in [[item.id, 1] for item in phase_items(state)]}
    caps[I.COINS.id] = float('inf')
    if stage == 6:
        caps[I.GOLD_BAR.id] = 1
    for item in list(CRYSTALS) + [I.WATCHTOWER_SPELL]:
        caps[item.id] = 1
    if stage <= 3:
        for item in list(RELIC_PARTS) + [I.OGRE_RELIC, I.OGRE_TOOTH, I.TOBAN_KEY, I.STOLEN_GOLD, I.FINGERNAILS]:
            caps[item.id] = 1
    if stage <= 9 and not (I.OGRE_POTION.id in ids) and not (I.MAGIC_OGRE_POTION.id in ids):
        caps[I.JANGERBERRIES.id] = 2
    if stage == 9 or stage == 10:
        for item in [I.OGRE_POTION, I.MAGIC_OGRE_POTION, I.SHAMAN_ROBE]:
            caps[item.id] = 1
    foods = set(edible_names(configured))
    names = {_k: _v for _k, _v in [[item.id, (item.name.lower() if item.name is not None else None)] for item in inventory]}
    occupied = set([item.slot for item in [item for item in ITEM_DB if item.slot and (((item.id in snap.worn_ids) if snap.worn_ids is not None else None) or (item.name.lower() in snap.worn))]])
    retained = {}
    slots = 0
    for id, count in ids.items():
        _v7 = names.get(id)
        if ((_v7 if _v7 is not None else '') in foods):
            continue
        gear = db.get(id)
        _v8 = caps.get(id)
        limit = (_v8 if _v8 is not None else (((float('inf') if gear.slot == 'quiver' else 1) if (gear.slot if gear is not None else None) and not (gear.slot in occupied) else 0)))
        qty = min(count, limit)
        if qty <= 0:
            continue
        retained[id] = qty
        slots += (1 if id == I.COINS.id or (gear.slot if gear is not None else None) == 'quiver' else qty)
        if (gear.slot if gear is not None else None):
            occupied.add(gear.slot)
    food = min(8, max(0, 28 - slots - reserve))
    keep_ids = []
    limits = []
    for id, count in ids.items():
        _v9 = names.get(id)
        edible = ((_v9 if _v9 is not None else '') in foods)
        qty = (min(count, food) if edible else (retained.get(id) if retained.get(id) is not None else 0))
        if edible:
            food -= qty
        if qty > 0:
            keep_ids.append(id)
        if qty > 0 and qty < count:
            limits.append(Record({'id': id, 'qty': qty}))
    return Record({'keep_ids': keep_ids, 'caps': limits})


def clear_space(snap, reserve=2):
    names = {I.get(key).id: I.get(key).name for key in I.keys()}
    inventory = []
    for id, count in (snap.inv_ids or {}).items():
        entry = db.get(id)
        inventory.append(Record({'id': id, 'count': count, 'noted': False,
                                 'name': entry.name if entry else names.get(id)}))
    plan = retain_watchtower_loadout(snap, inventory, quest_food.name, reserve)
    if len(plan.keep_ids) < len(inventory) or plan.caps:
        return Record({'kind': 'deposit', 'keep': [], 'exact_keep': True,
                       'keep_ids': plan.keep_ids, 'caps': plan.caps, 'bank': WT_TILE.YANILLE_BANK})
    return Record({'kind': 'wait',
                   'reason': f'Watch Tower needs {reserve} free inventory slots; no surplus supplies to bank'})


def fit_supplies(snap, step):
    slots = (sum([((((0 if ((I.COINS.id in snap.inv_ids) if snap.inv_ids is not None else None) else 1)) if item.get('id') == I.COINS.id else item.get('qty'))) for item in step.items]) if step.kind == 'withdraw' else (step.qty if step.kind == 'buy' else (1 if step.kind == 'grab_ground' else 0)))
    return (clear_space(snap, slots + 2) if slots > 0 and slots + 2 > ((snap.free_slots if snap.free_slots is not None else 28)) else step)
