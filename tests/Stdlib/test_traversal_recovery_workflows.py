"""Traversal escalates failed routes, funds hops and confirms object crossings."""

import rs2004.traversal as walker
import rs2004.routeplan as routes
import rs2004.bank as vault
from rs2004 import execution
from rs2004.geometry import Tile
from rs2004.walkgeom import PathTile
from helpers import FakeModule
from test_transport_crossings import TransportWorld, Entity


class RouteWorld(TransportWorld):
    def patch(self, owner, name, value):
        self.saved.append((owner, name, getattr(owner, name)))
        setattr(owner, name, value)

    def direct(self, tile, radius, timeout, *args):
        self.walks.append((tile, radius))
        yield execution.Ticks(1)
        return False


class ScriptedTraversal(walker._Traversal):
    def __init__(self, world):
        walker._Traversal.__init__(self)
        self.world = world
        self.outcomes = []
        self.probe_ok = False
        self.probe_terminal = Tile(3300, 3200)
        self.walk_ok = True

    def walk_to(self, dest, *args, **kwargs):
        self.world.walks.append(dest)
        yield execution.Ticks(1)
        if self.outcomes:
            self.last_outcome = self.outcomes.pop(0)
        else:
            self.last_outcome = 'failed'
        return self.walk_ok

    def _request(self, *args, **kwargs):
        end = self.probe_terminal
        return {'ok': self.probe_ok, 'cost': 1, 'waypoints': [{'x': end.x, 'z': end.z, 'level': end.level}]}


class FundedTraversal(ScriptedTraversal):
    def __init__(self, world):
        ScriptedTraversal.__init__(self, world)
        self.failed_leg = None

    def _request(self, me, dest, *args, **kwargs):
        bank_leg = dest.x == 3201
        points = [{'x': dest.x, 'z': dest.z, 'level': dest.level}]
        if not bank_leg:
            points[0]['transport'] = {'teleport_id': 'funded'}
        return {'ok': self.failed_leg != ('bank' if bank_leg else 'destination'), 'cost': 1, 'waypoints': points}


class MainTraversal(walker._Traversal):
    def __init__(self):
        walker._Traversal.__init__(self)
        self.result = 'arrived'
        self.fund_once = False
        self.underfunded = False
        self.funded = False
        self.followed = 0

    def _request(self, me, dest, *args, **kwargs):
        if self.underfunded and not self.funded:
            return {'ok': False, 'reason': 'unreachable'}
        return {'ok': True, 'cost': 1, 'expanded': 1,
                'waypoints': [{'x': me.x, 'z': me.z, 'level': me.level}, {'x': dest.x, 'z': dest.z, 'level': dest.level}]}

    def _explain_unreachable(self, *args):
        return [routes.MissingItem('Coins', 30)] if self.underfunded else []

    def _maybe_bank_for_route(self, *args):
        if self.fund_once and not self.funded:
            yield execution.Ticks(1)
            self.funded = True
            return True
        return False

    def _follow(self, *args):
        self.followed += 1
        yield execution.Ticks(1)
        return self.result


def test_resilient_walk_escalates_to_scene_unstick_and_dead_or_repeated_probe():
    for fresh in [True, False]:
        with RouteWorld() as world:
            world.passable = True
            world.patch(walker, 'direct_navigator', FakeModule(walk_to=world.direct))
            walk = ScriptedTraversal(world)
            walk.probe_ok = fresh
            assert world.run(walk.walk_resilient(Tile(3400, 3200), radius=0, log=world.logs.append)) is False
            assert walk.last_outcome == 'unreachable' and world.walks
            assert any(['verify probe' in line for line in world.logs])


def test_resilient_walk_pass_limit_blocked_outcome_and_missing_items():
    for outcome in ['failed', 'blocked', 'unreachable']:
        with RouteWorld() as world:
            world.patch(walker, 'direct_navigator', FakeModule(walk_to=world.direct))
            walk = ScriptedTraversal(world)
            walk.outcomes = [outcome]
            if outcome == 'unreachable':
                walk.last_missing_gate_items = [routes.MissingItem('Coins', 30)]
            result = world.run(walk.walk_resilient(Tile(3400, 3200), radius=0, attempts=1))
            assert result == (outcome == 'blocked')


def test_resilient_walk_runtime_interrupt_stops_before_route_request():
    with RouteWorld() as world:
        world.patch(execution, 'event_signal', FakeModule(pending=lambda: True))
        walk = ScriptedTraversal(world)
        assert world.run(walk.walk_resilient(Tile(3400, 3200))) is False
        assert walk.last_outcome == 'interrupted' and world.walks == []


def test_bank_ranking_checks_access_and_prices_reachable_candidates():
    with RouteWorld() as world:
        banks = [{'name': 'Near', 'tile': {'x': 3201, 'z': 3200, 'level': 0}},
                 {'name': 'Far', 'tile': {'x': 3300, 'z': 3200, 'level': 0}}]
        world.patch(walker, 'bank_locations', lambda: banks)
        assert walker.approach_of(banks[0]) == Tile(3201, 3200)
        assert walker.nearest_walkable_bank(world.here, lambda a, b: 10 if b.x == 3300 else None) is banks[1]
        nav = FakeModule(find_path=lambda start, dest, **kwargs: FakeModule(ok=dest.x == 3300, cost=5))
        assert walker.nearest_bank_reachable(world.here, nav) is banks[0]
        world.here = Tile(3100, 3200)
        assert walker.nearest_bank_reachable(world.here, nav) is banks[1]
        banks[0]['requires'] = {'quest': 'Quest'}
        assert walker.locked_bank_at(Tile(3201, 3200)) is banks[0]
        assert walker.locked_bank_at(Tile(3400, 3200)) is None
        assert not walker.bank_unlocked({'requires': {'skill': {'name': 'mining', 'level': 90}}})
        assert not walker.bank_unlocked(banks[0])


def test_scene_probe_reads_walk_flags_and_entity_adjacent_reach():
    with RouteWorld() as world:
        world.passable = True
        probe = walker._Probe()
        assert probe.walkable(world.here) and probe.can_reach_adjacent(world.here) and probe.probeable(world.here)
        world.patch(walker, '_core', FakeModule(walk_tile=lambda *args: None, is_reachable=lambda x, z: False))
        assert not probe.walkable(world.here)


def test_special_object_crossing_confirms_arrival_and_checks_key_use():
    for keyed in [True, False]:
        with RouteWorld() as world:
            approach, dest = world.here, Tile(3202, 3200)
            transport = {'loc_name': 'Gate', 'action': 'Open', 'loc_x': 3200, 'loc_z': 3200}
            gate = Entity(world, 'Gate', ['Open'])
            gate.on_interact = lambda op: world.events.append(('land', dest)) or True
            world.loc_items = [gate]
            crossing = {'locName': 'Gate', 'action': 'Open', 'x': 3200, 'z': 3200}
            if keyed:
                crossing['useItem'] = {'name': 'Key'}
                key = FakeModule(use_on=lambda target: world.events.append(('land', dest)) or True)
                world.patch(walker, 'inventory', FakeModule(first=lambda name: key))
            walk = walker._Traversal()
            assert world.run(walk._special_crossing(approach, PathTile(dest.x, dest.z, 0, transport), crossing, world.logs.append))
            assert world.here == dest


def test_special_crossing_missing_key_refused_click_and_silent_arrival():
    for failure in ['key', 'click', 'silent', 'missing']:
        with RouteWorld() as world:
            transport = {'loc_name': 'Gate', 'action': 'Open', 'loc_x': 3200, 'loc_z': 3200}
            crossing = {'locName': 'Gate', 'action': 'Open', 'x': 3200, 'z': 3200}
            gate = Entity(world, 'Gate', ['Open'])
            world.loc_items = [] if failure == 'missing' else [gate]
            if failure == 'key':
                crossing['useItem'] = {'name': 'Key'}
                world.patch(walker, 'inventory', FakeModule(first=lambda name: None))
            elif failure == 'click':
                gate.on_interact = lambda op: False
            walk = walker._Traversal()
            assert world.run(walk._special_crossing(world.here, PathTile(3202, 3200, 0, transport), crossing, world.logs.append)) is False


def test_special_missing_open_gate_can_already_be_passable_or_crossed():
    with RouteWorld() as world:
        world.passable = True
        transport = {'loc_name': 'Gate', 'action': 'Open', 'loc_x': 3200, 'loc_z': 3200}
        crossing = {'locName': 'Gate', 'action': 'Open', 'x': 3200, 'z': 3200}
        walk = walker._Traversal()
        assert world.run(walk._special_crossing(world.here, PathTile(3202, 3200, 0, transport), crossing, world.logs.append))
        assert world.here == Tile(3202, 3200)


def test_transport_dialogue_drives_choices_continues_and_idle_ticks():
    with RouteWorld() as world:
        walk = walker._Traversal()
        world.dialogue.open, world.dialogue.choices = True, ['Yes', 'No']
        world.run(walk._dialogue_step(['Yes']))
        assert world.dialogue.chosen == ['Yes']
        world.dialogue.open = True
        world.run(walk._dialogue_step([]))
        assert world.dialogue.continued == 1
        world.run(walk._dialogue_step([]))
        assert world.waits[-1].count == 1


def test_nearby_door_opens_and_route_helpers_preserve_layer_and_distance():
    with RouteWorld() as world:
        gate = Entity(world, 'Door', ['Open'])
        world.loc_items = [gate]
        gate.on_interact = lambda op: world.events.append(('open', gate)) or True
        assert world.run(walker._Traversal().try_nearby_door(world.logs.append))
        assert gate.ops == ['Close']
        assert walker._near_route(gate.tile(), [Tile(3201, 3200)])
        assert not walker._near_route(gate.tile(), [Tile(3400, 3200)])
        assert walker._open_leaf_near({'loc_name': 'Door', 'loc_x': 3200, 'loc_z': 3200}) is gate
        assert walker._name_aliases('Staircase') and walker._name_aliases('Stairs')


def test_jewellery_unknown_id_failed_rub_and_no_dialogue_requirement():
    with RouteWorld() as world:
        walk = walker._Traversal()
        assert not world.run(walk._rub_jewellery(None, {'teleport_id': 'unknown'}, world.logs.append))
        item = Entity(world, 'Ring of dueling', ['Rub'])
        world.held = [item]
        teleport = {'family': 'jewellery', 'teleportId': 'ring', 'itemNameMatch': ['Ring of dueling']}
        item.on_interact = lambda op: False
        assert not world.run(walk._rub_jewellery(teleport, {}, world.logs.append))
        item.on_interact = lambda op: True
        assert world.run(walk._rub_jewellery(teleport, {}, world.logs.append))


def test_post_quest_unlock_talks_once_and_returns_to_crossing():
    with RouteWorld() as world:
        talk = {'loc_x': 3200, 'loc_z': 3200, 'level': 0, 'require_complete': 'Quest', 'npc': 'Guard',
                'stand': Tile(3201, 3200), 'choose': ['Yes'], 'talks': 1, 'label': 'unlock'}
        world.patch(walker, 'post_quest_talk_for', lambda *args: talk)
        transport = {'loc_x': 3200, 'loc_z': 3200}
        walk = ScriptedTraversal(world)
        assert not world.run(walk._post_quest_talk(transport, world.here, world.logs.append))
        world.quest_statuses['Quest'] = 'complete'
        npc = Entity(world, 'Guard', ['Talk-to'])
        npc.on_interact = lambda op: world.events.append(('dialogue', (['Yes'], []))) or True
        world.npc_items = [npc]
        assert world.run(walk._post_quest_talk(transport, world.here, world.logs.append))
        assert world.dialogue.chosen == ['Yes'] and len(world.walks) == 2
        assert not world.run(walk._post_quest_talk(transport, world.here, world.logs.append))


def test_walk_bank_plan_withdraws_missing_fare_before_replanning():
    for failure in ['none', 'walk', 'open', 'bank', 'destination']:
        with RouteWorld() as world:
            state = {'open': False, 'items': {}}
            def opened(**kwargs):
                yield execution.Ticks(1)
                state['open'] = failure != 'open'
                return state['open']
            def withdraw(name, count):
                state['items'][name] = count
                yield execution.Ticks(1)
                return True
            def close():
                state['open'] = False
                yield execution.Ticks(1)
                return True
            world.patch(vault, 'bank', FakeModule(is_open=lambda: state['open'], items=lambda: [], withdraw_x=withdraw, close=close))
            world.patch(vault, 'banking', FakeModule(open=opened))
            world.patch(walker, 'world_state', lambda: {'items': state['items'], 'worn': {}, 'quests': {}})
            world.patch(walker, 'nearest_bank', lambda *args, **kwargs: {'name': 'Bank', 'tile': {'x': 3201, 'z': 3200, 'level': 0}})
            world.patch(walker, 'gate_item_candidates', lambda: {'Coins': 30})
            world.patch(routes, '_teleports', [{'teleportId': 'funded', 'requires': {'items': [{'name': 'Coins', 'count': 30}]}}])
            walk = FundedTraversal(world)
            walk.walk_ok = failure != 'walk'
            walk.failed_leg = failure
            assert world.run(walk._maybe_bank_for_route(world.here, Tile(3300, 3200), None, None, 1000, {}, False, [], world.logs.append)) == (failure == 'none')
            if failure == 'none':
                assert state['items'] == {'Coins': 30} and not state['open'] and walk._bank_leg_done
                assert not walk._in_bank_leg


def test_walk_route_cost_missing_items_explanation_and_cached_bank_counts():
    with RouteWorld() as world:
        world.patch(routes, '_teleports', [{'teleportId': 'funded', 'requires': {'items': [{'name': 'Coins', 'count': 30}]}}])
        walk = FundedTraversal(world)
        assert walk.route_cost(world.here, Tile(3300, 3200)) == 1
        walk.failed_leg = 'destination'
        assert walk.route_cost(world.here, Tile(3300, 3200)) is None
        walk.failed_leg = None
        missing = walk._explain_unreachable(world.here, Tile(3300, 3200), 'unreachable', 1000, {}, False, [])
        assert missing == [routes.MissingItem('Coins', 30)]
        points = [PathTile(3300, 3200, 0, {'teleport_id': 'funded'})]
        assert not walk._check_route_items(points, world.logs.append)
        assert walk.last_outcome == 'unreachable'
        walk._bank_item_counts = {'Coins': 30}
        assert walk._read_bank_item_counts() == {'Coins': 30}


def test_missing_door_can_be_crossed_when_passable_and_failed_open_is_bounded():
    for passable in [True, False]:
        with RouteWorld() as world:
            world.passable = passable
            world.walk_ack = passable
            transport = {'kind': 'door', 'loc_name': 'Door', 'action': 'Open', 'loc_x': 3200, 'loc_z': 3200}
            walk = walker._Traversal()
            result = world.run(walk._cross_door(world.here, Tile(3202, 3200), transport, world.logs.append))
            assert result == passable
    with RouteWorld() as world:
        door = Entity(world, 'Door', ['Open'])
        world.loc_items = [door]
        transport = {'kind': 'door', 'loc_name': 'Door', 'action': 'Open', 'loc_x': 3200, 'loc_z': 3200}
        assert not world.run(walker._Traversal()._cross_door(world.here, Tile(3202, 3200), transport, world.logs.append))
        assert any(['did not open' in line for line in world.logs])


def test_a_door_that_walks_you_through_and_shuts_again_counts_as_crossed():
    with RouteWorld() as world:
        door = Entity(world, 'Door', ['Open'])
        world.loc_items = [door]

        # Tenzing's door: the script moves you to the far side and the loc never reads open.
        def walk_through(action):
            world.here = Tile(3202, 3200)
            return True

        door.on_interact = walk_through
        transport = {'kind': 'door', 'loc_name': 'Door', 'action': 'Open', 'loc_x': 3200, 'loc_z': 3200}
        walk = walker._Traversal()
        assert world.run(walk._cross_door(world.here, Tile(3202, 3200), transport, world.logs.append))
        assert not any(['did not open' in line for line in world.logs])


def test_post_quest_unlock_failed_walk_missing_npc_and_silent_talk():
    for failure in ['walk', 'missing', 'silent', 'continue']:
        with RouteWorld() as world:
            talk = {'loc_x': 3200, 'loc_z': 3200, 'level': 0, 'require_complete': 'Quest', 'npc': 'Guard',
                    'stand': Tile(3201, 3200), 'choose': [], 'talks': 1, 'label': 'unlock'}
            world.patch(walker, 'post_quest_talk_for', lambda *args: talk)
            world.quest_statuses['Quest'] = 'complete'
            npc = Entity(world, 'Guard', ['Talk-to'])
            if failure == 'continue':
                npc.on_interact = lambda op: world.events.append(('dialogue', ([], ['Hello']))) or True
            world.npc_items = [] if failure == 'missing' else [npc]
            walk = ScriptedTraversal(world)
            walk.walk_ok = failure != 'walk'
            result = world.run(walk._post_quest_talk({'loc_x': 3200, 'loc_z': 3200}, world.here, world.logs.append))
            assert result == (failure == 'continue')


def test_world_walk_orchestration_propagates_follower_outcomes_and_repath_limit():
    for outcome in ['arrived', 'interrupted', 'repath']:
        with RouteWorld() as world:
            walk = MainTraversal()
            walk.result = outcome
            assert world.run(walk.walk_to(Tile(3300, 3200), radius=0, timeout_ms=120000,
                force_repath=True, policy={'use_teleports': False})) == (outcome == 'arrived')
            assert walk.last_outcome == ('failed' if outcome == 'repath' else outcome)
            assert walk.followed == (walker.MAX_REPATHS + 1 if outcome == 'repath' else 1)


def test_world_walk_immediate_arrival_and_expired_budget():
    with RouteWorld() as world:
        walk = MainTraversal()
        assert world.run(walk.walk_to(world.here, radius=0)) and walk.followed == 0
        assert world.run(walk.walk_to(Tile(3300, 3200), radius=0, timeout_ms=0)) is False
        assert walk.last_outcome == 'failed' and walk.followed == 0


def test_world_walk_replans_once_after_funding_reachable_or_unreachable_route():
    for underfunded in [True, False]:
        with RouteWorld() as world:
            walk = MainTraversal()
            walk.fund_once, walk.underfunded = True, underfunded
            assert world.run(walk.walk_to(Tile(3300, 3200), radius=0))
            assert walk.funded and walk._bank_leg_done and walk.followed == 1


def test_object_transport_without_level_change_confirms_destination():
    with RouteWorld() as world:
        npc = Entity(world, 'Aubury', ['Teleport'])
        # Object transport dispatch is also used by named portals in the mine.
        world.loc_items = [npc]
        dest = Tile(3300, 3200)
        npc.on_interact = lambda op: world.events.append(('land', dest)) or True
        transport = {'loc_name': 'Aubury', 'action': 'Teleport', 'loc_x': 3200, 'loc_z': 3200,
                     'to_tile': [3300, 3200]}
        walk = walker._Traversal()
        assert world.run(walk._use_transport_loc(world.here, PathTile(dest.x, dest.z, 0, transport), transport, world.logs.append))
        assert world.here == dest and any(['essence session' in line for line in world.logs])


def test_transport_scenery_aliases_and_nearby_fallback_find_stairs():
    with RouteWorld() as world:
        loc = Entity(world, 'Stone stairs', ['Climb-up'], Tile(3201, 3200))
        world.loc_items = [loc]
        transport = {'loc_name': 'Staircase', 'action': 'Climb-up', 'loc_x': 3200, 'loc_z': 3200}
        assert walker.find_transport_loc(transport) is loc
        assert walker._near_landing({'toTile': {'x': 3200, 'z': 3200, 'level': 1}}, 1) is False


def test_walker_bank_snapshot_skips_nameless_items_and_copies_counts():
    with RouteWorld() as world:
        world.patch(vault, 'bank', FakeModule(is_open=lambda: True,
            items=lambda: [FakeModule(name='Coins', count=30), FakeModule(name=None, count=1)]))
        assert walker._Traversal()._read_bank_item_counts() == {'Coins': 30}


def test_npc_transport_answers_continue_and_map_before_closing_modal():
    for has_button in [True, False]:
        with RouteWorld() as world:
            state = {'modal': True}
            dest = Tile(3300, 3300)
            npc = Entity(world, 'Pilot', ['Talk-to'])
            def greet(op):
                world.dialogue.open = True
                world.dialogue.lines = ['Choose your destination']
                return True
            npc.on_interact = greet
            world.npc_items = [npc]
            def click(id):
                assert id == 9
                world.events.append(('land', dest))
                return True
            def close():
                state['modal'] = False
                yield execution.Ticks(1)
            world.patch(walker, 'modals', FakeModule(is_open=lambda: state['modal'], close=close))
            world.patch(walker, 'interfaces', FakeModule(button_near_text=lambda *args: 9 if has_button else None, click=click))
            world.patch(walker, '_core', FakeModule(get_main_modal=lambda: 100))
            crossing = {'npc': 'Pilot', 'action': 'Talk-to', 'x': 3200, 'z': 3200, 'level': 0,
                        'mapChoice': 'Destination', 'toTile': {'x': 3300, 'z': 3300, 'level': 0}}
            walk = walker._Traversal()
            assert world.run(walk._npc_crossing(crossing, 'Glider', [], 1, world.here, world.logs.append)) == has_button
            assert world.dialogue.continued == 1
            if has_button:
                assert world.here == dest and not state['modal']


def test_npc_transport_closes_unrelated_modal_then_waits_for_landing():
    with RouteWorld() as world:
        state = {'modal': True}
        npc = Entity(world, 'Pilot', ['Talk-to'])
        world.npc_items = [npc]
        def close():
            state['modal'] = False
            yield execution.Ticks(1)
        world.patch(walker, 'modals', FakeModule(is_open=lambda: state['modal'], close=close))
        crossing = {'npc': 'Pilot', 'action': 'Talk-to', 'x': 3200, 'z': 3200, 'level': 0,
                    'toTile': {'x': 3300, 'z': 3300, 'level': 0}}
        assert not world.run(walker._Traversal()._npc_crossing(crossing, 'Glider', [], 1, world.here, world.logs.append))
        assert not state['modal'] and world.here == Tile(3200, 3200)


def test_transport_nearby_placement_fallback_and_already_crossed_door():
    with RouteWorld() as world:
        loc = Entity(world, 'Ladder', ['Climb-up'], Tile(3204, 3200))
        world.loc_items = [loc]
        assert walker.find_transport_loc({'loc_name': 'Ladder', 'action': 'Climb-up', 'loc_x': 3200, 'loc_z': 3200}) is loc
        approach = world.here
        world.here = Tile(3202, 3200)
        transport = {'loc_name': 'Door', 'action': 'Open', 'loc_x': 3200, 'loc_z': 3200}
        assert world.run(walker._Traversal()._cross_door(approach, world.here, transport, world.logs.append))
        assert world.walks == []
