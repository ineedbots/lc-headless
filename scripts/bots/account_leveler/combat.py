"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/combat.ts (MIT, see thirdparty/rs2b0t)."""

import math
from bots.account_leveler.record import Record

from rs2004.geometry import Tile

__all__ = ['COMBAT_CAMPS', 'scimitar_for', 'food_for', 'combat_plan']

from bots.account_leveler.equipment import melee_equipment, ranged_bow
from bots.account_leveler.offers import purchase_budget, supply_offer
from bots.account_leveler.catalog import can_catch, consumable_batch, FISH
from bots.account_leveler.magic import magic_equipment
from bots.account_leveler.combat_progression import combat_level, TARGET_TIERS, training_tier
from bots.account_leveler.training_camps import TRAINING_CAMPS
COMBAT_CAMPS = [Record({
    'id': 'lumbridge-chickens',
    'region': 'lumbridge',
    'target': 'Chicken',
    'x': 3230,
    'z': 3298,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'falador-chickens',
    'region': 'falador',
    'target': 'Chicken',
    'x': 3018,
    'z': 3289,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'lumbridge-goblins',
    'region': 'lumbridge',
    'target': 'Goblin',
    'x': 3252,
    'z': 3228,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'talisman': True,
}), Record({
    'id': 'goblin-village',
    'region': 'falador',
    'target': 'Goblin',
    'x': 2956,
    'z': 3500,
    'hp': 12,
    'offence': 5,
    'defence': 5,
    'talisman': True,
}), Record({
    'id': 'lumbridge-men',
    'region': 'lumbridge',
    'target': 'Man',
    'x': 3221,
    'z': 3219,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'herbs': True,
}), Record({
    'id': 'edgeville-men',
    'region': 'edgeville',
    'target': 'Man',
    'x': 3097,
    'z': 3508,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'herbs': True,
}), Record({
    'id': 'rimmington-rats',
    'region': 'rimmington',
    'target': 'Rat',
    'x': 2957,
    'z': 3204,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'port-sarim-goblins',
    'region': 'port-sarim',
    'target': 'Goblin',
    'x': 3000,
    'z': 3207,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'talisman': True,
}), Record({
    'id': 'draynor-goblins',
    'region': 'draynor',
    'target': 'Goblin',
    'x': 3144,
    'z': 3230,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'talisman': True,
}), Record({
    'id': 'lumbridge-west-chickens',
    'region': 'lumbridge',
    'target': 'Chicken',
    'x': 3188,
    'z': 3278,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'lumbridge-cows',
    'region': 'lumbridge',
    'target': 'Cow',
    'x': 3255,
    'z': 3278,
    'hp': 12,
    'offence': 5,
    'defence': 5,
}), Record({
    'id': 'falador-cows',
    'region': 'falador',
    'target': 'Cow',
    'x': 3030,
    'z': 3300,
    'hp': 12,
    'offence': 5,
    'defence': 5,
}), Record({
    'id': 'monastery',
    'region': 'edgeville',
    'target': 'Monk',
    'x': 3050,
    'z': 3491,
    'hp': 15,
    'offence': 10,
    'defence': 10,
}), Record({
    'id': 'ardougne-farmer',
    'region': 'ardougne',
    'target': 'Farmer',
    'x': 2645,
    'z': 3367,
    'hp': 15,
    'offence': 10,
    'defence': 10,
    'herbs': True,
}), Record({
    'id': 'barbarian-village',
    'region': 'edgeville',
    'target': 'Barbarian',
    'x': 3078,
    'z': 3419,
    'hp': 16,
    'offence': 10,
    'defence': 10,
    'herbs': True,
}), Record({
    'id': 'taverley-druids',
    'region': 'taverley',
    'target': 'Chaos druid',
    'x': 2931,
    'z': 9846,
    'hp': 25,
    'offence': 20,
    'defence': 15,
    'herbs': True,
}), Record({
    'id': 'seers-men',
    'region': 'seers',
    'target': 'Man',
    'x': 2695,
    'z': 3493,
    'hp': 25,
    'offence': 20,
    'defence': 20,
    'herbs': True,
}), Record({
    'id': 'seers-women',
    'region': 'seers',
    'target': 'Woman',
    'x': 2696,
    'z': 3496,
    'hp': 25,
    'offence': 20,
    'defence': 20,
    'herbs': True,
}), Record({
    'id': 'catherby-men',
    'region': 'catherby',
    'target': 'Man',
    'x': 2804,
    'z': 3430,
    'hp': 25,
    'offence': 20,
    'defence': 20,
    'herbs': True,
}), Record({
    'id': 'ardougne-men',
    'region': 'ardougne',
    'target': 'Man',
    'x': 2614,
    'z': 3318,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'ardougne-cows',
    'region': 'ardougne',
    'target': 'Cow',
    'x': 2664,
    'z': 3347,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'ardougne-monks',
    'region': 'ardougne',
    'target': 'Monk',
    'x': 2608,
    'z': 3213,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'ardougne-guards',
    'region': 'ardougne',
    'target': 'Guard',
    'x': 2659,
    'z': 3308,
    'hp': 30,
    'offence': 25,
    'defence': 25,
}), Record({
    'id': 'ardougne-goblins',
    'region': 'ardougne',
    'target': 'Goblin',
    'x': 2580,
    'z': 3413,
    'hp': 25,
    'offence': 20,
    'defence': 20,
    'talisman': True,
}), Record({
    'id': 'khazard-troopers',
    'region': 'khazard',
    'target': 'Khazard trooper',
    'x': 2528,
    'z': 3241,
    'hp': 30,
    'offence': 25,
    'defence': 25,
}), Record({
    'id': 'yanille-men',
    'region': 'yanille',
    'target': 'Man',
    'x': 2596,
    'z': 3105,
    'hp': 25,
    'offence': 20,
    'defence': 20,
    'herbs': True,
}), Record({
    'id': 'yanille-cows',
    'region': 'yanille',
    'target': 'Cow',
    'x': 2585,
    'z': 3119,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'yanille-soldiers',
    'region': 'yanille',
    'target': 'Soldier',
    'x': 2544,
    'z': 3094,
    'hp': 35,
    'offence': 30,
    'defence': 30,
}), Record({
    'id': 'taverley-surface-druids',
    'region': 'taverley',
    'target': 'Druid',
    'x': 2895,
    'z': 3438,
    'hp': 35,
    'offence': 30,
    'defence': 30,
    'herbs': True,
}), Record({
    'id': 'lumbridge-swamp-giant-rats',
    'region': 'lumbridge',
    'target': 'Giant rat',
    'x': 3195,
    'z': 3205,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'lumbridge-south-giant-rats',
    'region': 'lumbridge',
    'target': 'Giant rat',
    'x': 3209,
    'z': 3177,
    'hp': 12,
    'offence': 5,
    'defence': 5,
}), Record({
    'id': 'port-sarim-giant-rats',
    'region': 'port-sarim',
    'target': 'Giant rat',
    'x': 2997,
    'z': 3193,
    'hp': 12,
    'offence': 5,
    'defence': 5,
}), Record({
    'id': 'varrock-east-giant-rats',
    'region': 'varrock',
    'target': 'Giant rat',
    'x': 3265,
    'z': 3382,
    'hp': 12,
    'offence': 5,
    'defence': 5,
}), Record({
    'id': 'varrock-spiders',
    'region': 'varrock',
    'target': 'Spider',
    'x': 3243,
    'z': 3395,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'lumbridge-giant-spiders',
    'region': 'lumbridge',
    'target': 'Giant spider',
    'x': 3244,
    'z': 3234,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'edgeville-giant-spiders',
    'region': 'edgeville',
    'target': 'Giant spider',
    'x': 3147,
    'z': 3481,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'al-kharid-spiders',
    'region': 'al-kharid',
    'target': 'Spider',
    'x': 3322,
    'z': 3140,
    'hp': 10,
    'offence': 1,
    'defence': 1,
}), Record({
    'id': 'falador-dwarves',
    'region': 'falador',
    'target': 'Dwarf',
    'x': 3019,
    'z': 3338,
    'hp': 18,
    'offence': 10,
    'defence': 10,
}), Record({
    'id': 'ice-mountain-dwarves',
    'region': 'ice-mountain',
    'target': 'Dwarf',
    'x': 3015,
    'z': 3428,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'ice-mountain-west-dwarves',
    'region': 'ice-mountain',
    'target': 'Dwarf',
    'x': 2999,
    'z': 3449,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'lumbridge-women',
    'region': 'lumbridge',
    'target': 'Woman',
    'x': 3218,
    'z': 3205,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'herbs': True,
}), Record({
    'id': 'lumbridge-east-women',
    'region': 'lumbridge',
    'target': 'Woman',
    'x': 3243,
    'z': 3211,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'herbs': True,
}), Record({
    'id': 'port-sarim-women',
    'region': 'port-sarim',
    'target': 'Woman',
    'x': 3011,
    'z': 3236,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'herbs': True,
}), Record({
    'id': 'falador-women',
    'region': 'falador',
    'target': 'Woman',
    'x': 2970,
    'z': 3389,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'herbs': True,
}), Record({
    'id': 'varrock-square-women',
    'region': 'varrock',
    'target': 'Woman',
    'x': 3223,
    'z': 3401,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'herbs': True,
}), Record({
    'id': 'varrock-northeast-women',
    'region': 'varrock',
    'target': 'Woman',
    'x': 3278,
    'z': 3499,
    'hp': 10,
    'offence': 1,
    'defence': 1,
    'herbs': True,
}), Record({
    'id': 'catherby-women',
    'region': 'catherby',
    'target': 'Woman',
    'x': 2817,
    'z': 3443,
    'hp': 25,
    'offence': 20,
    'defence': 20,
    'herbs': True,
}), Record({
    'id': 'yanille-women',
    'region': 'yanille',
    'target': 'Woman',
    'x': 2566,
    'z': 3084,
    'hp': 25,
    'offence': 20,
    'defence': 20,
    'herbs': True,
}), Record({
    'id': 'barbarian-women',
    'region': 'edgeville',
    'target': 'Barbarian woman',
    'x': 3079,
    'z': 3423,
    'hp': 16,
    'offence': 10,
    'defence': 10,
    'herbs': True,
}), Record({
    'id': 'varrock-barbarian-woman',
    'region': 'varrock',
    'target': 'Barbarian woman',
    'x': 3225,
    'z': 3395,
    'hp': 16,
    'offence': 10,
    'defence': 10,
    'herbs': True,
}), Record({
    'id': 'al-kharid-warriors',
    'region': 'al-kharid',
    'target': 'Al-Kharid warrior',
    'x': 3287,
    'z': 3172,
    'hp': 18,
    'offence': 10,
    'defence': 10,
    'herbs': True,
}), Record({
    'id': 'falador-highwaymen',
    'region': 'falador',
    'target': 'Highwayman',
    'x': 3008,
    'z': 3276,
    'hp': 15,
    'offence': 10,
    'defence': 10,
}), Record({
    'id': 'draynor-highwayman',
    'region': 'draynor',
    'target': 'Highwayman',
    'x': 3110,
    'z': 3295,
    'hp': 15,
    'offence': 10,
    'defence': 10,
}), Record({
    'id': 'varrock-unicorns',
    'region': 'varrock',
    'target': 'Unicorn',
    'x': 3284,
    'z': 3352,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'edgeville-unicorns',
    'region': 'edgeville',
    'target': 'Unicorn',
    'x': 3087,
    'z': 3452,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'al-kharid-scorpions',
    'region': 'al-kharid',
    'target': 'Scorpion',
    'x': 3299,
    'z': 3303,
    'hp': 25,
    'offence': 20,
    'defence': 20,
}), Record({
    'id': 'khazard-gnomes',
    'region': 'khazard',
    'target': 'Gnome',
    'x': 2532,
    'z': 3219,
    'hp': 30,
    'offence': 25,
    'defence': 25,
}), Record({
    'id': 'wilderness-skeletons',
    'region': 'wilderness',
    'target': 'Skeleton',
    'x': 3106,
    'z': 3548,
    'hp': 30,
    'offence': 20,
    'defence': 20,
    'wilderness': True,
})] + list(TRAINING_CAMPS)


def scimitar_for(attack):
    return ('Mithril scimitar' if attack >= 20 else ('Steel scimitar' if attack >= 5 else 'Iron scimitar'))


def food_for(s):
    for food in ['Lobster', 'Salmon', 'Trout']:
        _v1 = s.stock.get(food.lower())
        if ((_v1 if _v1 is not None else 0)) >= 24:
            return food
    _v2 = s.stock.get('shrimps')
    if ((_v2 if _v2 is not None else 0)) >= 24:
        return 'Shrimps'
    return ('Trout' if s.levels.get('cooking') >= 15 and (((s.stock.get('raw trout') if s.stock.get('raw trout') is not None else 0)) >= 28 or can_catch(s, FISH[1])) else 'Shrimps')


def combat_plan(s, objective, memory, random, resource=None):
    style = ('mage' if objective == 'magic' else ('range' if objective == 'ranged' else 'melee'))
    offence = (s.levels.get('magic') if style == 'mage' else (s.levels.get('ranged') if style == 'range' else min(s.levels.get('attack'), s.levels.get('strength'))))
    level = combat_level(s.levels)
    death_walk = style == 'melee' and level < 15
    camps = [c for c in COMBAT_CAMPS if s.levels.get('hitpoints') >= c.hp and offence >= c.offence and s.levels.get('defence') >= c.defence and level >= ((c.min_combat if c.min_combat is not None else 0)) and (not death_walk or c.offence <= 15 and c.defence <= 15 and c.x >= 2840 and c.z < 3520 and not c.wilderness) and (c.x >= 2840 or ((s.stock.get('coins') if s.stock.get('coins') is not None else 0)) >= 200) and (not c.wilderness or s.wilderness) and ((memory.cooldowns.get(c.id) if memory.cooldowns.get(c.id) is not None else 0)) <= s.now and (resource != '#199' or c.herbs) and (resource != 'Air talisman' or c.talisman) and (resource != 'Cow hide' or c.target == 'Cow')]
    if level >= 15 and not resource and len(camps):
        def tier(camp):
            return ((camp.training_tier if camp.training_tier is not None else TARGET_TIERS.get(camp.target)) if (camp.training_tier if camp.training_tier is not None else TARGET_TIERS.get(camp.target)) is not None else 0)

        camps = [camp for camp in camps if tier(camp) <= training_tier(s.levels)]
        best = max([tier(_x) for _x in camps] or [-1])
        camps = [camp for camp in camps if tier(camp) == best]
    fresh = [c for c in camps if not (c.id in memory.recent[-3:])]
    if len(fresh):
        camps = fresh
    if not len(camps):
        return None
    regions = list(set([camp.region for camp in camps]))
    _flat3 = []
    for id in memory.recent:
        _flat3.extend([camp.region for camp in [camp for camp in COMBAT_CAMPS if camp.id == id]])
    recent_regions = _flat3

    def visits(region):
        return len([recent for recent in recent_regions if recent == region])

    least_visited = min([visits(_x) for _x in regions])
    fresh_regions = [region for region in regions if visits(region) == least_visited]
    region = fresh_regions[min(len(fresh_regions) - 1, math.floor(max(0, random()) * len(fresh_regions)))]
    camps = [camp for camp in camps if camp.region == region]
    camp = camps[min(len(camps) - 1, math.floor(max(0, random()) * len(camps)))]
    food = (None if death_walk else food_for(s))
    needs = ([Record({'item': food, 'count': 24, 'carry': 12, 'equip': False})] if food else [])
    _v4 = s.stock.get('coins')
    if ((_v4 if _v4 is not None else 0)) >= 200:
        needs.append(Record({'item': 'Coins', 'count': 200, 'carry': 200}))
    magic = (magic_equipment(s) if style == 'mage' else None)
    ammo = (consumable_batch(s, [Record({'item': 'Bronze arrow', 'count': 1})], 300) or [None])[0]
    if style == 'melee':
        needs.extend(list(melee_equipment(s)))
    elif style == 'range':
        _v5 = s.stock.get('bronze arrow')
        missing_ammo = max(0, ammo.count - ((_v5 if _v5 is not None else 0)))
        ammo_budget = (purchase_budget(supply_offer('Bronze arrow'), missing_ammo) if missing_ammo else 0)
        _v6 = s.stock.get('coins')
        _merged7 = {}
        for _k, _v in (s.stock._fields if isinstance(s.stock, Record) else s.stock).items():
            _merged7[_k] = _v
        for _k, _v in {'coins': ((_v6 if _v6 is not None else 0)) - ammo_budget}.items():
            _merged7[_k] = _v
        _merged8 = {}
        for _k, _v in (s._fields if isinstance(s, Record) else s).items():
            _merged8[_k] = _v
        for _k, _v in {'stock': Record(_merged7)}.items():
            _merged8[_k] = _v
        _v9 = s.stock.get('coins')
        _merged10 = {}
        for _k, _v in (s.stock._fields if isinstance(s.stock, Record) else s.stock).items():
            _merged10[_k] = _v
        for _k, _v in {'coins': ((_v9 if _v9 is not None else 0)) - ammo_budget}.items():
            _merged10[_k] = _v
        _merged11 = {}
        for _k, _v in (s._fields if isinstance(s, Record) else s).items():
            _merged11[_k] = _v
        for _k, _v in {'stock': Record(_merged10)}.items():
            _merged11[_k] = _v
        needs.append(ranged_bow(Record(_merged8)))
        _merged12 = {}
        for _k, _v in (ammo._fields if isinstance(ammo, Record) else ammo).items():
            _merged12[_k] = _v
        for _k, _v in {'equip': True}.items():
            _merged12[_k] = _v
        _merged13 = {}
        for _k, _v in (ammo._fields if isinstance(ammo, Record) else ammo).items():
            _merged13[_k] = _v
        for _k, _v in {'equip': True}.items():
            _merged13[_k] = _v
        needs.append(Record(_merged12))
    else:
        needs.extend(list(magic.needs))
    melee_style = (objective if (objective in ['attack', 'strength', 'defence']) else (sorted(['attack', 'strength', 'defence'], key=lambda a: s.levels.get(a)) or [None])[0])
    _v14 = (magic.spell if magic is not None else None)
    _v15 = (magic.casts if magic is not None else None)
    return Record({
        'id': camp.id,
        'label': f"{camp.target} at {camp.id.replace('-', ' ')}{str((' (death walk)' if death_walk else ''))}",
        'objective': objective,
        'script': 'AutoFighter',
        'needs': needs,
        'combat': True,
        'death_walk': death_walk,
        'wilderness': camp.wilderness,
        'food': food,
        'travel': Tile(camp.x, camp.z, 0),
        'output': (Record({'item': resource, 'count': (14 if resource == '#199' else 1)}) if resource else None),
        'settings': Record({
        'target': camp.target,
        'spot': 'Custom coordinates',
        'coordinates': Tile(camp.x, camp.z, 0),
        'leash_radius': 12,
        'combat_style': style,
        'melee_style': melee_style,
        'range_style': 'rapid',
        'spell': (_v14 if _v14 is not None else 'Wind Strike'),
        'runes_withdraw': (_v15 if _v15 is not None else 150),
        'ammo': 'Bronze arrow',
        'ammo_withdraw': ammo.carry,
        'use_special': False,
        'solve_clues': False,
        'banking': 'Auto',
        'food': (food if food is not None else 'Shrimps'),
        'food_withdraw': (0 if death_walk else 12),
        'panic_hp': (0 if death_walk else 15),
        'bury_bones': True,
        'bury_big_bones': True,
        'loot': ['Bones', 'Herb', 'Air talisman'] + list(((['Cow hide'] if resource == 'Cow hide' else []))),
        'avoid_herbs': [],
        'loadout': '',
        'bank_every_minutes': 8,
    }),
    })
