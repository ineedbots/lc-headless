"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/locations.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.catalogs import FIRE_SPOTS, FISHING_LOCATIONS, MINING_LOCATIONS, WOODCUTTING_LOCATIONS, cook_location
from bots.account_leveler.record import Record

from rs2004.geometry import Tile
from bots.account_leveler.runes import can_steal_chaos

__all__ = ['members_ready', 'locate_method']

from bots.account_leveler.types import stock_of
def travel_food(s):
    return ([food for food in ['Lobster', 'Salmon', 'Trout', 'Shrimps'] if stock_of(s, food) >= 12] or [None])[0]


def members_ready(s):
    return all([s.levels.get(skill) >= 20 for skill in ['attack', 'strength', 'defence']]) and s.levels.get('hitpoints') >= 25 and stock_of(s, 'Coins') >= 200 and travel_food(s) is not None


def gather(name, locations, members=False):
    location = ([location for location in locations if location.name == name] or [None])[0]
    return Record({'name': name, 'settings': Record({'location': name}), 'travel': location.bank_stand, 'members': members})


def sites(plan):
    if plan.script == 'Woodcutter':
        suffix = (Record({'Tree': '(trees)', 'Oak': 'Oaks', 'Willow': 'Willows'})).get(str(plan.settings.get('tree_name')))
        return ([
            gather(f'Seers {suffix}', WOODCUTTING_LOCATIONS, True),
            gather(f'Draynor {suffix}', WOODCUTTING_LOCATIONS),
        ] if suffix else [])
    elif plan.script == 'Fisher':
        if str(plan.settings.get('fish_method')).startswith('Fly fishing'):
            return [
                gather('Seers (fly fishing)', FISHING_LOCATIONS, True),
                gather('Barbarian Village', FISHING_LOCATIONS),
            ]
        if str(plan.settings.get('fish_method')).startswith('Lobster cage'):
            return [gather('Catherby', FISHING_LOCATIONS, True)]
        return [gather('Draynor Village', FISHING_LOCATIONS)]
    elif plan.script == 'Miner':
        return list((([gather('Fight Arena Mine', MINING_LOCATIONS, True)] if isinstance(plan.settings.get('rocks'), list) and ('Iron' in plan.settings.get('rocks')) else []))) + [gather('Southeast Varrock Mine', MINING_LOCATIONS), gather('Rimmington Mine', MINING_LOCATIONS)]
    elif plan.script == 'CookBot':
        return [(Record({
            'name': name,
            'settings': Record({'location': name}),
            'travel': cook_location(name).bank.tile,
            'members': name != 'Draynor',
        })) for name in ['Catherby', 'Seers', 'Draynor']]
    elif plan.script == 'Firemaker':
        return [(Record({
            'name': name,
            'settings': Record({'location': name}),
            'travel': Tile.from_tile(FIRE_SPOTS.get(name).bank),
            'members': name == 'Seers',
        })) for name in ['Seers', 'Varrock East', 'Varrock West', 'Draynor']]
    elif plan.script == 'SmelterBot':
        return [
            Record({
            'name': 'Ardougne',
            'settings': Record({'bank_stand': Tile(2655, 3283, 0), 'furnace_stand': Tile(2600, 3310, 0)}),
            'travel': Tile(2655, 3283, 0),
            'members': True,
        }),
            Record({
            'name': 'Al Kharid',
            'settings': Record({'bank_stand': Tile(3269, 3167, 0), 'furnace_stand': Tile(3275, 3185, 0)}),
            'travel': Tile(3269, 3167, 0),
        }),
        ]
    elif plan.script == 'Thiever':
        if plan.settings.get('target') == 'Paladin':
            return [Record({'name': 'Ardougne paladins', 'settings': {}, 'travel': Tile(2655, 3311, 0), 'members': True})]
        if plan.settings['target'] == 'Warrior woman':
            return [Record({
                'name': 'Ardougne warrior women',
                'settings': Record({}),
                'travel': Tile(2629, 3295, 0),
                'members': True,
            })]
        if plan.settings['target'] == 'Farmer':
            return [
                Record({'name': 'Ardougne farm', 'settings': Record({}), 'travel': Tile(2645, 3367, 0), 'members': True}),
                Record({'name': 'Lumbridge farm', 'settings': Record({}), 'travel': Tile(3227, 3290, 0)}),
            ]
        return [
            Record({'name': 'Seers village', 'settings': Record({}), 'travel': Tile(2694, 3497, 0), 'members': True}),
            Record({'name': 'Lumbridge', 'settings': Record({}), 'travel': Tile(3221, 3219, 0)}),
        ]
    elif plan.script == 'SmithingBot':
        return [Record({'name': 'Varrock West', 'settings': Record({}), 'travel': Tile(3185, 3440, 0)})]
    elif plan.script == 'TannerBot':
        return [Record({'name': 'Al Kharid', 'settings': Record({}), 'travel': Tile(3269, 3167, 0)})]
    elif plan.script == 'RuneCrafter':
        return [Record({'name': 'Falador East', 'settings': Record({}), 'travel': Tile(3013, 3355, 0)})]
    elif plan.script == 'EssMiner':
        return [Record({'name': 'Varrock East', 'settings': Record({}), 'travel': Tile(3251, 3420, 0)})]
    elif plan.script == 'EdgevilleMonkeyBars':
        return [Record({'name': 'Edgeville', 'settings': Record({}), 'travel': Tile(3094, 3493, 0)})]
    elif plan.script == 'AIOQuester':
        return [Record({'name': 'Varrock East', 'settings': Record({}), 'travel': Tile(3253, 3420, 0)})]
    else:
        return []


def transit(plan, food=None):
    coins = ([need for need in plan.needs if need.item == 'Coins'] or [None])[0]
    meals = ([need for need in plan.needs if need.item == food or need.item == plan.food] or [None])[0]
    needs = [need for need in plan.needs if need.item != 'Coins' and (not food or (need.item != food and need.item != plan.food))]
    carried_food = ([Record({
        'item': food,
        'count': max(12, ((meals.count if meals is not None else None) if (meals.count if meals is not None else None) is not None else 0)),
        'carry': max(12, ((meals.carry if meals is not None else None) if (meals.carry if meals is not None else None) is not None else 0)),
    })] if food else [])
    _v1 = (coins.count if coins is not None else None)
    _v2 = (coins.carry if coins is not None else None)
    fare = Record({
        'item': 'Coins',
        'count': max(200, (_v1 if _v1 is not None else 0)),
        'carry': max(200, (_v2 if _v2 is not None else 0)),
    })
    _merged3 = {}
    for _k, _v in (plan.settings._fields if isinstance(plan.settings, Record) else plan.settings).items():
        _merged3[_k] = _v
    for _k, _v in (((Record({'food': food}) if food and isinstance(plan.settings.get('food'), str) else Record({})))._fields if isinstance(((Record({'food': food}) if food and isinstance(plan.settings.get('food'), str) else Record({}))), Record) else ((Record({'food': food}) if food and isinstance(plan.settings.get('food'), str) else Record({})))).items():
        _merged3[_k] = _v
    _merged4 = {}
    for _k, _v in (plan._fields if isinstance(plan, Record) else plan).items():
        _merged4[_k] = _v
    for _k, _v in (((Record({'food': food}) if food else Record({})))._fields if isinstance(((Record({'food': food}) if food else Record({}))), Record) else ((Record({'food': food}) if food else Record({})))).items():
        _merged4[_k] = _v
    for _k, _v in {'needs': list(needs) + list(carried_food) + [fare], 'settings': Record(_merged3)}.items():
        _merged4[_k] = _v
    return Record(_merged4)


def locate_method(s, input, memory, random):
    if input.script == 'GnomeCourse' or input.script == 'FlaxAIO':
        _merged5 = {}
        for _k, _v in (input._fields if isinstance(input, Record) else input).items():
            _merged5[_k] = _v
        for _k, _v in {
            'travel': (Tile(2474, 3436, 0) if input.script == 'GnomeCourse' else Tile(2725, 3493, 0)),
            'needs': list(input.needs) + [Record({'item': 'Coins', 'count': 200, 'carry': 200})],
        }.items():
            _merged5[_k] = _v
        return Record(_merged5)
    ready = can_steal_chaos(s) if input.settings.get('target') == 'Paladin' else members_ready(s)
    _merged6 = {}
    for _k, _v in (input.settings._fields if isinstance(input.settings, Record) else input.settings).items():
        _merged6[_k] = _v
    for _k, _v in {'target': 'Warrior woman'}.items():
        _merged6[_k] = _v
    _merged7 = {}
    for _k, _v in (input._fields if isinstance(input, Record) else input).items():
        _merged7[_k] = _v
    for _k, _v in {'id': 'pickpocket-warrior-women', 'label': 'pickpocket warrior women', 'settings': Record(_merged6)}.items():
        _merged7[_k] = _v
    plan = (Record(_merged7) if input.script == 'Thiever' and input.settings.get('target') != 'Paladin' and s.levels.get('thieving') >= 25 and ready else input)
    options = sites(plan)
    if not len(options):
        return plan

    candidates = []
    for site in options:
        if site.members and not ready:
            continue
        original = not site.members and (site.settings.get('location') == plan.settings.get('location') or plan.script == 'SmelterBot')
        slug = '-'.join(''.join([c if c in 'abcdefghijklmnopqrstuvwxyz0123456789' else ' ' for c in site.name.lower()]).split())
        candidates.append(Record({'site': site, 'id': plan.id if original else f'{plan.id}-{slug}'}))
    if not len(candidates):
        return None
    active = [candidate for candidate in candidates if ((memory.cooldowns.get(candidate.id) if memory.cooldowns.get(candidate.id) is not None else 0)) <= s.now]
    available = (active if len(active) else candidates)
    fresh = [candidate for candidate in available if not (candidate.id in memory.recent[-3:])]
    choices = (fresh if len(fresh) else available)
    chosen = choices[min(len(choices) - 1, math.floor(max(0, random()) * len(choices)))]
    _merged10 = {}
    for _k, _v in (plan.settings._fields if isinstance(plan.settings, Record) else plan.settings).items():
        _merged10[_k] = _v
    for _k, _v in (chosen.site.settings._fields if isinstance(chosen.site.settings, Record) else chosen.site.settings).items():
        _merged10[_k] = _v
    _merged11 = {}
    for _k, _v in (plan._fields if isinstance(plan, Record) else plan).items():
        _merged11[_k] = _v
    for _k, _v in {
        'id': chosen.id,
        'label': f'{plan.label} at {chosen.site.name}',
        'travel': chosen.site.travel,
        'settings': _merged10,
    }.items():
        _merged11[_k] = _v
    located = Record(_merged11)
    return (transit(located, plan.food or travel_food(s)) if stock_of(s, 'Coins') >= 200 else located)
