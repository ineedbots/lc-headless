"""Ported from rs2b0t's src/bot/api/ai/quests/engine/resumePreparation.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.catalogs.record import Record
from rs2004.quests.defs.biohazard.areas import BIO_ITEM
from rs2004.quests.defs.chompybird.areas import CB_ID
from rs2004.quests.defs.deathplateau.areas import DEATH_ITEM
from rs2004.quests.defs.digsite.areas import DIG_ID
from rs2004.quests.defs.eadgar.areas import ER_ITEM
from rs2004.quests.defs.elementalworkshop.areas import EW_ITEM
from rs2004.quests.defs.familycrest.areas import FC_ID
from rs2004.quests.defs.fremenniktrials.areas import FT_ID
from rs2004.quests.defs.heroquest.areas import HERO_ID
from rs2004.quests.defs.legends.areas import LQ_ID
from rs2004.quests.defs.plaguecity.areas import PC_ITEM
from rs2004.quests.defs.regicide.areas import RG_ITEM
from rs2004.quests.defs.shilo.areas import SV_ITEM
from rs2004.quests.defs.tbwt.areas import TB_ID, TB_POTION_IDS, TB_SPEAR_IDS
from rs2004.quests.defs.upass.areas import UP_ITEM
from rs2004.quests.defs.watchtower.areas import WT_ITEM
from rs2004.quests.food import FOOD_FLOAT

__all__ = ['resume_preparation']

# Equipment and untradeable ids are preserved even when their names are unknown.
from rs2004.catalogs.tables import item_db
from rs2004.market._data import UNTRADEABLE_IDS
def ids(items):
    return [item.id for item in [items.get(key) for key in items.keys()]]


QUEST_IDS = Record({
    'biohazard': ids(BIO_ITEM),
    'chompybird': [CB_ID.get(key) for key in CB_ID.keys()],
    'death': ids(DEATH_ITEM),
    'itexam': [DIG_ID.get(key) for key in DIG_ID.keys()],
    'eadgar': ids(ER_ITEM),
    'elemental_workshop': ids(EW_ITEM),
    'crest': [FC_ID.get(key) for key in FC_ID.keys()],
    'viking': [FT_ID.get(key) for key in FT_ID.keys()],
    'hero': [HERO_ID.get(key) for key in HERO_ID.keys()],
    'legends': [LQ_ID.get(key) for key in LQ_ID.keys()],
    'elena': ids(PC_ITEM),
    'regicide': ids(RG_ITEM),
    'zombiequeen': ids(SV_ITEM),
    'tbwt': list([TB_ID.get(key) for key in TB_ID.keys()]) + list(TB_POTION_IDS) + list(TB_SPEAR_IDS),
    'upass': ids(UP_ITEM),
    'itwatchtower': ids(WT_ITEM),
})
MATERIAL_FOOD = Record({
    'death': Record({'bread': 10, 'trout': 10}),
    'crest': Record({'tuna': 1, 'bass': 1, 'salmon': 1, 'shrimps': 1, 'swordfish': 1}),
    'viking': Record({'cabbage': 1, 'onion': 1, 'potato': 1}),
    'regicide': Record({'cooked rabbit': 1}),
    'tbwt': Record({
    'banana': float('inf'),
    'sliced banana': float('inf'),
    'raw karambwan': float('inf'),
    'karambwan': float('inf'),
    'poorly cooked karambwan': float('inf'),
}),
})
EQUIPMENT_IDS = set([item.id for item in [item for item in item_db() if item.slot]])
PROTECTED_IDS = set(list(UNTRADEABLE_IDS) + [995] + list(EQUIPMENT_IDS))
FOODS = ['trout', 'salmon', 'tuna', 'lobster', 'swordfish', 'shark']


def resume_preparation(module, snap, inventory, food):
    if snap.journal != 'in_progress' or ((snap.free_slots if snap.free_slots is not None else 28)) > 4:
        return None
    if module.record.id == 'legends' and any([(((snap.inv_ids.get(id) if snap.inv_ids is not None else None) if (snap.inv_ids.get(id) if snap.inv_ids is not None else None) is not None else 0)) > 0 or any([item.id == id and item.count > 0 for item in inventory]) for id in [LQ_ID.GOLD_BOWL_WATER, LQ_ID.GOLD_BOWL_PURE, LQ_ID.GOLD_BOWL_BLESSED_WATER, LQ_ID.GOLD_BOWL_BLESSED_PURE]]):
        return None
    _v1 = QUEST_IDS.get(module.record.id)
    quest_ids = set((_v1 if _v1 is not None else []))
    _v2 = MATERIAL_FOOD.get(module.record.id)
    material_food = {key: _v2.get(key) for key in _v2.keys()} if _v2 is not None else {}
    materials = set(list([item.name.lower() for item in module.record.items]) + list(list(material_food.keys())))
    tool_names = module.tools() if callable(module.tools) else module.tools
    tools = [name.lower() for name in (tool_names or [])]
    _v3 = (module.sustain.foods if module.sustain is not None else None)
    foods = set([name.lower() for name in list(FOODS) + list(((_v3 if _v3 is not None else []))) + list((([food] if food else [])))])
    for item in module.record.items:
        name = item.name.lower()
        if (name in foods) or (name in material_food):
            _v4 = material_food.get(name)
            material_food[name] = max(item.qty, (_v4 if _v4 is not None else 0))
    totals = {}
    for item in inventory:
        if item.count <= 0:
            continue
        previous = totals.get(item.id)
        _v5 = (item.name.lower() if item.name is not None else None)
        _v6 = (_v5 if _v5 is not None else (previous.name if previous is not None else None))
        _v7 = (previous.count if previous is not None else None)
        _v8 = (previous.slots if previous is not None else None)
        totals[item.id] = Record({
            'name': (_v6 if _v6 is not None else None),
            'count': item.count + ((_v7 if _v7 is not None else 0)),
            'noted': item.noted == True,
            'slots': ((_v8 if _v8 is not None else 0)) + 1,
        })
    keep_ids = []
    caps = []
    remaining_food = (module.food if module.food is not None else FOOD_FLOAT)
    for id, item in totals.items():
        if item.noted:
            continue
        name = item.name
        material = name is not None and ((name in materials) or ((id in quest_ids) and not (name in FOODS)))
        edible = name is not None and (name in foods)
        tool = name is not None and any([(tool in name) for tool in tools])
        spare_gear = (id in EQUIPMENT_IDS) and item.slots > 1 and item.count == item.slots and not (id in quest_ids) and not material and not tool
        if name is None or (id in PROTECTED_IDS) or (id in quest_ids) or material or edible or tool or (name is not None and (name.endswith(' rune') or any([part in name for part in ['potion', 'antipoison', 'antifire']]))):
            keep_ids.append(id)
        target = (material_food.get(name) if name is not None and (name in material_food) else (remaining_food if edible and not material else (1 if spare_gear else None)))
        if target is not None and not (id in UNTRADEABLE_IDS):
            qty = min(item.count, target)
            if edible and not material:
                remaining_food -= qty
            if qty < item.count:
                caps.append(Record({'id': id, 'qty': qty}))
    return (Record({'keep_ids': keep_ids, 'caps': caps}) if len(keep_ids) < len(totals) or len(caps) > 0 else None)
