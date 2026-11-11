"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tbwt/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['TBWT_QUEST', 'TB_VARP', 'TB_MAIN', 'TB_TIADECHE', 'TB_TINSAY', 'TB_TAMAYU', 'TB_LUBUFU', 'KARAMBWANJI_WANTED', 'KARAMBWAN_BAIT', 'TB_ID', 'TB_NAME', 'TB_SPEARS', 'SPEAR_HUNT_KILLS', 'TB_SPEAR_IDS', 'TB_SPEAR_DROPS', 'AGILITY_DOSES', 'TB_POTIONS', 'TB_POTION_IDS', 'TB_BOWS', 'TB_ARROWS', 'TB_ARMOUR', 'TB_ARMOUR_SLOTS', 'ARROW_TARGET', 'FOOD_TARGET', 'COIN_TARGET', 'TB_TILE', 'TB_LOC', 'TB_NPC', 'TIMFRAKU_START', 'TIMFRAKU_REWARD', 'on_karamja', 'in_cutscene']

TBWT_QUEST = 'Tai Bwo Wannai Trio'
# Why: `tbwt_main` and `tbwt_tiadeche` are `transmit=yes`, so they're on the wire and exact, see docs/decisions/quest-state-not-varps.md, which names TBWT as the exception.
# Why: `tbwt_tinsay`, `tbwt_tamayu`, `tbwt_lubufu` and `tbwt_flags` are `scope=perm` only and read back 0, so they come off the journal page.
TB_VARP = Record({'MAIN': 320, 'TIADECHE': 321})
TB_MAIN = Record({'NOT_STARTED': 0, 'SPOKE': 1, 'ASKED_FOR_HELP': 2, 'STARTED': 3, 'ALL_BROTHERS': 4, 'GOLD': 5, 'COMPLETE': 6})
TB_TIADECHE = Record({
    'UNKNOWN': 0,
    'INTRO': 1,
    'RETURN_WHEN_CAUGHT': 2,
    'CAUGHT': 3,
    'REQUEST_MANUAL': 4,
    'RECEIVED_MANUAL': 5,
    'COMPLETE': 6,
    'CLAIMED': 7,
})
TB_TINSAY = Record({
    'UNKNOWN': 0,
    'INTRO': 1,
    'FETCH_RUM': 2,
    'GIVEN_RUM': 3,
    'FETCH_SANDWICH': 4,
    'GIVEN_SANDWICH': 5,
    'FETCH_BONES': 6,
    'COMPLETE': 7,
    'CLAIMED': 8,
})
TB_TAMAYU = Record({'UNKNOWN': 0, 'INTRO': 1, 'SLAY_SHAIKAHAN': 2, 'WATCHED_CUTSCENE': 3, 'COMPLETE': 4, 'CLAIMED': 5})
TB_LUBUFU = Record({
    'UNKNOWN': 0,
    'INTRO': 1,
    'INITIAL_OPS': 2,
    'ASKED_WHAT_DO': 3,
    'OFFERED_TO_HELP': 4,
    'FETCH_KARAMBWANJI': 5,
    'GIVEN_KARAMBWANJI': 25,
    'ASKED_QUESTIONS': 28,
    'OFFERED_APPRENTICE': 29,
    'BECAME_APPRENTICE': 30,
    'COMPLETE': 31,
})
KARAMBWANJI_WANTED = 20
KARAMBWAN_BAIT = 4
# Why: "Karambwan vessel", "Karamjan rum" and "Karambwan paste" each name 3 different objects, so every one of them is matched by id.
TB_ID = Record({
    'COINS': 995,
    'NET': 303,
    'KNIFE': 946,
    'PESTLE': 233,
    'TINDERBOX': 590,
    'SEAWEED': 401,
    'BANANA': 1963,
    'SLICED_BANANA': 3162,
    'RUM': 431,
    'RUM_SLICED': 3164,
    'RUM_WHOLE': 3165,
    'VESSEL': 3157,
    'VESSEL_LOADED': 3159,
    'RAW_KARAMBWANJI': 3150,
    'KARAMBWANJI_PASTE': 3155,
    'RAW_KARAMBWAN': 3142,
    'POORLY_COOKED_KARAMBWAN': 3146,
    'BURNT_KARAMBWAN': 3148,
    'KARAMBWAN_POISON_PASTE': 3153,
    'MONKEY_CORPSE': 3166,
    'MONKEY_SKIN': 3167,
    'SANDWICH': 3168,
    'JOGRE_BONES': 3125,
    'BURNT_JOGRE_BONES': 3127,
    'PASTY_JOGRE_BONES': 3128,
    'MARINATED_JOGRE_BONES': 3130,
    'CRAFTING_MANUAL': 3161,
})
TB_NAME = Record({
    'COINS': 'Coins',
    'NET': 'Small fishing net',
    'KNIFE': 'Knife',
    'PESTLE': 'Pestle and mortar',
    'TINDERBOX': 'Tinderbox',
    'SEAWEED': 'Seaweed',
    'BANANA': 'Banana',
    'RAW_KARAMBWANJI': 'Raw karambwanji',
    'RAW_SHRIMP': 'Raw shrimps',
    'BURNT_JOGRE_BONES': 'Burnt jogre bones',
    'JOGRE_BONES': 'Jogre bones',
    'MONKEY_CORPSE': 'Monkey corpse',
    'RUM': 'Karamjan rum',
    'BODY': 'Rune chainbody',
    'LEGS': 'Rune platelegs',
    'HELM': 'Rune full helm',
})
# Why: `tbwt_tamayu` re-reads all 3 spear bits from the last spear it was handed, so that spear has to be above bronze and Karambwan poisoned, see docs/decisions/quest-pitfalls-14.md.
# Why: cheapest first, `inv_del(inv, $spear, 1)` means Tamayu keeps whatever he is given.
TB_SPEARS = [
    Record({'name': 'Iron spear', 'id': 1239, 'kp_name': 'Iron spear(kp)', 'kp_id': 3171}),
    Record({'name': 'Steel spear', 'id': 1241, 'kp_name': 'Steel spear(kp)', 'kp_id': 3172}),
    Record({'name': 'Mithril spear', 'id': 1243, 'kp_name': 'Mithril spear(kp)', 'kp_id': 3173}),
    Record({'name': 'Adamant spear', 'id': 1245, 'kp_name': 'Adamant spear(kp)', 'kp_id': 3174}),
    Record({'name': 'Rune spear', 'id': 1247, 'kp_name': 'Rune spear(kp)', 'kp_id': 3175}),
]
SPEAR_HUNT_KILLS = 40
# Why: the (p) tiers are absent because `make_tbwt_poisoned_weapon` reads a `tbwt_weapon_poisoned` param only the unpoisoned spears carry, so paste never lands on one.
_flat1 = []
for s in TB_SPEARS:
    _flat1.extend([s.id, s.kp_id])


TB_SPEAR_IDS = _flat1
TB_SPEAR_DROPS = [s.id for s in TB_SPEARS]
AGILITY_DOSES = 4
TB_POTIONS = [
    Record({'name': 'Agility potion(4)', 'id': 3032, 'doses': 4}),
    Record({'name': 'Agility potion(3)', 'id': 3034, 'doses': 3}),
    Record({'name': 'Agility potion(2)', 'id': 3036, 'doses': 2}),
    Record({'name': 'Agility potion(1)', 'id': 3038, 'doses': 1}),
]
TB_POTION_IDS = [p.id for p in TB_POTIONS]
# Why: the bow isn't spent, so the best one the account can draw is the right one.
TB_BOWS = [
    Record({'name': 'Magic shortbow', 'ranged': 50}),
    Record({'name': 'Magic longbow', 'ranged': 50}),
    Record({'name': 'Yew shortbow', 'ranged': 40}),
    Record({'name': 'Yew longbow', 'ranged': 40}),
    Record({'name': 'Maple shortbow', 'ranged': 30}),
    Record({'name': 'Maple longbow', 'ranged': 30}),
    Record({'name': 'Willow shortbow', 'ranged': 20}),
    Record({'name': 'Willow longbow', 'ranged': 20}),
    Record({'name': 'Oak shortbow', 'ranged': 5}),
    Record({'name': 'Oak longbow', 'ranged': 5}),
    Record({'name': 'Shortbow', 'ranged': 1}),
    Record({'name': 'Longbow', 'ranged': 1}),
]
# Why: Any arrow works with any bow in this revision; prefer tested adamant arrows because 200 rune arrows exceed the reward value.
TB_ARROWS = ['Adamant arrow', 'Rune arrow', 'Mithril arrow', 'Steel arrow', 'Iron arrow', 'Bronze arrow']
TB_ARMOUR = [TB_NAME.BODY, TB_NAME.LEGS, TB_NAME.HELM]
TB_ARMOUR_SLOTS = ['torso', 'legs', 'hat']
ARROW_TARGET = 200
FOOD_TARGET = 6
COIN_TARGET = 500
TB_TILE = Record({
    'ARDOUGNE_BANK': Tile(2616, 3332, 0),
    'TIMFRAKU': Tile(2780, 3087, 1),
    'TAMAYU': Tile(2844, 3042, 0),
    'TINSAY': Tile(2764, 2976, 0),
    'TIADECHE': Tile(2912, 3118, 0),
    'LUBUFU': Tile(2770, 3169, 0),
    'KARAMBWANJI_SHOAL': Tile(2801, 3010, 0),
    'KARAMBWAN_SHOAL': Tile(2768, 3165, 0),
    'JIMINUA': Tile(2767, 3122, 0),
    'ZAMBO': Tile(2925, 3143, 0),
    'BANANA_PLANTATION': Tile(2916, 3161, 0),
    'FIRE': Tile(2789, 3049, 0),
    'MONKEYS': Tile(2833, 3031, 0),
    'JOGRES': Tile(2916, 3053, 0),
})
TB_LOC = Record({'FIRE': 'Fire', 'BANANA_TREE': 'Banana Tree'})
TB_NPC = Record({
    'TIMFRAKU': 'Timfraku',
    'TAMAYU': 'Tamayu',
    'TINSAY': 'Tinsay',
    'TIADECHE': 'Tiadeche',
    'LUBUFU': 'Lubufu',
    'MONKEY': 'Monkey',
    'JOGRE': 'Jogre',
    'ZAMBO': 'Zambo',
    'JIMINUA': 'Jiminua',
    'FISHING_SPOT': 'Fishing spot',
})
# Why: every option list is driven by preference, so re-ordered dialogue does not break a leg.
TIMFRAKU_START = Record({
    'npc': TB_NPC.TIMFRAKU,
    'anchor': TB_TILE.TIMFRAKU,
    'leash': 5,
    'prefer': ['I am a roving adventurer.', 'Trufitus sent me.', 'Your gratitude is all I deserve.', 'Yes'],
})
TIMFRAKU_REWARD = Record({
    'npc': TB_NPC.TIMFRAKU,
    'anchor': TB_TILE.TIMFRAKU,
    'leash': 5,
    'prefer': ['Oh it was nothing really.', 'Ok, thanks.'],
})


# Why: the bank is Ardougne, across a 30gp ferry, so "am I still on the island" decides whether a missing item is worth a crossing.
def on_karamja(t):
    """Karamja, Brimhaven and the ferry decks."""
    return not not t and t.x >= 2700 and t.x <= 3010 and t.z >= 2870 and t.z <= 3260


def in_cutscene(t):
    """The Shaikahan hunt teleports the player into the m39_71 pocket and back out again."""
    return not not t and t.x >= 2496 and t.x <= 2559 and t.z >= 4544 and t.z <= 4607
