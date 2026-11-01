"""Check phase 17f's quests against the real cache: every exact id a module looks up has the name it expects, every loc
it clicks by id offers the op it clicks, and every name it finds an NPC, loc or item by exists."""

from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.digsite.areas import CURATOR, DIG_ID, DIG_ITEM, DIG_LOC, DIG_NPC, DIG_SOIL_IDS, EXAMINER, EXPERT, PANNING_GUIDE
from rs2004.quests.defs.digsite.supplies import SHOP as DIG_SHOP
from rs2004.quests.defs.elementalworkshop.areas import EW_ITEM, PICKAXES
from rs2004.quests.defs.familycrest import BOOT, CALEB_START, DIMINTHEIS_START, GEM_TRADER, JOHNATHON
from rs2004.quests.defs.familycrest.areas import DUEL_RING_IDS, FC_ID, FC_ITEM, FC_NPC, FC_SHOP
from rs2004.quests.defs.familycrest.mine import LEVER_LOC
from rs2004.quests.defs.holygrail.areas import FISHERMAN, FISHER_KING, GALAHAD, HIGH_PRIEST, ITEM as GRAIL_ITEM, KING_ARTHUR_START, LADY_OF_THE_LAKE, MERLIN, MERLIN_ID, SIR_PERCIVAL, TITAN_ID, WHISTLE_DOOR_ID
from rs2004.quests.defs.horror.areas import ARCHERY_SHOP, GENERAL_SHOP, GUNNJORN, HD_ID, HD_ITEM, HD_LOC, JOSSIK, LARRISSA, RUNE_SHOP, SWORD_SHOP
from rs2004.quests.defs.horror.fight import DAGANNOTH_JR, MOTHER_IDS
from rs2004.quests.defs.horror.supplies import PRAYER_POTION_NAMES

QUESTS = ['elemental_workshop', 'itexam', 'grail', 'crest', 'horror']


def item_name(id):
    found = reader.item_type(id)
    return found.name if found is not None else None


def loc_name(id):
    found = reader.loc_type(id)
    return found.name if found is not None else None


def npc_name(id):
    found = reader.npc_type(id)
    return found.name if found is not None else None


def mismatches(pairs, read):
    """The (id, expected, found) of each pair the cache names differently."""
    return [[id, name, read(id)] for id, name in pairs if read(id) != name]


def without_op(pairs):
    """The (id, op) of each loc that doesn't offer the op its quest clicks."""
    missing = []
    for id, op in pairs:
        found = reader.loc_type(id)
        ops = [] if found is None else [o.lower() for o in found.ops if o is not None]
        if op.lower() not in ops:
            missing.append([id, op])
    return missing


def exact_items():
    pairs = [[EW_ITEM.get(key).id, EW_ITEM.get(key).name] for key in EW_ITEM.keys()]
    pairs += [[pick.id, pick.name] for pick in PICKAXES]
    pairs += [[DIG_ID.get(key), DIG_ITEM.get(key)] for key in DIG_ITEM.keys() if DIG_ID.get(key) is not None]
    pairs += [[FC_ID.get(key), FC_ITEM.get(key)] for key in FC_ITEM.keys() if FC_ID.get(key) is not None]
    pairs += [[HD_ID.get(key), HD_ITEM.get(key)] for key in HD_ITEM.keys() if HD_ID.get(key) is not None]
    # Display names collide here, which is why the modules go by id.
    pairs += [[DIG_ID.TRAY_EMPTY, DIG_ITEM.TRAY], [DIG_ID.TRAY_MUD, DIG_ITEM.TRAY], [DIG_ID.ROCK_SAMPLE_GREEN, 'Rock sample 1'],
              [DIG_ID.ROCK_SAMPLE_ORANGE, 'Rock sample 2'], [DIG_ID.ROCK_SAMPLE_PURPLE, 'Rock sample 3'], [DIG_ID.PRE_CHARCOAL, 'Mixed chemicals'],
              [DIG_ID.POST_CHARCOAL, 'Mixed chemicals'], [DIG_ID.COMPOUND, 'Chemical compound'], [DIG_ID.AMMONIUM_NITRATE, 'Ammonium nitrate'],
              [DIG_ID.NITROGLYCERIN, 'Nitroglycerin'], [DIG_ID.GROUND_CHARCOAL, 'Ground charcoal']]
    pairs += [[id, FC_ITEM.CREST_PART] for id in [FC_ID.CREST_FROM_CALEB, FC_ID.CREST_FROM_AVAN, FC_ID.CREST_FROM_CHRONOZON]]
    pairs += [[FC_ID.ANTIPOISON_4, 'Antipoison(4)'], [FC_ID.ANTIPOISON_3, 'Antipoison(3)'], [FC_ID.ANTIPOISON_2, 'Antipoison(2)'], [FC_ID.ANTIPOISON_1, 'Antipoison(1)']]
    pairs += [[id, 'Ring of dueling(' + str(8 - i) + ')'] for i, id in enumerate(DUEL_RING_IDS)]
    pairs += [[HD_ID.STEEL_BAR, 'Steel bar']]
    pairs += [[id, name] for id, name in PRAYER_POTION_NAMES.items()]
    expect(mismatches(pairs, item_name)).to_equal([])


test('every exact item id has the name its quest expects', exact_items)


def exact_npcs():
    pairs = [[DIG_NPC.WORKMAN, 'Digsite workman'], [DIG_NPC.CAVE_WORKMAN, 'Digsite workman'], [DIG_NPC.STUDENT_GREEN, 'Student'],
             [DIG_NPC.STUDENT_ORANGE, 'Student'], [DIG_NPC.STUDENT_PURPLE, 'Student'], [DIG_NPC.EXAMINER, EXAMINER.npc], [DIG_NPC.EXPERT, EXPERT.npc],
             [DIG_NPC.PANNING_GUIDE, PANNING_GUIDE.npc], [DIG_NPC.CURATOR, CURATOR.npc], [MERLIN_ID, MERLIN.npc], [TITAN_ID, 'Black Knight Titan'],
             [FC_NPC.AVAN_NPC_ID, 'Man'], [FC_NPC.CHRONOZON_NPC_ID, 'Chronozon'], [DAGANNOTH_JR, 'Dagannoth']]
    pairs += [[id, 'Dagannoth mother'] for id in MOTHER_IDS]
    expect(mismatches(pairs, npc_name)).to_equal([])


test('every exact NPC id is the NPC its quest talks to or fights', exact_npcs)


def exact_locs():
    pairs = [[DIG_LOC.WINCH_MAIN, 'Winch'], [DIG_LOC.WINCH_PRIVATE, 'Winch'], [DIG_LOC.SAMPLE_SACKS, 'Sacks'], [DIG_LOC.BARREL, 'Barrel'],
             [DIG_LOC.CHEST_OPEN, 'Chest'], [DIG_LOC.CHEST_SHUT, 'Chest'], [DIG_LOC.BRICK, 'Brick'], [WHISTLE_DOOR_ID, 'Door']]
    expect(mismatches(pairs, loc_name)).to_equal([])
    ops = [[DIG_LOC.WINCH_MAIN, 'Operate'], [DIG_LOC.WINCH_PRIVATE, 'Operate'], [DIG_LOC.SAMPLE_SACKS, 'Search'], [DIG_LOC.BUSH_SAMPLE, 'Search'],
           [DIG_LOC.CHEST_OPEN, 'Search'], [DIG_LOC.PANNING_POINT, 'Look'], [WHISTLE_DOOR_ID, 'Open'], [2098, 'Mine'], [2099, 'Mine']]
    for key in LEVER_LOC.keys():
        lever = LEVER_LOC.get(key)
        ops += [[lever.down, 'Pull'], [lever.up, 'Pull']]
    expect(without_op(ops)).to_equal([])
    expect([id for id in DIG_SOIL_IDS if reader.loc_type(id) is None]).to_equal([])


test('every exact loc id is the loc its quest drives, offering the op it clicks', exact_locs)


def named_targets():
    stops = [KING_ARTHUR_START, HIGH_PRIEST, GALAHAD, FISHERMAN, FISHER_KING, SIR_PERCIVAL, LADY_OF_THE_LAKE, DIMINTHEIS_START, CALEB_START,
             GEM_TRADER, BOOT, JOHNATHON, LARRISSA, GUNNJORN, JOSSIK, SWORD_SHOP, ARCHERY_SHOP, RUNE_SHOP, GENERAL_SHOP,
             DIG_SHOP.GENERAL, DIG_SHOP.TEA, DIG_SHOP.HERBLORE, FC_SHOP.AUBURY, FC_SHOP.DOMMIK, FC_SHOP.GEM_MERCHANT, FC_SHOP.JIMINUA, FC_SHOP.NURMOF]
    npc_names = [stop.npc for stop in stops] + ['Earth elemental', 'Water elemental', 'Grail Maiden']
    expect([name for name in npc_names if len(reader.npc_ids(name)) == 0]).to_equal([])
    loc_names = [HD_LOC.get(key) for key in HD_LOC.keys()]
    loc_names += ['Bookcase', 'Odd looking wall', 'Staircase', 'Water Valve', 'Lever', 'Crate', 'Boxes', 'Bellows', 'Lava trough', 'Furnace', 'Pile of Rock', 'Workbench',
                  'Rope', 'Sacks', 'Door', 'Ladder']
    expect([name for name in loc_names if len(reader.loc_ids(name)) == 0]).to_equal([])
    item_names = [GRAIL_ITEM.get(key) for key in GRAIL_ITEM.keys()]
    item_names += ['Steel pickaxe', 'Lobster', 'Swordfish', 'Salmon', 'Trout', 'Shark', 'Tuna', 'Herring', 'Ruby']
    for id in QUESTS:
        item_names += [item.name for item in def_by_id(id).record.items]
    expect([name for name in item_names if len(reader.item_ids(name)) == 0]).to_equal([])


test('every name a quest finds an NPC, loc or item by exists in the cache', named_targets)
