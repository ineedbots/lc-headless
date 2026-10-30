"""Check free-to-play quest item, NPC and loc names against the real 289 cache."""
from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.ernest.areas import EC_ID, EC_NAME
from rs2004.quests.defs.knightssword.areas import KS_ID, KS_NAME
from rs2004.quests.defs.piratestreasure.areas import PT_ID, PT_NAME
from rs2004.quests.defs.princeali.areas import PA_ITEM, PA_LOC, PA_NPC

def exact_items():
    for ids, names in [[EC_ID, EC_NAME], [KS_ID, KS_NAME], [PT_ID, PT_NAME]]:
        for key in names.keys():
            if key == 'GARDENER':
                continue
            id = ids.get(key)
            if id is not None:
                expect(reader.item_type(id).name).to_be(names.get(key))
    for item in PA_ITEM._fields.values():
        expect(reader.item_type(item.id).name).to_be(item.name)
test('each exact item id has the name its quest uses', exact_items)

NAMES = {'npc': ['Aggie', 'Bartender', 'Captain Rovin', 'Delrith', 'Doric', 'Dr Harlow', 'General Wartface', 'Goblin', 'Gypsy', 'Hassan', 'Joe', 'Kebab seller', 'Lady Keli', 'Leela', 'Luthas', 'Man', 'Morgan', 'Ned', 'Osman', 'Professor Oddenstein', 'Redbeard Frank', 'Reldo', 'Shantay', 'Shop keeper', 'Sir Prysin', 'Sir Vyvin', 'Squire', 'Thessalia', 'Thurgo', 'Traiborn', 'Veronica', 'Weakened Delrith', 'Wizard Mizgog', 'Wydin', 'Wyson the gardener', 'Zambo'], 'loc': ['Chest', 'Compost heap', 'Crate', 'Cupboard', 'Door', 'Drain', 'Fountain', 'Furnace', 'Lever A', 'Lever B', 'Lever C', 'Lever D', 'Lever E', 'Lever F', 'Manhole', 'Onion', 'Range', 'Sink', 'Staircase', 'Stairs'], 'item': ['Blue dye', 'Bones', 'Bronze pickaxe', 'Bucket', 'Bucket of water', 'Coins', 'Goblin mail', 'Onion', 'Orange dye', 'Red dye', 'Redberries', 'Silverlight', 'Woad leaf', 'Yellow dye']}

def named_targets():
    for kind in NAMES:
        lookup = reader.npc_ids if kind == 'npc' else (reader.loc_ids if kind == 'loc' else reader.item_ids)
        for name in NAMES[kind]:
            expect(len(lookup(name)), kind + ': ' + name).to_be_greater_than(0)
    for id in ['demon','doric','gobdip','imp','vampire','haunted','squire','hunt','prince']:
        for item in def_by_id(id).record.items:
            expect(len(reader.item_ids(item.name)), id + ': ' + item.name).to_be_greater_than(0)
test('every named target and record item exists in the cache', named_targets)


def exact_targets():
    for id, name in [[2071,'Crate'],[2072,'Crate'],[2079,'Chest'],[2612,'Cupboard'],[2613,'Cupboard'],[2614,'Coffin']]:
        expect(reader.loc_type(id).name).to_be(name)
    expect(reader.npc_type(1217).name).to_be('Gardener')
    expect(reader.npc_type(757).name).to_be('Count Draynor')
    for id in [2399,2400,2401]:
        expect(reader.item_type(id).name).to_be('Key')
    for name in PA_LOC._fields.values():
        expect(len(reader.loc_ids(name))).to_be_greater_than(0)
    for name in PA_NPC._fields.values():
        expect(len(reader.npc_ids(name))).to_be_greater_than(0)
test('same-name targets and quest keys use the correct cache ids', exact_targets)
