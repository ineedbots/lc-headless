import rs2004.routeplan as routes
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
    routes._crossings = [TOLL, SHIP, OTHER_SHIP]
    gate = {'loc_name': 'Gate', 'action': 'Open', 'loc_x': 3268, 'loc_z': 3227}
    assert special_crossing_for_transport(gate, tile(3267, 3227), tile(3269, 3227)) is TOLL
    ship = {'loc_name': 'Seaman Thresnor', 'action': 'Pay-fare', 'loc_x': 3027, 'loc_z': 3218}
    assert special_crossing_for_transport(ship, tile(3027, 3218), tile(2956, 3143, 1)) is SHIP
    # A hop that lands elsewhere isn't stolen by a crossing whose landing doesn't match.
    assert special_crossing_for_transport(ship, tile(3027, 3218), tile(3000, 3000, 1)) is None
    door = {'loc_name': 'Door', 'action': 'Open', 'loc_x': 3100, 'loc_z': 3100}
    assert special_crossing_for_transport(door, tile(3100, 3099), tile(3100, 3101)) is None
    routes._crossings = None


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
    assert walker.nearest_usable_bank(here, lambda bank: bank['name'] != 'Up')['name'] == 'Guild'
    assert walker.nearest_usable_bank(here, lambda bank: False) is None
    walker._banks = None


def test_a_bank_a_script_opts_into_follows_the_global_setting():
    zanaris = {'name': 'Zanaris', 'tile': {'x': 2383, 'z': 4458, 'level': 0}, 'requires': {'setting': 'useZanarisBank'}}
    settings_store.load({})
    assert not walker.bank_unlocked(zanaris)
    settings_store.load({'Global': {'use_zanaris_bank': True}})
    assert walker.bank_unlocked(zanaris)
    assert not walker.bank_unlocked(zanaris, {})
    settings_store.load({})


def test_rs2b0ts_walk_presets_and_teleports_off_by_default():
    assert traversal.pure_walk == NAV_PURE_WALK
    assert traversal.with_teles == NAV_WITH_TELES
    assert traversal.preload() is None
    settings_store.load({'Global': {'nav_teleports': True}})
    assert traversal.teleports_enabled()
    settings_store.load({})
    assert not traversal.teleports_enabled()


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


def test_webs_and_ladders_with_an_id_take_only_the_loc_on_their_tile():
    ladder = {'loc_name': 'Ladder', 'action': 'Climb-down', 'loc_id': 1759, 'loc_x': 2848, 'loc_z': 3513}
    assert walker._exact_placement(ladder)
    assert not walker._exact_placement({'loc_name': 'Ladder', 'action': 'Climb-down', 'loc_x': 2848, 'loc_z': 3513})
    assert walker._exact_placement({'loc_name': 'Web', 'action': 'Slash', 'loc_x': 2569, 'loc_z': 3118})
    assert not walker._exact_placement({'loc_name': 'Staircase', 'action': 'Climb-up', 'loc_id': 1738, 'loc_x': 3204, 'loc_z': 3207})


class FailedHop:
    def __init__(self, transport):
        self.transport = transport
        self.level = 0


def refused(self, approach, hop, say):
    return False
    yield


def take_hop(walk, hop):
    gen = walk._take_hop(tile(3222, 3218), hop, lambda m: None)
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        return stop.value


def test_a_teleport_that_fails_is_suppressed_without_a_door_strike():
    handle = walker._Traversal._handle_transport
    walker._Traversal._handle_transport = refused
    walk = walker._Traversal()
    spell = {'kind': 'teleport', 'family': 'spell', 'loc_name': 'Cast Ardougne teleport', 'teleport_id': 'ardougne'}
    assert take_hop(walk, FailedHop(spell)) == 'repath'
    assert walk._suppressed_teleports == ['ardougne']
    assert walk._door_strikes == {}
    door = {'loc_name': 'Door', 'action': 'Open', 'loc_x': 3100, 'loc_z': 3100}
    assert take_hop(walk, FailedHop(door)) == 'repath'
    assert walk._door_strikes == {'3100,3100': 1}
    walker._Traversal._handle_transport = handle


class FakeClock:
    def __init__(self):
        self.now = 1000

    def step_time(self):
        return self.now


def test_a_door_that_keeps_refusing_cools_down_then_is_tried_afresh():
    handle = walker._Traversal._handle_transport
    core = walker._core
    clock = FakeClock()
    walker._Traversal._handle_transport = refused
    walker._core = clock
    walk = walker._Traversal()
    door = {'kind': 'door', 'loc_name': 'Door', 'action': 'Open', 'loc_x': 3100, 'loc_z': 3100}
    for _ in range(walker.DOOR_COOLDOWN_STRIKES):
        take_hop(walk, FailedHop(door))
    # The next walk still leaves it out, until the cooldown runs out and the strikes go with it.
    walk._reset_avoids()
    assert walk._avoid_doors == [[3100, 3100]]
    clock.now += walker.DOOR_RETRY_MS
    walk._reset_avoids()
    assert walk._avoid_doors == []
    assert walk._door_strikes == {}
    # A ladder that refuses is left out of the walk, never cooled down across walks.
    ladder = {'kind': 'loc', 'loc_name': 'Ladder', 'action': 'Climb-up', 'loc_x': 3200, 'loc_z': 3200}
    for _ in range(walker.DOOR_COOLDOWN_STRIKES):
        take_hop(walk, FailedHop(ladder))
    walk._reset_avoids()
    assert walk._avoid_doors == []
    walker._Traversal._handle_transport = handle
    walker._core = core


def test_a_new_session_forgets_refused_doors_and_failed_teleports():
    handle = walker._Traversal._handle_transport
    walker._Traversal._handle_transport = refused
    walk = walker._Traversal()
    gate = {'kind': 'gate', 'loc_name': 'Gate', 'action': 'Open', 'loc_x': 3100, 'loc_z': 3100}
    for _ in range(walker.DOOR_COOLDOWN_STRIKES):
        take_hop(walk, FailedHop(gate))
    take_hop(walk, FailedHop({'kind': 'teleport', 'family': 'spell', 'loc_name': 'Cast Ardougne teleport', 'teleport_id': 'ardougne'}))
    walk.reset_session()
    walk._reset_avoids()
    assert walk._avoid_doors == [] and walk._door_strikes == {} and walk._suppressed_teleports == []
    walker._Traversal._handle_transport = handle


def test_only_doors_and_gates_cool_down():
    assert walker.barrier_bannable('door', None)
    assert walker.barrier_bannable(None, 'Large door')
    assert walker.barrier_bannable(None, 'Gate')
    assert not walker.barrier_bannable(None, 'Gangplank')
    assert not walker.barrier_bannable(None, 'Doorway arch')


def no_wait(*args, **kwargs):
    return None
    yield


def failed_world_walk(self, *args, **kwargs):
    self.world_walks = getattr(self, 'world_walks', 0) + 1
    self.last_outcome = 'failed'
    return False
    yield


def dead_probe(self, *args, **kwargs):
    return {'ok': False, 'reason': 'unreachable'}


def test_a_resilient_walk_plans_again_after_a_backoff_and_gives_up():
    from rs2004 import execution
    from rs2004 import walkgeom
    from rs2004.game import direct_navigator
    saved = [(walker, 'local_tile', walker.local_tile), (walker, '_arrived', walker._arrived), (execution, 'delay_ticks', execution.delay_ticks),
             (walkgeom, 'pick_unstick_step', walkgeom.pick_unstick_step), (walker._Traversal, 'walk_to', walker._Traversal.walk_to),
             (walker._Traversal, 'try_nearby_door', walker._Traversal.try_nearby_door), (walker._Traversal, '_request', walker._Traversal._request),
             (type(direct_navigator), 'walk_to', type(direct_navigator).walk_to)]
    walker.local_tile = lambda: tile(3267, 3294)
    walker._arrived = lambda dest, radius: False
    execution.delay_ticks = no_wait
    walkgeom.pick_unstick_step = lambda can_step, start: None
    walker._Traversal.walk_to = failed_world_walk
    walker._Traversal.try_nearby_door = no_wait
    walker._Traversal._request = dead_probe
    type(direct_navigator).walk_to = no_wait
    walk = walker._Traversal()
    gen = walk.walk_resilient(tile(2613, 3294), radius=4)
    try:
        while True:
            next(gen)
    except StopIteration as stop:
        arrived = stop.value
    for owner, name, value in saved:
        setattr(owner, name, value)
    # Two world walks fail, a backoff plans a third, and the probe from the same spot finds no route.
    assert arrived is False
    assert walk.world_walks >= 2
    assert walk.last_outcome == 'unreachable'
