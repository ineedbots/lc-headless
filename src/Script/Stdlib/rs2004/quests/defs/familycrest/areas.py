"""Ported from rs2b0t's src/bot/api/ai/quests/defs/familycrest/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['FC_QUEST', 'FC_STAGE', 'FC_ID', 'FC_ITEM', 'DUEL_RING_IDS', 'ANTIPOISON_IDS', 'PICKAXES', 'FC_NPC', 'FC_SHOP', 'FC_LOC', 'FC_BANK', 'in_perfect_gold_zone', 'in_chronozon_lair']

FC_QUEST = 'Family Crest'
FC_STAGE = Record({
    'NOT_STARTED': 0,
    'SPOKEN_DIMINTHEIS': 1,
    'SPOKEN_CALEB': 2,
    'CALEB_PIECE': 3,
    'CALEB_WHERE': 4,
    'SPOKEN_GEM_TRADER': 5,
    'SPOKEN_AVAN': 6,
    'SPOKEN_BOOT': 7,
    'AVAN_PIECE': 8,
    'SPOKEN_JOHNATHON': 9,
    'CURED_JOHNATHON': 10,
    'COMPLETE': 11,
})
# Why: all 3 fragments render "Crest part", so checks go by id; the server names are crossed (Caleb hands out `avan_crest`, Avan `caleb_crest`), so these are named for the giver.
FC_ID = Record({
    'CREST_FROM_CALEB': 779,
    'CREST_FROM_AVAN': 780,
    'CREST_FROM_CHRONOZON': 781,
    'FAMILY_CREST': 782,
    'PERFECT_GOLD_ORE': 446,
    'PERFECT_GOLD_BAR': 2365,
    'PERFECT_RUBY_RING': 773,
    'PERFECT_RUBY_NECKLACE': 774,
    'RUBY': 1603,
    'RING_MOULD': 1592,
    'NECKLACE_MOULD': 1597,
    'SWORDFISH': 373,
    'BASS': 365,
    'TUNA': 361,
    'SALMON': 329,
    'SHRIMP': 315,
    'ANTIPOISON_4': 2446,
    'ANTIPOISON_3': 175,
    'ANTIPOISON_2': 177,
    'ANTIPOISON_1': 179,
    'LAW_RUNE': 563,
    'AIR_RUNE': 556,
    'WATER_RUNE': 555,
    'EARTH_RUNE': 557,
    'FIRE_RUNE': 554,
    'DEATH_RUNE': 560,
    'COINS': 995,
})
FC_ITEM = Record({
    'CREST_PART': 'Crest part',
    'FAMILY_CREST': 'Family crest',
    'PERFECT_GOLD_ORE': "'perfect' gold ore",
    'PERFECT_GOLD_BAR': "'perfect' gold bar",
    'PERFECT_RUBY_RING': "'perfect' ring",
    'PERFECT_RUBY_NECKLACE': "'perfect' necklace",
    'RUBY': 'Ruby',
    'RING_MOULD': 'Ring mould',
    'NECKLACE_MOULD': 'Necklace mould',
    'SWORDFISH': 'Swordfish',
    'BASS': 'Bass',
    'TUNA': 'Tuna',
    'SALMON': 'Salmon',
    'SHRIMP': 'Shrimps',
    'LAW_RUNE': 'Law rune',
    'AIR_RUNE': 'Air rune',
    'WATER_RUNE': 'Water rune',
    'EARTH_RUNE': 'Earth rune',
    'FIRE_RUNE': 'Fire rune',
    'DEATH_RUNE': 'Death rune',
    'COINS': 'Coins',
})
# Why: the navigator rubs jewellery from the inventory only and never withdraws a ring, so the quest carries one for the Duel Arena hop to be planned.
# Ring of dueling, all 8 charge stages.
DUEL_RING_IDS = [2552, 2554, 2556, 2558, 2560, 2562, 2564, 2566]
ANTIPOISON_IDS = [FC_ID.ANTIPOISON_4, FC_ID.ANTIPOISON_3, FC_ID.ANTIPOISON_2, FC_ID.ANTIPOISON_1]
PICKAXES = [
    Record({'id': 1275, 'name': 'Rune pickaxe'}),
    Record({'id': 1271, 'name': 'Adamant pickaxe'}),
    Record({'id': 1273, 'name': 'Mithril pickaxe'}),
    Record({'id': 1269, 'name': 'Steel pickaxe'}),
    Record({'id': 1267, 'name': 'Iron pickaxe'}),
    Record({'id': 1265, 'name': 'Bronze pickaxe'}),
]
FC_NPC = Record({
    'DIMINTHEIS': Tile(3279, 3404, 0),
    'CALEB': Tile(2819, 3451, 0),
    'GEM_TRADER': Tile(3288, 3212, 0),
    'AVAN': Tile(3295, 3285, 0),
    'AVAN_NPC_ID': 663,
    'BOOT': Tile(2965, 9811, 0),
    'JOHNATHON': Tile(3279, 3503, 1),
    'CHRONOZON': Tile(3087, 9937, 0),
    'CHRONOZON_NPC_ID': 667,
})
FC_SHOP = Record({
    'AUBURY': Record({'npc': 'Aubury', 'anchor': Tile(3253, 3401, 0)}),
    'DOMMIK': Record({'npc': 'Dommik', 'anchor': Tile(3322, 3194, 0)}),
    'GEM_MERCHANT': Record({'npc': 'Gem merchant', 'anchor': Tile(2669, 3303, 0)}),
    'JIMINUA': Record({'npc': 'Jiminua', 'anchor': Tile(2767, 3122, 0)}),
    'NURMOF': Record({'npc': 'Nurmof', 'anchor': Tile(2997, 9844, 0)}),
})
FC_LOC = Record({
    'MINE_LADDER': Tile(2696, 3282, 0),
    'MINE_LANDING': Tile(2696, 9683, 0),
    'FURNACE': Tile(2601, 3310, 0),
    'GOLD_ROCK': Tile(2740, 9684, 0),
    'GOLD_STAND': Tile(2739, 9684, 0),
})
FC_BANK = Record({
    'VARROCK_EAST': Tile(3253, 3420, 0),
    'CATHERBY': Tile(2809, 3441, 0),
    'AL_KHARID': Tile(3269, 3167, 0),
    'ARDOUGNE_EAST': Tile(2655, 3283, 0),
    'FALADOR_EAST': Tile(3013, 3355, 0),
    'EDGEVILLE': Tile(3094, 3493, 0),
})
# Why: `inzone` tests the player's tile, so a boundary rock mined from outside the box yields ordinary gold ore.
# The perfect-gold zone from quest_crest.constant.
PERFECT_GOLD_ZONE = Record({'min_x': 2736, 'max_x': 2740, 'min_z': 9684, 'max_z': 9693})


def in_perfect_gold_zone(tile):
    if not tile or tile.level != 0:
        return False
    return tile.x >= PERFECT_GOLD_ZONE.min_x and tile.x <= PERFECT_GOLD_ZONE.max_x and tile.z >= PERFECT_GOLD_ZONE.min_z and tile.z <= PERFECT_GOLD_ZONE.max_z


def in_chronozon_lair(tile):
    """Chronozon's half of the Edgeville dungeon, past the poison-spider gates."""
    if not tile or tile.level != 0:
        return False
    return tile.x >= 3072 and tile.x <= 3135 and tile.z >= 9920 and tile.z <= 9983
