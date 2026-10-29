"""The ghost quest waits for shared skull spawns and confirmed coffin delivery."""

import rs2004.quests.defs.restlessghost as ghost
from rs2004 import execution
from rs2004.entities import EntityQuery
from helpers import FakeModule
from test_dialogue_workflows import DialogueWorld


class GhostObject:
    def __init__(self, world, name, actions):
        self.world = world
        self.name = name
        self.ops = actions
        self.dist = 1

    def actions(self):
        return self.ops

    def distance(self):
        return self.dist

    def interact(self, op):
        self.world.interactions.append((self.name, op))
        if op == 'Take':
            if self.world.take_accepts:
                arrives = self.world.take_results.pop(0) if self.world.take_results else True
                self.world.pending_take = arrives
            return self.world.take_accepts
        assert self.name == 'Coffin' and op == 'Open'
        if self.world.open_accepts:
            self.world.pending_open = True
        return self.world.open_accepts

    def use_on(self, target):
        assert self.name == ghost.SKULL and target.name == 'Coffin'
        self.world.uses.append((self.name, target.name))
        if self.world.use_accepts and self.world.delivery_arrives:
            self.world.pending_delivery = True
        return self.world.use_accepts


class GhostWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.coffin = GhostObject(self, 'Coffin', ['Open'])
        self.skull = GhostObject(self, ghost.SKULL, ['Take'])
        self.locations = [self.coffin]
        self.scene = [GhostObject(self, 'Restless ghost', ['Talk-to'])]
        self.drops = [self.skull]
        self.carried = None
        self.walks = []
        self.talks = []
        self.interactions = []
        self.uses = []
        self.walk_results = []
        self.talk_succeeds = True
        self.open_accepts = True
        self.take_accepts = True
        self.use_accepts = True
        self.delivery_arrives = True
        self.take_results = []
        self.pending_open = False
        self.pending_take = None
        self.pending_delivery = False
        self.respawn_at = None
        self.spawn_ghost_on_open = False

    def __enter__(self):
        DialogueWorld.__enter__(self)
        replacements = {
            'inventory': self,
            'locs': FakeModule(query=lambda: self.query(self.locations)),
            'npcs': FakeModule(query=lambda: self.query(self.scene)),
            'ground_items': FakeModule(query=lambda: self.query(self.drops)),
            'walk_with_hops': self.walk,
            'talk_through': self.talk,
        }
        self.ghost_saved = {}
        for name, value in replacements.items():
            self.ghost_saved[name] = getattr(ghost, name)
            setattr(ghost, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.ghost_saved.items():
            setattr(ghost, name, value)
        DialogueWorld.__exit__(self, *args)

    def query(self, objects):
        def supply(ids, names, radius, layer):
            return [obj for obj in objects if (names is None or obj.name in names)
                    and (radius is None or obj.distance() <= radius)]
        return EntityQuery(supply, lambda obj: True)

    def contains(self, name):
        assert name == ghost.SKULL
        return self.carried is not None

    def first(self, name):
        assert name == ghost.SKULL
        return self.carried

    def walk(self, tile, radius, hops, log):
        assert hops is ghost.WIZARD_HOPS
        self.walks.append((tile, radius))
        yield execution.Ticks(1)
        return self.walk_results.pop(0) if self.walk_results else True

    def talk(self, name, prefer, log):
        self.talks.append((name, prefer))
        yield execution.Ticks(1)
        return self.talk_succeeds

    def advance(self):
        DialogueWorld.advance(self)
        if self.pending_open:
            self.coffin.ops = ['Close']
            if self.spawn_ghost_on_open:
                self.scene.append(GhostObject(self, 'Restless ghost', ['Talk-to']))
            self.pending_open = False
        if self.pending_take is not None:
            if self.pending_take:
                self.carried = self.skull
            self.drops = []
            self.pending_take = None
        if self.respawn_at is not None and self.now >= self.respawn_at:
            self.drops = [self.skull]
            self.respawn_at = None
        if self.pending_delivery:
            self.carried = None
            self.pending_delivery = False

    def run(self, task):
        # Ten shared-spawn waits can span over eleven minutes of game time.
        for guard in range(2000):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            assert isinstance(wait, execution.Update) or isinstance(wait, execution.Ticks)
            self.waits.append(wait)
            self.now += 500
            self.advance()
        assert False, 'ghost workflow exceeded its simulated update budget'

    def grab(self):
        return self.run(ghost._grab_skull(self.logs.append))

    def trip(self):
        return self.run(ghost.ghost_and_skull(self.logs.append))

    def deliver(self):
        return self.run(ghost.return_skull(self.logs.append))


def test_ghost_opens_closed_coffin_and_waits_two_ticks():
    with GhostWorld() as world:
        world.run(ghost._ensure_coffin_open(world.logs.append))
        assert world.interactions == [('Coffin', 'Open')]
        assert len(world.waits) == 1 and world.waits[0].count == 2
        assert world.coffin.ops == ['Close']


def test_ghost_already_open_coffin_needs_no_interaction():
    with GhostWorld() as world:
        world.coffin.ops = ['Close']
        world.run(ghost._ensure_coffin_open(world.logs.append))
        assert world.interactions == [] and world.waits == []


def test_ghost_ignores_distant_or_unrelated_coffins():
    with GhostWorld() as world:
        world.coffin.dist = 7
        world.locations.append(GhostObject(world, 'Chest', ['Open']))
        world.run(ghost._ensure_coffin_open(world.logs.append))
        assert world.interactions == []


def test_ghost_grabs_skull_after_inventory_acknowledgement():
    with GhostWorld() as world:
        assert world.grab() and world.carried is world.skull
        assert world.interactions == [('Skull', 'Take')] and world.now == 500


def test_ghost_waits_for_missing_shared_skull_to_respawn():
    with GhostWorld() as world:
        world.drops = []
        world.respawn_at = 2500
        assert world.grab() and world.now == 3000
        assert 'already taken' in world.logs[0]
        assert world.interactions == [('Skull', 'Take')]


def test_ghost_lost_pickup_waits_for_respawn_then_retries():
    with GhostWorld() as world:
        world.take_results = [False, True]
        world.respawn_at = 10000
        assert world.grab() and world.now == 10500
        assert world.interactions == [('Skull', 'Take'), ('Skull', 'Take')]
        assert 'another quester' in world.logs[0]


def test_ghost_absent_skull_has_ten_bounded_respawn_waits():
    with GhostWorld() as world:
        world.drops = []
        assert world.grab() is False and world.now == 700000
        assert world.interactions == [] and len(world.logs) == 11
        assert 'never returned' in world.logs[-1]


def test_ghost_rejected_take_retries_without_claiming_success():
    with GhostWorld() as world:
        world.take_accepts = False
        assert world.grab() is False and world.carried is None
        assert len(world.interactions) == 10 and world.now == 80000


def test_ghost_skull_query_filters_name_and_distance():
    with GhostWorld() as world:
        world.skull.dist = 11
        world.drops.append(GhostObject(world, 'Bones', ['Take']))
        assert ghost._skull_near() is None
        world.skull.dist = 10
        assert ghost._skull_near() is world.skull


def test_ghost_trip_opens_coffin_talks_then_collects_skull():
    with GhostWorld() as world:
        assert world.trip() and world.carried is world.skull
        assert world.walks == [(ghost.COFFIN_STAND, 2), (ghost.SKULL_TILE, 2)]
        assert world.talks == [('Restless ghost', ghost.GHOST_PREFER)]
        assert world.interactions == [('Coffin', 'Open'), ('Skull', 'Take')]


def test_ghost_trip_failed_graveyard_walk_stops_before_opening():
    with GhostWorld() as world:
        world.walk_results = [False]
        assert world.trip() is False
        assert world.interactions == [] and world.talks == []


def test_ghost_trip_waits_for_ghost_spawn_after_opening():
    with GhostWorld() as world:
        world.scene = []
        world.spawn_ghost_on_open = True
        assert world.trip() and len(world.talks) == 1


def test_ghost_trip_missing_ghost_stops_before_tower_walk():
    with GhostWorld() as world:
        world.scene = []
        assert world.trip() is False and len(world.walks) == 1
        assert world.talks == [] and 'no ghost' in world.logs[-1]


def test_ghost_trip_distant_ghost_is_not_talked_to():
    with GhostWorld() as world:
        world.scene[0].dist = 9
        assert world.trip() is False and world.talks == []


def test_ghost_trip_failed_conversation_stops_before_tower_walk():
    with GhostWorld() as world:
        world.talk_succeeds = False
        assert world.trip() is False and len(world.walks) == 1
        assert world.interactions == [('Coffin', 'Open')]


def test_ghost_trip_failed_tower_walk_does_not_take_skull():
    with GhostWorld() as world:
        world.walk_results = [True, False]
        assert world.trip() is False and len(world.walks) == 2
        assert world.carried is None and world.interactions == [('Coffin', 'Open')]


def test_ghost_return_waits_for_skull_to_leave_inventory():
    with GhostWorld() as world:
        world.carried = world.skull
        assert world.deliver() and world.carried is None
        assert world.uses == [('Skull', 'Coffin')]
        assert world.walks == [(ghost.COFFIN_STAND, 2)]


def test_ghost_return_already_open_coffin_skips_open():
    with GhostWorld() as world:
        world.carried = world.skull
        world.coffin.ops = ['Close']
        assert world.deliver() and world.interactions == []


def test_ghost_return_failed_walk_preserves_skull():
    with GhostWorld() as world:
        world.carried = world.skull
        world.walk_results = [False]
        assert world.deliver() is False and world.carried is world.skull
        assert world.uses == [] and world.interactions == []


def test_ghost_return_missing_coffin_does_not_use_skull():
    with GhostWorld() as world:
        world.carried = world.skull
        world.locations = []
        assert world.deliver() is False and world.uses == []


def test_ghost_return_missing_skull_stops_without_item_use():
    with GhostWorld() as world:
        assert world.deliver() is False and world.uses == []


def test_ghost_return_rejected_use_preserves_skull_without_waiting():
    with GhostWorld() as world:
        world.carried = world.skull
        world.use_accepts = False
        assert world.deliver() is False and world.carried is world.skull
        assert len(world.waits) == 2


def test_ghost_return_unacknowledged_delivery_has_bounded_wait():
    with GhostWorld() as world:
        world.carried = world.skull
        world.delivery_arrives = False
        assert world.deliver() is False and world.carried is world.skull
        assert world.now == 9000
