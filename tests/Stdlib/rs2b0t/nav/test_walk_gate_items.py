"""rs2b0t's test/event/webwalk/gateItems.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
Here the probe plans at once, so it returns its route, and explain_unreachable takes how to read the route's
waypoints."""

from rs2004.routeplan import explain_unreachable, gate_item_candidates


def state(items=None):
    return {'members': True, 'skills': {'magic': 99}, 'quests': {}, 'items': items or {}, 'worn': {}, 'free_slots': 20, 'entrana_restricted_gear': False}


def shantay_path():
    return {
        'ok': True, 'cost': 100, 'expanded': 10,
        'waypoints': [
            Obj({'x': 3304, 'z': 3118, 'level': 0, 'transport': None}),
            Obj({'x': 3304, 'z': 3114, 'level': 0, 'transport': {'loc_name': 'Shantay pass', 'action': 'Go-through', 'loc_x': 3302, 'loc_z': 3116, 'kind': 'door'}}),
        ],
    }


def waypoints_of(path):
    return path['waypoints']


def _fn1():
    def _fn2():
        c = gate_item_candidates()
        expect(c.get('Shantay pass')).to_be_greater_than_or_equal(1)
        expect(c.get('Rope')).to_be_greater_than_or_equal(1)
        expect(c.get('Brass key')).to_be_greater_than_or_equal(1)
    test('includes every item a baked crossing can demand', _fn2)

    def _fn3():
        expect(gate_item_candidates().get('Coins')).to_be_greater_than_or_equal(30)
    test('coins cover the priciest fare, not the cheapest toll', _fn3)


describe('gateItemCandidates', _fn1)


def _fn4():
    def _fn5():
        missing = explain_unreachable(lambda _s: shantay_path(), state(), waypoints_of)
        expect(missing).to_equal([Obj({'name': 'Shantay pass', 'count': 1})])
    test('names the item that would open the route', _fn5)

    def _fn6():
        missing = explain_unreachable(lambda _s: shantay_path(), state({'Shantay pass': 1}), waypoints_of)
        expect(missing).to_equal([])
    test('says nothing when the player already holds the gate item', _fn6)

    def _fn7():
        missing = explain_unreachable(lambda _s: {'ok': False, 'reason': 'unreachable', 'expanded': 1}, state(), waypoints_of)
        expect(missing).to_equal([])
    test('a route that stays unreachable even with the full kit is a real nav gap', _fn7)

    def _fn8():
        seen = []

        def probe(s):
            seen.append(s)
            return shantay_path()
        explain_unreachable(probe, state(), waypoints_of)
        expect(len(seen)).to_be(1)
        expect(seen[0]['items'].get('Shantay pass')).to_be_greater_than_or_equal(1)
        expect(seen[0]['items'].get('Coins')).to_be_greater_than_or_equal(30)
    test('probes with every gate item virtualized, not the real inventory', _fn8)


describe('explainUnreachable', _fn4)
