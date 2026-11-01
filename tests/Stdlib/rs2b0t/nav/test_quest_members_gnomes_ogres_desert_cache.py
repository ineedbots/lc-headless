"""Check phase 17e's quests against the real cache: every exact id a module looks up has the name it expects, every loc
it clicks by id offers the op it clicks, and every name it finds an NPC, loc or item by exists."""

from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.chompybird.areas import BUGS, CB_ID, CB_LOC, CB_LOC_ID, CB_NAME, CB_NPC, FYCIE, GERRANT, RANTZ
from rs2004.quests.defs.chompybird.supplies import AXES
from rs2004.quests.defs.grandtree.areas import ANITA, CHARLIE, FEMI, FOREMAN, GLOUGH, GT_ITEMS, GT_LOC, GT_NPC, GT_OBJ, HAZELMERE, NARNODE, PILOT
from rs2004.quests.defs.touristtrap import ITEM, LOC, NPC, PUNISHMENT_ROCK_ID, SHANTAY_SHOP, SLAVE_OUTFIT_DROP_IDS, WATERSKINS
from rs2004.quests.defs.watchtower.areas import WT_ITEM, WT_LOC, WT_NPC
from rs2004.quests.defs.watchtower.supplies import ARDOUGNE_ADVENTURER, MAGIC_GUILD, OGRE_HERBLORE

QUESTS = ['desertrescue', 'itwatchtower', 'chompybird', 'grandtree']


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
    pairs = [[WT_ITEM.get(key).id, WT_ITEM.get(key).name] for key in WT_ITEM.keys()]
    pairs += [[CB_ID.get(key), CB_NAME.get(key)] for key in CB_NAME.keys() if CB_ID.get(key) is not None]
    pairs += [[GT_OBJ.BARK, 'Bark sample'], [GT_OBJ.TRANSLATION_BOOK, 'Translation book'], [GT_OBJ.JOURNAL, "Glough's journal"],
              [GT_OBJ.SCROLL, "Hazelmere's scroll"], [GT_OBJ.LUMBER_ORDER, 'Lumber order'], [GT_OBJ.KEY, "Glough's key"],
              [GT_OBJ.DACONIA, 'Daconia rock'], [GT_OBJ.INVASION_PLANS, 'Invasion plans']]
    pairs += [[id, 'Twigs'] for id in [GT_OBJ.TWIG_T, GT_OBJ.TWIG_U, GT_OBJ.TWIG_Z, GT_OBJ.TWIG_O]]
    pairs += [[SLAVE_OUTFIT_DROP_IDS[0], ITEM.SLAVE_SHIRT], [SLAVE_OUTFIT_DROP_IDS[1], ITEM.SLAVE_ROBE], [SLAVE_OUTFIT_DROP_IDS[2], ITEM.SLAVE_BOOTS]]
    # The punishment rock shares "Rock" with the common one (968), which is why the gate's count is by id.
    pairs += [[PUNISHMENT_ROCK_ID, 'Rock']]
    expect(mismatches(pairs, item_name)).to_equal([])


test('every exact item id has the name its quest expects', exact_items)


def exact_npcs():
    pairs = [[NPC.ANA, 'Ana'], [NPC.SLAVE, 'Male slave'], [NPC.ESCAPED_SLAVE, 'Escaping slave'], [NPC.ROWDY_SLAVE, 'Rowdy slave'],
             [NPC.CAPTAIN, 'Mercenary Captain'], [NPC.SIAD, 'Captain Siad'], [NPC.AL_SHABIM, 'Al Shabim'],
             [NPC.BEDABIN_GUARD, 'Bedabin Nomad Guard'], [NPC.IRENA, 'Irena'], [NPC.SHANTAY, 'Shantay'],
             [NPC.MINE_CART_DRIVER, 'Mine cart driver'], [GT_NPC.BLACK_DEMON, 'Black Demon']]
    expect(mismatches(pairs, npc_name)).to_equal([])


test('every exact NPC id is the NPC its quest talks to or fights', exact_npcs)


def exact_locs():
    pairs = [[CB_LOC_ID.CHEST, CB_LOC.CHEST_LOCKED], [CB_LOC_ID.CHEST_OPEN, CB_LOC.CHEST_OPEN], [CB_LOC_ID.SPIT_EMPTY, CB_LOC.SPIT],
             [GT_LOC.CHEST_SHUT, 'Closed chest'], [WT_LOC.ROCK_OF_DALGROTH, 'Rock of Dalgroth']]
    pairs += [[id, 'Pillar'] for id in [GT_LOC.PILLAR_T, GT_LOC.PILLAR_U, GT_LOC.PILLAR_Z, GT_LOC.PILLAR_O]]
    pairs += [[id, 'Root'] for id in [GT_LOC.ROOT_A, GT_LOC.ROOT_B]]
    expect(mismatches(pairs, loc_name)).to_equal([])
    ops = [[LOC.SHANTAY_PASS, 'Go-through'], [LOC.LADDER_UP, 'Climb-up'], [LOC.LADDER_DOWN, 'Climb-down'], [LOC.BOOKCASE, 'Search'],
           [LOC.SIAD_DESK, 'Search'], [LOC.CHEST, 'Open'], [LOC.BEDABIN_TENT_DOOR, 'Walk-through'], [LOC.EMPTY_BARREL, 'Search'],
           [LOC.MINE_CART, 'Search'], [LOC.SURFACE_WINCH, 'Use'], [LOC.FULL_BARREL, 'Search'], [LOC.SURFACE_CART, 'Search'],
           [LOC.WINDOW, 'Search'], [LOC.PUNISHMENT_ROCK, 'Mine'], [2694, 'Climb-to'], [2695, 'Climb-to'], [2696, 'Climb-to'],
           [2697, 'Climb down']]
    for ids, op in [[LOC.CAMP_GATE, 'Open'], [LOC.SURFACE_MINE_DOOR, 'Open'], [LOC.UNDERGROUND_MINE_DOOR, 'Open'],
                    [LOC.MINE_CAVE, 'Walk through'], [LOC.PUNISHMENT_GATE, 'Open'], [WT_LOC.CAVE_IN, 'Enter'],
                    [WT_LOC.CAVE_OUT, 'Leave']]:
        ops += [[id, op] for id in ids]
    ops += [[WT_LOC.WALL_CLIMB, 'Climb-up'], [WT_LOC.TOWER_LADDER, 'Climb-up'], [WT_LOC.WATCH_LADDER_UP, 'Climb-up'],
            [WT_LOC.WATCH_LADDER_DOWN, 'Climb-down'], [WT_LOC.LADDER_TOP, 'Climb-down'], [WT_LOC.LEVER, 'Pull'],
            [WT_LOC.BUSH_NAIL, 'Search'], [WT_LOC.ROPESWING, 'Swing-on'], [WT_LOC.TOBAN_CAVE, 'Enter'],
            [WT_LOC.TOBAN_LADDER_DOWN, 'Climb-down'], [WT_LOC.GATE_EAST, 'Open'], [WT_LOC.ROCK_CAKE_STALL, 'Steal-From'],
            [WT_LOC.BATTLEMENT, 'Climb-over'], [WT_LOC.JUMP_IN, 'Jump-From'], [WT_LOC.JUMP_OUT, 'Jump-From'],
            [WT_LOC.ENCLAVE_CAVE, 'Enter'], [WT_LOC.DARK_CAVE_ESCAPE, 'Climb'], [WT_LOC.ROCK_OF_DALGROTH, 'Mine']]
    ops += [[GT_LOC.CUPBOARD_SHUT, 'Open'], [GT_LOC.CUPBOARD_OPEN, 'Search'], [GT_LOC.TRAPDOOR_SHUT, 'Open'],
            [GT_LOC.CLIMB_TREE, 'Climb-up'], [GT_LOC.DOWN_TREE, 'Climb-down'], [GT_LOC.ROOT_A, 'Search'], [GT_LOC.ROOT_B, 'Search']]
    # The vegetable patches carry no name, so Big Chompy Bird Hunting picks them by id.
    ops += [[CB_LOC_ID.CHEST, 'Unlock'], [CB_LOC_ID.CHEST_OPEN, 'Search'], [312, 'Pick'], [1161, 'Pick'], [3366, 'Pick']]
    expect(without_op(ops)).to_equal([])


test('every exact loc id is the loc its quest drives, offering the op it clicks', exact_locs)


def named_targets():
    stops = [NARNODE, HAZELMERE, GLOUGH, CHARLIE, ANITA, FOREMAN, FEMI, PILOT, RANTZ, BUGS, FYCIE, GERRANT,
             ARDOUGNE_ADVENTURER, MAGIC_GUILD, OGRE_HERBLORE, SHANTAY_SHOP]
    npc_names = [stop.npc for stop in stops] + ['Man', 'Kebab seller', 'Bob']
    npc_names += [WT_NPC.get(key) for key in WT_NPC.keys()] + [CB_NPC.get(key) for key in CB_NPC.keys()]
    expect([name for name in npc_names if len(reader.npc_ids(name)) == 0]).to_equal([])
    loc_names = [CB_LOC.get(key) for key in CB_LOC.keys() if key != 'CABBAGE'] + ['Staircase', 'Ladder', 'Root', 'Pillar', 'Closed chest']
    expect([name for name in loc_names if len(reader.loc_ids(name)) == 0]).to_equal([])
    item_names = [ITEM.get(key) for key in ITEM.keys()] + list(WATERSKINS) + list(AXES) + [name[0].upper() + name[1:] for name in GT_ITEMS]
    item_names += ['Tuna', 'Swordfish', 'Lobster', 'Trout', 'Kebab', 'Ogre bellows', 'Spell scroll']
    for id in QUESTS:
        item_names += [item.name for item in def_by_id(id).record.items]
    expect([name for name in item_names if len(reader.item_ids(name)) == 0]).to_equal([])


test('every name a quest finds an NPC, loc or item by exists in the cache', named_targets)
