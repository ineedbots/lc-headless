"""Check phase 17b's quests against the real cache: every exact id a module looks up has the name it expects, and
every name it finds an NPC, loc or item by exists."""

from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.dwarfcannon.areas import MC_LOC, MC_OBJ
from rs2004.quests.defs.fightarena.areas import FA_ITEM, FA_LOC, FA_NPC, FA_OBJ
from rs2004.quests.defs.observatory.areas import OBS_ID, OBS_ITEM, OBS_LOC, OBS_LOC_NAME
from rs2004.quests.defs.scorpcatcher.areas import CAGE_ID, CAGE_NAME, SCORPION_NPC, SC_ID, SC_ITEM
from rs2004.quests.defs.sheepherder.areas import BONES_OBJ, FEED, FEED_OBJ, FURNACE_LOC, GATE_LOC, JACKET, JACKET_OBJ, PROD, PROD_OBJ, TROUSERS, TROUSERS_OBJ, sheep_name
from rs2004.quests.defs.treegnome.areas import TG_ITEM, TG_LOC, TG_NPC
import rs2004.quests.defs.lostcity as lostcity
import rs2004.quests.defs.merlinscrystal as merlinscrystal
import rs2004.quests.defs.waterfall as waterfall

QUESTS = ['mcannon', 'sheepherder', 'tree', 'waterfall', 'scorpcatcher', 'itgronigen', 'arena', 'arthur', 'zanaris']


def item_is(id, name):
    expect(reader.item_type(id).name, str(id)).to_be(name)


def loc_is(id, name):
    found = reader.loc_type(id)
    expect(found.name if found is not None else None, str(id)).to_be(name)


def npc_is(id, name):
    found = reader.npc_type(id)
    expect(found.name if found is not None else None, str(id)).to_be(name)


def exact_items():
    for key in MC_OBJ.keys():
        item_is(MC_OBJ.get(key).id, MC_OBJ.get(key).name)
    for id in BONES_OBJ.values():
        item_is(id, 'Bones')
    for id, name in [[PROD_OBJ, PROD], [FEED_OBJ, FEED], [JACKET_OBJ, JACKET], [TROUSERS_OBJ, TROUSERS]]:
        item_is(id, name)
    for key in TG_ITEM.keys():
        item_is(TG_ITEM.get(key).id, TG_ITEM.get(key).name)
    for key in CAGE_ID.keys():
        item_is(CAGE_ID.get(key), CAGE_NAME)
    item_is(SC_ID.DUSTY_KEY, SC_ITEM.DUSTY_KEY)
    item_is(SC_ID.JAIL_KEY, SC_ITEM.JAIL_KEY)
    for key in OBS_ITEM.keys():
        item_is(OBS_ID.get(key), OBS_ITEM.get(key))
    for key in FA_ITEM.keys():
        item_is(FA_OBJ.get(key), FA_ITEM.get(key))
    for key in waterfall.ITEM.keys():
        item_is(waterfall.ITEM.get(key).id, waterfall.ITEM.get(key).name)


test('every exact item id has the name its quest expects', exact_items)


def exact_locs():
    loc_is(MC_LOC.CRATE, 'Crate')
    loc_is(MC_LOC.CAVE, 'Cave Entrance')
    loc_is(MC_LOC.MUD_PILE, 'Mud pile')
    for id in range(MC_LOC.RAILING_FIRST, MC_LOC.RAILING_LAST + 1):
        loc_is(id, 'Railing')
    loc_is(FURNACE_LOC, 'Furnace')
    for id in GATE_LOC:
        loc_is(id, 'Gate')
    for key, name in [['BALLISTA', 'Ballista'], ['CHEST_SHUT', 'Closed chest'], ['CHEST_OPEN', 'Open chest'], ['FRONT_DOOR', 'Door'],
                      ['CRUMBLED_WALL', 'Crumbled wall'], ['INNER_DOOR', 'Door'], ['LADDER_UP', 'Ladder'], ['LADDER_DOWN', 'Ladder']]:
        loc_is(TG_LOC.get(key), name)
    for id, name in [[SC_ID.SECRET_WALL, 'Old wall'], [SC_ID.DEEP_GATE, 'Gate'], [SC_ID.JAIL_DOOR, 'Door'], [SC_ID.MONASTERY_LADDER, 'Ladder']]:
        loc_is(id, name)
    for key, name in [['RECEPTION_LADDER', OBS_LOC_NAME.LADDER], ['KEY_CHEST_SHUT', OBS_LOC_NAME.CHEST], ['KEY_CHEST_OPEN', OBS_LOC_NAME.CHEST],
                      ['GATE_RIGHT', OBS_LOC_NAME.GATE], ['GATE_LEFT', OBS_LOC_NAME.GATE], ['SACK', OBS_LOC_NAME.SACK], ['TELESCOPE', OBS_LOC_NAME.TELESCOPE]]:
        loc_is(OBS_LOC.get(key), name)
    loc_is(FA_LOC.DOOR1, 'Door')
    loc_is(FA_LOC.DOOR2, 'Door')
    loc_is(FA_LOC.JEREMY_DOOR, 'Prison Door')
    for key, name in [['RAFT', 'Log raft'], ['BOOKCASE', 'Bookcase'], ['GOLRIE_CRATE', 'Crate'], ['GOLRIE_GATE', 'Door'], ['TOMBSTONE', 'Tombstone of glarial'],
                      ['CHEST_CLOSED', 'Closed chest'], ['CHEST_OPEN', 'Open chest'], ['COFFIN', 'Tomb of glarial'], ['CROSSING_ROCK', 'Rock'],
                      ['BAXTORIAN_CRATE', 'Crate'], ['ENTRY_DOOR', 'Door'], ['KEYED_DOOR', 'Door'], ['PILLAR', 'Pillar'], ['GLARIAL_STATUE', 'Statue of Glarial'],
                      ['CHALICE', 'Chalice of eternity'], ['BARREL', 'Barrel']]:
        loc_is(waterfall.LOC.get(key), name)
    for id, name in [[lostcity.SHAMUS_TREE_ID, 'Tree'], [lostcity.DRAMEN_TREE_ID, 'Dramen tree'], [lostcity.MAGIC_DOOR_ID, 'Magic door'], [2406, 'Door'], [1172, 'Fungus']]:
        loc_is(id, name)


test('every exact loc id is the loc its quest drives', exact_locs)


def exact_npcs():
    for id in SCORPION_NPC.values():
        npc_is(id, 'Kharid Scorpion')
    for key, name in [['GUARD1', 'Khazard Guard'], ['DRUNK_GUARD', 'Khazard Guard'], ['KHAZARD', 'General Khazard'], ['BARMAN', 'Khazard barman'],
                      ['HENGRAD', 'Hengrad'], ['LADY_SERVIL', 'Lady Servil'], ['JEREMY_CELL', 'Jeremy Servil'], ['JEREMY_ARENA', 'Jeremy Servil'],
                      ['JUSTIN', 'Justin Servil'], ['BOUNCER', 'Bouncer'], ['OGRE', 'Khazard Ogre'], ['SCORPION', 'Khazard Scorpion']]:
        npc_is(FA_NPC.get(key), name)
    for id, name in [[lostcity.SHAMUS_ID, 'Shamus'], [lostcity.ENTRANA_ZOMBIE_ID, 'Zombie'], [655, 'Tree spirit'], [477, TG_NPC.WARLORD], [478, TG_NPC.COMMANDER]]:
        npc_is(id, name)


test('every exact NPC id is the NPC its quest fights or talks to', exact_npcs)


def named_targets():
    npc_names = ['Dwarf Commander', 'Dwarf youngster', 'Nulodion', 'Councillor Halgrive', 'Doctor Orbon', 'Abbot Langley', 'Seer',
                 'Thormac', 'Velrak the explorer', 'Jailer', 'Observatory professor', 'Goblin guard', 'Lady Servil', 'Khazard barman',
                 'Almera', 'Hudon', 'Golrie', 'Betty', 'Aemad', 'Man', 'Kebab seller', 'Shop keeper', 'Wydin', 'Bob', 'King Arthur',
                 'Sir Gawain', 'Sir Lancelot', 'Sir Mordred', 'The Lady of the Lake', 'Candle maker', 'Beggar', 'Giant bat', 'Merlin',
                 merlinscrystal.THRANTAX, 'Warrior', 'Shamus', 'Monk of Entrana', 'Cave monk']
    npc_names += [sheep_name(n) for n in [1, 2, 3, 4]] + [TG_NPC.get(key) for key in TG_NPC.keys()]
    expect([name for name in npc_names if len(reader.npc_ids(name)) == 0]).to_equal([])
    loc_names = ['Cave Entrance', 'Mud pile', 'Ladder', 'Tree', 'Beehive', 'Chaos altar', 'Crate', 'Door', 'Gangplank', 'Giant crystal',
                 'Large door', 'Staircase', OBS_LOC_NAME.RANGE, OBS_LOC_NAME.FURNACE]
    expect([name for name in loc_names if len(reader.loc_ids(name)) == 0]).to_equal([])
    item_names = [merlinscrystal.EXCALIBUR, merlinscrystal.UNLIT_CANDLE, merlinscrystal.LIT_CANDLE, merlinscrystal.BAT_BONES, merlinscrystal.WAX,
                 merlinscrystal.BUCKET, merlinscrystal.REPELLENT, merlinscrystal.BREAD, merlinscrystal.TINDERBOX, merlinscrystal.WEAPON,
                  lostcity.KNIFE, lostcity.BRANCH, lostcity.STAFF, SC_ITEM.ANTIPOISON, 'Iron axe', 'Bronze axe']
    for id in QUESTS:
        item_names += [item.name for item in def_by_id(id).record.items]
    expect([name for name in item_names if len(reader.item_ids(name)) == 0]).to_equal([])


test('every name a quest finds an NPC, loc or item by exists in the cache', named_targets)
