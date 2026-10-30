"""Check members quest gathering supplies and targets against the real 289 cache."""
from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.druidicritual import RITUAL_MEATS, CAULDRON_ID, SUIT_OF_ARMOUR_ID
from rs2004.quests.defs.monksfriend import AXES, BLANKET_OBJ, JUG_OBJ, JUG_WATER_OBJ, SINK_LOC
from rs2004.quests.defs.gertrudescat import FLUFFS_OBJ, CAT_NPC, CRATE_NPC
from rs2004.quests.defs.junglepotion import JUNGLE_HERBS
from rs2004.quests.defs.clocktower import COG_OBJ, SPINDLE_LOC, RAT_POISON_OBJ
from rs2004.quests.defs.hazeelcult import ARMOUR_OBJ, VALVES, RAFT_LOC, CUPBOARD_SHUT, CUPBOARD_OPEN


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
    for name in ['Kaqemeex', 'Sanfew', 'Brother Omad', 'Brother Cedric', 'Shop keeper', 'Kortan',
                 'Gertrude', 'Shilop', 'Wilough', 'Gerrant', 'Cow', 'Trufitus', 'Brother Kojo',
                 'Ceril Carnillean', 'Clivet', 'Alomone']:
        expect(len(reader.npc_ids(name)), name).to_be_greater_than(0)
    for name in ['Ladder', 'Prison door', 'Tree', 'Sink', 'Well', 'Clock spindle', 'Food trough',
                 'Sewer valve', 'Raft', 'Cupboard', 'Cave entrance', 'Stairs', 'Rocks', 'Hand holds']:
        expect(len(reader.loc_ids(name)), name).to_be_greater_than(0)
    for name in AXES + ['Logs', 'Coins', 'Doogle leaves', 'Raw sardine', 'Bucket', 'Bucket of milk',
                        'Bucket of water', 'Rat poison', 'Carnillean armour']:
        expect(len(reader.item_ids(name)), name).to_be_greater_than(0)
    for id in ['druid', 'drunkmonk', 'fluffs', 'junglepotion', 'cog', 'hazeelcult']:
        for item in def_by_id(id).record.items:
            expect(len(reader.item_ids(item.name)), item.name).to_be_greater_than(0)


test('every named target and record item exists in the cache', named_targets)


def new_exact_targets():
    for key, name in [['doogle_leaves', 'Doogle leaves'], ['raw_sardine', 'Raw sardine'],
                      ['seasoned_sardine', 'Seasoned sardine'], ['bucket_of_milk', 'Bucket of milk'],
                      ['kitten', "Fluffs' kitten"]]:
        expect(reader.item_type(getattr(FLUFFS_OBJ, key)).name).to_be(name)
    expect(reader.npc_type(CAT_NPC).name).to_be('Gertrudes cat')
    expect(reader.npc_type(CRATE_NPC).name).to_be('Crate')
    for herb in JUNGLE_HERBS:
        expect(reader.item_type(herb.id).name).to_be(herb.name)
        expect(reader.item_type(herb.unid_id).name).to_be('Unidentified herb')
        expect(len(reader.loc_ids(herb.loc)), herb.loc).to_be_greater_than(0)
    for id in COG_OBJ._fields.values():
        expect(reader.item_type(id).name).to_be('Cog')
    for id in SPINDLE_LOC.values():
        expect(reader.loc_type(id).name).to_be('Clock spindle')
    expect(reader.item_type(RAT_POISON_OBJ).name).to_be('Rat poison')
    expect(reader.item_type(ARMOUR_OBJ).name).to_be('Carnillean armour')
    for valve in VALVES:
        expect(reader.loc_type(valve.id).name).to_be('Sewer valve')
    expect(reader.loc_type(RAFT_LOC).name).to_be('Raft')
    for id in [CUPBOARD_SHUT, CUPBOARD_OPEN]:
        expect(reader.loc_type(id).name).to_be('Cupboard')


test('cat, herb, cog and armour ids match their rendered cache names', new_exact_targets)
