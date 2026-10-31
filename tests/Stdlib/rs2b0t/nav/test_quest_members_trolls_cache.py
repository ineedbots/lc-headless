"""Check phase 17c's quests against the real cache: every exact id a module looks up has the name it expects, and
every name it finds an NPC, loc or item by exists."""

from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, BIO_LOC, BIO_NPC, SICK_MOURNER_ID
from rs2004.quests.defs.deathplateau.areas import DEATH_ITEM, HAROLD_DOOR
from rs2004.quests.defs.eadgar.areas import CHICKEN_NPC_ID, ER_ITEM, ER_LOC, ER_NPC, LIQUORS
from rs2004.quests.defs.eadgar.trollheim import FIRE_LOC
from rs2004.quests.defs.plaguecity.areas import PC_ITEM, PC_LOC, PC_NPC
from rs2004.quests.defs.trollstronghold.areas import COMBAT_FOODS, ITEM as TROLL_ITEM, PRAYER_POTIONS

QUESTS = ['death', 'troll', 'eadgar', 'elena', 'biohazard']


def item_is(id, name):
    expect(reader.item_type(id).name, str(id)).to_be(name)


def loc_is(id, name):
    found = reader.loc_type(id)
    expect(found.name if found is not None else None, str(id)).to_be(name)


def npc_is(id, name):
    found = reader.npc_type(id)
    expect(found.name if found is not None else None, str(id)).to_be(name)


def exact_items():
    for table in [PC_ITEM, BIO_ITEM, ER_ITEM, DEATH_ITEM]:
        for key in table.keys():
            item_is(table.get(key).id, table.get(key).name)
    for liquor in LIQUORS:
        item_is(liquor.id, liquor.name)


test('every exact item id has the name its quest expects', exact_items)


def exact_locs():
    for id in PC_LOC.MUD_PATCH:
        loc_is(id, 'Mud patch')
    for key, name in [['MUD_PILE', 'Mud pile'], ['SEWER_PIPE', 'Sewer pipe'], ['MANHOLE_SHUT', 'Manhole'], ['MANHOLE_OPEN', 'Manhole'],
                      ['CUPBOARD_SHUT', 'Cupboard'], ['CUPBOARD_OPEN', 'Cupboard'], ['REHNISON_DOOR', 'Door'], ['REHNISON_STAIRS_UP', 'Stairs'],
                      ['REHNISON_STAIRS_DOWN', 'Stairs'], ['PLAGUE_DOOR', 'Door'], ['BARREL', 'Barrel'], ['HOUSE_STAIRS_DOWN', 'Spooky stairs'],
                      ['HOUSE_STAIRS_UP', 'Spooky stairs'], ['ELENA_GATE', 'Door'], ['BRAVEK_DOOR', 'Door']]:
        loc_is(PC_LOC.get(key), name)
    for key, name in [['JERICO_CUPBOARD_SHUT', 'Cupboard'], ['JERICO_CUPBOARD_OPEN', 'Cupboard'], ['WATCHTOWER', 'Watchtower'], ['CAULDRON', 'Cauldron'],
                      ['NURSE_CUPBOARD_SHUT', 'Cupboard'], ['NURSE_CUPBOARD_OPEN', 'Cupboard'], ['HQ_DOOR', 'Door'], ['HQ_CRATE', 'Crate'], ['GUIDOR_DOOR', 'Door']]:
        loc_is(BIO_LOC.get(key), name)
    for id in BIO_LOC.VARROCK_GATE:
        loc_is(id, 'Gate')
    for key, name in [['AVIARY_HATCH', 'Aviary Hatch'], ['RACK', 'Rack'], ['KITCHEN_DRAWERS', 'Kitchen Drawers'], ['KITCHEN_DRAWERS_OPEN', 'Kitchen Drawers'],
                      ['STOREROOM_DOOR', 'Storeroom Door'], ['GOUTWEED_CRATE', 'Goutweed Crate'], ['CAVE_ENTRANCE', 'Cave Entrance'], ['CAVE_EXIT', 'Cave Exit']]:
        loc_is(ER_LOC.get(key), name)
    loc_is(HAROLD_DOOR.id, 'Door')
    loc_is(FIRE_LOC, 'Fire')


test('every exact loc id is the loc its quest drives', exact_locs)


def exact_npcs():
    npc_is(SICK_MOURNER_ID, BIO_NPC.MOURNER)
    npc_is(CHICKEN_NPC_ID, ER_NPC.CHICKEN)


test('every exact NPC id is the NPC its quest fights or talks to', exact_npcs)


def named_targets():
    npc_names = [PC_NPC.get(key) for key in PC_NPC.keys()] + [BIO_NPC.get(key) for key in BIO_NPC.keys()] + [ER_NPC.get(key) for key in ER_NPC.keys()]
    npc_names += ['Denulth', 'Eohric', 'Harold', 'Saba', 'Tenzing', 'Dunstan', 'Barman', 'Tostig', 'Dad', 'Troll General', 'Twig', 'Berry',
                  'Thrower Troll', 'Aemad', 'Jatix', 'Wydin', 'Heckel Funch', 'Gulluck', 'Wistan', 'Cow']
    expect([name for name in npc_names if len(reader.npc_ids(name)) == 0]).to_equal([])
    loc_names = ['Fountain', 'Stairs', 'Staircase', 'Cave Entrance', 'Cave Exit', 'Stone Mechanism', 'Arena Exit', 'Cell Door', 'Tree', 'Wheat', 'Door']
    expect([name for name in loc_names if len(reader.loc_ids(name)) == 0]).to_equal([])
    item_names = [TROLL_ITEM.get(key) for key in TROLL_ITEM.keys()] + list(COMBAT_FOODS) + list(PRAYER_POTIONS) + ['Lobster', 'Stone ball']
    for id in QUESTS:
        item_names += [item.name for item in def_by_id(id).record.items]
    expect([name for name in item_names if len(reader.item_ids(name)) == 0]).to_equal([])


test('every name a quest finds an NPC, loc or item by exists in the cache', named_targets)
