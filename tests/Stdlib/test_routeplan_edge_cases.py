"""Route funding, requirement failures and virtual inventory preserve planning semantics."""

import rs2004.routeplan as routes
from rs2004.walkgeom import PathTile
from rs2004.geometry import Tile
from coverage_world import PatchWorld


def test_route_requirements_report_each_unsatisfied_resource():
    cases = [({'members': True}, {}, 'members-only'),
        ({'freeSlots': 2}, {'free_slots': 1}, 'free inventory'),
        ({'skills': [{'name': 'agility', 'level': 20}]}, {'skills': {'agility': 10}}, 'agility 20'),
        ({'currency': {'name': 'Coins', 'amount': 30}}, {'items': {'Coins': 20}}, '30x Coins'),
        ({'items': [{'name': 'Key', 'count': 1}]}, {}, '1x Key'),
        ({'worn': [{'name': 'Boots', 'count': 1}]}, {}, 'wear Boots'),
        ({'forbidEntranaRestricted': True}, {'entrana_restricted_gear': True}, 'Entrana'),
        ({'slashTool': True}, {'can_slash_web': False}, 'slash webs'),
        ({'quests': [{'quest': 'Quest', 'maxStatus': 'started'}]}, {}, 'known quest'),
        ({'quests': [{'quest': 'Quest', 'maxStatus': 'started'}]}, {'quests': {'Quest': 'complete'}}, 'at most'),
        ({'quests': [{'quest': 'Quest', 'minStatus': 'complete'}]}, {'quests': {'Quest': 'not_started'}}, 'complete'),
        ({'essenceExitReturn': 'aubury'}, {'essence_exit_return': 'sedridor'}, 'sedridor')]
    for requires, state, reason in cases:
        ok, message = routes.meets_requires(requires, state)
        assert not ok and reason in message
    assert routes.meets_requires(None, {}) == (True, None)
    requires = {'members': True, 'freeSlots': 1, 'skills': [{'name': 'agility', 'level': 20}],
                'currency': {'name': 'Coins', 'amount': 30}, 'items': [{'name': 'Key', 'count': 1}],
                'questWaivesItems': 'Quest', 'worn': [{'name': 'Boots', 'count': 1}]}
    state = {'members': True, 'free_slots': 2, 'skills': {'agility': 20}, 'quests': {'Quest': 'complete'}, 'worn': {'Boots': 1}}
    assert routes.meets_requires(requires, state) == (True, None)


def test_route_fares_sum_while_keys_and_teleport_runes_use_largest_need():
    crossings = [
        {'x': 10, 'z': 10, 'level': 0, 'locName': 'Gate', 'action': 'Open', 'requires': {'item': 'Coins', 'count': 10}, 'questWaivesItems': 'Quest'},
        {'x': 20, 'z': 10, 'level': 0, 'locName': 'Door', 'action': 'Open', 'requires': {'item': 'Key', 'count': 1}},
    ]
    points = [PathTile(10, 10, 0, {'loc_name': 'Gate', 'action': 'Open', 'loc_x': 10, 'loc_z': 10}),
              PathTile(10, 10, 0, {'loc_name': 'Gate', 'action': 'Open', 'loc_x': 10, 'loc_z': 10}),
              PathTile(20, 10, 0, {'loc_name': 'Door', 'action': 'Open', 'loc_x': 20, 'loc_z': 10}),
              PathTile(30, 10, 0, {'teleport_id': 'test'})]
    with PatchWorld() as world:
        world.patch(routes, '_crossings', crossings)
        world.patch(routes, '_teleports', [{'teleportId': 'test', 'requires': {'items': [{'name': 'Law rune', 'count': 1}, {'name': 'Ignored', 'count': 0}]}}])
        assert routes.items_required_by_waypoints(points) == {'Coins': 20, 'Key': 1, 'Law rune': 1}
        assert routes.items_required_by_waypoints(points, {'quests': {'Quest': 'complete'}}) == {'Key': 1, 'Law rune': 1}
        missing = routes.missing_items_for_path(points, {'items': {'coins': 15, 'lawrune': 1}})
        assert missing == [routes.MissingItem('Coins', 5), routes.MissingItem('Key', 1)]
        assert routes.gate_item_candidates()['Coins'] == 10
        assert routes.explain_unreachable(lambda state: {'ok': False}, {}, lambda path: points) == []
        assert routes.explain_unreachable(lambda state: {'ok': True}, {}, lambda path: points)


def test_bank_leg_compares_cost_and_virtual_inventory_does_not_mutate_source():
    missing = [routes.MissingItem('Coins', 30)]
    assert routes.plan_bank_leg(100, True, 1, 1, missing).action == 'skip'
    assert routes.plan_bank_leg(100, False, 1, 1, []).action == 'skip'
    assert routes.plan_bank_leg(10, False, 1, 1, missing).action == 'skip'
    plan = routes.plan_bank_leg(None, False, 1, 2, missing)
    assert plan.action == 'bank' and plan.estimated_cost == 27 and 'Fields' in repr(plan)
    state = {'items': {'lawrune': 2}, 'worn': {}}
    virtual = routes.virtualize_with_items(state, {'Law rune': 3, 'Knife': 1, 'Nothing': 0})
    assert virtual['items']['lawrune'] == 5 and virtual['items']['Law rune'] == 5
    assert state['items'] == {'lawrune': 2} and virtual['can_slash_web']
    assert routes.lookup_item({}, 'Missing') == 0
    assert routes.MissingItem('Coins', 1) != routes.MissingItem('Coins', 2)


def test_lock_text_variants_and_essence_unknown_transport_fallback():
    for line in ['no', 'you must finish this quest', 'you need to find a key', 'you are not worthy',
                 'nothing interesting happens', 'finish the quest first', 'quest completion required']:
        assert routes.is_quest_lock_text(line) == (line != 'no')
    session = routes._EssenceSession()
    assert session.note_entry_from_npc('') is None
    tile = routes.ESSENCE_EXIT_RETURNS['aubury']
    assert session.note_entry_from_transport({'action': 'Teleport', 'loc_x': tile.x, 'loc_z': tile.z}) == 'aubury'
    assert session.note_entry_from_transport({'action': 'Teleport', 'loc_x': 1, 'loc_z': 1}) is None
    assert routes.essence_return_id_from_tile(Tile(1, 2, 3)) is None
