"""Random-event interactions over delayed interfaces, inventory changes and maze movement."""

import rs2004.random_solvers as solvers
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_dialogue_workflows import DialogueWorld


class RandomWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.stock = {'Strange box': 0, 'Lamp': 0}
        self.question = 'What colour is the Triangle?'
        self.parts = [3063, 3071, 3079]
        self.screen = None
        self.items_open = True
        self.consume = True
        self.lamp_disappears_on_select = False
        self.lamp_components = True
        self.chosen_skill = None
        self.position = Tile(3000, 3000)
        self.mime_animation = 860
        self.mime_buttons = False
        self.mime_finishes = True
        self.walk_lands = True
        self.door_lands = True
        self.pending_position = None
        self.walks = []
        self.scene = []
        self.maze_locs = []
        self.maze_reads = 0
        self.shrine_exits = True

    def __enter__(self):
        DialogueWorld.__enter__(self)
        replacements = {
            '_core': self,
            'inventory': FakeModule(contains=lambda name: self.stock.get(name, 0) > 0,
                                    count=lambda name: self.stock.get(name, 0), first=self.item),
            'local_tile': lambda: self.position,
            'npcs': FakeModule(query=lambda: EntityQuery(self.mime_supply, lambda npc: True)),
            'locs': FakeModule(query=lambda: EntityQuery(self.loc_supply, lambda loc: True)),
            '_maze': None,
        }
        self.solver_saved = {}
        for name, value in replacements.items():
            self.solver_saved[name] = getattr(solvers, name)
            setattr(solvers, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.solver_saved.items():
            setattr(solvers, name, value)
        DialogueWorld.__exit__(self, *args)

    def item(self, name):
        return FakeModule(interact=self.open_item)

    def open_item(self, op):
        self.clicks.append(op)
        if self.items_open:
            self.pending = 'cube' if op == 'Open' else 'lamp'
        return self.items_open

    def get_main_modal(self):
        return 200 if self.screen is not None else DialogueWorld.get_main_modal(self)

    def get_chat_modal(self):
        return 100 if self.mime_buttons else DialogueWorld.get_chat_modal(self)

    def get_texts(self, root):
        if root == 100 and self.mime_buttons:
            return ['Think', 'Glass Box', 'Cry']
        return ['Confirm'] if self.screen == 'lamp' else []

    def get_interface(self, root):
        if self.screen == 'cube':
            return ([FakeModule(type='model', item=id) for id in self.parts]
                    + [FakeModule(type='text', text=self.question)])
        if self.screen == 'lamp' and self.lamp_components:
            return [FakeModule(id=300 + index, button='ok', value=index + 1, varp=261)
                    for index in range(len(solvers.LAMP_SKILLS))]
        return []

    def click_component(self, com):
        self.clicks.append(com)
        self.chosen_skill = com - 300
        if self.lamp_disappears_on_select:
            self.pending = 'hide_lamp'
        return True

    def click_text(self, text, root):
        self.clicks.append((text, root))
        if self.mime_buttons:
            self.pending = 'mime_done'
        else:
            self.pending = 'lamp_done' if text == 'Confirm' else 'box_done'
        return True

    def mime_supply(self, ids, names, radius, layer):
        return [FakeModule(animation=self.mime_animation, distance=lambda: 1)]

    def loc_supply(self, ids, names, radius, layer):
        return [loc for loc in self.scene if (ids is None or loc.id in ids)
                and (radius is None or loc.distance() <= radius)]

    def walk_to(self, x, z, run):
        self.walks.append((x, z, run))
        if self.walk_lands:
            self.pending_position = Tile(x, z)
        return self.walk_lands

    def open_door(self, op):
        self.clicks.append(op)
        if self.door_lands:
            self.pending_position = Tile(self.position.x + 2, self.position.z)
        return self.door_lands

    def square_locs(self, x, z, level):
        assert (x, z, level) == (45, 71, 0)
        self.maze_reads += 1
        return self.maze_locs

    def touch_shrine(self, op):
        self.clicks.append(op)
        if self.shrine_exits:
            self.pending_position = Tile(3000, 3000)
        return True

    def shrine_route(self, actions=None):
        self.position = Tile(2909, 4576)
        self.maze_locs = [(30, 32, 3628, 0, 2)]
        self.scene = [
            FakeModule(id=3628, tile=lambda: Tile(2910, 4576), distance=lambda: 1, interact=self.open_door),
            FakeModule(id=3634, distance=lambda: 3, actions=lambda: actions if actions is not None else ['Examine', 'Touch'],
                       interact=self.touch_shrine),
        ]

    def advance(self):
        pending = self.pending
        if self.respond and pending in ['cube', 'lamp', 'hide_lamp', 'box_done', 'lamp_done', 'mime_done']:
            self.pending = None
            if pending in ['cube', 'lamp']:
                self.screen = pending
            elif pending == 'hide_lamp':
                self.screen = None
            elif pending == 'box_done' and self.consume:
                self.stock['Strange box'] -= 1
                self.screen = None
            elif pending == 'lamp_done' and self.consume:
                self.stock['Lamp'] -= 1
                self.screen = None
            elif pending == 'mime_done':
                self.mime_buttons = False
                if self.mime_finishes:
                    self.position = Tile(3000, 3000)
        # Closing the interface uses dialogue's real modal-wait implementation.
        if self.respond and self.pending == 'page' and self.screen is not None:
            self.screen = None
        DialogueWorld.advance(self)
        if self.pending_position is not None:
            self.position = self.pending_position
            self.pending_position = None


def test_strange_boxes_are_solved_one_at_a_time_and_stop_when_inventory_is_empty():
    with RandomWorld() as world:
        world.stock['Strange box'] = 3
        assert world.run(solvers.solve_all_boxes(world.logs.append))
        assert world.stock['Strange box'] == 0
        assert world.clicks == ['Open', ('Red', 200)] * 3
        assert world.logs[-1] == 'random event: solved 3 strange boxes'


def test_strange_box_shape_question_clicks_shape_instead_of_colour():
    with RandomWorld() as world:
        world.stock['Strange box'] = 1
        world.question = 'Which shape is Yellow?'
        assert world.run(solvers.solve_all_boxes(world.logs.append))
        assert world.clicks == ['Open', ('Circle', 200)]
        assert world.logs[-1] == 'random event: solved 1 strange box'


def test_no_strange_box_does_not_open_or_click_interface():
    with RandomWorld() as world:
        assert world.run(solvers.solve_all_boxes(world.logs.append)) is False
        assert world.clicks == []
        assert world.logs[-1] == 'random event: solved 0 strange boxes'


def test_strange_box_closes_bank_before_opening_the_box():
    with RandomWorld() as world:
        world.stock['Strange box'] = 1
        world.pages = [('main', ['Bank'])]
        assert world.run(solvers.solve_all_boxes(world.logs.append))
        assert world.clicks == ['close', 'Open', ('Red', 200)]
        assert 'closing the open interface' in world.logs[0]


def test_strange_box_stops_when_existing_interface_cannot_close():
    with RandomWorld() as world:
        world.stock['Strange box'] = 1
        world.pages = [('main', ['Bank'])]
        world.respond = False
        assert world.run(solvers.solve_all_boxes(world.logs.append)) is False
        assert world.clicks == ['close']
        assert world.stock['Strange box'] == 1


def test_strange_box_open_timeout_does_not_send_an_answer():
    with RandomWorld() as world:
        world.stock['Strange box'] = 1
        world.items_open = False
        assert world.run(solvers.solve_all_boxes(world.logs.append)) is False
        assert world.now >= 5000
        assert world.clicks == ['Open']
        assert 'did not open' in world.logs[-2]


def test_unanswerable_strange_box_is_closed_without_guessing():
    with RandomWorld() as world:
        world.stock['Strange box'] = 1
        world.question = 'Which shape is Purple?'
        assert world.run(solvers.solve_all_boxes(world.logs.append)) is False
        assert world.clicks == ['Open', 'close']
        assert world.stock['Strange box'] == 1 and world.screen is None


def test_unacknowledged_box_answer_does_not_count_as_solved():
    with RandomWorld() as world:
        world.stock['Strange box'] = 1
        world.consume = False
        assert world.run(solvers.solve_all_boxes(world.logs.append)) is False
        assert world.stock['Strange box'] == 1
        assert 'answer was not taken' in world.logs[-2]


def test_cube_screen_rejects_incomplete_or_unrelated_interface():
    with RandomWorld() as world:
        assert solvers._cube_screen() is None
        world.screen = 'cube'
        world.parts = [3063, 3071]
        assert solvers._cube_screen() is None
        world.parts = [3063, 3071, 3079]
        world.question = 'Not a question'
        assert solvers._cube_screen() is None


def test_lamp_selects_requested_skill_then_confirms_after_update():
    with RandomWorld() as world:
        world.stock['Lamp'] = 1
        assert world.run(solvers.rub_lamp('MAGIC', world.logs.append))
        assert world.chosen_skill == solvers.LAMP_SKILLS.index('magic')
        assert world.clicks == ['Rub', 303, ('Confirm', 200)]
        assert world.stock['Lamp'] == 0


def test_unknown_lamp_skill_defaults_to_strength():
    with RandomWorld() as world:
        world.stock['Lamp'] = 1
        assert world.run(solvers.rub_lamp('unknown', world.logs.append))
        assert world.chosen_skill == solvers.LAMP_SKILLS.index('strength')


def test_missing_lamp_does_not_open_interface():
    with RandomWorld() as world:
        assert world.run(solvers.rub_lamp('magic', world.logs.append)) is False
        assert world.clicks == []


def test_lamp_does_not_confirm_if_interface_closed_after_skill_selection():
    with RandomWorld() as world:
        world.stock['Lamp'] = 1
        world.lamp_disappears_on_select = True
        assert world.run(solvers.rub_lamp('magic', world.logs.append)) is False
        assert world.clicks == ['Rub', 303]
        assert 'closed before Confirm' in world.logs[-1]


def test_lamp_waits_for_valid_skill_buttons_and_times_out_if_missing():
    with RandomWorld() as world:
        world.stock['Lamp'] = 1
        world.lamp_components = False
        assert world.run(solvers.rub_lamp('magic', world.logs.append)) is False
        assert world.now >= 5000
        assert world.clicks == ['Rub']


def test_unconsumed_lamp_logs_failure_after_bounded_wait():
    with RandomWorld() as world:
        world.stock['Lamp'] = 1
        world.consume = False
        world.run(solvers.rub_lamp('magic', world.logs.append))
        assert world.stock['Lamp'] == 1
        assert world.logs[-1] == 'random event: the lamp was not used'
        assert world.now >= 4000


def test_lamp_does_not_rub_while_an_existing_modal_refuses_to_close():
    with RandomWorld() as world:
        world.stock['Lamp'] = 1
        world.pages = [('main', ['Bank'])]
        world.respond = False
        assert world.run(solvers.rub_lamp('magic', world.logs.append)) is False
        assert world.clicks == ['close']


def test_mime_copies_each_known_animation_and_waits_for_stage_exit():
    for animation, label in solvers.MIME_EMOTES.items():
        with RandomWorld() as world:
            world.position = Tile(31 * 64, 74 * 64)
            world.mime_animation = animation
            world.mime_buttons = True
            assert world.run(solvers.perform_mime(world.logs.append))
            assert world.clicks == [(label, 100)]
            assert world.logs[-1] == 'random event: mime solved'


def test_mime_does_not_click_unknown_animation():
    with RandomWorld() as world:
        world.position = Tile(31 * 64, 74 * 64)
        world.mime_animation = 99999
        world.mime_buttons = True
        # Simulate the server ending the event on the next update.
        world.pending_position = Tile(3000, 3000)
        assert world.run(solvers.perform_mime(world.logs.append))
        assert world.clicks == []


def test_mime_continues_dialogue_while_waiting_for_emote_buttons():
    with RandomWorld() as world:
        world.position = Tile(31 * 64, 74 * 64)
        world.pages = [('continue', ['Perform for me'])]
        world.pending_position = Tile(3000, 3000)
        assert world.run(solvers.perform_mime(world.logs.append))
        assert world.clicks == ['continue']


def test_maze_walker_waits_for_arrival_and_does_not_walk_if_already_near():
    with RandomWorld() as world:
        world.position = Tile(2881, 4545)
        assert world.run(solvers._walk_towards((2885, 4545), True))
        assert world.position.equals(Tile(2885, 4545))
        assert world.walks == [(2885, 4545, False)]
        assert world.run(solvers._walk_towards((2886, 4545), False))
        assert len(world.walks) == 1


def test_blocked_maze_walker_stops_after_three_unmoving_attempts():
    with RandomWorld() as world:
        world.position = Tile(2881, 4545)
        world.walk_lands = False
        assert world.run(solvers._walk_towards((2885, 4545), True)) is False
        assert len(world.walks) == 3
        assert world.now >= 4500


def test_maze_walker_does_not_issue_clicks_after_leaving_event_square():
    with RandomWorld() as world:
        assert world.run(solvers._walk_towards((2885, 4545), True)) is False
        assert world.walks == []


def test_maze_door_is_selected_by_tile_and_waits_for_player_to_cross():
    with RandomWorld() as world:
        world.position = Tile(2881, 4545)
        world.scene = [FakeModule(id=3628, tile=lambda: Tile(2882, 4545), distance=lambda: 1,
                                 interact=world.open_door)]
        world.run(solvers._open_maze_door((2882, 4545), world.logs.append))
        assert world.clicks == ['Open']
        assert world.position.equals(Tile(2883, 4545))


def test_missing_maze_door_is_reported_without_sending_an_open_click():
    with RandomWorld() as world:
        world.position = Tile(2881, 4545)
        world.run(solvers._open_maze_door((2882, 4545), world.logs.append))
        assert world.clicks == []
        assert 'not in view' in world.logs[-1]


def test_maze_solves_route_from_map_doors_then_touches_shrine_to_exit():
    with RandomWorld() as world:
        world.shrine_route()
        assert world.run(solvers.solve_maze(world.logs.append))
        assert world.clicks == ['Open', 'Touch']
        assert world.position.equals(Tile(3000, 3000))
        assert world.logs[-1] == 'random event: maze solved'
        assert world.maze_reads == 1


def test_maze_shrine_uses_touch_fallback_when_action_labels_are_missing():
    with RandomWorld() as world:
        world.shrine_route(actions=[])
        world.run(solvers.solve_maze(world.logs.append))
        assert world.clicks == ['Open', 'Touch']
        assert world.logs[-1] == 'random event: maze solved'


def test_maze_no_route_reports_blocked_spawn_without_clicking():
    with RandomWorld() as world:
        world.position = Tile(2890, 4554)
        world.maze_locs = [(10, 10, solvers.WALL_ID, 0, angle) for angle in range(4)]
        world.run(solvers.solve_maze(world.logs.append))
        assert 'no route' in world.logs[-1]
        assert world.clicks == [] and world.walks == []


def test_maze_missing_shrine_waits_for_scene_but_bounds_attempts():
    with RandomWorld() as world:
        world.shrine_route()
        world.scene.pop()
        world.run(solvers.solve_maze(world.logs.append))
        assert world.clicks == ['Open']
        assert world.logs[-1] == 'random event: maze, still inside'
        assert len(world.waits) == 7


def test_maze_unresponsive_shrine_bounds_touch_retries():
    with RandomWorld() as world:
        world.shrine_route()
        world.shrine_exits = False
        world.run(solvers.solve_maze(world.logs.append))
        assert world.clicks == ['Open'] + ['Touch'] * 6
        assert world.logs[-1] == 'random event: maze, still inside'


def test_maze_map_is_cached_between_graph_requests():
    with RandomWorld() as world:
        world.shrine_route()
        graph = solvers.maze_graph()
        assert solvers.maze_graph() is graph
        assert world.maze_reads == 1
