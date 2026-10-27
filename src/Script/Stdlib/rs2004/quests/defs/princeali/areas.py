"""Ported from rs2b0t's src/bot/api/ai/quests/defs/princeali/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile


__all__ = ['PA_ITEM', 'PA_TILE', 'PA_SHOP', 'PA_LOC', 'PA_NPC', 'HASSAN_START', 'HASSAN_REWARD', 'OSMAN_BRIEF', 'OSMAN_FORGE', 'LEELA_STOP', 'NED_WIG', 'NED_ROPE', 'AGGIE_PASTE', 'KELI_PRINT', 'JOE_BEER', 'BARTENDER']

# Names are the engine's; Wig, Beer, Pot of flour, Logs and Coins each collide with another object, so every lookup goes through the id.
PA_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'PRINCE_KEY': Record({'id': 2418, 'name': 'Bronze key'}),
    'BLOND_WIG': Record({'id': 2419, 'name': 'Wig'}),
    'PLAIN_WIG': Record({'id': 2421, 'name': 'Wig'}),
    'KEY_PRINT': Record({'id': 2423, 'name': 'Key print'}),
    'PASTE': Record({'id': 2424, 'name': 'Paste'}),
    'PINK_SKIRT': Record({'id': 1013, 'name': 'Pink skirt'}),
    'ROPE': Record({'id': 954, 'name': 'Rope'}),
    'BEER': Record({'id': 1917, 'name': 'Beer'}),
    'SOFT_CLAY': Record({'id': 1761, 'name': 'Soft clay'}),
    'CLAY': Record({'id': 434, 'name': 'Clay'}),
    'YELLOW_DYE': Record({'id': 1765, 'name': 'Yellow dye'}),
    'ONION': Record({'id': 1957, 'name': 'Onion'}),
    'BALL_OF_WOOL': Record({'id': 1759, 'name': 'Ball of wool'}),
    'WOOL': Record({'id': 1737, 'name': 'Wool'}),
    'SHEARS': Record({'id': 1735, 'name': 'Shears'}),
    'REDBERRIES': Record({'id': 1951, 'name': 'Redberries'}),
    'POT_OF_FLOUR': Record({'id': 1933, 'name': 'Pot of flour'}),
    'ASHES': Record({'id': 592, 'name': 'Ashes'}),
    'TINDERBOX': Record({'id': 590, 'name': 'Tinderbox'}),
    'BRONZE_BAR': Record({'id': 2349, 'name': 'Bronze bar'}),
    'JUG_OF_WATER': Record({'id': 1937, 'name': 'Jug of water'}),
    'LOGS': Record({'id': 1511, 'name': 'Logs'}),
    'PICKAXE': Record({'id': 1265, 'name': 'Bronze pickaxe'}),
})
PA_TILE = Record({
    'DRAYNOR_BANK': Tile(3093, 3243, 0),
    'HASSAN': Tile(3302, 3163, 0),
    'OSMAN': Tile(3286, 3180, 0),
    'LEELA': Tile(3113, 3263, 0),
    'NED': Tile(3100, 3258, 0),
    'AGGIE': Tile(3086, 3259, 0),
    'JOE': Tile(3123, 3245, 0),
    'KELI': Tile(3128, 3244, 0),
    'DOOR_STAND': Tile(3123, 3244, 0),
    'CELL': Tile(3123, 3243, 0),
    'PRINCE': Tile(3123, 3242, 0),
    'BARTENDER': Tile(3045, 3257, 0),
    'LOGS_SPAWN': Tile(3089, 3265, 0),
    'ONION_PATCH': Tile(3189, 3267, 0),
    'SHEEP_PEN': Tile(3197, 3266, 0),
    'SHEARS_SPAWN': Tile(3152, 3306, 0),
    'SPIN_STAND': Tile(3209, 3213, 1),
    'CLAY_ROCKS': Tile(2986, 3239, 0),
    'PICKAXE_SPAWN': Tile(2963, 3216, 0),
})
PA_SHOP = Record({
    'SHANTAY': Record({'npc': 'Shantay', 'anchor': Tile(3304, 3123, 0)}),
    'LUMBRIDGE': Record({'npc': 'Shop keeper', 'anchor': Tile(3209, 3247, 0)}),
    'THESSALIA': Record({'npc': 'Thessalia', 'anchor': Tile(3204, 3417, 0)}),
    'WYDIN': Record({'npc': 'Wydin', 'anchor': Tile(3014, 3204, 0)}),
})
PA_LOC = Record({'PRISON_DOOR': 'Prison Door', 'ONION': 'Onion'})
PA_NPC = Record({'PRINCE': 'Prince Ali', 'KELI': 'Lady Keli', 'AGGIE': 'Aggie'})
HASSAN_START = Record({
    'npc': 'Hassan',
    'anchor': PA_TILE.HASSAN,
    'leash': 6,
    'prefer': ['Can I help you? You must need some help here in the desert.'],
})
HASSAN_REWARD = Record({'npc': 'Hassan', 'anchor': PA_TILE.HASSAN, 'leash': 6, 'prefer': []})
# The exit first: osman_second_thing re-offers the first branch, and taking it loops.
OSMAN_BRIEF = Record({
    'npc': 'Osman',
    'anchor': PA_TILE.OSMAN,
    'leash': 6,
    'prefer': ['Okay, I better go find some things.', 'What is the second thing you need?'],
})
OSMAN_FORGE = Record({
    'npc': 'Osman',
    'anchor': PA_TILE.OSMAN,
    'leash': 6,
    'prefer': ['Thank you. I will try to find the other items.'],
})
LEELA_STOP = Record({
    'npc': 'Leela',
    'anchor': PA_TILE.LEELA,
    'leash': 6,
    'prefer': ['I hoped to get him drunk.', 'I will go and get the rest of the escape equipment.'],
})
NED_WIG = Record({
    'npc': 'Ned',
    'anchor': PA_TILE.NED,
    'leash': 6,
    'prefer': [
    'Ned, could you make other things from wool?',
    'How about some sort of wig?',
    'I have that now. Please, make me a wig.',
],
})
# "Okay, please sell me some rope." must outrank Ned's offer to spin 4 balls of wool.
NED_ROPE = Record({
    'npc': 'Ned',
    'anchor': PA_TILE.NED,
    'leash': 6,
    'prefer': ['Yes, I would like some rope.', 'Okay, please sell me some rope.'],
})
AGGIE_PASTE = Record({
    'npc': 'Aggie',
    'anchor': PA_TILE.AGGIE,
    'leash': 6,
    'prefer': ['Could you think of a way to make skin paste?', 'Yes please. Mix me some skin paste.'],
})
KELI_PRINT = Record({
    'npc': 'Lady Keli',
    'anchor': PA_TILE.KELI,
    'leash': 8,
    'prefer': [
    'Heard of you? You are famous in RuneScape!',
    'What is your latest plan then?',
    'Can you be sure they will not try to get him out?',
    'Could I see the key please?',
    'Could I touch the key for a moment?',
],
})
JOE_BEER = Record({'npc': 'Joe', 'anchor': PA_TILE.JOE, 'leash': 6, 'prefer': ['I have some beer here, fancy one?']})
BARTENDER = Record({'npc': 'Bartender', 'anchor': PA_TILE.BARTENDER, 'leash': 6, 'prefer': ['Could I buy a beer please?']})
