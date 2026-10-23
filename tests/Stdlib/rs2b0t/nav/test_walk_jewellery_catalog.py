"""rs2b0t's test/event/webwalk/jewelleryAndStateAware.test.ts (MIT, see thirdparty/rs2b0t): its catalog half, on
spec.py's describe, test and expect. The state-aware ladder half reads rs2b0t's own pack and stair rows, which here
are data/nav's edges and the planner's real-cache tests."""

from rs2004.routeplan import teleport_by_id, teleports


def _fn1():
    def _fn2():
        jewellery = [t for t in teleports() if t.get('family') == 'jewellery']
        expect(len(jewellery)).to_be_greater_than(0)
        for t in jewellery:
            expect(len(t.get('dialogueChoose', [])), t['teleportId']).to_be_greater_than(0)
            # The rub needs an item to find, which the planner matches by the same names.
            expect(len(t.get('itemNameMatch', []))).to_be_greater_than(0)
            expect(teleport_by_id(t['teleportId'])['family']).to_be('jewellery')
    test('every jewellery dest has dialogueChoose for Rub menus', _fn2)

    def _fn3():
        expect(teleport_by_id('watchtower')['family']).to_be('spell')
        expect(teleport_by_id('trollheim')['family']).to_be('spell')
        expect(teleport_by_id('varrock')['to']).to_equal({'x': 3213, 'z': 3424, 'level': 0})
    test('spell ids resolve including watchtower and trollheim', _fn3)


describe('jewellery catalog execution metadata', _fn1)
