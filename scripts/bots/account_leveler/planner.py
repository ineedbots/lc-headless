import random as _random
"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/planner.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

__all__ = ['enabled_skills', 'empty_memory', 'resolve_activity', 'plan_next']

from rs2004.events import SKILL_NAMES
from bots.account_leveler.session import uses_activity_cooldown
from bots.account_leveler.methods import method_for, producer
from bots.account_leveler.offers import purchase_budget, supply_offer
from bots.account_leveler.shopping import SHOPPING_RESERVE
from bots.account_leveler.priority import can_resume_objective, training_priority
from bots.account_leveler.types import requirement_key, stock_of
from bots.account_leveler.combat import scimitar_for
enabled_skills = list(SKILL_NAMES.values())


def empty_memory():
    return (Record({'objective': None, 'recent': [], 'cooldowns': Record({}), 'attempted': Record({}), 'deaths': 0}))


def resolve_activity(s, plan, memory, random, chain=None):
    if chain is None:
        chain = []
    if (plan.id in chain):
        return Record({'kind': 'blocked', 'reason': f"Supply dependency cycle: {' -> '.join(list(chain) + [plan.id])}"})
    if uses_activity_cooldown(plan) and ((memory.cooldowns.get(plan.id) if memory.cooldowns.get(plan.id) is not None else 0)) > s.now:
        return Record({'kind': 'blocked', 'reason': f'{plan.label} is cooling down after a failed attempt'})
    budget = 0
    reserve = max([SHOPPING_RESERVE] + [need.count for need in plan.needs if need.item == 'Coins'])
    for need in plan.needs:
        missing = need.count - stock_of(s, requirement_key(need))
        if missing <= 0:
            continue
        alternative = producer(s, plan.objective, need, memory, random) if need.item == 'Chaos rune' else None
        if not alternative and ((need.item.lower() in s.unavailable_items) if s.unavailable_items is not None else None):
            return Record({'kind': 'blocked', 'reason': f'{need.item} is unavailable from its supplier this run'})
        offer = supply_offer(need.item)
        if offer and not alternative:
            budget += purchase_budget(offer, missing)
            if budget + reserve > stock_of(s, 'Coins'):
                return Record({
                    'kind': 'blocked',
                    'reason': f'Not enough banked Coins to buy {need.item} (budget {budget + reserve}, including travel reserve)',
                })
            continue
        dependency = alternative or producer(s, plan.objective, need, memory, random)
        if not dependency:
            return Record({'kind': 'blocked', 'reason': f'Cannot source {need.count} {need.item} for {plan.label}'})
        resolved = resolve_activity(s, dependency, memory, random, list(chain) + [plan.id])
        if resolved.kind != 'activity':
            return resolved
        _merged1 = {}
        for _k, _v in (resolved._fields if isinstance(resolved, Record) else resolved).items():
            _merged1[_k] = _v
        for _k, _v in {'queue': list(resolved.queue) + [plan]}.items():
            _merged1[_k] = _v
        return (Record(_merged1) if resolved.kind == 'activity' else resolved)
    return Record({'kind': 'activity', 'plan': plan, 'queue': [plan]})


def plan_next(s, memory, random=None):
    if random is None:
        random = _random.random
    if not s.bank_ready:
        return Record({'kind': 'refresh'})
    if any([not (isinstance(s.levels.get(skill), int) or isinstance(s.levels.get(skill), float)) or s.levels.get(skill) <= 0 for skill in enabled_skills]):
        return Record({'kind': 'blocked', 'reason': 'Skill levels have not loaded'})
    from rs2004.quests.data import quest_record
    from bots.account_leveler.dragon_weapons import zanaris_exit_needs
    from bots.account_leveler.methods import quest_plan
    lost_city = quest_record('zanaris')
    if not s.quests.get(lost_city.name) and zanaris_exit_needs(s) and all([s.levels.get(req.skill) >= req.level for req in lost_city.requirements.skills or []]) and memory.cooldowns.get('quest-zanaris', 0) <= s.now:
        choices = training_priority(s.levels, s.target).skills
        objective = choices[0] if choices else 'attack'
        decision = resolve_activity(s, quest_plan(s, objective, lost_city.id, lost_city.name, True), memory, random)
        if decision.kind == 'activity':
            return decision
    unfinished = [skill for skill in enabled_skills if s.levels.get(skill) < s.target]
    if not len(unfinished):
        return Record({'kind': 'complete'})
    priority = training_priority(s.levels, s.target)

    ordered = [entry.skill for entry in sorted([(Record({
        'skill': skill,
        'level': (s.levels.get(skill) if priority.balance else 0),
        'score': (memory.attempted.get(skill) if memory.attempted.get(skill) is not None else 0),
        'tie': random(),
    })) for skill in [skill for skill in unfinished if (skill in priority.skills)]], key=lambda entry: (entry.level, entry.score, entry.tie))]
    if memory.objective and can_resume_objective(s.levels, s.target, memory.objective):
        ordered.remove(memory.objective)
        ordered.insert(0, memory.objective)
    reasons = []
    for objective in ordered:
        method = method_for(s, objective, memory, random)
        if not method:
            reasons.append(f'No eligible method for {objective}')
            continue
        decision = resolve_activity(s, method, memory, random, [])
        if decision.kind == 'activity':
            return decision
        if decision.kind == 'blocked':
            reasons.append(decision.reason)
    return Record({'kind': 'blocked', 'reason': f"{priority.label}: {'; '.join(list(set(reasons)))}"})
