"""Phase 16c's exact items, NPCs and objects against the real revision-289 cache."""
from rs2004.quests.defs.dragonslayer.areas import DS_ID, DS_ITEM
from rs2004.quests.defs.dragonslayer.maze import MAZE_NPC
from rs2004.quests.defs.shieldofarrav.areas import SOA_ID, SOA_LOC
from rs2004.quests.barcrawl.barcrawl_logic import BARS, BARBARIAN_GUARD_ID


def items():
    for key in DS_ITEM.keys():
        id = DS_ID.get(key)
        if id is not None:
            expect(reader.item_type(id).name).to_be(DS_ITEM.get(key))
    for id, name in [[757,'Book'],[759,'Key'],[761,'Scroll'],[763,'Broken shield'],[765,'Broken shield'],[767,'Phoenix crossbow'],[769,'Certificate']]:
        expect(reader.item_type(id).name).to_be(name)


test('exact item ids match the names used in interactions', items)


def targets():
    for id, name in [[748,'Giant rat'],[749,'Ghost'],[750,'Skeleton'],[751,'Zombie'],[752,'Lesser demon'],[753,'Melzar the mad'],[643,'Weaponsmaster'],[644,'Straven'],[645,'Jonny the beard'],[BARBARIAN_GUARD_ID,'Barbarian guard']]:
        expect(reader.npc_type(id).name).to_be(name)
    for bar in BARS:
        expect(reader.npc_type(bar.id).name).to_be(bar.npc)
    for id in [SOA_LOC.PHOENIX_DOOR, SOA_LOC.STORE_DOOR, SOA_LOC.BLACKARM_DOOR]:
        expect(reader.loc_type(id).name).to_be('Door')


test('exact combat, bartender and door targets exist', targets)
