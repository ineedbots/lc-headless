"""Check phase 17h's quests against the real cache: every exact id a module looks up has the name it expects, every loc it
clicks by id offers the op it clicks, every name it finds things by exists, and the routes baked from rs2b0t's collision
pack hold on this client's own map."""

from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_LOC, RG_NPC, RG_TILE
from rs2004.quests.defs.regicide.bomb import RANGE_LOC, STILL_LABELS, STILL_ROOT
from rs2004.quests.defs.regicide.pockets import pocket_at
from rs2004.quests.defs.regicide.seams import REGICIDE_SEAMS
from rs2004.quests.defs.regicide.supplies import BOW_LEVELS, usable_bows
from rs2004.quests.defs.upass.areas import PLATFORM_LINKS, CAVERN_LINKS, UP_ITEM, UP_LOC, UP_NPC, UP_TILE
from rs2004.quests.defs.upass.route import UPASS_AREAS, UPASS_CROSSINGS
from rs2004.quests.defs.upass.supplies import BOW_IDS

QUESTS = ['upass', 'regicide']


def item_name(id):
    found = reader.item_type(id)
    return found.name if found is not None else None


def loc_name(id):
    found = reader.loc_type(id)
    return found.name if found is not None else None


def npc_name(id):
    found = reader.npc_type(id)
    return found.name if found is not None else None


def without_op(pairs):
    """The (id, op) of each loc that doesn't offer the op its quest clicks."""
    missing = []
    for id, op in pairs:
        found = reader.loc_type(id)
        ops = [] if found is None else [o.lower() for o in found.ops if o is not None]
        if op.lower() not in ops:
            missing.append([id, op, None if found is None else found.ops])
    return missing


def exact_items():
    pairs = [UP_ITEM.get(key) for key in UP_ITEM.keys()] + [RG_ITEM.get(key) for key in RG_ITEM.keys()]
    expect([[item.id, item.name, item_name(item.id)] for item in pairs if item_name(item.id) != item.name]).to_equal([])


test('every exact item id is the item its quest looks for', exact_items)


def thirteen_bows():
    # Why: upass_bridge.rs2's weapon_bow category: a crossbow must not qualify, and the shot needs a bow of each tier.
    named = sorted([item_name(id) for id in BOW_IDS])
    expect(len(named)).to_be(13)
    expect('Crossbow' in named).to_be(False)
    expect('Ogre bow' in named).to_be(True)
    expect(50 in [BOW_LEVELS[key] for key in BOW_LEVELS]).to_be(True)
    expect(841 in usable_bows(1)).to_be(True)
    expect(861 in usable_bows(49)).to_be(False)


test('the bow list is the bridge rope script category', thirteen_bows)


def exact_npcs():
    names = {'KOFTIK_SURFACE': 'Koftik', 'KOFTIK_BRIDGE': 'Koftik', 'KOFTIK_GRID': 'Koftik', 'KOFTIK_INSANE': 'Koftik', 'KOFTIK_LAST': 'Koftik', 'NILHOOF': 'Nilhoof',
             'KLANK': 'Klank', 'KAMEN': 'Kamen', 'KALRAG': 'Kalrag', 'OTHAINIAN': 'Othainian', 'DOOMION': 'Doomion', 'HOLTHION': 'Holthion',
             'DISCIPLE': 'Iban disciple', 'IBAN': 'Lord Iban', 'WITCH': 'Kardia', 'WITCH_CAT': 'Witches cat'}
    expect([[key, name, npc_name(UP_NPC.get(key))] for key, name in names.items() if npc_name(UP_NPC.get(key)) != name]).to_equal([])
    expect([key for key in UP_NPC.keys() if npc_name(UP_NPC.get(key)) is None]).to_equal([])
    expect([key for key in RG_NPC.keys() if npc_name(RG_NPC.get(key)) is None]).to_equal([])
    expect(npc_name(RG_NPC.LAZY_GUARD)).to_be('Tyras guard')
    expect(npc_name(RG_NPC.ARIANWYN)).to_be('Arianwyn')
    expect(npc_name(RG_NPC.RABBIT)).to_be('Rabbit')


test('every exact NPC id is the NPC its quest talks to or fights', exact_npcs)


def exact_locs():
    ops = [[UP_LOC.CAVE_ENTRANCE, 'Enter'], [UP_LOC.GUIDEROPE, 'Fire-at'], [UP_LOC.GRID_HANDHOLDS, 'Climb'], [UP_LOC.PORTCULLIS_LEVER, 'Pull'],
           [UP_LOC.ROCKSLIDE, 'Climb-over'], [UP_LOC.ROCK_BRIDGE, 'Cross'], [UP_LOC.LEDGE, 'Cross'], [UP_LOC.PIPE_AREA1, 'Squeeze-through'],
           [UP_LOC.PIPE_AREA2, 'Squeeze-through'], [UP_LOC.COLLAPSED_A, 'Cross'], [UP_LOC.COLLAPSED_B, 'Cross'], [UP_LOC.ROCKSWING_BACK, 'Swing-on'],
           [UP_LOC.UNICORN_DOOR_L, 'Pass-through'], [UP_LOC.UNICORN_DOOR_R, 'Pass-through'], [UP_LOC.RAILINGS_LOCKED, 'Pick-lock'],
           [UP_LOC.RAILINGS_HARD, 'Pick-lock'], [UP_LOC.RAILINGS_LOOSE, 'Search'], [UP_LOC.WALL_DOOR_L, 'Open'], [UP_LOC.WALL_DOOR_R, 'Open'],
           [UP_LOC.SPEARTRAP, 'Search'], [UP_LOC.SPRINGTRAP, 'Search'], [UP_LOC.LOGTRAP_TRIGGER, 'Search'], [UP_LOC.TABLET_EAST, 'Read'],
           [UP_LOC.TABLET_WEST, 'Read'], [UP_LOC.WITCH_DOOR, 'Open'], [UP_LOC.WITCH_DOOR, 'Knock'], [UP_LOC.WITCH_CHEST, 'Open'],
           [UP_LOC.WITCH_CHEST_OPEN, 'Search'],
           [RG_LOC.WELL_OF_VOYAGE, 'Climb-down'], [RG_LOC.TEMPLE_EXIT, 'Exit'], [RG_LOC.FOOTPRINTS, 'Follow'], [RG_LOC.SULPHUR1, 'Take'],
           [RG_LOC.SULPHUR2, 'Take'], [RG_LOC.SULPHUR3, 'Take'], [3998, 'Enter'], [3927, 'Climb']]
    ops += [[seam.loc_id, seam.op] for seam in REGICIDE_SEAMS]
    # Why: the rope swing and the spade dig are item uses, whose ops in the table are only labels.
    ops += [[edge.loc, edge.op] for edge in UPASS_CROSSINGS if not edge.op.startswith('use ')]
    expect(without_op(ops)).to_equal([])
    expect([key for key in UP_LOC.keys() if loc_name(UP_LOC.get(key)) is None]).to_equal([])
    expect([key for key in RG_LOC.keys() if loc_name(RG_LOC.get(key)) is None]).to_equal([])
    expect(loc_name(UP_LOC.WITCH_CHEST)).to_be('Chest')
    expect(loc_name(RANGE_LOC)).to_be('Range')


test('every exact loc id is the loc its quest drives, offering the op it clicks', exact_locs)


def still_labels():
    # Why: interface.pack's ids are the server's, so the still's buttons are only ever found by their labels.
    missing = [key for key, label in STILL_LABELS.items() if key != 'close' and reader.button_by_text(STILL_ROOT, label) == -1]
    expect(missing).to_equal([])


test("the still's interface carries every label the control law presses", still_labels)


def named_targets():
    npc_names = ['King Lathas', 'Aemad', 'Lowe', 'Jatix', 'Hickton', 'Kings messenger', 'Lord Iorwerth', 'Elf Tracker']
    expect([name for name in npc_names if len(reader.npc_ids(name)) == 0]).to_equal([])
    item_names = []
    for id in QUESTS:
        item_names += [item.name for item in def_by_id(id).record.items]
    expect([name for name in item_names if len(reader.item_ids(name)) == 0]).to_equal([])


test('every name a quest finds an NPC or item by exists in the cache', named_targets)


def route(a, b):
    return navigator.find_path(a, b, max_expansions=400000, policy={'use_teleports': False}).ok


def anchor_of(area):
    return [row.anchor for row in UPASS_AREAS if row.area == area][0]


def stands_hold():
    wrong = [[edge.loc, edge.from_, str(edge.stand)] for edge in UPASS_CROSSINGS if not route(edge.stand, anchor_of(edge.from_))]
    expect(wrong).to_equal([])


test('every crossing of the pass stands in the pocket the table says it leaves', stands_hold)


def landings_hold():
    wrong = [[edge.loc, edge.to, str(edge.lands)] for edge in UPASS_CROSSINGS if not route(edge.lands, anchor_of(edge.to))]
    expect(wrong).to_equal([])


test('every crossing of the pass lands in the pocket the table says it enters', landings_hold)


def links_hold():
    # Why: only each side's own bridge is checked; a side reaching its bridge's far side would mean the pockets are one.
    wrong = []
    for link in list(PLATFORM_LINKS) + list(CAVERN_LINKS):
        if route(link.a.tile, link.b.tile):
            wrong.append(str(link.bridge))
    expect(wrong).to_equal([])


test('a collapsed bridge joins two pockets no walk joins', links_hold)


def forest_holds():
    wrong = []
    for seam in REGICIDE_SEAMS:
        for side in seam.sides:
            if side.pocket != 'ardougne' and pocket_at(Tile(side.stand.x, side.stand.z, 0)) != side.pocket:
                wrong.append([seam.loc, side.pocket])
    expect(wrong).to_equal([])
    expect(pocket_at(RG_TILE.ISAFDAR_ENTRY)).to_be('isafdar-entry')


test('the forest seam stands hold on the pockets they name', forest_holds)
