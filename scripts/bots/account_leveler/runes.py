"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/runes.ts (MIT, see thirdparty/rs2b0t)."""


__all__ = ['can_steal_chaos']

def can_steal_chaos(s):
    return s.levels.get('thieving') >= 70 and s.levels.get('hitpoints') >= 30 and all([s.levels.get(skill) >= 20 for skill in ['attack', 'strength', 'defence']]) and ((s.stock.get('coins') if s.stock.get('coins') is not None else 0)) >= 200
