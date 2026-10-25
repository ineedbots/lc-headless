"""rs2b0t's test/api/ai/quests/exec/talkThrough.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.

Here open_dialogue reaches the NPC through reach.entity_op, which finds the door in the way among the scene's
wall-layer locs, so the fixture is a scene of one NPC and at most one door, with reachability answered by the NPC's
tile."""

import rs2004.reach as reach_module
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.geometry import Tile
from rs2004.messages import GameMessage, game_messages
from rs2004.quests.exec.primitives import talk_through
from rs2004.traversal import traversal

S = {}


class FakeNpc:
    def __init__(self, name, tile, ops):
        self.name = name
        self._tile = tile
        self.ops = ops

    def tile(self):
        return self._tile

    def distance(self):
        return 3

    def actions(self):
        return self.ops

    def interact(self, op):
        S['npc_ops'].append(op)
        if S['cant_reach']:
            S['messages'].append("I can't reach that!")
            return True
        S['dialog_open'] = not S['continue_only']
        S['can_continue'] = True
        return True


class FakeDoor:
    def __init__(self, tile):
        self.name = 'Door'
        self.layer = LAYER_WALL
        self._tile = tile

    def tile(self):
        return self._tile

    def actions(self):
        return ['Open']

    def distance(self):
        return 1

    def interact(self, op):
        S['door_ops'].append(op)
        S['cant_reach'] = False
        S['npc_reachable'] = True
        S['door'] = None
        return True


def can_reach(tile, adjacent=False):
    npc = S['npc']
    return S['npc_reachable'] or not (npc is not None and tile.x == npc.tile().x and tile.z == npc.tile().z)


def answered(cond, ms=0):
    return cond()
    yield


def ticks(n=1):
    if False:
        yield


def walked(*args, **kwargs):
    return True
    yield


def continued():
    S['continues'] += 1
    S['can_continue'] = False
    S['dialog_open'] = False
    return True
    yield


def chosen(option):
    return True
    yield


def since(mark):
    return [GameMessage(i, S['messages'][i]) for i in range(mark, len(S['messages']))]


def _setup():
    S['npc'] = FakeNpc('Fred the Farmer', Tile(3, 1, 0), ['Talk-to'])
    S['door'] = None
    S['cant_reach'] = False
    S['npc_reachable'] = True
    S['dialog_open'] = False
    S['can_continue'] = False
    S['continues'] = 0
    S['continue_only'] = False
    S['npc_ops'] = []
    S['door_ops'] = []
    S['messages'] = []
    spy_on(reach_module, 'local_tile', returns=Tile(0, 0, 0))
    spy_on(reach_module, '_can_reach', impl=can_reach)
    spy_on(execution, 'delay_until', impl=answered)
    spy_on(execution, 'delay_ticks', impl=ticks)
    spy_on(traversal, 'walk_resilient', impl=walked)
    spy_on(locs, 'query', impl=lambda: FakeQuery([S['door']] if S['door'] is not None else []))
    spy_on(npcs, 'query', impl=lambda: FakeQuery([S['npc']] if S['npc'] is not None else []))
    spy_on(chat_dialog, 'is_open', impl=lambda: S['dialog_open'])
    spy_on(chat_dialog, 'can_continue', impl=lambda: S['can_continue'])
    spy_on(chat_dialog, 'options', returns=[])
    spy_on(chat_dialog, 'continue_', impl=continued)
    spy_on(chat_dialog, 'choose_option', impl=chosen)
    spy_on(game_messages, 'mark', impl=lambda: len(S['messages']))
    spy_on(game_messages, 'since', impl=since)


before_each(_setup)


def quiet(m):
    pass


def talk(log=None):
    ok = yield from talk_through('Fred the Farmer', [], log if log is not None else quiet)
    return ok


def _fn1():
    def _fn2():
        # The live case: Fred wanders into his bedroom, the interior door re-shuts, and the server stays silent; only the
        # scene knows he's unreachable.
        S['npc_reachable'] = False
        S['door'] = FakeDoor(Tile(1, 0, 0))
        ok = yield from talk()
        expect(S['door_ops']).to_equal(['Open'])
        expect(S['npc_ops']).to_equal(['Talk-to'])
        expect(ok).to_be(True)
    test('an NPC walled off with no server verdict is still reached by opening the door', _fn2)

    def _fn3():
        # Why: 400 expansions run out at ~11 tiles of open ground, so a patrolling NPC would otherwise have us opening
        # doors it's too far to need.
        S['npc_reachable'] = False
        S['npc'] = FakeNpc('Fred the Farmer', Tile(40, 40, 0), ['Talk-to'])
        S['door'] = FakeDoor(Tile(1, 0, 0))
        ok = yield from talk()
        expect(S['door_ops']).to_equal([])
        expect(S['npc_ops']).to_equal(['Talk-to'])
        expect(ok).to_be(True)
    test('a distant target is never probed — out of BFS range reads as walled off', _fn3)

    def _fn4():
        S['npc_reachable'] = False
        S['npc'] = FakeNpc('Fred the Farmer', Tile(3, 1, 1), ['Talk-to'])
        S['door'] = FakeDoor(Tile(1, 0, 0))
        ok = yield from talk()
        expect(S['door_ops']).to_equal([])
        expect(ok).to_be(True)
    test('a target on another level is never probed', _fn4)

    def _fn5():
        S['npc_reachable'] = False
        ok = yield from talk()
        expect(S['door_ops']).to_equal([])
        expect(S['npc_ops']).to_equal(['Talk-to'])
        expect(ok).to_be(True)
    test('walled off with no door to open falls through to the plain click', _fn5)

    def _fn6():
        # The server does report "I can't reach that!" when its own path dead-ends.
        S['cant_reach'] = True
        S['door'] = FakeDoor(Tile(1, 0, 0))
        ok = yield from talk()
        expect(S['door_ops']).to_equal(['Open'])
        expect(S['npc_ops']).to_equal(['Talk-to', 'Talk-to'])
        expect(ok).to_be(True)
    test('an NPC shut behind a door is reached by opening it, not abandoned', _fn6)

    def _fn7():
        ok = yield from talk()
        expect(S['npc_ops']).to_equal(['Talk-to'])
        expect(S['door_ops']).to_equal([])
        expect(ok).to_be(True)
    test('a reachable NPC still opens on the first click and touches no door', _fn7)

    def _fn8():
        S['continue_only'] = True
        ok = yield from talk()
        expect(S['npc_ops']).to_equal(['Talk-to'])
        expect(S['continues']).to_be(1)
        expect(ok).to_be(True)
    test("Fred's continue-only final response counts as an opened dialogue", _fn8)

    def _fn9():
        S['cant_reach'] = True
        ok = yield from talk()
        expect(S['npc_ops']).to_equal(['Talk-to'])
        expect(ok).to_be(False)
    test("can't-reach with no openable door gives up rather than spinning", _fn9)

    def _fn10():
        S['npc'] = None
        lines = []
        ok = yield from talk(lambda m: lines.append(m))
        expect(ok).to_be(False)
        expect(lines).to_equal(["no 'Fred the Farmer' nearby to talk to"])
    test('an NPC that is not in the scene is reported, not clicked', _fn10)


describe('talkThrough door handling', _fn1)
