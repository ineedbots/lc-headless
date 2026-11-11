"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/combatProgression.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

__all__ = ['combat_level', 'training_tier', 'TARGET_TIERS']

def combat_level(levels):
    _v1 = levels.get('defence')
    _v2 = levels.get('hitpoints')
    _v3 = levels.get('prayer')
    _v4 = levels.get('prayer')
    base = ((_v1 if _v1 is not None else 1)) + ((_v2 if _v2 is not None else 10)) + (((_v4 if _v4 is not None else 1)) // 2)
    _v5 = levels.get('attack')
    _v6 = levels.get('strength')
    _v7 = levels.get('ranged')
    _v8 = levels.get('ranged')
    _v9 = levels.get('magic')
    _v10 = levels.get('magic')
    offence = max(((_v5 if _v5 is not None else 1)) + ((_v6 if _v6 is not None else 1)), (((_v8 if _v8 is not None else 1)) * 3 // 2), (((_v10 if _v10 is not None else 1)) * 3 // 2))
    return ((10 * base + 13 * offence) // 40)


def training_tier(levels):
    level = combat_level(levels)
    if level >= 80:
        return 5
    if level >= 60:
        return 4
    return (3 if level >= 35 else (2 if level >= 25 else (1 if level >= 15 else 0)))


TARGET_TIERS = Record({
    'Monk': 1,
    'Barbarian': 1,
    'Barbarian woman': 1,
    'Dwarf': 1,
    'Al-Kharid warrior': 1,
    'Guard': 2,
    'Chaos druid': 2,
    'Unicorn': 2,
    'Scorpion': 2,
    'Skeleton': 2,
    'Khazard trooper': 2,
    'Soldier': 2,
    'Druid': 3,
})
