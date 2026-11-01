"""Check phase 17g's quests against the real cache: every exact id a module looks up has the name it expects, every loc
it clicks by id offers the op it clicks, and every name it finds an NPC, loc or item by exists."""

from rs2004.quests.defs import def_by_id
from rs2004.quests.defs.fremenniktrials.areas import ASKELADDEN, BRUNDT, COUNCIL_WORKMAN, FISHERMAN, FT_ID, FT_LOC, LALLI, MANNI, MAZE_ROUTE, OLAF, PEER, POISON_SALESMAN, SAILOR, SIGLI, SIGMUND, SKULGRIMEN, SWENSEN, THORA, THORVALD, YRSA
from rs2004.quests.defs.fremenniktrials.supplies import COMBAT_FOODS
from rs2004.quests.defs.heroquest.areas import ACHIETTIES, ALFONSE, CHARLIE, GERRANT, GRIP, HERO_ID, HERO_LOC, HERO_NAMED, HERO_NPC, HERO_SHOP, KATRINE_TASK, STRAVEN_TASK, TROBERT, VELRAK
from rs2004.quests.defs.heroquest.feather import COMBAT_KIT
from rs2004.quests.defs.ikov.areas import GUARDIAN_STOP, IKOV_LOC, IKOV_NAME, IKOV_NPC, IKOV_OBJ, LUCIEN_START, WINELDA_STOP
from rs2004.quests.defs.ikov.gear import MELEE_WEAPONS, RANGED_SLOTS

QUESTS = ['hero', 'ikov', 'viking']


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
    pairs = [[HERO_ID.get(key), HERO_NAMED.get(key)] for key in HERO_NAMED.keys() if HERO_ID.get(key) is not None]
    pairs += [[HERO_ID.UNID_HARRALANDER, HERO_NAMED.UNID_HERB]]
    pairs += [[item.id, item.name] for item in COMBAT_KIT]
    pairs += [[IKOV_OBJ.get(key), IKOV_NAME.get(key)] for key in IKOV_NAME.keys() if IKOV_OBJ.get(key) is not None]
    pairs += [[IKOV_OBJ.UNLIT_CANDLE, IKOV_NAME.CANDLE]]
    expect(mismatches(pairs, item_name)).to_equal([])
    expect([key for key in FT_ID.keys() if item_name(FT_ID.get(key)) is None]).to_equal([])
    named = [[FT_ID.RAW_SHARK, 'Raw shark'], [FT_ID.KNIFE, 'Knife'], [FT_ID.CABBAGE, 'Cabbage'], [FT_ID.POTATO, 'Potato'], [FT_ID.ONION, 'Onion'],
             [FT_ID.PET_ROCK, 'Pet rock'], [FT_ID.LYRE, 'Lyre'], [FT_ID.FLOWER, 'Exotic flower'], [FT_ID.BALLAD, 'Fremennik ballad'], [FT_ID.STURDY_BOOTS, 'Sturdy boots'],
             [FT_ID.FISCAL_STATEMENT, 'Fiscal statement'], [FT_ID.HUNTERS_MAP, 'Hunters map'], [FT_ID.BOWSTRING, 'Custom bow string'], [FT_ID.UNUSUAL_FISH, 'Unusual fish'],
             [FT_ID.SEA_MAP, 'Sea fishing map'], [FT_ID.FORECAST, 'Weather forecast'], [FT_ID.WARRIORS_CONTRACT, "Warriors' contract"], [FT_ID.CHAMPIONS_TOKEN, 'Champions token'],
             [FT_ID.COCKTAIL, 'Legendary cocktail'], [FT_ID.PROMISSORY_NOTE, 'Promissory note']]
    expect(mismatches(named, item_name)).to_equal([])


test('every exact item id is the item its quest looks for', exact_items)


def exact_npcs():
    pairs = [[HERO_NPC.ACHIETTIES, 'Achietties'], [HERO_NPC.KATRINE, 'Katrine'], [HERO_NPC.STRAVEN, 'Straven'], [HERO_NPC.GRUBOR, 'Grubor'], [HERO_NPC.TROBERT, 'Trobert'],
             [HERO_NPC.ALFONSE, 'Alfonse the waiter'], [HERO_NPC.CHARLIE, 'Charlie the cook'], [HERO_NPC.GARV, 'Garv'], [HERO_NPC.GRIP, 'Grip'], [HERO_NPC.PIRATE_GUARD, 'Pirate Guard'],
             [HERO_NPC.ICE_QUEEN, 'Ice Queen'], [HERO_NPC.FIREBIRD, 'Entrana Fire Bird'], [HERO_NPC.CHAOS_DRUID, 'Chaos druid'], [HERO_NPC.LAVA_FISH, 'Fishing spot'], [HERO_NPC.JAILER, 'Jailer'],
             [HERO_NPC.VELRAK, 'Velrak the explorer'], [HERO_NPC.GERRANT, 'Gerrant'], [HERO_NPC.JATIX, 'Jatix'],
             [IKOV_NPC.HOBGOBLIN_UNARMED, 'Hobgoblin'], [IKOV_NPC.HOBGOBLIN_ARMED, 'Hobgoblin'], [IKOV_NPC.LUCIEN_HOSTILE, 'Lucien'], [IKOV_NPC.LUCIEN_QUESTGIVER, 'Lucien'],
             [IKOV_NPC.GUARDIAN_MALE, 'Guardian of Armadyl'], [IKOV_NPC.GUARDIAN_FEMALE, 'Guardian of Armadyl'], [IKOV_NPC.WINELDA, 'Winelda'], [IKOV_NPC.FIRE_WARRIOR, 'Fire Warrior of Lesarkus']]
    expect(mismatches(pairs, npc_name)).to_equal([])


test('every exact NPC id is the NPC its quest talks to or fights', exact_npcs)


def exact_locs():
    ops = [[HERO_LOC.GRUBOR_DOOR, 'Open'], [HERO_LOC.GARV_DOOR, 'Open'], [HERO_LOC.KITCHEN_DOOR, 'Open'], [HERO_LOC.KITCHEN_PANEL, 'Push'], [HERO_LOC.SIDE_DOOR, 'Open'], [HERO_LOC.TREASURE_DOOR, 'Open'],
           [HERO_LOC.CHEST_SHUT, 'Open'], [HERO_LOC.CHEST_OPEN, 'Search'], [HERO_LOC.CABINET_SHUT, 'Open'], [HERO_LOC.CABINET_OPEN, 'Search'], [HERO_LOC.JAIL_DOOR, 'Open'], [HERO_LOC.DEEP_GATE, 'Open'],
           [IKOV_LOC.TRAP_LEVER, 'Search for traps'], [IKOV_LOC.TRAP_LEVER, 'Pull'], [IKOV_LOC.MENDED_LEVER, 'Pull'], [IKOV_LOC.SOUTH_GATE_LEFT, 'Open'], [IKOV_LOC.SOUTH_GATE_RIGHT, 'Open'],
           [IKOV_LOC.FIREWARRIOR_DOOR, 'Open'], [IKOV_LOC.DARK_STAIRS_UP, 'Climb-up'], [IKOV_LOC.DARK_STAIRS_DOWN, 'Climb-down'], [IKOV_LOC.TRAP_LADDER, 'Climb-up'], [IKOV_LOC.CHEST_SHUT, 'Open'],
           [IKOV_LOC.CHEST_OPEN, 'Search'], [IKOV_LOC.YEW_TREE, 'Chop down'], [IKOV_LOC.SECRET_WALL, 'Push'], [IKOV_LOC.FLAX, 'Pick'],
           [FT_LOC.MUSICAL_TREE, 'Cut-branch'], [FT_LOC.MAZE_LADDER_TOP, 'Climb-down'], [FT_LOC.MAZE_EXIT, 'Climb-up'], [FT_LOC.BACKSTAGE_DOOR, 'Open'], [FT_LOC.PIPE, 'Put-inside'],
           [FT_LOC.SEER_UP_LADDER, 'Climb-up'], [FT_LOC.SEER_DOWN_LADDER, 'Climb-up'], [FT_LOC.SEER_DOOR1, 'Open'], [FT_LOC.SEER_CHEST_SHUT, 'Open'], [FT_LOC.SEER_CHEST_OPEN, 'Search'],
           [FT_LOC.BOOKCASE, 'Search'], [FT_LOC.TRAPDOOR_OPEN, 'Climb-down'], [FT_LOC.TRAPDOOR_SHUT, 'Open'], [FT_LOC.CUPBOARD_SHUT, 'Open'], [FT_LOC.CUPBOARD_OPEN, 'Search'],
           [FT_LOC.MURAL, 'Study'], [FT_LOC.UNICORN_HEAD, 'Study'], [FT_LOC.BULL_HEAD, 'Study'], [FT_LOC.WARRIOR_LADDER, 'Climb-down'], [FT_LOC.WARRIOR_LADDER_DOWN, 'Climb-down']]
    ops += [[hop.id, 'Use'] for hop in MAZE_ROUTE]
    expect(without_op(ops)).to_equal([])
    names = [[FT_LOC.LAKE_ALTAR, 'Strange altar'], [FT_LOC.TROLL_CAULDRON, "Lalli's Stew"], [FT_LOC.MAZE_PORTAL_1, 'Portal'], [FT_LOC.FROZEN_TABLE, 'Frozen table'], [FT_LOC.SCALES_CHEST, 'Chest'],
             [FT_LOC.RANGE, 'Cooking range'], [FT_LOC.DRAIN, 'Drain'], [FT_LOC.TAP, 'Tap'], [FT_LOC.MURAL, 'Abstract mural'], [FT_LOC.UNICORN_HEAD, "Unicorn's head"], [FT_LOC.BULL_HEAD, "Bull's head"],
             [HERO_LOC.TREASURE_DOOR, 'Door'], [HERO_LOC.KITCHEN_PANEL, 'Wall'], [HERO_LOC.DEEP_GATE, 'Gate']]
    expect(mismatches(names, loc_name)).to_equal([])
    expect([id for id in [IKOV_LOC.LEVER_BRACKET, IKOV_LOC.WEB, IKOV_LOC.FEAR_GATE_LEFT] if loc_name(id) is None]).to_equal([])


test('every exact loc id is the loc its quest drives, offering the op it clicks', exact_locs)


def named_targets():
    stops = [ACHIETTIES, KATRINE_TASK, STRAVEN_TASK, TROBERT, ALFONSE, CHARLIE, VELRAK, GERRANT, GRIP, LUCIEN_START, WINELDA_STOP, GUARDIAN_STOP]
    stops += [HERO_SHOP.get(key) for key in HERO_SHOP.keys()]
    stops += [stop([]) for stop in [BRUNDT, MANNI, THORA, OLAF, PEER, SIGLI, SIGMUND, SWENSEN, THORVALD, YRSA, SKULGRIMEN, FISHERMAN, SAILOR, ASKELADDEN, LALLI, COUNCIL_WORKMAN, POISON_SALESMAN]]
    npc_names = [stop.npc for stop in stops] + ['Monk of Entrana', 'Aemad', 'Arhein', 'Candle maker', 'Rufus', 'The Draugen', 'Koschei the deathless', 'Bartender', 'Olaf the Bard', 'Manni the Reveller', 'Lalli']
    expect([name for name in npc_names if len(reader.npc_ids(name)) == 0]).to_equal([])
    loc_names = ['Gangplank', 'Range', 'Door', 'Ladder', 'Spinning wheel', 'Chest', 'Cupboard', 'Pipe', 'Swaying tree', 'Escape rope', 'Cabbage', 'Potato', 'Onion']
    expect([name for name in loc_names if len(reader.loc_ids(name)) == 0]).to_equal([])
    # rs2b0t's weapon list is every tier by every kind, and no adamant warhammer exists.
    item_names = list(COMBAT_FOODS) + [w for w in MELEE_WEAPONS if w != 'Adamant warhammer'] + ['Beer', 'Strange object', 'Keg of beer', 'Bronze axe', 'Iron axe', 'Raw shark', 'Tinderbox', 'Knife', 'Coins', 'Bronze pickaxe']
    for slot in RANGED_SLOTS:
        item_names += slot
    for id in QUESTS:
        item_names += [item.name for item in def_by_id(id).record.items]
    expect([name for name in item_names if len(reader.item_ids(name)) == 0]).to_equal([])


test('every name a quest finds an NPC, loc or item by exists in the cache', named_targets)
