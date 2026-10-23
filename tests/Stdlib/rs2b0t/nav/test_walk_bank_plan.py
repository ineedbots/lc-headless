"""rs2b0t's test/event/webwalk/bankPlan.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.routeplan import WITHDRAW_COST, items_required_by_waypoints, missing_items_for_path, path_has_teleport, plan_bank_leg, virtualize_with_items


def empty_world_state(members=True):
    """rs2b0t's emptyWorldStateData, as world_state()'s dict."""
    return {'members': members, 'skills': {}, 'items': {}, 'worn': {}, 'quests': {}, 'free_slots': 28}


def wp(x, z, transport=None):
    return (Obj({'x': x, 'z': z, 'level': 0, 'transport': transport}))


def _fn1():
    def _fn2():
        base = empty_world_state()
        base['items']['Law rune'] = 1
        v = virtualize_with_items(base, Obj({'Law rune': 5, 'Air rune': 3}))
        expect(v['items'].get('Law rune')).to_be(6)
        expect(v['items'].get('Air rune')).to_be(3)
        expect(base['items'].get('Air rune')).to_be_undefined()
    test('adds counts on top of inventory', _fn2)


describe('virtualizeWithItems', _fn1)


def _fn3():
    def _fn4():
        path = [
        wp(3222, 3218),
        wp(3213, 3424, Obj({
        'loc_name': 'Varrock teleport',
        'action': 'Cast',
        'loc_x': 3222,
        'loc_z': 3218,
        'kind': 'teleport',
        'teleport_id': 'varrock',
    })),
    ]
        need = items_required_by_waypoints(path)
        expect(need.get('Law rune')).to_be(1)
        expect(need.get('Fire rune')).to_be(1)
        expect(need.get('Air rune')).to_be(3)
        expect(path_has_teleport(path)).to_be(True)
        empty = empty_world_state()
        empty['skills']['magic'] = 25
        missing = missing_items_for_path(path, empty)
        expect((([m for m in missing if m.name == 'Law rune'] or [None])[0].count if ([m for m in missing if m.name == 'Law rune'] or [None])[0] is not None else None)).to_be(1)
        # Partial inventory: count is shortage only (required − held), not total.
        partial = empty_world_state()
        partial['skills']['magic'] = 25
        partial['items'] = Obj({'Law rune': 0, 'Fire rune': 1, 'Air rune': 1})
        partial_missing = missing_items_for_path(path, partial)
        expect((([m for m in partial_missing if m.name == 'Law rune'] or [None])[0].count if ([m for m in partial_missing if m.name == 'Law rune'] or [None])[0] is not None else None)).to_be(1)
        expect(([m for m in partial_missing if m.name == 'Fire rune'] or [None])[0]).to_be_undefined()
        expect((([m for m in partial_missing if m.name == 'Air rune'] or [None])[0].count if ([m for m in partial_missing if m.name == 'Air rune'] or [None])[0] is not None else None)).to_be(2)
        full = empty_world_state()
        full['items'] = Obj({'Law rune': 1, 'Fire rune': 1, 'Air rune': 3})
        expect(missing_items_for_path(path, full)).to_equal([])
    test('varrock tele hop needs runes', _fn4)

    def _fn5():
        path = [
        wp(3267, 3227),
        wp(3268, 3227, Obj({'loc_name': 'Gate', 'action': 'Open', 'loc_x': 3268, 'loc_z': 3227, 'kind': 'door'})),
    ]
        need = items_required_by_waypoints(path)
        expect(need.get('Coins')).to_be(10)
    test('Al Kharid toll on path needs coins', _fn5)

    def _fn6():
        path = [
        wp(3267, 3227),
        wp(3268, 3227, Obj({'loc_name': 'Gate', 'action': 'Open', 'loc_x': 3268, 'loc_z': 3227, 'kind': 'door'})),
    ]
        done = empty_world_state()
        done['quests'] = Obj({'Prince Ali Rescue': 'complete'})
        expect(items_required_by_waypoints(path, done).get('Coins')).to_be_undefined()
        expect(missing_items_for_path(path, done)).to_equal([])
        stuck = empty_world_state()
        stuck['quests'] = Obj({'Prince Ali Rescue': 'not_started'})
        expect(missing_items_for_path(path, stuck)).to_equal([Obj({'name': 'Coins', 'count': 10})])
    test('Prince Ali Rescue complete waives the Al Kharid toll', _fn6)

    def _fn7():
        path = [
        Obj({'x': 3027, 'z': 3218, 'level': 1}),
        Obj({
        'x': 2956,
        'z': 3143,
        'level': 1,
        'transport': Obj({'loc_name': 'Seaman Thresnor', 'action': 'Pay-fare', 'loc_x': 3027, 'loc_z': 3218, 'kind': 'ship'}),
    }),
        Obj({'x': 2772, 'z': 3234, 'level': 1}),
        Obj({
        'x': 2683,
        'z': 3268,
        'level': 1,
        'transport': Obj({'loc_name': 'Customs officer', 'action': 'Pay-fare', 'loc_x': 2772, 'loc_z': 3234, 'kind': 'ship'}),
    }),
    ]
        expect(items_required_by_waypoints(path).get('Coins')).to_be(60)
        empty = empty_world_state()
        expect(missing_items_for_path(path, empty)).to_equal([Obj({'name': 'Coins', 'count': 60})])
        half = empty_world_state()
        half['items'] = Obj({'Coins': 30})
        expect(missing_items_for_path(path, half)).to_equal([Obj({'name': 'Coins', 'count': 30})])
    test('two ship fares sum, they are not the same 30 coins twice', _fn7)

    # Why: the baked pack keys the crossing at the approach stand (3304,3118) while the loc sits at (3302,3116), so a lookup on the loc alone finds nothing.
    def _fn8():
        path = [
        wp(3304, 3118),
        wp(3304, 3114, Obj({'loc_name': 'Shantay pass', 'action': 'Go-through', 'loc_x': 3302, 'loc_z': 3116, 'kind': 'door'})),
    ]
        expect(items_required_by_waypoints(path).get('Shantay pass')).to_be(1)
        broke = empty_world_state()
        expect(missing_items_for_path(path, broke)).to_equal([Obj({'name': 'Shantay pass', 'count': 1})])
        holding = empty_world_state()
        holding['items'] = Obj({'Shantay pass': 1})
        expect(missing_items_for_path(path, holding)).to_equal([])
    test('Shantay pass toll is found when the loc tile differs from the crossing key', _fn8)


describe('itemsRequiredByWaypoints / missing', _fn3)


def _fn9():
    def _fn10():
        r = plan_bank_leg(200, True, 10, 40, [Obj({'name': 'Law rune', 'count': 1})])
        expect(r.action).to_be('skip')
    test('skips when direct already has teleport', _fn10)

    def _fn11():
        r = plan_bank_leg(500, False, 20, 40, [])
        expect(r.action).to_be('skip')
    test('skips when missing empty', _fn11)

    def _fn12():
        r = plan_bank_leg(400, False, 30, 50, [Obj({'name': 'Law rune', 'count': 1})])
        expect(r.action).to_be('bank')
        if r.action == 'bank':
            expect(r.estimated_cost).to_be(30 + WITHDRAW_COST + 50)
            expect(r.missing[0].name).to_be('Law rune')
    test('banks when virtual route is cheaper', _fn12)

    def _fn13():
        r = plan_bank_leg(80, False, 100, 50, [Obj({'name': 'Law rune', 'count': 1})])
        expect(r.action).to_be('skip')
    test('skips when bank detour is more expensive', _fn13)


describe('planBankLeg', _fn9)
