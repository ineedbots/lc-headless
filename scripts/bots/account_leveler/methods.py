"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/methods.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

from rs2004.geometry import Tile

__all__ = ['quest_plan', 'method_for', 'producer']

from bots.account_leveler.combat import combat_plan, food_for
from bots.account_leveler.equipment import gathering_tool, melee_equipment
from bots.account_leveler.locations import locate_method, members_ready
from bots.account_leveler.catalog import FISH, FLETCHING, WOODS, POTIONS, can_source_wood, can_catch, consumable_batch, next_milestone, smith_product
from bots.account_leveler.types import stock_of
def banked(item, count=28):
    return (Record({'item': item, 'count': count}))


def tool(item):
    return (Record({'item': item, 'count': 1, 'carry': 1}))


gather_settings = Record({
    'bank': True,
    'tool_acquire': 'Off',
    'bank_teleport': 'Off',
    'tick_manip': 'Off',
    'withdraw_coins': 0,
    'forgetful_bank': False,
})


def activity(objective, id, script, settings, needs=None):
    if needs is None:
        needs = []
    return Record({
        'objective': objective,
        'id': id,
        'label': id.replace('-', ' '),
        'script': script,
        'settings': settings,
        'needs': needs,
    })


def quest_plan(s, objective, id, name, combat=False):
    from bots.account_leveler.dragons import dragon_planks
    from bots.account_leveler.dragon_weapons import zanaris_exit_needs
    from rs2004.quests.defs.dragonslayer.journal import DRAGON_STAGE
    from rs2004.quests.strike import STRIKE_CASTS, strike_spell
    from rs2004.catalogs.combat import runes_per_cast
    dragon = name == 'Dragon Slayer'
    food = 'Lobster' if dragon or combat else food_for(s)
    repaired = (s.dragon_stage or 0) >= DRAGON_STAGE.REPAIRED_SHIP
    coins = 2000
    if dragon:
        coins = 200 if repaired else (max(200, min(15000, stock_of(s, 'Coins'))) if s.dragon_stage else 15000)
    supply = Record(s._fields)
    supply.stock = Record(s.stock._fields if isinstance(s.stock, Record) else s.stock)
    supply.stock['coins'] = max(0, stock_of(s, 'Coins') - coins)
    kit = melee_equipment(supply) if id != 'zanaris' and (id == 'druid' or dragon or combat) else []
    needs = [Record({'item': food, 'count': 24, 'carry': 12}), banked('Coins', coins)] + kit
    if id == 'zanaris':
        needs.extend(zanaris_exit_needs(s) or [])
        for cost in runes_per_cast(strike_spell(s.levels.get('magic')) or 'Wind Strike', []):
            rune = cost['rune']
            count = cost['count']
            existing = [need for need in needs if need.item == rune]
            if existing:
                existing[0].count += count * STRIKE_CASTS
            else:
                needs.append(banked(rune, count * STRIKE_CASTS))
    if not s.wilderness and dragon and not repaired:
        needs.append(Record({'item': 'Plank', 'count': dragon_planks(s), 'carry': dragon_planks(s)}))
    plan = activity(objective, f'quest-{id}', 'AIOQuester', Record({'quests': [id], 'food': food, 'loadout': '', 'gather_wilderness_planks': s.wilderness}), needs)
    plan['quest'] = name
    plan['food'] = food
    return plan


def prerequisite_combat(s, objective, memory, random, levels):
    _v3 = ([(name, level) for name, level in list(levels.items()) if s.levels.get(name) < level] or [None])[0]
    skill = (_v3[0] if _v3 is not None else None)
    if not skill:
        return None
    plan = combat_plan(s, skill, memory, random)
    if plan is None:
        return None
    _merged4 = {}
    for _k, _v in (plan._fields if isinstance(plan, Record) else plan).items():
        _merged4[_k] = _v
    for _k, _v in {'objective': objective, 'prerequisite_levels': {skill: levels.get(skill)}}.items():
        _merged4[_k] = _v
    return (Record(_merged4) if plan else None)


def select_method(s, objective, memory, random):
    from bots.account_leveler.dragons import dragon_food_levels, dragon_prayer, dragon_ready, dragon_supply_levels, next_dragon_quest
    if objective in ['attack', 'strength', 'defence', 'prayer'] and s.levels.get(objective) < s.target:
        quest = next_dragon_quest(s, memory)
        if quest or objective == 'prayer' and dragon_ready(s) and stock_of(s, 'Dragonfire shield') > 0:
            levels = dragon_food_levels(s)
            if quest and quest.id == 'dragon':
                for skill, level in dragon_supply_levels(s).items():
                    levels[skill] = level
            for req in (quest.requirements.skills or []) if quest else []:
                levels[req.skill] = max(levels.get(req.skill, 0), req.level)
            missing = [(skill, level) for skill, level in levels.items() if s.levels.get(skill) < level]
            if missing:
                skill, level = missing[0]
                plan = select_method(s, skill, memory, random)
                if plan:
                    plan['objective'] = objective
                    plan['prerequisite_levels'] = Record({skill: level})
                    return plan
            elif quest:
                return quest_plan(s, objective, quest.id, quest.name, True)
        if objective == 'prayer':
            plan = dragon_prayer(s, memory, random)
            if plan:
                return plan
    if objective in ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']:
        return combat_plan(s, objective, memory, random)
    elif objective == 'fishing':
        return fish_plan(s, objective)
    elif objective == 'cooking':
        return cook_plan(s, objective)
    elif objective == 'woodcutting':
        return logs_plan(s, objective)
    elif objective == 'firemaking':
        wood = ([w for w in list(reversed(WOODS)) if s.levels.get('firemaking') >= w.level and can_source_wood(s, w.item)] or [None])[0]
        return activity(objective, f"burn-{wood.item.lower().replace(' ', '-')}", 'Firemaker', Record({'log_type': wood.item, 'location': 'Varrock East'}), [tool('Tinderbox'), banked(wood.item)])
    elif objective == 'fletching':
        recipe = ([r for r in list(reversed(FLETCHING)) if s.levels.get('fletching') >= r.level and can_source_wood(s, r.item)] or [None])[0]
        return activity(objective, f"fletch-{recipe.item.lower().replace(' ', '-')}", 'BankFletcher', Record({'mode': 'cut', 'material': recipe.item, 'product': recipe.product}), [tool('Knife'), banked(recipe.item)])
    elif objective == 'mining':
        return ore_plan(s, objective, ('Iron' if s.levels.get('mining') >= 30 else ('Copper' if stock_of(s, 'Copper ore') <= stock_of(s, 'Tin ore') else 'Tin')))
    elif objective == 'smithing':
        metal = ('Iron' if s.levels.get('smithing') >= 15 and (s.levels.get('mining') >= 30 or stock_of(s, 'Iron ore') >= 28 or stock_of(s, 'Iron bar') >= 14) else 'Bronze')
        return (activity(objective, f'smith-{metal.lower()}', 'SmithingBot', Record({'bar': metal, 'product': smith_product(s.levels.get('smithing'), metal)}), [tool('Hammer'), banked(f'{metal} bar', 14)]) if stock_of(s, f'{metal} bar') >= 14 else smelt_plan(objective, metal))
    elif objective == 'crafting':
        thread = (consumable_batch(s, [Record({'item': 'Thread', 'count': 1})], 100) or [None])[0]
        if s.levels.get('crafting') < 10 or stock_of(s, 'Leather') >= 26:
            _merged5 = {}
            for _k, _v in (activity(objective, 'craft-soft-leather', 'LeatherCrafter', Record({'leather_type': 'Leather', 'thread_per_trip': thread.carry}), [tool('Needle'), thread, banked('Leather', 26)])._fields if isinstance(activity(objective, 'craft-soft-leather', 'LeatherCrafter', Record({'leather_type': 'Leather', 'thread_per_trip': thread.carry}), [tool('Needle'), thread, banked('Leather', 26)]), Record) else activity(objective, 'craft-soft-leather', 'LeatherCrafter', Record({'leather_type': 'Leather', 'thread_per_trip': thread.carry}), [tool('Needle'), thread, banked('Leather', 26)])).items():
                _merged5[_k] = _v
            for _k, _v in (((Record({'prerequisite_levels': Record({'crafting': min(10, s.target)})}) if s.levels.get('crafting') < 10 else Record({})))._fields if isinstance(((Record({'prerequisite_levels': Record({'crafting': min(10, s.target)})}) if s.levels.get('crafting') < 10 else Record({}))), Record) else ((Record({'prerequisite_levels': Record({'crafting': min(10, s.target)})}) if s.levels.get('crafting') < 10 else Record({})))).items():
                _merged5[_k] = _v
            return Record(_merged5)
        return with_food(s, activity(objective, 'pick-and-spin-flax', 'FlaxAIO', Record({'picking': True, 'spinning': True})))
    elif objective == 'agility':
        if s.levels.get('agility') >= 15 and s.wilderness:
            food = food_for(s)
            _merged6 = {}
            for _k, _v in (with_food(s, activity(objective, 'edgeville-monkey-bars', 'EdgevilleMonkeyBars', Record({
                'food': food,
                'food_amount': 12,
                'min_food': 1,
                'restock_mode': 'Dungeon ladder (out of food)',
                'loadout': '',
            })))._fields if isinstance(with_food(s, activity(objective, 'edgeville-monkey-bars', 'EdgevilleMonkeyBars', Record({
                'food': food,
                'food_amount': 12,
                'min_food': 1,
                'restock_mode': 'Dungeon ladder (out of food)',
                'loadout': '',
            }))), Record) else with_food(s, activity(objective, 'edgeville-monkey-bars', 'EdgevilleMonkeyBars', Record({
                'food': food,
                'food_amount': 12,
                'min_food': 1,
                'restock_mode': 'Dungeon ladder (out of food)',
                'loadout': '',
            })))).items():
                _merged6[_k] = _v
            for _k, _v in {'wilderness': True}.items():
                _merged6[_k] = _v
            return Record(_merged6)
        return with_food(s, activity(objective, 'gnome-course', 'GnomeCourse', Record({})))
    elif objective == 'thieving':
        food = food_for(s)
        farmer = s.levels.get('thieving') >= 10
        _merged7 = {}
        for _k, _v in (activity(objective, ('pickpocket-farmers' if farmer else 'pickpocket-men'), 'Thiever', Record({
            'target': ('Farmer' if farmer else 'Man'),
            'action': 'Pickpocket',
            'banking': 'Auto',
            'food': food,
            'food_withdraw': 12,
            'suicide': False,
            'loadout': '',
        }), [Record({'item': food, 'count': 24, 'carry': 12})])._fields if isinstance(activity(objective, ('pickpocket-farmers' if farmer else 'pickpocket-men'), 'Thiever', Record({
            'target': ('Farmer' if farmer else 'Man'),
            'action': 'Pickpocket',
            'banking': 'Auto',
            'food': food,
            'food_withdraw': 12,
            'suicide': False,
            'loadout': '',
        }), [Record({'item': food, 'count': 24, 'carry': 12})]), Record) else activity(objective, ('pickpocket-farmers' if farmer else 'pickpocket-men'), 'Thiever', Record({
            'target': ('Farmer' if farmer else 'Man'),
            'action': 'Pickpocket',
            'banking': 'Auto',
            'food': food,
            'food_withdraw': 12,
            'suicide': False,
            'loadout': '',
        }), [Record({'item': food, 'count': 24, 'carry': 12})])).items():
            _merged7[_k] = _v
        for _k, _v in {'travel': (Tile(2645, 3367, 0) if farmer else Tile(3221, 3219, 0)), 'food': food}.items():
            _merged7[_k] = _v
        return Record(_merged7)
    elif objective == 'herblore':
        if not s.quests.get('Druidic Ritual'):
            levels = Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25})
            if any([s.levels.get(skill) < level for skill, level in list(levels.items())]):
                return prerequisite_combat(s, objective, memory, random, levels)
            return quest_plan(s, objective, 'druid', 'Druidic Ritual')
        _v9 = ([p for p in list(reversed(POTIONS)) if s.levels.get('herblore') >= p.level and stock_of(s, p.herb) >= 14 and stock_of(s, p.secondary) >= 14] or [None])[0]
        recipe = (_v9 if _v9 is not None else POTIONS[0])
        return activity(objective, f"make-{recipe.herb.lower().replace(' ', '-')}-potions", 'PotionMaker', Record({'herb': recipe.herb, 'secondary': recipe.secondary}), [banked(recipe.herb, 14), banked('Vial of water', 14), banked(recipe.secondary, 14)])
    elif objective == 'runecraft':
        if not s.quests.get('Rune Mysteries Quest'):
            return quest_plan(s, objective, 'runemysteries', 'Rune Mysteries Quest')
        return activity(objective, 'craft-air-runes', 'RuneCrafter', Record({'rune': 'Air runes', 'mode': 'Solo'}), [tool('Air talisman'), banked('Rune essence', 27)])
    else:
        return None


def with_food(s, plan):
    food = food_for(s)
    _merged10 = {}
    for _k, _v in (plan._fields if isinstance(plan, Record) else plan).items():
        _merged10[_k] = _v
    for _k, _v in {'food': food, 'needs': list(plan.needs) + [Record({'item': food, 'count': 24, 'carry': 12})]}.items():
        _merged10[_k] = _v
    return Record(_merged10)


def method_for(s, objective, memory, random):
    selected = select_method(s, objective, memory, random)
    plan = (locate_method(s, selected, memory, random) if selected else None)
    next_ = next_milestone(s, objective)
    if plan is None:
        return None
    _merged11 = {}
    for _k, _v in (plan._fields if isinstance(plan, Record) else plan).items():
        _merged11[_k] = _v
    for _k, _v in {'prerequisite_levels': {objective: next_}}.items():
        _merged11[_k] = _v
    return (Record(_merged11) if plan and next_ and not plan.quest and not plan.prerequisite_levels else plan)


def fish_plan(s, objective, raw=None):
    fly_ready = can_catch(s, FISH[1])
    recipe = (([f for f in FISH if f'raw {f.food.lower()}' == raw.lower()] or [None])[0] if raw else (FISH[3] if members_ready(s) and can_catch(s, FISH[3]) else FISH[(1 if s.levels.get('fishing') >= 20 and (s.levels.get('fishing') >= 40 or fly_ready) else 0)]))
    fly = recipe.tool == 'Fly fishing rod'
    bait = (consumable_batch(s, [Record({'item': 'Feather', 'count': 1})], 200) if fly else [])
    _v12 = (bait[0].carry if bait else None)
    _merged13 = {}
    for _k, _v in (gather_settings._fields if isinstance(gather_settings, Record) else gather_settings).items():
        _merged13[_k] = _v
    for _k, _v in {
        'fish_method': recipe.method,
        'location': recipe.location,
        'cook_mode': 'Off',
        'bait_qty': (_v12 if _v12 is not None else 200),
    }.items():
        _merged13[_k] = _v
    return activity(objective, f'fish-{recipe.food.lower()}', 'Fisher', Record(_merged13), [tool(recipe.tool)] + list(bait))


def cook_plan(s, objective, requested=None):
    available = [f for f in list(reversed(FISH)) if s.levels.get('cooking') >= f.cooking and (f.food != 'Lobster' or members_ready(s) or stock_of(s, 'Raw lobster') >= 28)]
    candidates = [fish for fish in available if stock_of(s, f'Raw {fish.food.lower()}') >= 28]
    if not candidates:
        candidates = [fish for fish in available if can_catch(s, fish)]
    food = requested if requested is not None else (candidates[0].food if candidates else FISH[0].food)
    return activity(objective, f'cook-{food.lower()}', 'CookBot', Record({'fish': f'Raw {food.lower()}', 'location': 'Draynor', 'surface': 'Range'}), [banked(f'Raw {food.lower()}')])


def logs_plan(s, objective, requested=None):
    wood = (([w for w in WOODS if w.item.lower() == requested.lower()] or [None])[0] if requested else ([w for w in list(reversed(WOODS)) if s.levels.get('woodcutting') >= w.level] or [None])[0])
    _merged14 = {}
    for _k, _v in (gather_settings._fields if isinstance(gather_settings, Record) else gather_settings).items():
        _merged14[_k] = _v
    for _k, _v in {'tree_name': wood.tree, 'location': wood.location, 'burn_mode': 'Off'}.items():
        _merged14[_k] = _v
    return activity(objective, f"gather-{wood.item.lower().replace(' ', '-')}", 'Woodcutter', Record(_merged14), [gathering_tool(s, 'axe')])


def ore_plan(s, objective, ore):
    _merged15 = {}
    for _k, _v in (gather_settings._fields if isinstance(gather_settings, Record) else gather_settings).items():
        _merged15[_k] = _v
    for _k, _v in {'rocks': [ore], 'location': 'Southeast Varrock Mine'}.items():
        _merged15[_k] = _v
    return activity(objective, f'mine-{ore.lower()}', 'Miner', Record(_merged15), [gathering_tool(s, 'pickaxe')])


def smelt_plan(objective, metal='Bronze'):
    return activity(objective, f'smelt-{metal.lower()}', 'SmelterBot', Record({'bar': metal}), ([banked('Iron ore')] if metal == 'Iron' else [banked('Copper ore', 14), banked('Tin ore', 14)]))


def producer(s, objective, need, memory, random):
    plan = None
    _case16 = need.item.lower()
    if _case16 == 'chaos rune':
        from bots.account_leveler.runes import can_steal_chaos
        if not can_steal_chaos(s):
            return None
        food = food_for(s)
        plan = activity(objective, 'pickpocket-paladins', 'Thiever', Record({'target': 'Paladin', 'action': 'Pickpocket', 'banking': 'Auto', 'food': food, 'food_withdraw': 12, 'suicide': False, 'loadout': ''}), [Record({'item': food, 'count': 24, 'carry': 12})])
        plan['food'] = food
    elif _case16 in ['shrimps', 'trout', 'salmon', 'lobster']:
        plan = (cook_plan(s, objective, need.item) if s.levels.get('cooking') >= ([f for f in FISH if f.food.lower() == need.item.lower()] or [None])[0].cooking else None)
    elif _case16 in ['raw shrimps', 'raw trout', 'raw salmon', 'raw lobster']:
        fish = ([f for f in FISH if f'raw {f.food.lower()}' == need.item.lower()] or [None])[0]
        plan = (fish_plan(s, objective, need.item) if s.levels.get('fishing') >= fish.level else None)
    elif _case16 in ['logs', 'oak logs', 'willow logs']:
        plan = (logs_plan(s, objective, need.item) if s.levels.get('woodcutting') >= ([w for w in WOODS if w.item.lower() == need.item.lower()] or [None])[0].level else None)
    elif _case16 == 'copper ore':
        plan = ore_plan(s, objective, 'Copper')
    elif _case16 == 'tin ore':
        plan = ore_plan(s, objective, 'Tin')
    elif _case16 == 'iron ore':
        plan = (ore_plan(s, objective, 'Iron') if s.levels.get('mining') >= 30 else None)
    elif _case16 == 'iron bar':
        plan = (smelt_plan(objective, 'Iron') if s.levels.get('smithing') >= 15 else None)
    elif _case16 == 'bronze bar':
        plan = smelt_plan(objective)
    elif _case16 == 'leather':
        plan = activity(objective, 'tan-cow-hides', 'TannerBot', Record({'hide_type': 'Soft leather', 'buy_thread': False, 'coins_per_trip': 100}), [banked('Cow hide', 26), Record({'item': 'Coins', 'count': 100, 'carry': 100})])
    elif _case16 == 'cow hide':
        levels = Record({'attack': 5, 'strength': 5, 'defence': 5, 'hitpoints': 12})
        plan = (prerequisite_combat(s, objective, memory, random, levels) if any([s.levels.get(skill) < level for skill, level in list(levels.items())]) else combat_plan(s, objective, memory, random, 'Cow hide'))
    elif _case16 == 'guam leaf':
        plan = activity(objective, 'clean-guam', 'HerbCleaner', Record({'herbs': ['Guam leaf']}), [banked('#199', 14)])
    elif _case16 in ['#199', 'air talisman']:
        plan = combat_plan(s, objective, memory, random, need.item)
    elif _case16 == 'rune essence':
        plan = activity(objective, 'mine-essence', 'EssMiner', Record({}), [gathering_tool(s, 'pickaxe')])
    else:
        return None
    plan = (locate_method(s, plan, memory, random) if plan else None)
    if plan is None:
        return None
    _merged18 = {}
    for _k, _v in (plan._fields if isinstance(plan, Record) else plan).items():
        _merged18[_k] = _v
    for _k, _v in {'output': Record({'item': need.item, 'count': (max(1000, need.count) if plan.script == 'EssMiner' else need.count)})}.items():
        _merged18[_k] = _v
    return ((plan if plan.prerequisite_levels else Record(_merged18)) if plan else None)
