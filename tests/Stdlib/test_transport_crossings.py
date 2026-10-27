"""Transport handlers over simulated scene and dialogue updates; no handler methods are replaced."""

import json
import rs2004.traversal as walker
import rs2004.routeplan as routes
from rs2004 import execution
from rs2004.walkgeom import PathTile


class Message:
    def __init__(self, text):
        self.text = text


class Entity:
    def __init__(self, world, name, actions, tile=None, id=123):
        self.world = world
        self.name = name
        self.ops = actions
        self.position = tile or Tile(3200, 3200)
        self.id = id
        self.layer = LAYER_WALL
        self.on_interact = None

    def tile(self):
        return self.position

    def distance(self):
        return self.position.distance_to(self.world.here)

    def actions(self):
        return self.ops

    def interact(self, action):
        self.world.interactions.append((self.name, action))
        if action not in self.ops:
            return False
        return self.on_interact(action) if self.on_interact is not None else True


class Query:
    def __init__(self, entities, world):
        self.entities = list(entities)
        self.world = world

    def name(self, names):
        names = names if isinstance(names, list) else [names]
        wanted = [name.lower() for name in names]
        return self.where(lambda entity: (entity.name or '').lower() in wanted)

    def action(self, action):
        return self.where(lambda entity: action.lower() in [op.lower() for op in entity.actions()])

    def where(self, predicate):
        self.entities = [entity for entity in self.entities if predicate(entity)]
        return self

    def within_of(self, tile, radius):
        return self.where(lambda entity: entity.tile().distance_to(tile) <= radius)

    def within(self, radius):
        return self.within_of(self.world.here, radius)

    def nearest(self):
        self.entities.sort(key=lambda entity: entity.distance())
        return self.entities[0] if self.entities else None


class Entities:
    def __init__(self, world, field):
        self.world = world
        self.field = field

    def query(self):
        return Query(getattr(self.world, self.field), self.world)


class Dialogue:
    def __init__(self, world):
        self.world = world
        self.open = False
        self.choices = []
        self.lines = []
        self.chosen = []
        self.continued = 0
        self.on_choose = None

    def is_open(self):
        return self.open

    def options(self):
        return self.choices

    def texts(self):
        return self.lines

    def can_continue(self):
        return self.open and not self.choices

    def continue_(self):
        self.continued += 1
        self.open = False
        yield execution.Ticks(1)

    def choose_option(self, choice):
        assert choice in self.choices
        self.chosen.append(choice)
        self.open = False
        self.choices = []
        if self.on_choose is not None:
            self.on_choose(choice)
        yield execution.Ticks(1)


class NoModals:
    def is_open(self):
        return False


class TransportWorld:
    def __init__(self):
        self.here = Tile(3200, 3200)
        self.now = 0
        self.ticks = 0
        self.events = []
        self.on_advance = None
        self.loc_items = []
        self.npc_items = []
        self.held = []
        self.coins = 30
        self.quest_statuses = {}
        self.skill_levels = {}
        self.interactions = []
        self.walks = []
        self.spells = []
        self.waits = []
        self.logs = []
        self.messages = []
        self.passable = False
        self.walk_ack = True
        self.spell_ack = True
        self.spell_landing = None
        self.crossings = []
        self.teleports = []
        self.route = []
        self.requests = []
        self.dialogue = Dialogue(self)

    def __enter__(self):
        self.saved = []
        for owner, name, value in [
            (walker, '_core', self), (execution, '_core', self),
            (walker, 'local_tile', lambda: self.here), (walker, 'game', self),
            (walker, 'game_messages', self), (walker, 'inventory', self),
            (walker, 'quests', self), (walker, 'skills', self),
            (walker, 'locs', Entities(self, 'loc_items')), (walker, 'npcs', Entities(self, 'npc_items')),
            (walker, 'chat_dialog', self.dialogue), (walker, 'modals', NoModals()),
            (walker, 'world_state', lambda: {'items': {}, 'worn': {}, 'quests': {}}),
            (walker, 'bank_locations', lambda: []), (walker, 'gate_item_candidates', lambda: {}),
            (routes, '_crossings', self.crossings), (routes, '_teleports', self.teleports),
        ]:
            self.saved.append((owner, name, getattr(owner, name)))
            setattr(owner, name, value)
        self.essence_before = routes.essence_session.get_return_id()
        return self

    def __exit__(self, *args):
        self.saved.reverse()
        for owner, name, value in self.saved:
            setattr(owner, name, value)
        routes.essence_session.note_entry(self.essence_before)

    def step_time(self):
        return self.now

    def tick(self):
        return self.ticks

    def get_level(self):
        return self.here.level

    def can_step(self, x, z, to_x, to_z):
        return self.passable

    def can_reach_entity(self, x, z):
        return self.passable

    def combat_level(self):
        return 50

    def in_combat(self):
        return False

    def in_scene(self, x, z):
        return True

    def is_reachable(self, x, z):
        return self.passable

    def walk_tile(self, x, z, level):
        return [1 if self.passable else 0, 0]

    def find_world_path(self, text):
        self.requests.append(json.loads(text))
        return json.dumps({'ok': True, 'cost': 1, 'expanded': 2, 'waypoints': self.route})

    def walk_to(self, x, z, run):
        self.walks.append((x, z, run))
        if self.walk_ack:
            tile = Tile(x, z, self.here.level)
            self.events.append(('land', tile))
        return self.walk_ack

    def teleport(self, name):
        self.spells.append(name)
        if self.spell_ack and self.spell_landing is not None:
            self.events.append(('land', self.spell_landing))
        return self.spell_ack

    def land(self, tile):
        self.here = tile

    def climb(self, action):
        self.events.append(('land', Tile(3200, 3200, 1)))
        return True

    def sail(self, action):
        self.events.append(('land', Tile(3000, 3000, 1)))
        return True

    def mark(self):
        return len(self.messages)

    def since(self, mark):
        return [Message(text) for text in self.messages[mark:]]

    def saw_since(self, mark, text):
        return any([text.lower() in message.lower() for message in self.messages[mark:]])

    def count(self, name):
        return self.coins if name == 'Coins' else 0

    def items(self):
        return self.held

    def status(self, name):
        return self.quest_statuses.get(name, 'not_started')

    def level(self, skill):
        return self.skill_levels.get(skill, 1)

    def run(self, task):
        for guard in range(120):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            self.waits.append(wait)
            assert isinstance(wait, execution.Update) or isinstance(wait, execution.Ticks)
            elapsed = 600 * wait.count if isinstance(wait, execution.Ticks) else 500
            self.now += elapsed
            self.ticks += wait.count if isinstance(wait, execution.Ticks) else 1
            events = self.events
            self.events = []
            for kind, value in events:
                if kind == 'land':
                    self.here = value
                elif kind == 'message':
                    self.messages.append(value)
                elif kind == 'open':
                    value.ops = ['Close']
                    self.passable = True
                elif kind == 'actions':
                    entity, actions = value
                    entity.ops = actions
                elif kind == 'dialogue':
                    self.dialogue.open = True
                    self.dialogue.choices, self.dialogue.lines = value
                else:
                    assert False, 'unknown simulated update'
            if self.on_advance is not None:
                self.on_advance()
        assert False, 'transport exceeded the simulated update budget'

    def take(self, transport, landing=None):
        landing = landing or Tile(3201, 3200)
        self.hop = PathTile(landing.x, landing.z, landing.level, transport)
        self.walk = walker._Traversal()
        return self.run(self.walk._take_hop(Tile(3200, 3200), self.hop, self.logs.append))


def door():
    return {'kind': 'door', 'loc_name': 'Door', 'action': 'Open', 'loc_x': 3200, 'loc_z': 3200}


def ladder():
    return {'kind': 'loc', 'loc_name': 'Ladder', 'action': 'Climb-down', 'loc_id': 1759,
            'loc_x': 3200, 'loc_z': 3200, 'to_level': 1}


def ship():
    return {'kind': 'npc', 'loc_name': 'Captain', 'action': 'Pay-fare', 'loc_x': 3200, 'loc_z': 3200,
            'to_tile': [3000, 3000]}


def spell():
    return {'kind': 'teleport', 'family': 'spell', 'loc_name': 'Falador teleport',
            'teleport_id': 'falador', 'to_tile': [3000, 3000]}


def add_ship(world):
    world.crossings.append({'x': 3200, 'z': 3200, 'level': 0, 'locName': 'Captain', 'npc': 'Captain',
                            'action': 'Pay-fare', 'requires': {'item': 'Coins', 'count': 30},
                            'dialogue': {'choose': ['Yes please']},
                            'toTile': {'x': 3000, 'z': 3000, 'level': 1}, 'label': 'Test ferry'})
    captain = Entity(world, 'Captain', ['Pay-fare', 'Talk-to'])
    world.npc_items.append(captain)
    return captain


def add_glory(world):
    world.teleports.append({'teleportId': 'glory', 'family': 'jewellery', 'to': {'level': 0},
                            'itemNameMatch': ['amulet of glory'], 'dialogueChoose': ['Edgeville']})
    item = Entity(world, 'Amulet of glory(4)', ['Wear', 'Rub'])
    world.held = [item]
    return item


def glory():
    return {'kind': 'teleport', 'family': 'jewellery', 'loc_name': 'Rub glory',
            'teleport_id': 'glory', 'to_tile': [3000, 3000]}


def test_a_closed_door_opens_then_waits_a_tick_before_walking_through():
    with TransportWorld() as world:
        loc = Entity(world, 'Door', ['Open'])
        world.loc_items = [loc]

        def opened(action):
            world.events.append(('open', loc))
            return True

        loc.on_interact = opened
        assert world.take(door()) == 'crossed'
        assert world.here == Tile(3201, 3200)
        assert world.interactions == [('Door', 'Open')]
        assert world.walks == [(3201, 3200, False)]
        assert isinstance(world.waits[1], execution.Ticks) and world.waits[1].count == 1
        assert world.hop.transport is None


def test_walk_to_executes_a_door_hop_from_the_planners_waypoints():
    with TransportWorld() as world:
        loc = Entity(world, 'Door', ['Open'])
        world.loc_items = [loc]
        world.route = [{'x': 3200, 'z': 3200, 'level': 0},
                       {'x': 3201, 'z': 3200, 'level': 0, 'transport': door()}]

        def opened(action):
            world.events.append(('open', loc))
            return True

        loc.on_interact = opened
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3201, 3200), radius=0, timeout_ms=10000))
        assert walk.last_outcome == 'arrived'
        assert len(world.requests) == 1
        assert world.interactions == [('Door', 'Open')]
        assert world.walks == [(3201, 3200, False)]


def test_a_door_interaction_refusal_does_not_walk_through_it():
    with TransportWorld() as world:
        loc = Entity(world, 'Door', ['Open'])
        loc.on_interact = lambda action: False
        world.loc_items = [loc]
        assert world.take(door()) == 'repath'
        assert world.walks == [] and world.waits == []
        assert world.walk._door_strikes == {'3200,3200': 1}


def test_a_door_cant_reach_reply_stops_the_crossing_without_a_walk_click():
    with TransportWorld() as world:
        loc = Entity(world, 'Door', ['Open'])
        world.loc_items = [loc]

        def unreachable(action):
            world.events.append(('message', "I can't reach that!"))
            return True

        loc.on_interact = unreachable
        assert world.take(door()) == 'repath'
        assert world.walks == []
        assert len(world.interactions) == 1


def test_a_quest_locked_door_is_blacklisted_and_its_dialogue_dismissed():
    with TransportWorld() as world:
        loc = Entity(world, 'Door', ['Open'])
        world.loc_items = [loc]

        def locked(action):
            world.events.append(('dialogue', ([], ['You need a key to open this door.'])))
            return True

        loc.on_interact = locked
        assert world.take(door()) == 'repath'
        assert world.walk._avoid_doors == [[3200, 3200]]
        assert world.dialogue.continued == 1
        assert not world.dialogue.open
        assert world.walks == []


def test_a_quest_lock_in_game_chat_also_blacklists_the_door():
    with TransportWorld() as world:
        loc = Entity(world, 'Door', ['Open'])
        world.loc_items = [loc]

        def locked(action):
            world.events.append(('message', 'You need a key to open this door.'))
            return True

        loc.on_interact = locked
        assert world.take(door()) == 'repath'
        assert world.walk._avoid_doors == [[3200, 3200]]
        assert world.dialogue.continued == 0
        assert world.walks == []


def test_a_ladder_uses_its_exact_placement_and_waits_for_the_new_level():
    with TransportWorld() as world:
        neighbour = Entity(world, 'Ladder', ['Climb-down'], Tile(3201, 3200), id=1759)
        target = Entity(world, 'Ladder', ['Climb-down'], id=1759)
        world.loc_items = [neighbour, target]

        target.on_interact = world.climb
        assert world.take(ladder(), Tile(3200, 3200, 1)) == 'crossed'
        assert world.here.level == 1
        assert len(world.interactions) == 1
        assert world.waits[-1].count == 2


def test_a_missing_ladder_does_not_use_the_neighbouring_placement():
    with TransportWorld() as world:
        world.loc_items = [Entity(world, 'Ladder', ['Climb-down'], Tile(3201, 3200), id=1759)]
        assert world.take(ladder(), Tile(3200, 3200, 1)) == 'repath'
        assert world.interactions == []
        assert world.now >= walker.SCENE_REBUILD_MS


def test_a_ladder_can_appear_during_a_scene_rebuild():
    with TransportWorld() as world:
        def rebuilt():
            if world.now >= 1000:
                target = Entity(world, 'Ladder', ['Climb-down'], id=1759)
                target.on_interact = world.climb
                world.loc_items = [target]
                world.on_advance = None

        world.on_advance = rebuilt
        assert world.take(ladder(), Tile(3200, 3200, 1)) == 'crossed'
        assert world.interactions == [('Ladder', 'Climb-down')]


def test_a_shut_trapdoor_is_opened_before_using_its_climb_action():
    with TransportWorld() as world:
        target = Entity(world, 'Trapdoor', ['Open'], id=1759)
        world.loc_items = [target]

        def interact(action):
            if action == 'Open':
                world.events.append(('actions', (target, ['Climb-down'])))
                return True
            return world.climb(action)

        target.on_interact = interact
        transport = ladder()
        transport['loc_name'] = 'Trapdoor'
        assert world.take(transport, Tile(3200, 3200, 1)) == 'crossed'
        assert world.interactions == [('Trapdoor', 'Open'), ('Trapdoor', 'Climb-down')]
        assert world.here.level == 1


def test_a_ladder_cant_reach_reply_steps_to_the_approach_then_retries_once():
    with TransportWorld() as world:
        world.here = Tile(3199, 3200)
        target = Entity(world, 'Ladder', ['Climb-down'], id=1759)
        world.loc_items = [target]

        def climbed(action):
            if len(world.interactions) == 1:
                world.events.append(('message', "I can't reach that!"))
            else:
                world.events.append(('land', Tile(3200, 3200, 1)))
            return True

        target.on_interact = climbed
        assert world.take(ladder(), Tile(3200, 3200, 1)) == 'crossed'
        assert world.walks == [(3200, 3200, False)]
        assert world.interactions == [('Ladder', 'Climb-down'), ('Ladder', 'Climb-down')]
        assert world.walk._door_strikes == {}


def test_landing_on_the_wrong_level_does_not_complete_a_ladder_hop():
    with TransportWorld() as world:
        target = Entity(world, 'Ladder', ['Climb-down'], id=1759)
        world.loc_items = [target]

        def wrong_level(action):
            world.events.append(('land', Tile(3200, 3200, 2)))
            return True

        target.on_interact = wrong_level
        assert world.take(ladder(), Tile(3200, 3200, 1)) == 'repath'
        assert len(world.interactions) == 2
        assert world.hop.transport is not None


def test_a_spell_teleport_waits_for_landing_and_scene_settling():
    with TransportWorld() as world:
        world.teleports.append({'teleportId': 'falador', 'family': 'spell', 'to': {'level': 0}})
        world.spell_landing = Tile(3000, 3000)
        assert world.take(spell(), Tile(3000, 3000)) == 'crossed'
        assert world.spells == ['Falador teleport']
        assert world.hop.transport is None
        assert world.waits[-1].count == 2


def test_a_spell_that_cannot_be_cast_is_suppressed_without_blacking_out_doors():
    with TransportWorld() as world:
        world.spell_ack = False
        assert world.take(spell(), Tile(3000, 3000)) == 'repath'
        assert world.walk._suppressed_teleports == ['falador']
        assert world.walk._door_strikes == {}
        assert world.waits == []


def test_a_spell_that_never_lands_times_out_and_requests_another_route():
    with TransportWorld() as world:
        assert world.take(spell(), Tile(3000, 3000)) == 'repath'
        assert world.now >= walker.TELEPORT_LAND_MS
        assert world.walk._suppressed_teleports == ['falador']


def test_an_unexpected_teleport_landing_replans_without_suppressing_a_working_teleport():
    with TransportWorld() as world:
        transport = spell()
        transport['accept_any_landing'] = True
        world.spell_landing = Tile(3100, 3100)
        assert world.take(transport, Tile(3000, 3000)) == 'repath'
        assert world.walk._suppressed_teleports == []
        assert world.hop.transport is None
        assert any(['not where planned' in line for line in world.logs])


def test_jewellery_is_rubbed_and_its_named_destination_chosen_before_landing():
    with TransportWorld() as world:
        item = add_glory(world)

        def rub(action):
            world.events.append(('dialogue', (['Karamja', 'Edgeville'], [])))
            return True

        item.on_interact = rub
        world.dialogue.on_choose = lambda choice: world.events.append(('land', Tile(3000, 3000)))
        assert world.take(glory(), Tile(3000, 3000)) == 'crossed'
        assert world.interactions == [('Amulet of glory(4)', 'Rub')]
        assert world.dialogue.chosen == ['Edgeville']
        assert world.spells == []


def test_jewellery_without_the_catalogued_destination_is_not_chosen_at_random():
    with TransportWorld() as world:
        item = add_glory(world)

        def rub(action):
            world.events.append(('dialogue', (['Karamja'], [])))
            return True

        item.on_interact = rub
        assert world.take(glory(), Tile(3000, 3000)) == 'repath'
        assert world.dialogue.chosen == []
        assert world.walk._suppressed_teleports == ['glory']


def test_a_jewellery_rub_that_never_opens_dialogue_has_a_bounded_wait():
    with TransportWorld() as world:
        add_glory(world)
        assert world.take(glory(), Tile(3000, 3000)) == 'repath'
        assert world.now >= walker.TELEPORT_DIALOGUE_MS
        assert world.dialogue.chosen == []
        assert world.interactions == [('Amulet of glory(4)', 'Rub')]


def test_missing_or_unrubbable_jewellery_is_rejected_without_an_item_action():
    for missing in [True, False]:
        with TransportWorld() as world:
            item = add_glory(world)
            if missing:
                world.held = []
            else:
                item.ops = ['Wear']
            assert world.take(glory(), Tile(3000, 3000)) == 'repath'
            assert world.interactions == [] and world.waits == []


def test_a_ship_refuses_departure_without_the_fare():
    with TransportWorld() as world:
        add_ship(world)
        world.coins = 29
        assert world.take(ship(), Tile(3000, 3000, 1)) == 'repath'
        assert world.interactions == [] and world.waits == []


def test_a_ship_falls_back_to_talking_and_answers_the_fare_dialogue():
    with TransportWorld() as world:
        captain = add_ship(world)

        def talk(action):
            if action == 'Pay-fare':
                return False
            world.events.append(('dialogue', (['No thanks.', 'Yes please.'], [])))
            return True

        captain.on_interact = talk
        world.dialogue.on_choose = lambda choice: world.events.append(('land', Tile(3000, 3000, 1)))
        assert world.take(ship(), Tile(3000, 3000, 1)) == 'crossed'
        assert world.interactions == [('Captain', 'Pay-fare'), ('Captain', 'Talk-to')]
        assert world.dialogue.chosen == ['Yes please.']
        assert world.here == Tile(3000, 3000, 1)


def test_a_missing_captain_does_not_start_a_ship_dialogue():
    with TransportWorld() as world:
        add_ship(world)
        world.npc_items = []
        assert world.take(ship(), Tile(3000, 3000, 1)) == 'repath'
        assert world.interactions == [] and world.waits == []


def test_a_captain_who_never_sends_dialogue_or_a_landing_does_not_hang_the_walk():
    with TransportWorld() as world:
        add_ship(world)
        assert world.take(ship(), Tile(3000, 3000, 1)) == 'repath'
        assert len(world.waits) == walker.SHIP_DIALOGUE_STEPS
        assert world.dialogue.chosen == []
        assert world.hop.transport is not None


def test_a_ship_must_land_on_the_expected_level_and_near_the_expected_pier():
    for landing in [Tile(3000, 3000, 0), Tile(3010, 3000, 1)]:
        with TransportWorld() as world:
            captain = add_ship(world)
            world.spell_landing = landing

            def land_elsewhere(action):
                world.events.append(('land', world.spell_landing))
                return True

            captain.on_interact = land_elsewhere
            assert world.take(ship(), Tile(3000, 3000, 1)) == 'repath'
            assert len(world.waits) == walker.SHIP_DIALOGUE_STEPS
            assert world.hop.transport is not None


def test_a_completed_quest_can_waive_a_crossings_fare():
    with TransportWorld() as world:
        captain = add_ship(world)
        world.crossings[0]['questWaivesItems'] = 'Prince Ali Rescue'
        world.quest_statuses['Prince Ali Rescue'] = 'complete'
        world.coins = 0
        captain.on_interact = world.sail
        assert world.take(ship(), Tile(3000, 3000, 1)) == 'crossed'
        assert world.interactions == [('Captain', 'Pay-fare')]


def test_a_crossing_checks_its_skill_requirement_before_interacting():
    with TransportWorld() as world:
        add_ship(world)
        world.crossings[0]['requiresSkill'] = {'name': 'Agility', 'level': 50}
        world.skill_levels['Agility'] = 49
        assert world.take(ship(), Tile(3000, 3000, 1)) == 'repath'
        assert world.interactions == [] and world.waits == []


def test_a_roaming_captain_can_be_found_near_the_player_instead_of_the_baked_stand():
    with TransportWorld() as world:
        captain = add_ship(world)
        captain.position = Tile(3211, 3200)
        captain.on_interact = world.sail
        assert world.take(ship(), Tile(3000, 3000, 1)) == 'crossed'
        assert world.interactions == [('Captain', 'Pay-fare')]
