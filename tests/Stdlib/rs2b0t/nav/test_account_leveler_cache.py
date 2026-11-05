"""AccountLeveler's source/nav audits, over the headless cache and route planner (rs2b0t, MIT)."""
from bots.account_leveler.combat import COMBAT_CAMPS
from bots.account_leveler.offers import vendors, vial_vendors
from bots.account_leveler.travel import leveler_travel_zones
from bots.account_leveler.zanaris import BANK, GATE, LADDER, SHED, SHOP
from rs2004.walkgeom import resolve_danger_zones, tile_in_danger_zones

NPC_IDS = {
    'lumbridge-swamp-giant-rats': [86, 87],
    'lumbridge-south-giant-rats': [86, 87],
    'port-sarim-giant-rats': [86, 87],
    'varrock-east-giant-rats': [86, 87],
    'varrock-spiders': [61],
    'lumbridge-giant-spiders': [59, 60],
    'edgeville-giant-spiders': [59, 60],
    'al-kharid-spiders': [61],
    'falador-dwarves': [118, 120, 206],
    'ice-mountain-dwarves': [118, 120, 206],
    'ice-mountain-west-dwarves': [118, 120, 206],
    'lumbridge-women': [4, 5, 6],
    'lumbridge-east-women': [4, 5, 6],
    'port-sarim-women': [4, 5, 6],
    'falador-women': [4, 5, 6],
    'varrock-square-women': [4, 5, 6],
    'varrock-northeast-women': [4, 5, 6],
    'catherby-women': [4, 5, 6],
    'yanille-women': [4, 5, 6],
    'barbarian-women': [17],
    'varrock-barbarian-woman': [17],
    'al-kharid-warriors': [18],
    'falador-highwaymen': [180],
    'draynor-highwayman': [180],
    'varrock-unicorns': [89],
    'edgeville-unicorns': [89],
    'al-kharid-scorpions': [107],
    'khazard-gnomes': [66, 67, 68],
    'varrock-west-guards': [9],
    'varrock-east-guards': [9],
    'falador-north-guards': [9],
    'falador-south-guards': [9],
    'lumbridge-bears': [105],
    'varrock-east-bears': [106],
    'ice-mountain-bears': [106],
    'varrock-sewer-zombies': [73],
    'edgeville-dungeon-skeletons': [91],
    'rimmington-hobgoblins': [122],
    'yanille-giants': [117],
    'varrock-warrior-women': [15],
    'burthorpe-guards': [1076, 1077],
    'varrock-palace-guards': [9],
    'edgeville-dungeon-giants': [117],
    'wilderness-east-giants': [117],
    'ardougne-moss-giants': [112],
    'wilderness-hobgoblins': [122],
}


def exact_targets():
    for camp in COMBAT_CAMPS:
        assert reader.npc_ids(camp.target), camp.id + ': ' + camp.target
        for id in NPC_IDS.get(camp.id, []):
            npc = reader.npc_type(id)
            assert npc.name == camp.target, camp.id + ': ' + str(id)
            assert 'Attack' in npc.ops, camp.id + ': no Attack'


test('training camp targets and exact variants exist and are attackable in the cache', exact_targets)


def route(start, dest, wilderness=False):
    state = world_state()
    state['members'] = True
    state['items']['Coins'] = 200
    state['skills']['agility'] = 1
    return navigator.find_path(start, dest, max_expansions=4000000, policy={'use_teleports': False},
                               avoid_zones=resolve_danger_zones(leveler_travel_zones(dest, wilderness)), state=state)


def camps():
    for camp in COMBAT_CAMPS:
        dest = Tile(camp.x, camp.z)
        for start in [Tile(3093, 3243), Tile(2946, 3368), Tile(3185, 3436)]:
            path = route(start, dest, bool(camp.wilderness))
            assert path.ok, camp.id + ': ' + path.reason


test('all training camps can be routed from Draynor, Falador and Varrock without quest unlocks', camps)


def shops():
    for key, keeper, x, z in vendors + vial_vendors:
        if keeper == 'Jakut':
            continue
        path = route(Tile(3185, 3436), Tile(x, z))
        assert path.ok, keeper + ': ' + path.reason


test('tool, armour, rune and vial suppliers have reachable shopping stands', shops)


def zanaris():
    for start, dest in [[BANK, GATE], [GATE.translate(1, 0), SHOP], [SHOP, LADDER]]:
        assert route(start, dest).ok, str(dest)
    for id, op in [[2406, 'Open'], [2411, 'Open'], [2410, 'Climb-up']]:
        assert op in reader.loc_type(id).ops, str(id)


test('Zanaris stands connect on each side of the paid gate and offer the scripted operations', zanaris)


def safe_return():
    path = route(Tile(2725, 3492), Tile(3231, 3421))
    assert path.ok, path.reason
    zones = resolve_danger_zones(leveler_travel_zones())
    for tile in path.waypoints:
        assert not tile_in_danger_zones(tile.x, tile.z, tile.level, zones), str(tile)


test('Seers to Lowe avoids the deep Wilderness lever shortcut', safe_return)
