"""Check Legends Quest against the real cache: every exact id it looks up has the name it expects, every loc it clicks by
id offers the op it clicks, every name it finds things by exists, and the pockets baked from rs2b0t's collision pack hold
on this client's own map. Then rs2b0t's test/api/bank/legends-guild.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.legends.areas import GEM_CUTS, GEM_ROCKS, LQ_BANK, LQ_ID, LQ_ITEM, LQ_LOC, LQ_LOC_ID, LQ_NPC, LQ_SHOP, LQ_TILE, WALL_RUNES
from rs2004.quests.defs.legends.pockets import legends_pocket
from rs2004.quests.defs.legends.supplies import PICKAXES, PRAYER_POTIONS
from rs2004.quests.defs.legends.viyeldi import LEDGES

BANK_LOCATIONS = as_records(BANK_LOCATIONS)
bank_unlocked = record_view(bank_unlocked)
GUILD = [row for row in BANK_LOCATIONS if row.name == 'Legends Guild'][0]


def item_name(id):
    found = reader.item_type(id)
    return found.name if found is not None else None


def loc_type_name(id):
    found = reader.loc_type(id)
    return found.name if found is not None else None


def exact_items():
    # Why: LQ_ITEM names what the client renders, and the fill states of the bowl share names, so only the ids both tables spell the same way are compared.
    wrong = []
    for key in LQ_ITEM.keys():
        id = LQ_ID.get(key)
        if id is not None and item_name(id) != LQ_ITEM.get(key):
            wrong.append([key, id, LQ_ITEM.get(key), item_name(id)])
    expect(wrong).to_equal([])
    expect([key for key in LQ_ID.keys() if item_name(LQ_ID.get(key)) is None]).to_equal([])
    named = list(GEM_ROCKS) + list(WALL_RUNES) + list(PICKAXES) + list(PRAYER_POTIONS)
    expect([[row.id, row.name, item_name(row.id)] for row in named if item_name(row.id) != row.name]).to_equal([])
    expect([[row.uncut, row.uncut_name, item_name(row.uncut)] for row in GEM_CUTS if item_name(row.uncut) != row.uncut_name]).to_equal([])
    expect([[row.cut, row.name, item_name(row.cut)] for row in GEM_CUTS if item_name(row.cut) != row.name]).to_equal([])


test('every exact item id is the item the quest looks for', exact_items)


def exact_locs():
    ops = [
        [LQ_LOC_ID.GUILD_GATE_L, 'Open'], [LQ_LOC_ID.GUILD_GATE_R, 'Open'], [LQ_LOC_ID.LOCKPICK_GATE_L, 'Search'], [LQ_LOC_ID.LOCKPICK_GATE_R, 'Search'],
        [LQ_LOC_ID.LOCKPICK_GATE_L, 'Open'], [LQ_LOC_ID.LOCKPICK_GATE_R, 'Open'], [LQ_LOC_ID.STRENGTH_GATE_L, 'Open'], [LQ_LOC_ID.STRENGTH_GATE_R, 'Open'],
        [LQ_LOC_ID.BOULDER_1, 'Smash-to-bits'], [LQ_LOC_ID.BOULDER_2, 'Smash-to-bits'], [LQ_LOC_ID.BOULDER_3, 'Smash-to-bits'], [LQ_LOC_ID.MARKED_WALL, 'Use'],
        [LQ_LOC_ID.MAGIC_GATE, 'Open'], [LQ_LOC_ID.WINCH_NO_ROPE, 'Search'], [LQ_LOC_ID.WINCH_ROPE, 'Climb-down'], [LQ_LOC_ID.MOSSY_ROCK_1, 'Search'],
        [LQ_LOC_ID.MOSSY_ROCK_2, 'Search'], [LQ_LOC_ID.MOSSY_ROCK_3, 'Search'], [LQ_LOC_ID.CUPBOARD_OPEN, 'Search'], [LQ_LOC_ID.CUPBOARD_SHUT, 'Open'],
        [LQ_LOC_ID.YOMMI_TOTEM, 'Lift'], [2111, 'Mine'],
    ]
    ops += [[ledge.id, 'Climb-over'] for ledge in LEDGES]
    wrong = []
    for row in ops:
        found = reader.loc_type(row[0])
        offered = [] if found is None else [op.lower() for op in found.ops if op is not None]
        if row[1].lower() not in offered:
            wrong.append([row[0], row[1], None if found is None else found.ops])
    expect(wrong).to_equal([])
    # Why: `next_loc_stage` swings the picked gate's leaves to a model with no name and no ops, which is what the module reads as open.
    nameless = ['LOCKPICK_GATE_L_OPEN', 'LOCKPICK_GATE_R_OPEN']
    expect([key for key in LQ_LOC_ID.keys() if loc_type_name(LQ_LOC_ID.get(key)) is None and key not in nameless]).to_equal([])


test('every exact loc id is the loc the quest drives, offering the op it clicks', exact_locs)


def named_locs():
    wrong = []
    pairs = [[LQ_LOC_ID.MARKED_WALL, LQ_LOC.MARKED_WALL], [LQ_LOC_ID.FURNACE, LQ_LOC.FURNACE], [LQ_LOC_ID.RECESS_EMPTY, LQ_LOC.RECESS], [LQ_LOC_ID.RECESS_FULL, LQ_LOC.RECESS_FULL],
             [LQ_LOC_ID.BARRIER, LQ_LOC.BARRIER], [LQ_LOC_ID.SACRED_WATER, LQ_LOC.SACRED_WATER], [LQ_LOC_ID.TALL_REEDS, LQ_LOC.TALL_REEDS], [LQ_LOC_ID.WATER_POOL_SOURCE, LQ_LOC.SOURCE_POOL],
             [LQ_LOC_ID.FERTILE_SOIL, LQ_LOC.FERTILE_SOIL], [LQ_LOC_ID.YOMMI_SAPLING, LQ_LOC.YOMMI_SAPLING], [LQ_LOC_ID.YOMMI_ADULT, LQ_LOC.YOMMI_ADULT], [LQ_LOC_ID.YOMMI_FELLED, LQ_LOC.YOMMI_FELLED],
             [LQ_LOC_ID.YOMMI_TRIMMED, LQ_LOC.YOMMI_TRIMMED], [LQ_LOC_ID.YOMMI_TOTEM, LQ_LOC.YOMMI_TOTEM], [LQ_LOC_ID.EVIL_TOTEM, LQ_LOC.TOTEM_POLE], [LQ_LOC_ID.WINCH_NO_ROPE, LQ_LOC.WINCH],
             [LQ_LOC_ID.CUPBOARD_SHUT, LQ_LOC.CUPBOARD], [LQ_LOC_ID.CUPBOARD_OPEN, LQ_LOC.CUPBOARD_OPEN], [LQ_LOC_ID.GUILD_GATE_L, LQ_LOC.GUILD_GATE], [LQ_LOC_ID.DRAGONS_EYE_ROCK, LQ_LOC.MOSSY_ROCK]]
    pairs += [[ledge.id, ledge.name] for ledge in LEDGES]
    for row in pairs:
        if loc_type_name(row[0]) != row[1]:
            wrong.append([row[0], row[1], loc_type_name(row[0])])
    expect(wrong).to_equal([])


test('every name the quest finds a loc by is the name that id carries', named_locs)


def named_targets():
    names = [LQ_NPC.get(key) for key in LQ_NPC.keys()] + [LQ_SHOP.JIMINUA.npc, LQ_SHOP.MAGIC_GUILD.npc]
    expect([name for name in names if len(reader.npc_ids(name)) == 0]).to_equal([])
    items = [item.name for item in def_by_id('legends').record.items]
    expect([name for name in items if len(reader.item_ids(name)) == 0]).to_equal([])


test('every name the quest finds an NPC or item by exists in the cache', named_targets)


def route(a, b):
    return navigator.find_path(a, b, max_expansions=400000, policy={'use_teleports': False}).ok


def pocket_tiles():
    wants = [
        ['CAVE_LANDING', 'shaman_cave'], ['OCTAGRAM_OUTSIDE', 'shaman_cave'], ['SHAMAN_BOOKCASE', 'shaman_cave'], ['OCTAGRAM_INSIDE', 'octagram'],
        ['SHAMAN_CREVICE', 'crevice'], ['LOCKPICK_GATE_NORTH', 'crevice'], ['LOCKPICK_GATE_SOUTH', 'outer_gate'], ['BOULDER_1_NORTH', 'outer_gate'],
        ['BOULDER_1_SOUTH', 'boulder_one'], ['BOULDER_2_SOUTH', 'boulder_two'], ['BOULDER_3_SOUTH', 'inner_gate'], ['STRENGTH_GATE_NORTH', 'inner_gate'],
        ['STRENGTH_GATE_SOUTH', 'trials'], ['JAGGED_WALL_SOUTH', 'trials'], ['JAGGED_WALL_NORTH', 'wall_room'], ['MARKED_WALL_IN', 'wall_room'],
        ['MARKED_WALL_OUT', 'gem_room'], ['GEM_ROOM_LANDING', 'gem_room'], ['BOOK_SPAWN', 'gem_room'], ['MAGIC_GATE_SOUTH', 'gem_room'],
        ['MAGIC_GATE_NORTH', 'winch_room'], ['WINCH', 'winch_room'], ['VIYELDI_LEDGE', 'viyeldi_ledge'], ['VIYELDI_MAIN', 'viyeldi_main'],
        ['DRAGONS_EYE', 'viyeldi_main'], ['LAVA_FURNACE', 'viyeldi_main'], ['BARRIER_NORTH', 'viyeldi_main'], ['BARRIER_SOUTH', 'viyeldi_source'], ['SOURCE_STAND', 'viyeldi_source'],
    ]
    expect([[row[0], row[1], legends_pocket(LQ_TILE.get(row[0]))] for row in wants if legends_pocket(LQ_TILE.get(row[0])) != row[1]]).to_equal([])


test('every stand the quest walks to is in the pocket its crossing expects', pocket_tiles)


def walks_inside():
    pairs = [
        ['CAVE_LANDING', 'SHAMAN_BOOKCASE'], ['CAVE_LANDING', 'FIRE_WALL_WEST'], ['SHAMAN_CREVICE', 'LOCKPICK_GATE_NORTH'], ['LOCKPICK_GATE_SOUTH', 'BOULDER_1_NORTH'],
        ['BOULDER_3_SOUTH', 'STRENGTH_GATE_NORTH'], ['STRENGTH_GATE_SOUTH', 'JAGGED_WALL_SOUTH'], ['JAGGED_WALL_NORTH', 'MARKED_WALL_IN'], ['MARKED_WALL_OUT', 'BOOK_SPAWN'],
        ['GEM_ROOM_LANDING', 'MAGIC_GATE_SOUTH'], ['MAGIC_GATE_NORTH', 'WINCH'], ['VIYELDI_MAIN', 'DRAGONS_EYE'], ['VIYELDI_MAIN', 'LAVA_FURNACE'], ['VIYELDI_MAIN', 'BARRIER_NORTH'],
        ['BARRIER_SOUTH', 'SOURCE_STAND'], ['JUNGLE_INSIDE', 'MAP_WEST'], ['JUNGLE_INSIDE', 'MAP_MIDDLE'], ['JUNGLE_INSIDE', 'MAP_EAST'], ['JUNGLE_INSIDE', 'BULLROARER_SPOT'],
        ['JUNGLE_INSIDE', 'MOSSY_ROCKS'], ['JUNGLE_INSIDE', 'SACRED_POOL'],
    ]
    expect([row for row in pairs if not route(LQ_TILE.get(row[0]), LQ_TILE.get(row[1]))]).to_equal([])


test('the walker joins the tiles the quest walks between inside one pocket', walks_inside)


def sealed():
    # Why: each pair sits either side of a crossing the module scripts, and a route across one means the walker would stroll at a gate that refuses it, as rs2b0t's doors.json once did.
    pairs = [
        ['SHAMAN_BOOKCASE', 'SHAMAN_CREVICE'], ['LOCKPICK_GATE_NORTH', 'LOCKPICK_GATE_SOUTH'], ['BOULDER_1_NORTH', 'BOULDER_1_SOUTH'], ['BOULDER_1_SOUTH', 'BOULDER_2_SOUTH'],
        ['BOULDER_2_SOUTH', 'BOULDER_3_SOUTH'], ['STRENGTH_GATE_NORTH', 'STRENGTH_GATE_SOUTH'], ['JAGGED_WALL_SOUTH', 'JAGGED_WALL_NORTH'], ['MARKED_WALL_IN', 'MARKED_WALL_OUT'],
        ['MAGIC_GATE_SOUTH', 'MAGIC_GATE_NORTH'], ['VIYELDI_LEDGE', 'VIYELDI_MAIN'], ['BARRIER_NORTH', 'BARRIER_SOUTH'], ['JUNGLE_MOUTH', 'JUNGLE_INSIDE'],
    ]
    expect([row for row in pairs if route(LQ_TILE.get(row[0]), LQ_TILE.get(row[1]))]).to_equal([])


test('no walk crosses what the quest crosses by script', sealed)


def counters():
    # Why: the ship and the cart want coin and Shilo's gate wants the quest, so the state is an account's that has both.
    state = world_state()
    state['quests']['Shilo Village'] = 'complete'
    state['items']['Coins'] = 20000
    state['members'] = True
    state['skills']['magic'] = 70
    start = LQ_BANK.ARDOUGNE
    for dest in [LQ_TILE.JUNGLE_MOUTH, LQ_BANK.SHILO, LQ_TILE.GEM_ROCKS, LQ_SHOP.JIMINUA.anchor, LQ_SHOP.MAGIC_GUILD.anchor, LQ_BANK.YANILLE, LQ_TILE.GUARD, LQ_TILE.FURNACE, LQ_TILE.GOLD_ROCKS, LQ_TILE.ANVIL, LQ_TILE.SNAKE_WEED, LQ_TILE.ARDRIGAL]:
        path = navigator.find_path(start, dest, max_expansions=4000000, policy={'use_teleports': False}, state=state)
        expect([dest.x, dest.z, path.ok]).to_equal([dest.x, dest.z, True])


test('from Ardougne the walker reaches every counter, bank and rock the quest walks to', counters)


# Why: as rs2b0t's bank test says, the guild's bankers are two floors up, and only for those who finished the quest.
def guild_bank():
    expect(GUILD.tile).to_match_object(Record({'x': 2732, 'z': 3378, 'level': 2}))
    expect(GUILD.npc_access).to_match_object(Record({'name': 'Banker', 'op': 'Bank'}))
    spy_on(quests, 'status', returns='not_started')
    expect(bank_unlocked(GUILD)).to_be(False)
    spy_on(quests, 'status', returns='complete')
    expect(bank_unlocked(GUILD)).to_be(True)


test('Legends Guild banks with the bankers on the second floor after Legends Quest', guild_bank)


def hops(path):
    return [w['transport']['action'] for w in path.raw['waypoints'] if w.get('transport') is not None]


def shadow_warriors():
    spy_on(quests, 'status', impl=lambda name: 'complete' if name == 'Legends Quest' else 'not_started')
    basement = Tile(2700, 9774, 0)
    guild = Tile(GUILD.tile.x, GUILD.tile.z, GUILD.tile.level)
    outward = navigator.find_path(basement, guild, max_expansions=500000, policy={'use_teleports': False})
    returning = navigator.find_path(guild, basement, max_expansions=500000, policy={'use_teleports': False})
    expect(outward.ok).to_be(True)
    expect(returning.ok).to_be(True)
    expect(hops(outward)).to_equal(['Climb-up', 'Climb-up', 'Climb-up'])
    expect(hops(returning)).to_equal(['Climb-down', 'Climb-down', 'Climb-down'])


test('shadow warriors can bank upstairs and walk back through the dungeon stairs', shadow_warriors)
