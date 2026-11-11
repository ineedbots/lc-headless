"""Quest preparation planner from rs2b0t's AIOQuester/preparation.ts (MIT, see thirdparty/rs2b0t)."""

import random
from bots.account_leveler.record import Record
from bots.account_leveler.catalog import FISH, WOODS
from bots.account_leveler.locations import members_ready
from bots.account_leveler.methods import method_for, producer
from bots.account_leveler.offers import purchase_budget, supply_offer
from bots.account_leveler.types import requirement_key, stock_of
from bots.aioquester.supply_producers import quest_supply_producer


def copy_record(value, **fields):
    data = {key: getattr(value, key) for key in value.keys()}
    data.update(fields)
    return Record(data)


class PreparationPlanner:
    def __init__(self, snapshot, memory, choose):
        self.snapshot = copy_record(snapshot, allow_quests=False)
        self.memory = memory
        self.choose = choose

    def blocked(self, reason):
        return Record({'kind': 'blocked', 'reason': reason})

    def train(self, skill, level, chain):
        s = self.snapshot
        if not isinstance(s.levels.get(skill), (int, float)) or s.levels.get(skill) < 1:
            return self.blocked(f'Cannot train {skill}: skill is unavailable')
        locked = 'Druidic Ritual' if skill == 'herblore' else ('Rune Mysteries Quest' if skill == 'runecraft' else None)
        if locked and not s.quests.get(locked):
            return self.blocked(f'Complete {locked} before training {skill}')
        plan = method_for(copy_record(s, target=level), skill, self.memory, self.choose)
        if plan is None or plan.quest or plan.script == 'AIOQuester':
            return self.blocked(f'No supported training method for {skill} {level}')
        return self.resolve(copy_record(plan, prerequisite_levels=plan.prerequisite_levels or {skill: level}), chain)

    def resolve(self, plan, chain):
        s = self.snapshot
        if plan.id in chain or len(chain) >= 20:
            return self.blocked('Preparation dependency cycle: ' + ' -> '.join(chain + [plan.id]))
        budget = 0
        for need in plan.needs:
            missing = need.count - stock_of(s, requirement_key(need))
            if missing <= 0:
                continue
            if need.item.lower() in (s.unavailable_items or []):
                return self.blocked(f'Supplier unavailable for {need.item}')
            offer = supply_offer(need.item)
            if offer:
                budget += purchase_budget(offer, missing)
                funds = [n.count for n in plan.needs if n.item == 'Coins']
                if budget + max(200, funds[0] if funds else 0) > stock_of(s, 'Coins'):
                    return self.blocked(f'Not enough Coins to buy {need.item} and keep travel funds')
                continue
            fish = [f for f in FISH if need.item.lower() in [f.food.lower(), 'raw ' + f.food.lower()]]
            wood = [w for w in WOODS if w.item.lower() == need.item.lower()]
            raw = need.item.lower().startswith('raw ')
            levels = {}
            if fish:
                if raw or stock_of(s, 'Raw ' + fish[0].food) == 0:
                    levels['fishing'] = fish[0].level
                if not raw:
                    levels['cooking'] = fish[0].cooking
            elif wood:
                levels['woodcutting'] = wood[0].level
            elif need.item.lower() in ['iron ore', 'iron bar', 'cake', 'agility potion(3)']:
                targets = {'iron ore': ('mining', 30), 'iron bar': ('smithing', 15), 'cake': ('thieving', 5), 'agility potion(3)': ('herblore', 34)}
                skill, level = targets[need.item.lower()]
                levels[skill] = level
            deficits = [(skill, level) for skill, level in levels.items() if s.levels.get(skill, 0) < level]
            next_chain = chain + [plan.id]
            if deficits:
                dependency = self.train(deficits[0][0], deficits[0][1], next_chain)
            elif raw and fish and fish[0].food in ['Lobster', 'Shark'] and not members_ready(s):
                combat = [(skill, level) for skill, level in {'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25}.items() if s.levels.get(skill, 0) < level]
                if combat:
                    dependency = self.train(combat[0][0], combat[0][1], next_chain)
                elif stock_of(s, 'Coins') < 200:
                    return self.blocked('Need 200 Coins for the coastal fishing route')
                else:
                    dependency = self.resolve(Record({'id': 'fishing-travel-food', 'label': 'Food for coastal fishing travel', 'objective': plan.objective, 'script': '', 'settings': {}, 'needs': [{'item': 'Shrimps', 'count': 12, 'carry': 0}]}), next_chain)
            else:
                child = quest_supply_producer(s, need, self.memory, self.choose) or producer(s, plan.objective, need, self.memory, self.choose)
                if child is None:
                    return self.blocked(f'Cannot source {need.count} {need.item} for {plan.label}')
                if child.script == 'CookBot' and fish and not raw:
                    raw_item = 'Raw ' + fish[0].food.lower()
                    for entry in child.needs:
                        if entry.item.lower() == raw_item.lower():
                            entry.count = min(entry.count, missing, stock_of(s, raw_item) or float('inf'))
                dependency = self.resolve(child, next_chain)
            return copy_record(dependency, queue=dependency.queue + [plan]) if dependency.kind == 'activity' else dependency
        return Record({'kind': 'activity', 'plan': plan, 'queue': [plan]})


def plan_preparation(snapshot, request, memory, choose=None):
    if not snapshot.bank_ready:
        return Record({'kind': 'refresh'})
    planner = PreparationPlanner(snapshot, memory, choose or random.random)
    for target in request.skills or []:
        if not isinstance(target.level, int) or target.level < 1 or target.level > 99:
            return planner.blocked(f'Invalid target {target.skill} {target.level}')
        if snapshot.levels.get(target.skill, 0) < target.level:
            return planner.train(target.skill, target.level, [])
    needs = []
    for need in (request.items or []) + ([request.food] if request.food else []):
        if not isinstance(need.count, int) or need.count < 1:
            return planner.blocked(f'Invalid quantity for {need.item}')
        existing = [n for n in needs if requirement_key(n).lower() == requirement_key(need).lower()]
        if existing:
            existing[0].count = max(existing[0].count, need.count)
        else:
            needs.append(copy_record(need, carry=0))
    if all([stock_of(snapshot, requirement_key(need)) >= need.count for need in needs]):
        return Record({'kind': 'complete'})
    return planner.resolve(Record({'id': 'quest-supplies', 'label': 'Quest supplies', 'objective': 'supplies', 'script': '', 'settings': {}, 'needs': needs}), [])
