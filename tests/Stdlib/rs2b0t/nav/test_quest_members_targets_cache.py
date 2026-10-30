"""Check members quest targets and both gathering bots against the real cache."""
import _core
from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.witchshouse.areas import WH_OBJ, WH_NAME, WH_LOC, EXPERIMENT_IDS, EXPERIMENT_NAMES
from rs2004.quests.defs.fishingcontest.areas import FC_ID, RED_VINE_LOCS, FC_NPC
from rs2004.quests.defs.murder.areas import SUSPECTS, MURDER_EVIDENCE
from rs2004.quests.defs.seaslug.areas import SS_OBJ, SS_ITEM


def items():
    for key, name in WH_NAME._fields.items():
        expect(reader.item_type(getattr(WH_OBJ, key)).name).to_be(name)
    for id, name in [[25, 'Red vine worm'], [26, 'Fishing trophy'], [27, 'Fishing pass'],
                     [307, 'Fishing rod'], [327, 'Raw sardine'], [338, 'Raw giant carp'],
                     [1857, 'Totem'], [1858, 'Address label'], [2944, 'Golden key'], [2945, 'Iron key']]:
        expect(reader.item_type(id).name).to_be(name)
    for key, name in SS_ITEM._fields.items():
        expect(reader.item_type(getattr(SS_OBJ, key)).name).to_be(name)
    for id in [SS_OBJ.TORCH_LIT, SS_OBJ.TORCH_UNLIT]:
        expect(reader.item_type(id).name).to_be('Torch')
    for item in MURDER_EVIDENCE:
        expect(len(reader.item_type(item.id).name)).to_be_greater_than(0)
    for id in ['ball', 'fishingcompo', 'murder', 'seaslug', 'priestperil', 'totem']:
        for item in def_by_id(id).record.items:
            expect(len(reader.item_ids(item.name)), item.name).to_be_greater_than(0)


test('quest tools, evidence and torches match their exact cache ids', items)


def targets():
    for id, name in zip(EXPERIMENT_IDS, EXPERIMENT_NAMES):
        expect(reader.npc_type(id).name).to_be(name)
    for id in FC_NPC._fields.values():
        expect(reader.npc_type(id).name).to_be('Fishing spot')
    expect(reader.npc_type(1046).name).to_be('Monk of Zamorak')
    for id in RED_VINE_LOCS:
        expect(reader.loc_type(id).name).to_be('Vine')
    for suspect in SUSPECTS:
        expect(len(reader.npc_ids(suspect.stop.npc))).to_be_greater_than(0)
        for loc in [suspect.barrel, suspect.poison]:
            expect(reader.loc_type(loc.id).name).to_be(loc.name)
    for name in ['Boy', 'Wydin', 'Thessalia', 'Harry', 'Mountain Dwarf', 'Bonzo', 'Arhein', 'Poison Salesman',
                 'Caroline', 'Holgart', 'Bailey', 'Kent', 'King Roald', 'Drezel', 'Temple guardian', 'Aubury',
                 'Kangai Mau', 'Wizard Cromperty', 'RPDT employee']:
        expect(len(reader.npc_ids(name)), name).to_be_greater_than(0)
    for name in ['Potted plant', 'Cupboard', 'Fountain', 'Smashed window', 'Barrel of flour', 'Sacks',
                 'Large door', 'Cell door', 'Coffin', 'Gate', 'Well', 'Monument', 'Rune Essence', 'Portal', 'Crate', 'Stairs', 'Chest']:
        expect(len(reader.loc_ids(name)), name).to_be_greater_than(0)


test('quest creatures, shops, herbs, evidence and puzzle targets exist in the cache', targets)


def garden_corridor():
    # rs2b0t's witchshouse-patrol.test.ts checks its collision.lcnav.gz here (MIT, see thirdparty/rs2b0t).
    from rs2004.quests.defs.witchshouse.patrol import garden_legs, GARDEN_ENTRY, FOUNTAIN_STAND
    for leg in garden_legs(GARDEN_ENTRY, FOUNTAIN_STAND):
        for tile in leg:
            found = _core.walk_tile(tile.x, tile.z, tile.level)
            expect(found is not None, str(tile)).to_be(True)
            expect(found[0], str(tile)).to_be(1)


test('every planned witch garden corridor tile is walkable in the native map', garden_corridor)
