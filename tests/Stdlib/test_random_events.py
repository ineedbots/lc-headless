# Ported in part from rs2b0t's test/runtime/randomevents (MIT, see third_party/rs2b0t): the pure parts of the
# random event guardian and its solvers. The real maze is in tests/Script/RealCacheScriptTests.cpp.

from rs2004.geometry import Tile
from rs2004.random_events import step_off_candidates, flee_candidates, plant_strategy, targets_another_player
from rs2004.random_events import pick_sacrificial, handle_location, is_hostile_event, is_ent_hijack
from rs2004.random_events import GearLossTracker, Event, random_events
from rs2004.random_solvers import mime_answer, MIME_EMOTES, solve_cube, cube_label, CUBE_PARTS
from rs2004.random_solvers import build_maze, solve_maze_route, door_passable, edge_key, LAMP_SKILLS

HERE = Tile(100, 100, 0)
WEST_THREAT = Tile(98, 100, 0)


def ring(tiles, d):
    return [t for t in tiles if max(abs(t.x - 100), abs(t.z - 100)) == d]


def test_flee_candidates_offer_the_full_compass_away_from_the_threat_first():
    tiles = flee_candidates(HERE, WEST_THREAT, 12)
    assert len(ring(tiles, 12)) == 8
    assert (tiles[0].x, tiles[0].z, tiles[0].level) == (112, 100, 0)


def test_flee_candidates_sweep_inward_to_the_minimum_without_duplicates():
    tiles = flee_candidates(HERE, WEST_THREAT, 12)
    for d in [12, 10, 8, 6, 4]:
        assert len(ring(tiles, d)) > 0
    assert min([max(abs(t.x - 100), abs(t.z - 100)) for t in tiles]) == 4
    assert len(set([(t.x, t.z) for t in tiles])) == len(tiles)
    assert len(flee_candidates(HERE, HERE, 4)) == 8
    assert len([t for t in flee_candidates(Tile(100, 100, 2), WEST_THREAT, 12) if t.level != 2]) == 0


def test_step_off_candidates_are_the_neighbours_away_from_the_ent_first():
    tiles = step_off_candidates(HERE, WEST_THREAT)
    assert len(tiles) == 8
    assert (tiles[0].x, tiles[0].z) == (101, 100)
    assert len(ring(tiles, 1)) == 8


def test_plant_is_picked_while_it_can_be_and_evaded_once_it_can_only_be_attacked():
    assert plant_strategy(['Pick', None, None, None, None]) == 'pick'
    assert plant_strategy([None, 'Attack', None, None, None]) == 'evade'
    assert plant_strategy([None, None, None, None, None]) == 'pick'


class FakeNpc:
    def __init__(self, target):
        self.target = target


def test_an_event_npc_following_someone_else_is_not_ours():
    assert targets_another_player(FakeNpc(('player', 7)), 3)
    assert not targets_another_player(FakeNpc(('player', 3)), 3)
    assert not targets_another_player(FakeNpc(None), 3)
    assert not targets_another_player(FakeNpc(('player', 7)), -1)


def test_the_sacrificial_item_is_the_most_numerous_that_is_not_a_tool():
    assert pick_sacrificial(['Bronze pickaxe', 'Iron ore', 'Iron ore', 'Copper ore', None]) == 'Iron ore'
    assert pick_sacrificial(['Bronze axe', 'Hammer', 'Bronze axe head', 'Tinderbox']) is None
    assert pick_sacrificial([]) is None


def test_a_bare_handle_is_found_worn_before_carried():
    assert handle_location(['Axe handle'], ['Bronze axe handle']) == 'worn'
    assert handle_location(['Bronze pickaxe handle'], []) == 'inventory'
    assert handle_location(['Bronze axe'], ['Bronze pickaxe']) is None


def test_hostile_events_need_a_real_hit_and_a_nearby_event_monster():
    assert is_hostile_event(391, 3, True)
    assert not is_hostile_event(391, 3, False)
    assert not is_hostile_event(391, 9, True)
    assert not is_hostile_event(1, 1, True)


def test_an_ent_is_a_hijack_only_when_it_is_the_tree_being_chopped():
    assert is_ent_hijack(444, 12, 1, ('npc', 12), True)
    assert not is_ent_hijack(444, 12, 1, ('npc', 13), True)
    assert not is_ent_hijack(444, 12, 1, ('npc', 12), False)
    assert not is_ent_hijack(444, 12, 2, ('npc', 12), True)
    assert not is_ent_hijack(1, 12, 1, ('npc', 12), True)


def test_gear_that_leaves_the_backpack_while_fishing_is_lost():
    tracker = GearLossTracker(1000)
    tracker.update(['Harpoon', 'Raw tuna'], False, 0, True, 10)
    tracker.update(['Raw tuna'], False, 600, True, 11)
    assert tracker.recently_lost('harpoon', 700)
    assert not tracker.recently_lost('harpoon', 5000)
    tracker.update(['Harpoon'], False, 1200, True, 12)
    assert not tracker.recently_lost('harpoon', 1300)


def test_gear_dropped_away_from_fishing_or_while_suppressed_is_not_lost():
    tracker = GearLossTracker(1000)
    tracker.update(['Harpoon'], False, 0, False, 10)
    tracker.update([], False, 600, False, 11)
    assert not tracker.recently_lost('harpoon', 700)

    tracker = GearLossTracker(1000)
    tracker.update(['Harpoon'], True, 0, True, 10)
    tracker.update([], False, 600, True, 11)
    assert not tracker.recently_lost('harpoon', 700)


def test_events_are_keyed_by_kind_and_name():
    assert Event('dialog', 'genie').key() == 'dialog:genie'


def test_the_guardian_finds_nothing_without_a_game():
    assert random_events.check(None) is None


def test_every_mime_emote_has_its_own_button():
    assert len(set(MIME_EMOTES.values())) == 8
    assert mime_answer(860) == 'Cry' and mime_answer(1131) == 'Glass Box'
    assert mime_answer(None) is None and mime_answer(-1) is None


def part(shape, colour):
    for id, known in CUBE_PARTS.items():
        if known == (shape, colour):
            return id
    raise AssertionError(shape + colour)


def test_the_strange_box_answers_colour_and_shape_questions():
    parts = [part('Star', 'Red'), part('Halfmoon', 'Blue'), part('Circle', 'Yellow')]
    assert len(CUBE_PARTS) == 15
    assert solve_cube('What colour is the Star?', parts) == 0
    assert solve_cube('What colour is the Half moon?', parts) == 1
    assert solve_cube('Which shape is Yellow?', parts) == 2
    assert cube_label('What colour is the Star?', parts, 0) == 'Red'
    assert cube_label('Which shape is Yellow?', parts, 2) == 'Circle'


def test_the_strange_box_gives_up_on_what_it_cannot_tell():
    parts = [part('Star', 'Red'), part('Square', 'Blue'), part('Circle', 'Yellow')]
    assert solve_cube('What colour is the Triangle?', parts) is None
    assert solve_cube('How many sides?', parts) is None
    assert solve_cube('Which shape is Red?', [parts[0], None, parts[2]]) is None
    assert solve_cube('Which shape is Red?', [parts[0], 1, parts[2]]) is None


def test_every_lamp_skill_is_named_once():
    assert len(LAMP_SKILLS) == 19 and len(set(LAMP_SKILLS)) == 19


WALL = 3626


def boxed(door_id):
    """A 6x6 room walled round, with a door at (5, 2) in its east wall, and a shrine at (8, 1)."""
    locs = []
    for i in range(6):
        locs.append((0, i, WALL, 0, 0))
        locs.append((i, 0, WALL, 0, 3))
        locs.append((i, 5, WALL, 0, 1))
        if i != 2:
            locs.append((5, i, WALL, 0, 2))
    locs.append((5, 2, door_id, 0, 2))
    return locs


def test_the_maze_route_goes_through_a_door_that_opens_from_this_side():
    for door_id in [3628, 3629]:
        graph = build_maze(boxed(door_id), (0, 0))
        assert solve_maze_route(graph, (2, 2), (8, 1)) == [(5, 2)], door_id


def test_the_maze_route_is_empty_when_the_only_door_opens_from_the_other_side():
    graph = build_maze(boxed(3630), (0, 0))
    assert solve_maze_route(graph, (2, 2), (8, 1)) == []


def test_the_maze_route_ends_with_the_shrine_door():
    locs = boxed(3628)
    locs.append((8, 2, 3628, 0, 0))
    graph = build_maze(locs, (0, 0))
    assert solve_maze_route(graph, (2, 2), (8, 1)) == [(5, 2), (8, 2)]


def test_maze_doors_open_by_side_and_corner_walls_close_two_edges():
    door = {'x': 5, 'z': 2, 'id': 3629, 'angle': 2}
    assert door_passable(door, 5, 2) and not door_passable(door, 6, 2)
    door['id'] = 3630
    assert not door_passable(door, 5, 2) and door_passable(door, 6, 2)
    graph = build_maze([(3, 3, WALL, 2, 0)], (0, 0))
    assert edge_key(3, 3, 3, 4) in graph.walls and edge_key(3, 3, 2, 3) in graph.walls
    assert len(graph.walls) == 2
