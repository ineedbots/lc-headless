"""Walking through doors and choosing how to reach a bank, with rs2b0t's test/event/webwalk/walkOpening.test.ts and
test/api/bank/banking-route.test.ts ported."""

from rs2004.bank import NEARBY_BANK_RADIUS, bank_pace_ticks, resolve_bank_open_route
from rs2004.navigation import face_steps, far_side, is_openable_obstacle, opened_neighbour


def test_a_shut_door_or_gate_is_openable_by_name_and_its_open_option():
    assert is_openable_obstacle('Door', ['Open'], ['door', 'gate'])
    assert is_openable_obstacle('Large door', ['Open'], ['door'])
    assert is_openable_obstacle('Wooden gate', [None, 'Open'], ['door', 'gate'])
    # An open door offers Close.
    assert not is_openable_obstacle('Door', ['Close'], ['door'])
    assert not is_openable_obstacle('Bank booth', ['Open'], ['door', 'gate'])
    assert not is_openable_obstacle(None, ['Open'], ['door'])


def test_the_opened_neighbour_is_across_the_face_the_door_swung_free():
    door = Tile(2949, 3450, 0)
    found = opened_neighbour(door, [True, True, False, True], [True, True, True, True])
    assert (found.x, found.z, found.level) == (2950, 3450, 0)
    assert opened_neighbour(door, [True, True, False, True], [True, True, False, True]) is None
    # A face that was already open is ignored.
    found = opened_neighbour(door, [True, False, False, False], [True, False, False, True])
    assert (found.x, found.z) == (2949, 3449)


def test_faces_are_asked_west_north_east_then_south():
    asked = []

    def step(start, to):
        asked.append((to.x, to.z))
        return False

    assert face_steps(Tile(5, 5, 0), step) == [False, False, False, False]
    assert asked == [(4, 5), (5, 6), (6, 5), (5, 4)]


def test_the_far_side_is_the_tile_you_are_not_on():
    door = Tile(2949, 3450, 0)
    across = Tile(2950, 3450, 0)
    assert far_side(door, across, door) == across
    assert far_side(door, across, across) == door
    # Beside the passage, the further of the two.
    assert far_side(door, across, Tile(2948, 3451, 0)) == across
    assert far_side(door, across, Tile(2951, 3449, 0)) == door


DRAYNOR = Tile(3093, 3243, 0)
EDGEVILLE = Tile(3094, 3493, 0)
CATHERBY = Tile(2809, 3441, 0)
VARROCK_WEST = Tile(3185, 3440, 0)


def bank_at(name, tile):
    return {'name': name, 'tile': {'x': tile.x, 'z': tile.z, 'level': tile.level}}


def test_an_open_bank_or_a_booth_in_the_scene_wins():
    assert NEARBY_BANK_RADIUS == 14
    draynor = bank_at('Draynor', DRAYNOR)
    assert resolve_bank_open_route(True, DRAYNOR, EDGEVILLE, 2, draynor) == 'already-open'
    # The camp's bank is Edgeville, but a booth stands in the scene at Draynor.
    assert resolve_bank_open_route(False, DRAYNOR, EDGEVILLE, 3, draynor) == 'scene-booth'
    assert resolve_bank_open_route(False, DRAYNOR, EDGEVILLE, NEARBY_BANK_RADIUS, draynor) == 'scene-booth'
    assert resolve_bank_open_route(False, DRAYNOR, EDGEVILLE, NEARBY_BANK_RADIUS + 1, draynor) != 'scene-booth'
    assert resolve_bank_open_route(False, DRAYNOR, EDGEVILLE, 2, draynor, prefer_nearby=False) == 'preset-stand'
    assert resolve_bank_open_route(False, DRAYNOR, EDGEVILLE, 10, draynor, nearby_radius=8) != 'scene-booth'
    assert resolve_bank_open_route(False, DRAYNOR, EDGEVILLE, 10, draynor, nearby_radius=12) == 'scene-booth'


def test_a_known_bank_where_you_stand_beats_a_distant_stand():
    # Smithing at Varrock West while the camp table still says Draynor.
    assert resolve_bank_open_route(False, VARROCK_WEST, DRAYNOR, None, bank_at('Varrock West', VARROCK_WEST)) == 'local-bank'
    # At Catherby with Catherby's stand, the stand is walked.
    assert resolve_bank_open_route(False, CATHERBY, CATHERBY, None, bank_at('Catherby', CATHERBY)) == 'preset-stand'
    assert resolve_bank_open_route(False, Tile(3000, 3300, 0), EDGEVILLE, None, None) == 'preset-stand'
    # Far from every bank, with no stand, the nearest is walked to.
    assert resolve_bank_open_route(False, Tile(2500, 3200, 0), None, None, bank_at('Draynor', DRAYNOR)) == 'nearest-fallback'
    assert resolve_bank_open_route(False, DRAYNOR, None, None, bank_at('Draynor', DRAYNOR)) == 'local-bank'


def test_bank_actions_pause_one_tick_or_now_and_then_two():
    assert bank_pace_ticks(lambda: 0.1) == 2
    assert bank_pace_ticks(lambda: 0.5) == 1
    assert bank_pace_ticks() in [1, 2]
