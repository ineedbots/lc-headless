"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/priority.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

__all__ = ['training_priority', 'can_resume_objective']

MELEE = ['attack', 'strength', 'defence']
COMBAT = list(MELEE) + ['hitpoints', 'ranged', 'magic', 'prayer']


def training_priority(levels, target):
    melee = [skill for skill in MELEE if levels.get(skill) < target]
    if len(melee):
        return Record({'label': f'Build melee stats to {target}', 'skills': melee, 'balance': True})
    combat = [skill for skill in COMBAT if levels.get(skill) < target]
    if len(combat):
        return Record({'label': f'Finish combat stats to {target}', 'skills': combat, 'balance': False})
    return Record({
        'label': f'Train remaining skills to {target}',
        'skills': [skill for skill in list(levels.keys()) if levels.get(skill) < target],
        'balance': False,
    })


def can_resume_objective(levels, target, objective):
    priority = training_priority(levels, target)
    return (objective in priority.skills) and (not priority.balance or levels.get(objective) == min([levels.get(skill) for skill in priority.skills]))
