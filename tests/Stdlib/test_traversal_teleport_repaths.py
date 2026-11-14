"""Failed teleport suppression reaches the next route request and preserves caller policy."""

import json
import rs2004.traversal as walker
from rs2004.geometry import Tile
from test_transport_crossings import TransportWorld


class TeleportPolicyWorld(TransportWorld):
    def __init__(self):
        TransportWorld.__init__(self)
        self.passable = True
        self.teleports.append({'teleportId': 'falador', 'family': 'spell', 'to': {'level': 0}})

    def find_world_path(self, text):
        request = json.loads(text)
        self.requests.append(request)
        start = request['from']
        end = request['to']
        points = [{'x': start[0], 'z': start[1], 'level': start[2]}]
        if request['use_teleport_catalog'] and 'falador' not in request['policy'].get('deny_teleport_ids', []):
            points.append({'x': 3300, 'z': 3200, 'level': 0, 'transport': {
                'kind': 'teleport', 'family': 'spell', 'loc_name': 'Falador teleport', 'action': 'Cast',
                'teleport_id': 'falador', 'to_tile': [3300, 3200]}})
        points.append({'x': end[0], 'z': end[1], 'level': end[2]})
        return json.dumps({'ok': True, 'cost': 10, 'expanded': 2, 'waypoints': points})


def test_failed_teleport_repaths_to_a_walking_alternative_and_stays_suppressed():
    for accepted in [True, False]:
        with TeleportPolicyWorld() as world:
            world.spell_ack = accepted
            walk = walker._Traversal()
            assert world.run(walk.walk_to(Tile(3310, 3200), radius=0, use_teleport_catalog=True))
            assert walk.last_outcome == 'arrived'
            assert world.here.equals(Tile(3310, 3200))
            assert len(world.spells) == 1 and len(world.requests) == 2
            assert world.requests[0]['policy']['deny_teleport_ids'] == []
            assert world.requests[1]['policy']['deny_teleport_ids'] == ['falador']
            assert walk._suppressed_teleports == ['falador'] and walk._door_strikes == {}
            world.here = Tile(3200, 3200)
            assert world.run(walk.walk_to(Tile(3310, 3200), radius=0, use_teleport_catalog=True))
            assert len(world.spells) == 1 and len(world.requests) == 3
            assert world.requests[2]['policy']['deny_teleport_ids'] == ['falador']


def test_caller_policy_cannot_override_new_or_existing_teleport_suppression():
    for already_suppressed in [True, False]:
        with TeleportPolicyWorld() as world:
            walk = walker._Traversal()
            if already_suppressed:
                walk._suppressed_teleports = ['falador']
            policy = {'deny_teleport_ids': ['varrock'], 'allow_teleport_ids': ['falador'], 'use_ships': False}
            assert world.run(walk.walk_to(Tile(3310, 3200), radius=0, use_teleport_catalog=True, policy=policy))
            assert walk.last_outcome == 'arrived'
            assert len(world.spells) == (0 if already_suppressed else 1)
            assert len(world.requests) == (1 if already_suppressed else 2)
            assert world.requests[-1]['policy']['deny_teleport_ids'] == ['varrock', 'falador']
            assert all([r['policy']['allow_teleport_ids'] == ['falador'] for r in world.requests])
            assert all([r['policy']['use_ships'] is False for r in world.requests])
            assert policy == {'deny_teleport_ids': ['varrock'], 'allow_teleport_ids': ['falador'], 'use_ships': False}


def test_suppression_merges_without_duplicates_or_mutating_direct_request_policy():
    with TeleportPolicyWorld() as world:
        walk = walker._Traversal()
        walk._suppressed_teleports = ['falador', 'camelot']
        policy = {'deny_teleport_ids': ['falador'], 'use_teleports': True}
        walk._request(world.here, Tile(3310, 3200), None, policy, True, [])
        assert world.requests[0]['policy']['deny_teleport_ids'] == ['falador', 'camelot']
        assert policy == {'deny_teleport_ids': ['falador'], 'use_teleports': True}


def test_delayed_success_remains_a_single_cast_without_suppression():
    with TeleportPolicyWorld() as world:
        def delayed_landing():
            if world.now >= 7500:
                world.here = Tile(3300, 3200)
                world.on_advance = None
        world.on_advance = delayed_landing
        walk = walker._Traversal()
        assert world.run(walk.walk_to(Tile(3310, 3200), radius=0, use_teleport_catalog=True))
        assert walk.last_outcome == 'arrived' and world.here.equals(Tile(3310, 3200))
        assert len(world.spells) == 1 and len(world.requests) == 1
        assert walk._suppressed_teleports == []
