"""Who the gatherers' FleeCombat sees as an attacker. Not one of rs2b0t's tests: rs2b0t's check needs the npc to
have been hit, which missed a dark wizard casting from range, and this pins the fix."""

from bots.gathering.tasks import attacking_beside, attacking_me


class FakeNpc:
    def __init__(self, in_combat, mine, other, actions, distance):
        self.in_combat = in_combat
        self.mine = mine
        self.other = other
        self.ops = actions
        self.away = distance

    def targets_me(self):
        return self.mine

    def targets_another_player(self):
        return self.other

    def actions(self):
        return self.ops

    def distance(self):
        return self.away


WIZARD = FakeNpc(False, True, False, ['Attack'], 6)

describe('attacking_me', lambda: [
    test('a caster facing you counts though nothing has hit it', lambda: expect(attacking_me(WIZARD)).to_be(True)),
    test('an npc facing someone else, or one with no Attack, does not', lambda: [
        expect(attacking_me(FakeNpc(True, False, True, ['Attack'], 1))).to_be(False),
        expect(attacking_me(FakeNpc(False, True, False, ['Talk-to'], 1))).to_be(False),
    ]),
])

describe('attacking_beside', lambda: [
    test('a fighting npc beside you that faces no other player counts', lambda: expect(attacking_beside(FakeNpc(True, False, False, ['Attack'], 2))).to_be(True)),
    test('one further off, or idle, does not', lambda: [
        expect(attacking_beside(FakeNpc(True, False, False, ['Attack'], 3))).to_be(False),
        expect(attacking_beside(FakeNpc(False, False, False, ['Attack'], 1))).to_be(False),
    ]),
])
