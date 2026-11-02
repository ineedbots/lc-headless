"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/config.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

__all__ = ['LEGENDS_REWARD_OPTIONS', 'legends_config']

# Why: Radimus offers 12 skills across four pages and grants four training choices.
# Why: Prayer is the default because 3 Nezikchened fights and 3 aggressive guardians are survived on Protect from Melee, and the reward is the largest prayer lump in the 2004 game.
LEGENDS_REWARD_OPTIONS = [
    'Attack',
    'Defence',
    'Strength',
    'Hitpoints',
    'Prayer',
    'Magic',
    'Woodcutting',
    'Crafting',
    'Smithing',
    'Herblore',
    'Agility',
    'Thieving',
]
legends_config = Record({'reward': 'Prayer'})
