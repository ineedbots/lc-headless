"""Random-event recovery waits for inventory changes and protects carried tools."""

import rs2004.random_events as events
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_dialogue_workflows import DialogueWorld


class RecoveryItem:
    def __init__(self, world, name, distance=1):
        self.world = world
        self.name = name
        self.dist = distance

    def distance(self):
        return self.dist

    def actions(self):
        return ['Wield'] if self.name == 'Bronze axe' else []

    def interact(self, op):
        self.world.item_clicks.append((self.name, op))
        if self.world.accept_items:
            self.world.pending_item = (op, self)
        return self.world.accept_items

    def use_on(self, handle):
        self.world.joins.append((self.name, handle.name))
        if self.world.join_lands:
            self.world.pending_join = (self, handle)
        return self.world.join_lands


class EventNpc:
    def __init__(self, world, name='Genie', id=409, distance=1):
        self.world = world
        self.name = name
        self.id = id
        self.dist = distance

    def distance(self):
        return self.dist

    def tile(self):
        return Tile(3001, 3000)

    def interact(self, op):
        assert op == 'Talk-to'
        self.world.talks += 1
        if self.world.talk_opens:
            self.world.pending_talk = True
        return self.world.talk_opens


class RecoveryWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.guardian = events._RandomEvents()
        self.pack = []
        self.worn = []
        self.drops = []
        self.scene = []
        self.capacity = 28
        self.position = Tile(3000, 3000)
        self.accept_items = True
        self.items_land = True
        self.unequip_lands = True
        self.join_lands = True
        self.pending_item = None
        self.pending_join = None
        self.pending_unequip = None
        self.pending_position = None
        self.pending_talk = False
        self.talk_opens = True
        self.talk_pages = [('continue', ['Hello']), ('options', ['Thank you'])]
        self.item_clicks = []
        self.joins = []
        self.equip_calls = []
        self.walks = []
        self.reachable = True
        self.reach_results = []
        self.reach_checks = []
        self.talks = 0

    def __enter__(self):
        DialogueWorld.__enter__(self)
        replacements = {
            '_core': self, 'inventory': self, 'local_tile': lambda: self.position,
            'equipment': FakeModule(items=lambda: self.worn, unequip=self.unequip, equip=self.equip),
            'ground_items': FakeModule(query=lambda: EntityQuery(self.ground_scene, lambda item: True)),
            'npcs': FakeModule(query=lambda: EntityQuery(self.npc_scene, lambda npc: True)),
            'direct_navigator': FakeModule(walk_to=self.navigate),
        }
        self.event_saved = {}
        for name, value in replacements.items():
            self.event_saved[name] = getattr(events, name)
            setattr(events, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.event_saved.items():
            setattr(events, name, value)
        DialogueWorld.__exit__(self, *args)

    def items(self):
        return self.pack

    def used(self):
        return len(self.pack)

    def is_full(self):
        return self.used() >= self.capacity

    def first(self, name):
        return [item for item in self.pack if item.name == name][0]

    def ground_scene(self, ids, names, radius, layer):
        return [item for item in self.drops if radius is None or item.distance() <= radius]

    def npc_scene(self, ids, names, radius, layer):
        return self.scene

    def carry(self, name):
        self.pack.append(RecoveryItem(self, name))

    def unequip(self, name):
        self.equip_calls.append(('unequip', name))
        if self.unequip_lands and not self.is_full():
            self.pending_unequip = self.worn[0]
            yield execution.Ticks(1)
            return True
        return False

    def equip(self, name):
        self.equip_calls.append(('equip', name))
        item = self.first(name)
        self.pack.remove(item)
        self.worn.append(item)
        yield execution.Ticks(1)
        return True

    def is_reachable(self, x, z):
        self.reach_checks.append((x, z))
        return self.reach_results.pop(0) if self.reach_results else self.reachable

    def navigate(self, tile, radius, timeout_ms):
        self.walks.append((tile, radius, timeout_ms))
        self.pending_position = tile
        yield execution.Ticks(1)
        return True

    def walk_to(self, x, z, run):
        self.walks.append((x, z, run))
        self.pending_position = Tile(x, z, self.position.level)
        return True

    def advance(self):
        DialogueWorld.advance(self)
        if self.pending_item is not None:
            op, item = self.pending_item
            if self.items_land:
                if op == 'Drop':
                    self.pack.remove(item)
                elif op == 'Take' and not self.is_full():
                    self.pack.append(item)
                    self.drops.remove(item)
            self.pending_item = None
        if self.pending_unequip is not None:
            self.worn.remove(self.pending_unequip)
            self.pack.append(self.pending_unequip)
            self.pending_unequip = None
        if self.pending_join is not None:
            head, handle = self.pending_join
            self.pack.remove(head)
            self.pack.remove(handle)
            self.carry('Bronze axe')
            self.pending_join = None
        if self.pending_position is not None:
            self.position = self.pending_position
            self.pending_position = None
        if self.pending_talk:
            self.pages = list(self.talk_pages)
            self.pending_talk = False

    def mend(self):
        return self.run(self.guardian._lost_tool(self.logs.append))

    def gear(self, name='small fishing net'):
        return self.run(self.guardian._lost_gear(name, self.logs.append))

    def free_slot(self):
        return self.run(self.guardian._free_slot(self.logs.append))


def test_random_free_slot_with_space_does_not_drop():
    with RecoveryWorld() as world:
        world.carry('Logs')
        world.free_slot()
        assert world.item_clicks == [] and world.waits == []


def test_random_free_slot_drops_most_numerous_disposable_item():
    with RecoveryWorld() as world:
        world.capacity = 4
        for name in ['Bronze axe', 'Logs', 'Logs', 'Coins']:
            world.carry(name)
        world.free_slot()
        assert world.item_clicks == [('Logs', 'Drop')]
        assert world.used() == 3 and not world.is_full()


def test_random_free_slot_preserves_tools_heads_and_handles():
    with RecoveryWorld() as world:
        world.capacity = 3
        for name in ['Bronze axe handle', 'Bronze axe head', 'Small fishing net']:
            world.carry(name)
        world.free_slot()
        assert world.item_clicks == [] and world.waits == []
        assert 'nothing in it can go' in world.logs[-1]


def test_random_free_slot_unacknowledged_drop_has_bounded_wait():
    with RecoveryWorld() as world:
        world.capacity = 1
        world.carry('Logs')
        world.items_land = False
        world.free_slot()
        assert world.used() == 1 and world.now == 4000


def test_random_lost_tool_without_handle_is_failure():
    with RecoveryWorld() as world:
        world.carry('Bronze axe head')
        assert world.mend() is False
        assert world.joins == [] and world.waits == []


def test_random_lost_tool_combines_carried_head_and_handle():
    with RecoveryWorld() as world:
        world.carry('Bronze axe handle')
        world.carry('Bronze axe head')
        assert world.mend()
        assert world.joins == [('Bronze axe head', 'Bronze axe handle')]
        assert [item.name for item in world.pack] == ['Bronze axe']
        assert world.logs[-1] == 'random event: tool mended'
        assert world.equip_calls == []


def test_random_lost_tool_collects_ground_head_before_combining():
    with RecoveryWorld() as world:
        world.carry('Bronze axe handle')
        world.drops = [RecoveryItem(world, 'Bronze axe head')]
        assert world.mend()
        assert world.item_clicks == [('Bronze axe head', 'Take')]
        assert [item.name for item in world.pack] == ['Bronze axe']


def test_random_lost_tool_ignores_distant_and_unrelated_ground_items():
    with RecoveryWorld() as world:
        world.carry('Bronze axe handle')
        world.drops = [RecoveryItem(world, 'Logs'), RecoveryItem(world, 'Bronze axe head', distance=13)]
        assert world.mend()
        assert world.item_clicks == [] and world.joins == []
        assert 'head or the handle is still missing' in world.logs[-1]


def test_random_lost_tool_unequips_handle_and_reequips_repaired_axe():
    with RecoveryWorld() as world:
        world.worn = [RecoveryItem(world, 'Bronze axe handle')]
        world.drops = [RecoveryItem(world, 'Bronze axe head')]
        assert world.mend()
        assert world.equip_calls == [('unequip', 'Bronze axe handle'), ('equip', 'Bronze axe')]
        assert world.pack == [] and world.worn[0].name == 'Bronze axe'


def test_random_lost_tool_makes_room_for_worn_handle_and_ground_head():
    with RecoveryWorld() as world:
        world.capacity = 3
        for name in ['Logs', 'Logs', 'Logs']:
            world.carry(name)
        world.worn = [RecoveryItem(world, 'Bronze axe handle')]
        world.drops = [RecoveryItem(world, 'Bronze axe head')]
        assert world.mend()
        assert world.item_clicks == [('Logs', 'Drop'), ('Logs', 'Drop'), ('Bronze axe head', 'Take')]
        assert world.worn[0].name == 'Bronze axe' and world.used() == 1


def test_random_lost_tool_failed_unequip_stops_before_head_pickup():
    with RecoveryWorld() as world:
        world.worn = [RecoveryItem(world, 'Bronze axe handle')]
        world.unequip_lands = False
        assert world.mend() is False
        assert world.item_clicks == [] and world.joins == []


def test_random_lost_tool_no_disposable_slot_cannot_unequip_handle():
    with RecoveryWorld() as world:
        world.capacity = 1
        world.carry('Fishing rod')
        world.worn = [RecoveryItem(world, 'Bronze axe handle')]
        assert world.mend() is False
        assert world.worn[0].name == 'Bronze axe handle' and world.item_clicks == []


def test_random_lost_tool_unacknowledged_head_pickup_is_logged():
    with RecoveryWorld() as world:
        world.carry('Bronze axe handle')
        world.drops = [RecoveryItem(world, 'Bronze axe head')]
        world.items_land = False
        assert world.mend()
        assert world.now == 6000 and world.joins == []
        assert 'head or the handle is still missing' in world.logs[-1]


def test_random_lost_tool_unacknowledged_join_times_out_without_reequipping():
    with RecoveryWorld() as world:
        world.carry('Bronze axe handle')
        world.carry('Bronze axe head')
        world.join_lands = False
        assert world.mend()
        assert world.now == 5000 and world.used() == 2
        assert world.logs[-1] == 'random event: the tool did not mend'


def test_random_lost_gear_matches_name_without_case_and_waits_for_pickup():
    with RecoveryWorld() as world:
        world.drops = [RecoveryItem(world, 'Small fishing net', distance=10)]
        assert world.gear()
        assert world.item_clicks == [('Small fishing net', 'Take')]
        assert world.used() == 1 and world.logs[-1] == 'random event: small fishing net recovered'


def test_random_lost_gear_ignores_unrelated_or_distant_items():
    with RecoveryWorld() as world:
        world.drops = [RecoveryItem(world, 'Big fishing net'), RecoveryItem(world, 'Small fishing net', distance=11)]
        assert world.gear() is False
        assert world.waits == [] and world.item_clicks == []


def test_random_lost_gear_failed_pickup_has_bounded_wait_and_log():
    with RecoveryWorld() as world:
        world.drops = [RecoveryItem(world, 'Small fishing net')]
        world.accept_items = False
        assert world.gear()
        assert world.now == 8000 and world.used() == 0
        assert world.logs[-1] == 'random event: could not pick up the small fishing net'


def test_random_hazard_uses_first_reachable_escape_and_waits_out_hazard():
    with RecoveryWorld() as world:
        world.reach_results = [False, True]
        assert world.run(world.guardian._hazard('smoking rock', Tile(3001, 3000), world.logs.append))
        assert len(world.reach_checks) == 2 and len(world.walks) == 1
        assert world.walks[0][1:] == (1, 15000)
        assert world.position.distance_to(Tile(3001, 3000)) >= 4
        assert world.waits[-1].count == 60


def test_random_hazard_without_source_uses_current_tile():
    with RecoveryWorld() as world:
        assert world.run(world.guardian._hazard('gas chest', None, world.logs.append))
        assert world.position.distance_to(Tile(3000, 3000)) == events.HAZARD_STEP


def test_random_hazard_no_reachable_escape_still_waits_for_expiry():
    with RecoveryWorld() as world:
        world.reachable = False
        assert world.run(world.guardian._hazard('smoking rock', None, world.logs.append))
        assert world.walks == [] and len(world.reach_checks) == 8
        assert len(world.waits) == 1 and world.waits[0].count == 60


def test_random_ent_missing_or_distant_does_not_stop_chopping():
    with RecoveryWorld() as world:
        world.scene = [EventNpc(world, id=1), EventNpc(world, id=444, distance=2)]
        assert world.run(world.guardian._hijack(world.logs.append)) is False
        assert world.walks == [] and world.waits == []


def test_random_ent_steps_away_and_sets_lifetime_cooldown():
    with RecoveryWorld() as world:
        world.scene = [EventNpc(world, name='Ent', id=444)]
        world.reach_results = [False, True]
        assert world.run(world.guardian._hijack(world.logs.append))
        assert len(world.reach_checks) == 2 and len(world.walks) == 1
        assert world.walks[0][2] is False
        assert world.guardian.cooldown_until['hijack:ent'] == world.now + events.ENT_LIFE_MS + 4000


def test_random_ent_no_reachable_neighbor_still_tries_furthest_step():
    with RecoveryWorld() as world:
        world.scene = [EventNpc(world, name='Ent', id=444)]
        world.reachable = False
        assert world.run(world.guardian._hijack(world.logs.append))
        assert len(world.reach_checks) == 8 and len(world.walks) == 1


def test_random_dialogue_missing_npc_is_failure():
    with RecoveryWorld() as world:
        assert world.run(world.guardian._dialog('genie', world.logs.append)) is False
        assert world.talks == 0 and world.waits == []


def test_random_dialogue_drives_continue_and_option_pages():
    with RecoveryWorld() as world:
        world.scene = [EventNpc(world)]
        assert world.run(world.guardian._dialog('genie', world.logs.append))
        assert world.talks == 1 and world.clicks == ['continue', 110]
        assert not world.pages and world.logs[-1] == 'random event: genie answered'


def test_random_dialogue_waiting_page_is_bounded():
    with RecoveryWorld() as world:
        world.scene = [EventNpc(world)]
        world.talk_pages = [('waiting', ['Loading'])]
        assert world.run(world.guardian._dialog('genie', world.logs.append))
        assert len(world.waits) == 26 and world.clicks == []


def test_random_dialogue_no_response_bounds_opening_wait():
    with RecoveryWorld() as world:
        world.scene = [EventNpc(world)]
        world.talk_opens = False
        world.run(world.guardian._dialog('genie', world.logs.append))
        assert world.now == 5000 and world.clicks == []
