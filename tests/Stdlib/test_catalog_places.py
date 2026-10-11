# Ported in part from rs2b0t's test/data/GatheringLocations.test.ts, MiningLocations.test.ts,
# FishingLocations.test.ts, CowKillerLocations.test.ts and cookingRanges.test.ts (MIT, see thirdparty/rs2b0t).
# The real cache's names are checked in tests/Script/RealCacheScriptTests.cpp.

from rs2004.catalogs.gathering import MAP_SQUARE, booth_fields, location_options, resolve_gathering_location
from rs2004.catalogs.gathering import same_map_square, MINING_LOCATIONS, MINING_LOCATION_OPTIONS
from rs2004.catalogs.gathering import resolve_mining_location, resolve_fishing_location, FISHING_LOCATIONS
from rs2004.catalogs.gathering import FISHING_LOCATION_OPTIONS, WOODCUTTING_LOCATIONS, resolve_woodcutting_location
from rs2004.catalogs.gathering import mining_location_label, ent_npc_on_tile, is_ent_npc_id
from rs2004.catalogs.record import Record
from rs2004.catalogs.tables import COW_LOCATIONS, resolve_cow_location, nearest_cow_location, is_cow_field_loot_tile
from rs2004.catalogs.tables import needs_toll_coins, cow_bank_destination, should_bootstrap_toll_coins, AL_KHARID_BANK
from rs2004.catalogs.tables import RUNES, RUNE_OPTIONS, DEFAULT_RUNE, PICKPOCKET_TARGET_NAMES, HERBS
from rs2004.catalogs.tables import resolve_destination, nearest_cooking_range, cook_surface_for_fish_camp
from rs2004.catalogs.tables import resolve_fish_camp_cook_surface, nearest_cook_surface, resolve_cook_location
from rs2004.catalogs.tables import logs_for_tree, firemaking_level_for_logs, resolve_fire_spot, nearest_fire_spot
from rs2004.catalogs.tables import local_fire_plot, expand_local_fire_plot, in_fire_plot, shops_selling
from rs2004.geometry import Tile

TABLE = [
    Record({'name': 'Near', 'spot': Tile(3100, 3200, 0), 'bank_stand': Tile(3093, 3243, 0), 'verified': True}),
    Record({'name': 'Far', 'spot': Tile(3200, 3300, 0), 'bank_stand': Tile(3253, 3420, 0), 'verified': False}),
    Record({'name': 'Upstairs', 'spot': Tile(3100, 3200, 1), 'bank_stand': Tile(3093, 3243, 1), 'verified': False}),
    Record({'name': 'NearSibling', 'spot': Tile(3110, 3210, 0), 'bank_stand': Tile(3093, 3243, 0), 'verified': True}),
]


def name_of(loc):
    return loc.name if loc is not None else None


def test_map_squares_are_64_tiles_on_one_level():
    assert MAP_SQUARE == 64
    assert same_map_square(Tile(3100, 3200, 0), Tile(3101, 3201, 0))
    assert not same_map_square(Tile(3100, 3200, 0), Tile(3200, 3300, 0))
    assert not same_map_square(Tile(3100, 3200, 0), Tile(3100, 3200, 1))


def test_freeform_and_unknown_settings_have_no_camp():
    for setting in ['Use Start Position', 'Use Custom Position', '  ', 'Atlantis']:
        assert resolve_gathering_location(setting, Tile(3100, 3200, 0), TABLE) is None, setting
    assert name_of(resolve_gathering_location('near', Tile(0, 0, 0), TABLE)) == 'Near'
    assert name_of(resolve_gathering_location('FAR', Tile(0, 0, 0), TABLE)) == 'Far'


def test_auto_snaps_only_within_the_start_map_square():
    assert resolve_gathering_location('Auto', Tile(3150, 3250, 0), TABLE) is None
    assert name_of(resolve_gathering_location('Auto', Tile(3100, 3200, 1), TABLE)) == 'Upstairs'
    assert name_of(resolve_gathering_location('Auto', Tile(3101, 3201, 0), TABLE)) == 'Near'


def test_use_closest_is_the_nearest_in_a_straight_line_on_any_level():
    assert name_of(resolve_gathering_location('Use Closest', Tile(3101, 3201, 0), TABLE)) == 'Near'
    assert name_of(resolve_gathering_location('Use Closest', Tile(3205, 3305, 0), TABLE)) == 'Far'
    assert name_of(resolve_gathering_location('Use Closest', Tile(3150, 3250, 0), TABLE)) == 'NearSibling'
    assert name_of(resolve_gathering_location('Use Closest', Tile(3222, 3218, 0), TABLE)) == 'Far'
    assert name_of(resolve_gathering_location('Use Closest', Tile(3100, 3200, 1), TABLE)) == 'Near'
    assert name_of(resolve_gathering_location('Use Closest', Tile(3100, 3200, 2), TABLE[:2])) == 'Near'
    assert name_of(resolve_gathering_location('Use Closest', Tile(3112, 3212, 0), TABLE)) == 'NearSibling'


def test_options_and_booths():
    assert location_options(TABLE) == ['Auto', 'Use Closest', 'Use Start Position', 'Use Custom Position', 'None', 'Near', 'Far', 'Upstairs', 'NearSibling']
    assert booth_fields(None) == ('Bank booth', 'Use-quickly')
    assert booth_fields(TABLE[0]) == ('Bank booth', 'Use-quickly')
    assert booth_fields(Record({'name': 'Chest', 'booth_name': 'Bank chest', 'booth_op': 'Use'})) == ('Bank chest', 'Use')


def test_mining_camps():
    assert resolve_mining_location('Use Start Position', Tile(3181, 3371, 0)) is None
    assert name_of(resolve_mining_location('Use Closest', Tile(3181, 3371, 0))) == 'Southwest Varrock Mine'
    assert name_of(resolve_mining_location('Use Closest', Tile(3080, 3420, 0))) == 'Barbarian Village'
    assert name_of(resolve_mining_location('Use Closest', Tile(3018, 3590, 0))) == 'Wilderness Skeleton Mine'
    assert name_of(resolve_mining_location('rimmington mine', Tile(0, 0, 0))) == 'Rimmington Mine'
    hobgoblins = resolve_mining_location('wilderness hobgoblin mine', Tile(0, 0, 0))
    assert hobgoblins.spot == Tile(3093, 3751, 0) and hobgoblins.bank_stand == Tile(3094, 3493, 0)
    assert hobgoblins.resources == ['iron', 'coal', 'mithril', 'adamantite']
    dungeon = resolve_mining_location('edgeville dungeon mine', Tile(0, 0, 0))
    assert dungeon.spot == Tile(3132, 9874, 0) and 'no Brass key required' in dungeon.notes
    assert name_of(resolve_mining_location('Use Closest', Tile(3323, 9458, 0))) == 'Desert Mining Camp'
    assert MINING_LOCATION_OPTIONS[:5] == ['Auto', 'Use Closest', 'Use Start Position', 'Use Custom Position', 'None']
    assert len(MINING_LOCATION_OPTIONS) == len(MINING_LOCATIONS) + 5
    camps = MINING_LOCATION_OPTIONS[5:]
    assert camps == sorted(camps, key=lambda n: n.lower())
    provisional = ['Legends Guild Iron (west)', 'Legends Guild Iron (east)', 'South-east Ardougne Mine']
    for loc in MINING_LOCATIONS:
        assert loc.verified == (loc.name not in provisional), loc.name
        if loc.recommended_combat is not None:
            assert mining_location_label(loc).endswith('Combat recommended)')


def test_fishing_camps():
    assert name_of(resolve_fishing_location('Use Closest', Tile(3086, 3231, 0))) == 'Draynor Village'
    assert name_of(resolve_fishing_location('Use Closest', Tile(3092, 3243, 0))) == 'Draynor Village'
    assert name_of(resolve_fishing_location('Use Closest', Tile(3086, 3231, 1))) == 'Draynor Village'
    assert name_of(resolve_fishing_location('Auto', Tile(3086, 3231, 0))) == 'Draynor Village'
    for name in ['Catherby', 'Fishing Guild', 'Karamja (Musa Point)', 'Taverley Dungeon (lava eels)']:
        assert name_of(resolve_fishing_location(name, Tile(0, 0, 0))) == name
    catherby = resolve_fishing_location('Catherby', Tile(0, 0, 0))
    assert catherby.range_stand == Tile(2817, 3443, 0) and catherby.range_name == 'Range' and 'door' in catherby.obstacles
    assert resolve_fishing_location('Karamja (Musa Point)', Tile(0, 0, 0)).bank_stand == Tile(3093, 3243, 0)
    assert [loc.name for loc in FISHING_LOCATIONS if loc.bait_vendor is not None] == ['Fishing Guild', 'Shilo Village']
    shilo = resolve_fishing_location('Shilo Village', Tile(0, 0, 0))
    assert shilo.booth_name is None and shilo.bait_vendor.keeper == 'Fernahei' and shilo.camp_radius == 48
    assert FISHING_LOCATION_OPTIONS[5:] == [loc.name for loc in FISHING_LOCATIONS]


class FakeNpc:
    def __init__(self, id, tile):
        self.id = id
        self._tile = tile

    def tile(self):
        return self._tile


def test_woodcutting_camps_and_ents():
    assert len(WOODCUTTING_LOCATIONS) > 5
    assert name_of(resolve_woodcutting_location('Use Closest', WOODCUTTING_LOCATIONS[0].spot)) == WOODCUTTING_LOCATIONS[0].name
    assert is_ent_npc_id(444) and is_ent_npc_id(452) and not is_ent_npc_id(453)

    assert ent_npc_on_tile([FakeNpc(445, Tile(1, 2, 0))], Tile(1, 2, 0))
    assert not ent_npc_on_tile([FakeNpc(1, Tile(1, 2, 0))], Tile(1, 2, 0))


def test_cow_fields():
    assert resolve_cow_location('Start tile', Tile(3255, 3288, 0)) is None
    lumbridge = resolve_cow_location('lumbridge cow field', Tile(0, 0, 0))
    assert lumbridge.name == 'Lumbridge cow field' and lumbridge.uses_al_kharid_toll
    assert name_of(resolve_cow_location('Auto', Tile(3255, 3290, 0))) == 'Lumbridge cow field'
    assert nearest_cow_location(Tile(3168, 3330, 0)).name == 'North-west of Lumbridge'
    assert is_cow_field_loot_tile(Tile(100, 100, 0), 10, Tile(110, 95, 0))
    assert not is_cow_field_loot_tile(Tile(100, 100, 0), 10, Tile(111, 100, 0))
    assert not is_cow_field_loot_tile(Tile(100, 100, 0), 10, Tile(100, 100, 1))
    assert needs_toll_coins(lumbridge, True) and not needs_toll_coins(lumbridge, False)
    assert cow_bank_destination(lumbridge, True) == ('Al Kharid', AL_KHARID_BANK)
    assert cow_bank_destination(resolve_cow_location('North-west of Lumbridge', Tile(0, 0, 0)), True)[0] == 'Draynor'
    assert should_bootstrap_toll_coins(lumbridge, Tile(3270, 3170, 0), 0, True)
    assert not should_bootstrap_toll_coins(lumbridge, Tile(3270, 3170, 0), 25, True)


def test_runes_pickpocketing_herbs_and_destinations():
    assert DEFAULT_RUNE in RUNE_OPTIONS and RUNES['Air rune'].talisman == 'Air talisman'
    assert 'Man' in PICKPOCKET_TARGET_NAMES
    assert HERBS[0].name == 'Guam leaf'
    assert resolve_destination('lumbridge').tile == Tile(3221, 3218, 0)
    assert resolve_destination('Atlantis') is None


def test_cooking_surfaces():
    catherby = nearest_cooking_range(Tile(2817, 3446, 0))
    assert catherby.loc == Tile(2817, 3444, 0) and catherby.stand == Tile(2817, 3443, 0)
    assert nearest_cooking_range(Tile(2817, 3446, 1), 5) is None
    assert cook_surface_for_fish_camp('Atlantis') is None
    draynor = cook_surface_for_fish_camp('Draynor Village')
    assert draynor is not None and draynor.loc_name == 'Fireplace'
    assert resolve_fish_camp_cook_surface(None, Tile(2817, 3446, 0)).loc == Tile(2817, 3444, 0)
    surface = nearest_cook_surface(Tile(3237, 3405, 0))
    assert surface is not None and surface.kind == 'oven'
    assert resolve_cook_location('Custom', Tile(0, 0, 0)) is None
    assert resolve_cook_location('varrock east', Tile(0, 0, 0)).name == 'Varrock East'
    assert resolve_cook_location('Auto', Tile(3250, 3420, 0)).name == 'Varrock East'
    assert resolve_cook_location('varrock east', Tile(0, 0, 0), lambda loc: False) is None


def test_fire_spots_and_logs():
    assert logs_for_tree('Tree') == 'Logs' and logs_for_tree('Willow tree') == 'Willow logs' and logs_for_tree('Yew') == 'Yew logs'
    assert firemaking_level_for_logs('Maple logs') == 45 and firemaking_level_for_logs('Nothing') is None
    name, plot = resolve_fire_spot('draynor')
    assert name == 'Draynor' and plot.x0 == 3072
    assert nearest_fire_spot(Tile(3250, 3420, 0))[0] == 'Varrock East'
    plot = local_fire_plot(Tile(100, 100, 0))
    assert (plot.x0, plot.x1, plot.z0, plot.z1) == (92, 108, 92, 108)
    assert in_fire_plot(Tile(92, 108, 0), plot) and not in_fire_plot(Tile(91, 100, 0), plot)
    bigger = expand_local_fire_plot(plot)
    assert (bigger.x0, bigger.x1) == (88, 112)
    assert expand_local_fire_plot(local_fire_plot(Tile(100, 100, 0), 24)) is None


def test_the_shop_database_finds_who_sells_an_item():
    sellers = [key for key, shop in shops_selling('Bronze pickaxe')]
    assert len(sellers) > 0


def test_targets_prefer_the_best_bucket_then_the_local_nearest():
    from rs2004.catalogs import pick_nearest_prefer_local, pick_bucket_nearest, should_cooldown_gather_tile
    near = (1, 5)
    far = (1, 20)
    farther_better = (2, 30)
    distance = lambda c: c[1]
    assert pick_nearest_prefer_local([far, near], distance) == near
    assert pick_nearest_prefer_local([(1, 15), (1, 14)], distance) == (1, 14)
    assert pick_nearest_prefer_local([], distance) is None
    assert pick_bucket_nearest([near, far, farther_better], lambda c: c[0], distance) == farther_better
    assert should_cooldown_gather_tile(False, True) and not should_cooldown_gather_tile(True, True)
    assert not should_cooldown_gather_tile(False, False)
