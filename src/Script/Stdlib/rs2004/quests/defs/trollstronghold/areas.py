"""Ported from rs2b0t's src/bot/api/ai/quests/defs/trollstronghold/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.food import FOOD_FLOAT
from rs2004.quests.exec.primitives import LineRule, NpcStop

__all__ = ['ITEM', 'BOOT_COST', 'COIN_FLOAT', 'FOOD_TARGET', 'FOOD_FLOOR', 'PRAYER_POTIONS', 'PRAYER_POTION_TARGET', 'PRAYER_SIP_AT', 'COMBAT_FOODS', 'FALADOR_WEST_BANK', 'TILE', 'troll_zone', 'committed', 'DENULTH_START', 'DUNSTAN_FINISH', 'TENZING_BOOTS', 'TENZING_DONE_RULES']

ITEM = Record({
    'CLIMBING_BOOTS': 'Climbing boots',
    'PRISON_KEY': 'Prison key',
    'CELL_KEY_1': 'Cell key 1',
    'CELL_KEY_2': 'Cell key 2',
    'COINS': 'Coins',
})
BOOT_COST = 12
COIN_FLOAT = 500
FOOD_TARGET = FOOD_FLOAT
FOOD_FLOOR = 4
PRAYER_POTIONS = ['Prayer potion(4)', 'Prayer potion(3)', 'Prayer potion(2)', 'Prayer potion(1)']
PRAYER_POTION_TARGET = 2
PRAYER_SIP_AT = 0.5
COMBAT_FOODS = ['Shark', 'Swordfish', 'Lobster', 'Tuna', 'Salmon', 'Trout', 'Cooked meat', 'Bread']
FALADOR_WEST_BANK = Tile(2946, 3369, 0)
TILE = Record({
    'DENULTH': Tile(2896, 3528, 0),
    'DUNSTAN': Tile(2919, 3574, 0),
    'TENZING': Tile(2820, 3556, 0),
    'DAD': Tile(2911, 3612, 0),
    'ARENA_GATE': Tile(2896, 3618, 0),
    'GENERAL': Tile(2831, 10086, 2),
    'STRONGHOLD_TOP': Tile(2837, 10090, 2),
    'PRISON_DOOR': Tile(2847, 10107, 1),
    'PRISON_LANDING': Tile(2852, 10105, 0),
    'GODRIC_CELL': Tile(2833, 10078, 0),
    'EADGAR_CELL': Tile(2833, 10082, 0),
})


# Why: everything past the stile is committed ground, and re-provisioning from up there means climbing back down the secret way.
def troll_zone(tile):
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    level = tile.level
    # Stronghold interior: mapsquare 44,157 across all 3 levels.
    if x >= 2816 and x <= 2879 and z >= 10048 and z <= 10111:
        return 'stronghold'
    # The troll pass cave between the arena and the northern mountain.
    if x >= 2880 and x <= 2943 and z >= 9984 and z <= 10047:
        return 'trollPass'
    if level != 0:
        return 'unknown'
    if x >= 2879 and x <= 2925 and z >= 3596 and z <= 3648:
        return 'arena'
    if x >= 2828 and x <= 2920 and z >= 3649 and z <= 3711:
        return 'mountain'
    # Everything above the stile on the secret way, plus the north-west pocket the prison's back door opens onto.
    if x >= 2812 and x <= 2882 and z >= 3563 and z <= 3648:
        return 'secretWay'
    return 'mainland'


def committed(zone):
    """True once you're past the stile: no more cheap bank trips."""
    return zone != 'mainland' and zone != 'unknown'


DENULTH_START = NpcStop('Denulth', TILE.DENULTH, 8, ['How goes your fight with the trolls?', 'Is there anything I can do to help?', "I'll get Godric back!"])
DUNSTAN_FINISH = NpcStop('Dunstan', TILE.DUNSTAN, 8, ['Nothing, thanks.'])
# Why: Tenzing's post-quest shop is a dialogue that loops: after every purchase he asks "Was there anything else?" and re-offers the same 5 options.
# Why: a plain preference list matches "Can I buy some Climbing boots?" again and buys until the pack is full, so the exit keys off his line.
TENZING_BOOTS = NpcStop('Tenzing', TILE.TENZING, 6, ['Can I buy some Climbing boots?', 'OK, sounds good.', 'Nothing, thanks!'])
TENZING_DONE_RULES = [LineRule('was there anything else', 'Nothing, thanks!')]
