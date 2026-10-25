"""rs2b0t's test/api/ai/quests/exec/crossTeleportDoor.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
rs2b0t records its messages into GameMessages; here mark and since read the fixture's list."""

from rs2004 import execution
from rs2004.dialogue import modals
from rs2004.entities import locs
from rs2004.geometry import Tile
from rs2004.messages import GameMessage, game_messages
from rs2004.quests.exec.prompts import DoorCrossing, cross_teleport_door
from rs2004.traversal import traversal

DOOR_ID = 1536
STAND = Tile(2774, 3187, 0)

S = {}


def quiet(m):
    pass


class Leaf:
    id = DOOR_ID
    name = 'Door'

    def tile(self):
        return Tile(2774, 3188, 0)

    def actions(self):
        return ['Open']

    def interact(self, op):
        if S['refusal']:
            S['messages'].append(S['refusal'])
        return True


class Chain:
    def action(self, *args):
        return self

    def name(self, *args):
        return self

    def within(self, *args):
        return self

    def where(self, *args):
        return self

    def nearest(self):
        return Leaf()


def ticks(n=1):
    if False:
        yield


# Why: delay_until polls once a tick up to its cap, so the poll count is what a stall costs.
def polling_until(fn, ms=0):
    rounds = max(1, round(ms / 600))
    for i in range(rounds):
        S['polls'] += 1
        if fn():
            return True
    return fn()
    yield


def walked(*args, **kwargs):
    return True
    yield


def since(mark):
    return [GameMessage(i, S['messages'][i]) for i in range(mark, len(S['messages']))]


def _setup():
    S['refusal'] = None
    S['polls'] = 0
    S['messages'] = []
    spy_on(execution, 'delay_ticks', impl=ticks)
    spy_on(execution, 'delay_until', impl=polling_until)
    spy_on(traversal, 'walk_resilient', impl=walked)
    spy_on(locs, 'query', impl=lambda: Chain())
    spy_on(modals, 'is_open', returns=False)
    spy_on(game_messages, 'mark', impl=lambda: len(S['messages']))
    spy_on(game_messages, 'since', impl=since)


before_each(_setup)


# Why: open_and_close_door prints nothing on a crossing, so a message instead of the teleport is the script refusing,
# and without watching for it the crossing polls out its full cap.
def _fn1():
    S['refusal'] = 'This door is securely locked.'
    crossed = yield from cross_teleport_door(DoorCrossing(DOOR_ID, STAND, lambda: False, quiet))
    expect(crossed).to_be(False)
    # Why: one poll for the box-or-refusal wait and one for the crossing, both cut short by the message, against a cap of
    # three each.
    expect(S['polls']).to_be_less_than_or_equal(2)


test('a refused door gives up as soon as the script answers', _fn1)


def _fn2():
    crossed = yield from cross_teleport_door(DoorCrossing(DOOR_ID, STAND, lambda: False, quiet))
    expect(crossed).to_be(False)
    expect(S['polls']).to_be_greater_than(1)


test('a silent door still polls out its cap before giving up', _fn2)


def _fn3():
    S['refusal'] = 'You go through the door.'
    S['far'] = False
    crossed = yield from cross_teleport_door(DoorCrossing(DOOR_ID, STAND, lambda: S['far'], quiet))
    expect(crossed).to_be(False)
    S['far'] = True
    crossed = yield from cross_teleport_door(DoorCrossing(DOOR_ID, STAND, lambda: S['far'], quiet))
    expect(crossed).to_be(True)


test('a crossing that lands is not read as a refusal by its own narration', _fn3)
