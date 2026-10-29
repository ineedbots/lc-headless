"""Vendor level transitions, danger-zone decoding and walker escalation boundaries."""

import _core
import rs2004.walkgeom as geom
import rs2004.entities as entities
import rs2004.traversal as routes
import rs2004.catalogs.tool_acquire as acquire
import rs2004.catalogs.combat as combat
import rs2004.items as items
import rs2004.tabs as tabs
import rs2004.random_events as randoms
from rs2004 import execution, _runtime
from rs2004.geometry import Tile
from helpers import FakeModule, raises
from coverage_world import PatchWorld


def test_walkgeom_zone_decode_and_unstick_compass_order():
    zone = geom._zone_from_json({'id': 'zone', 'rects': [{'minX': 1, 'maxX': 2, 'minZ': 3, 'maxZ': 4}], 'automatic': True})
    assert zone['rects'] == [{'min_x': 1, 'max_x': 2, 'min_z': 3, 'max_z': 4, 'level': None}]
    assert zone['automatic'] and zone['label'] is None
    assert geom.resolve_danger_zones(['zone', 'zone'], known=[zone]) == zone['rects']
    assert geom.pick_unstick_step(lambda dx, dz: dx == 1 and dz == 0, 0) == (1, 0)
    assert geom.pick_unstick_step(lambda dx, dz: False, 3) is None
    assert geom.expand_waypoints([]) == []
    assert 'Climb-up' in repr(geom.PathTile(1, 2, 1, {'action': 'Climb-up', 'loc_name': 'Ladder'}))
    assert 'LadderState' in repr(geom.LadderState(5))
    state = geom.LadderState(10)
    assert geom.advance(state, 9, False, False, 'failed')[0] == ('world', False)
    assert geom.advance(state, 10, False, True, None)[0] == ('interrupted',)
    assert geom.advance(state, 10, False, False, 'budget')[0] == ('world', True)
    assert geom.advance(geom.LadderState(10, phase='verify'), 10, False, False, 'probe-fresh')[0][0] == 'backoff'


class VendorWorld(PatchWorld):
    def __init__(self):
        PatchWorld.__init__(self)
        self.position = Tile(3019, 3449)
        self.walks = []
        self.walk_results = []
        self.entered = True
        self.actions = []
        self.traps = []

    def __enter__(self):
        PatchWorld.__enter__(self)
        self.patch(entities, 'local_tile', lambda: self.position)
        self.patch(entities, 'locs', FakeModule(query=lambda: entities.EntityQuery(self.scene, lambda obj: True)))
        self.patch(routes, 'traversal', FakeModule(walk_resilient=self.walk))
        self.patch(_core, 'get_z', lambda: self.position.z)
        return self

    def scene(self, ids, names, radius, layer):
        return self.traps

    def walk(self, tile, **kwargs):
        self.walks.append(tile)
        yield execution.Ticks(1)
        return self.walk_results.pop(0) if self.walk_results else True

    def interact(self, op):
        self.actions.append(op)
        if self.entered:
            self.position = Tile(3019, 9849)
        return True

    def trap(self, op='Climb-down'):
        self.traps = [FakeModule(name='Trapdoor', actions=lambda: [op], interact=self.interact, distance=lambda: 1)]


def test_vendor_surface_hop_uses_trapdoor_and_waits_for_underground():
    with VendorWorld() as world:
        assert 'Nurmof' in repr(acquire.NURMOF_VENDOR)
        assert 'Logs' in repr(acquire.ShopOffer('Logs', 1, acquire.NURMOF_VENDOR))
        world.trap()
        assert world.run(acquire.walk_to_tool_vendor(acquire.NURMOF_VENDOR, world.logs.append))
        assert world.walks == [acquire.NURMOF_VENDOR.hop_from, acquire.NURMOF_VENDOR.stand]
        assert world.actions == ['Climb-down'] and world.position.z > 9000


def test_vendor_hop_failed_approach_stops_and_missing_trap_falls_back_to_route():
    with VendorWorld() as world:
        world.walk_results = [False]
        assert world.run(acquire.walk_to_tool_vendor(acquire.NURMOF_VENDOR)) is False
        assert len(world.walks) == 1 and world.actions == []
    with VendorWorld() as world:
        assert world.run(acquire.walk_to_tool_vendor(acquire.NURMOF_VENDOR))
        assert len(world.walks) == 2 and world.actions == []


def test_vendor_underground_walk_and_unacknowledged_hop_retry():
    with VendorWorld() as world:
        world.position = Tile(3019, 9849)
        assert world.run(acquire.walk_to_tool_vendor(acquire.NURMOF_VENDOR))
        assert world.walks == [acquire.NURMOF_VENDOR.stand]
    with VendorWorld() as world:
        world.trap('Open')
        world.entered = False
        assert world.run(acquire.walk_to_tool_vendor(acquire.NURMOF_VENDOR))
        assert world.actions == ['Open', 'Open'] and world.now >= 17000


def test_combat_bone_bury_waits_for_inventory_change_and_respects_swing():
    state = {'used': 1, 'accept': True}
    def bury(op):
        assert op == 'Bury'
        if state['accept']:
            state['used'] = 0
        return state['accept']
    with PatchWorld() as world:
        world.patch(combat, '_core', FakeModule(tick=world.tick, get_local_player=lambda: FakeModule(animation=-1)))
        world.patch(combat, '_clock', combat.AttackClock())
        world.patch(items, 'inventory', FakeModule(first=lambda name: FakeModule(interact=bury) if state['used'] else None,
            used=lambda: state['used']))
        assert world.run(combat.bury_one_in_fight('Bones'))
        assert world.run(combat.bury_one_in_fight('Bones')) is False
        state['used'], state['accept'] = 1, False
        assert world.run(combat.bury_one_in_fight('Bones')) is False
        combat._clock.observe(1, world.tick())
        combat._core.get_local_player = lambda: FakeModule(animation=1)
        assert world.run(combat.bury_one_in_fight('Bones')) is False
    assert combat.food_heal_amount('') == combat.DEFAULT_FOOD_HEAL
    assert combat.eat_at_hp_threshold(0, 10) == 5
    assert combat.casts_available('unknown', [], lambda name: 0) == 0
    assert 'Super attack' in repr(combat.SUPER_ATTACK)


class SceneGuardian(randoms._RandomEvents):
    def _detect_scene(self):
        return None


def test_random_guardian_detects_held_events_and_special_areas():
    state = {'area': None, 'item': None, 'handle': False}
    with PatchWorld() as world:
        world.patch(randoms, 'solvers', FakeModule(MIME_SQUARE='mime', MAZE_SQUARE='maze', in_square=lambda area: state['area'] == area))
        world.patch(randoms, 'inventory', FakeModule(items=lambda: [FakeModule(name='Bronze axe handle')] if state['handle'] else [],
            contains=lambda name: state['item'] == name))
        world.patch(randoms, 'equipment', FakeModule(items=lambda: []))
        guardian = SceneGuardian()
        assert guardian._detect_raw() is None
        for area in ['mime', 'maze']:
            state['area'] = area
            assert guardian._detect_raw().kind == area
        state['area'], state['handle'] = None, True
        assert guardian._detect_raw().kind == 'lost-tool'
        state['handle'] = False
        for item, kind in [('Strange box', 'box'), ('Lamp', 'lamp')]:
            state['item'] = item
            assert guardian._detect_raw().kind == kind
        assert 'lamp' in repr(guardian._detect_raw())


def test_runtime_rejects_bad_settings_cadence_and_negative_waits():
    assert 'object' in raises(TypeError, lambda: _runtime.make_settings('[]'))
    assert 'loop_cadence' in raises(ValueError, lambda: _runtime._cadence_wait({'kind': 'invalid'}))
    assert 'yield 0' in raises(ValueError, lambda: _runtime._yielded(-1))
    with PatchWorld() as world:
        world.patch(_runtime, 'bot', FakeModule(loop_delay=-1))
        assert 'loop_delay' in raises(TypeError, lambda: _runtime._after_loop(None))
        world.patch(_runtime, '_paused', False)
        assert _runtime.resume() is None
        assert 'object' in raises(ValueError, lambda: _runtime.load(FakeModule(loop=lambda: 0), _runtime.SettingsBag({'Global': 3})))
        assert 'neither BOT' in raises(ValueError, lambda: _runtime.load(FakeModule(), _runtime.SettingsBag({})))
