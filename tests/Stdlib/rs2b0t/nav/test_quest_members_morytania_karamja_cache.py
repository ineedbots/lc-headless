"""Check phase 17d's quests against the real cache: every exact id a module looks up has the name it expects, and
every name it finds an NPC, loc or item by exists."""

from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.druidspirit.areas import BOB, DOMMIK, DREZEL, FILLIMAN, NATURE_SPIRIT, NS_ID, NS_LOC, NS_NAME, URHNEY
from rs2004.quests.defs.mortton.areas import SM_ID, SM_LOC, SM_LOC_ID, SM_NAME, SM_NPC, SM_NPC_ID, VARROCK_GENERAL
from rs2004.quests.defs.mortton.supplies import PERM_SERUM_BY_DOSE, SERUM_BY_DOSE
from rs2004.quests.defs.shilo.areas import SV_ITEM, SV_LOC, SV_NPC
from rs2004.quests.defs.tbwt.areas import TB_ARROWS, TB_BOWS, TB_ID, TB_LOC, TB_NAME, TB_NPC, TB_POTIONS, TB_SPEARS

QUESTS = ['druidspirit', 'mortton', 'tbwt', 'zombiequeen']


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


def shared_keys(ids, names):
    return [[ids.get(key), names.get(key)] for key in names.keys() if ids.get(key) is not None]


def exact_items():
    pairs = shared_keys(NS_ID, NS_NAME) + [[NS_ID.POUCH_EMPTY, NS_NAME.POUCH]]
    pairs += shared_keys(SM_ID, SM_NAME)
    pairs += [[id, f'Serum 207 ({dose})'] for id, dose in SERUM_BY_DOSE]
    pairs += [[id, f'Serum 207(p) ({dose})'] for id, dose in PERM_SERUM_BY_DOSE]
    pairs += shared_keys(TB_ID, TB_NAME)
    pairs += [[spear.id, spear.name] for spear in TB_SPEARS] + [[spear.kp_id, spear.kp_name] for spear in TB_SPEARS]
    pairs += [[potion.id, potion.name] for potion in TB_POTIONS]
    pairs += [[SV_ITEM.get(key).id, SV_ITEM.get(key).name] for key in SV_ITEM.keys()]
    expect(mismatches(pairs, item_name)).to_equal([])


test('every exact item id has the name its quest expects', exact_items)


def exact_locs():
    pairs = [[SM_LOC_ID.SHELF, SM_LOC.SHELF], [SM_LOC_ID.TABLE, SM_LOC.TABLE], [SM_LOC_ID.SINK, SM_LOC.SINK],
             [SM_LOC_ID.ALTAR_LIT, SM_LOC.ALTAR_LIT], [SM_LOC_ID.ALTAR_UNLIT, SM_LOC.ALTAR_UNLIT],
             [SM_LOC_ID.ALTAR_BROKEN, SM_LOC.ALTAR_BROKEN], [SM_LOC_ID.PYRE_EMPTY, SM_LOC.PYRE],
             [SM_LOC_ID.PYRE_LOGS, SM_LOC.PYRE], [SM_LOC_ID.PYRE_BONES, SM_LOC.PYRE]]
    # A piece at level 0 is the broken wall the temple starts as; every level after it is a temple wall.
    for base, done in [[SM_LOC_ID.WALL_BASE, SM_LOC_ID.WALL_DONE], [SM_LOC_ID.CORNER_BASE, SM_LOC_ID.CORNER_DONE]]:
        pairs.append([base, SM_LOC.BROKEN_WALL])
        for id in range(base + 1, done + 1):
            pairs.append([id, SM_LOC.TEMPLE_WALL])
    expect(mismatches(pairs, loc_name)).to_equal([])


test('every exact loc id is the loc its quest drives', exact_locs)


def exact_npcs():
    expect(mismatches([[SM_NPC_ID.SHADOW, SM_NPC.SHADOW], [SM_NPC_ID.SHADE, SM_NPC.SHADE]], npc_name)).to_equal([])


test('every exact NPC id is the NPC its quest fights', exact_npcs)


def named_targets():
    npc_names = [stop.npc for stop in [DREZEL, URHNEY, FILLIMAN, NATURE_SPIRIT, DOMMIK, BOB, VARROCK_GENERAL]] + ['Ghast']
    npc_names += [SM_NPC.get(key) for key in SM_NPC.keys()]
    npc_names += [TB_NPC.get(key) for key in TB_NPC.keys()]
    npc_names += [SV_NPC.get(key) for key in SV_NPC.keys()]
    expect([name for name in npc_names if len(reader.npc_ids(name)) == 0]).to_equal([])
    loc_names = [NS_LOC.get(key) for key in NS_LOC.keys()] + [SM_LOC.get(key) for key in SM_LOC.keys()]
    loc_names += [TB_LOC.get(key) for key in TB_LOC.keys()] + [SV_LOC.get(key) for key in SV_LOC.keys()] + ['Anvil', 'Trapdoor', 'Ladder']
    expect([name for name in loc_names if len(reader.loc_ids(name)) == 0]).to_equal([])
    item_names = [bow.name for bow in TB_BOWS] + list(TB_ARROWS) + ['Bronze pickaxe', 'Lobster', 'Swordfish', 'Tuna']
    for id in QUESTS:
        item_names += [item.name for item in def_by_id(id).record.items]
    expect([name for name in item_names if len(reader.item_ids(name)) == 0]).to_equal([])


test('every name a quest finds an NPC, loc or item by exists in the cache', named_targets)
