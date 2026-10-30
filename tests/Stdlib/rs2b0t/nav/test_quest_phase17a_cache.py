"""The first phase 17a quests' targets against the real 289 cache."""
from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.druidicritual import RITUAL_MEATS, CAULDRON_ID, SUIT_OF_ARMOUR_ID
from rs2004.quests.defs.monksfriend import AXES, BLANKET_OBJ, JUG_OBJ, JUG_WATER_OBJ, SINK_LOC


def exact_targets():
    for meat in RITUAL_MEATS:
        expect(reader.npc_type(meat.npc_id).name).to_be(meat.npc)
        for name in [meat.raw, meat.enchanted]:
            expect(len(reader.item_ids(name)), name).to_be_greater_than(0)
    expect(reader.npc_type(SUIT_OF_ARMOUR_ID).name).to_be('Suit of armour')
    expect(reader.loc_type(CAULDRON_ID).name).to_be('Cauldron of Thunder')
    expect(reader.loc_type(SINK_LOC).name).to_be('Sink')
    for id, name in [[BLANKET_OBJ, "Child's blanket"], [JUG_OBJ, 'Jug'], [JUG_WATER_OBJ, 'Jug of water']]:
        expect(reader.item_type(id).name).to_be(name)


test('ritual creatures, cauldron, blanket and water use the expected cache ids', exact_targets)


def named_targets():
    for name in ['Kaqemeex', 'Sanfew', 'Brother Omad', 'Brother Cedric', 'Shop keeper', 'Kortan']:
        expect(len(reader.npc_ids(name)), name).to_be_greater_than(0)
    for name in ['Ladder', 'Prison door', 'Tree', 'Sink']:
        expect(len(reader.loc_ids(name)), name).to_be_greater_than(0)
    for name in AXES + ['Logs', 'Coins']:
        expect(len(reader.item_ids(name)), name).to_be_greater_than(0)
    for id in ['druid', 'drunkmonk']:
        for item in def_by_id(id).record.items:
            expect(len(reader.item_ids(item.name)), item.name).to_be_greater_than(0)


test('every named target and record item exists in the cache', named_targets)
