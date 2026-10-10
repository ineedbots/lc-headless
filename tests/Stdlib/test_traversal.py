import rs2004.traversal as walker
from rs2004.traversal import matches_landing, special_crossing_for_transport, pick_choice

TOLL = {'x': 3268, 'z': 3227, 'level': 0, 'locName': 'Gate', 'action': 'Open', 'requires': {'item': 'Coins', 'count': 10},
        'questWaivesItems': 'Prince Ali Rescue', 'dialogue': {'choose': ['Yes, ok.']}, 'label': 'Al Kharid toll gate'}
SHIP = {'x': 3027, 'z': 3218, 'level': 1, 'npc': 'Seaman Thresnor', 'locName': 'Seaman Thresnor', 'action': 'Pay-fare',
        'requires': {'item': 'Coins', 'count': 30}, 'dialogue': {'choose': ['Yes please.']},
        'toTile': {'x': 2956, 'z': 3143, 'level': 1}, 'label': 'Port Sarim->Musa ship'}
OTHER_SHIP = {'x': 3027, 'z': 3218, 'level': 1, 'npc': 'Seaman Thresnor', 'locName': 'Seaman Thresnor', 'action': 'Pay-fare',
              'toTile': {'x': 1000, 'z': 1000, 'level': 1}, 'label': 'somewhere else'}


def tile(x, z, level=0):
    return Tile(x, z, level)


def test_crossings_are_found_by_the_tiles_and_landing_of_the_hop():
    walker._crossings = [TOLL, SHIP, OTHER_SHIP]
    gate = {'loc_name': 'Gate', 'action': 'Open', 'loc_x': 3268, 'loc_z': 3227}
    assert special_crossing_for_transport(gate, tile(3267, 3227), tile(3269, 3227)) is TOLL
    ship = {'loc_name': 'Seaman Thresnor', 'action': 'Pay-fare', 'loc_x': 3027, 'loc_z': 3218}
    assert special_crossing_for_transport(ship, tile(3027, 3218), tile(2956, 3143, 1)) is SHIP
    # A hop that lands elsewhere isn't stolen by a crossing whose landing doesn't match.
    assert special_crossing_for_transport(ship, tile(3027, 3218), tile(3000, 3000, 1)) is None
    door = {'loc_name': 'Door', 'action': 'Open', 'loc_x': 3100, 'loc_z': 3100}
    assert special_crossing_for_transport(door, tile(3100, 3099), tile(3100, 3101)) is None
    walker._crossings = None


def test_dialogue_choices_match_by_part():
    assert pick_choice(['No thank you.', 'Yes, ok.'], ['yes, ok']) == 'Yes, ok.'
    assert pick_choice(['Who are you?'], ['Yes']) is None
    assert pick_choice([], ['Yes']) is None


def test_a_hop_has_landed_when_it_reaches_its_tile():
    ship = {'to_tile': [2956, 3143], 'accept_any_landing': False}
    pier = tile(3027, 3218)
    assert matches_landing(ship, 1, pier, tile(2956, 3144, 1))
    assert not matches_landing(ship, 1, pier, tile(2956, 3144, 0))
    assert not matches_landing(ship, 1, pier, None)
    # A short hop, a stile, counts only on its tile, not on every frame of the climb.
    stile = {'to_tile': [3200, 3202]}
    assert not matches_landing(stile, 0, tile(3200, 3200), tile(3200, 3201))
    assert matches_landing(stile, 0, tile(3200, 3200), tile(3200, 3202))
    portal = {'accept_any_landing': True}
    assert matches_landing(portal, 0, tile(3200, 3200), tile(2900, 4800))
    assert not matches_landing(portal, 0, tile(3200, 3200), tile(3210, 3200))


def test_banks_are_ranked_by_the_straight_line_whatever_the_level():
    walker._banks = [
        {'name': 'Far', 'tile': {'x': 3300, 'z': 3300, 'level': 0}},
        {'name': 'Up', 'tile': {'x': 3205, 'z': 3205, 'level': 2}},
        {'name': 'Guild', 'tile': {'x': 3201, 'z': 3201, 'level': 0}, 'requires': {'setting': 'useGuildBank'}},
    ]
    here = tile(3200, 3200)
    assert [bank['name'] for bank in walker.nearest_banks(here)] == ['Up', 'Far']
    assert walker.nearest_bank(here, {'useGuildBank': True})['name'] == 'Guild'
    walker._banks = None


def test_walking_needs_the_walker_data():
    assert not traversal.teleports_enabled()
    walk = traversal.walk_to(Tile(3253, 3420, 0))
    try:
        next(walk)
        assert False, 'a walk without walker data should not yield'
    except StopIteration:
        pass
    assert traversal.last_outcome == 'failed'
    assert 'navigation unavailable' in traversal.last_reason
