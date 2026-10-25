"""rs2b0t's test/api/ai/quests/strike-combat.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
rs2b0t stubs the client's server tile and npc list; here game.tile and npcs.all stand in, and rs2b0t's raw autocast
toggle is autocast.disarm."""

from rs2004 import execution
from rs2004.catalogs import sustain
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.navigation import reachability
from rs2004.quests.strike_combat import ARENA_COVER, DEMON_COVER, cast_from_cover, cast_strike, ready_strikes, take_strike_cover
from rs2004.tabs import autocast
from rs2004.traversal import traversal

S = {}


class FakeNpc:
    def __init__(self, tile, size=3):
        self.index = 1
        self.id = 677
        self.name = 'Black Demon'
        self.size = size
        self._tile = tile

    def tile(self):
        return self._tile

    def network_tile(self):
        return self._tile

    def targets_me(self):
        return False


def quiet(m):
    pass


def cast_on_npc(spell, target):
    S['casts'].append(spell)
    S['runes'] -= 1
    return True


def delay_ticks(n=1):
    if S['delay'] is not None:
        S['delay']()
    if False:
        yield


def walk(dest, run=False):
    S['walks'].append(dest)
    return True


def nothing():
    if False:
        yield


def _setup():
    S['here'] = DEMON_COVER
    S['runes'] = 150
    S['casts'] = []
    S['walks'] = []
    S['delay'] = None
    S['npc'] = FakeNpc(Tile(2478, 9866, 0))
    spy_on(game, 'tile', impl=lambda: S['here'])
    spy_on(npcs, 'all', impl=lambda: [S['npc']])
    spy_on(reachability, 'line_of_sight', returns=True)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(game, 'set_auto_retaliate', returns=True)
    spy_on(game, 'cast_on_npc', impl=cast_on_npc)
    spy_on(inventory, 'count', impl=lambda name: S['runes'])
    spy_on(skills, 'effective', returns=1)
    spy_on(sustain, 'run', impl=nothing)
    spy_on(execution, 'delay_ticks', impl=delay_ticks)
    spy_on(direct_navigator, 'walk', impl=walk)


before_each(_setup)


def opened_tab(tab):
    return True
    yield


def disarm():
    S['armed'] = False
    return True
    yield


def until_ticks(cond, ticks):
    return cond()
    yield


def walk_resilient(tile, **kwargs):
    S['here'] = tile
    S['route'].append(tile)
    return True
    yield


def _fn6():
    def _fn7():
        S['armed'] = True
        spy_on(autocast, 'armed', impl=lambda: S['armed'])
        spy_on(game, 'open_side_tab', impl=opened_tab)
        spy_on(autocast, 'disarm', impl=disarm)
        spy_on(equipment, 'items', returns=[])
        spy_on(execution, 'delay_until_ticks', impl=until_ticks)
        ready = yield from ready_strikes(quiet)
        expect(ready).to_be(True)
        expect(S['armed']).to_be(False)
    test('preparation disables staff autocast as well as retaliation', _fn7)

    def _fn12():
        S['here'] = ARENA_COVER
        S['npc'] = FakeNpc(Tile(2597, 3168, 0), 2)
        S['route'] = []
        spy_on(traversal, 'walk_resilient', impl=walk_resilient)
        covered = yield from take_strike_cover(ARENA_COVER, quiet, lambda: S['npc'])
        expect(covered).to_be(True)
        expect([[tile.x, tile.z] for tile in S['route']]).to_equal([[2598, 3167], [2598, 3169], [2594, 3169], [2594, 3167]])
        expect(S['casts']).to_equal(['Wind Strike'])
    test('a lost arena lure runs again even when already standing at cover', _fn12)

    def _fn16():
        cast = yield from cast_strike(DEMON_COVER, S['npc'], quiet)
        expect(cast).to_be(True)
        expect(S['casts']).to_equal(['Wind Strike'])
    test('casts without requiring the player to take damage', _fn16)

    def _fn18():
        S['runes'] = 0
        cast = yield from cast_strike(DEMON_COVER, S['npc'], quiet)
        expect(cast).to_be(False)
        expect(S['casts']).to_equal([])
    test('empty runes never fall back to melee', _fn18)

    def _fn20():
        spy_on(reachability, 'line_of_sight', returns=False)
        cast = yield from cast_strike(DEMON_COVER, S['npc'], quiet)
        expect(cast).to_be(False)
        expect(S['casts']).to_equal([])
    test('a blocked ray is never submitted to the server', _fn20)

    def _fn22():
        npc = FakeNpc(Tile(DEMON_COVER.x + 11, DEMON_COVER.z + 1, 0))
        expect(cast_from_cover(DEMON_COVER, npc)).to_be(True)
    test('casting range uses the body origin rather than the rendered centre', _fn22)

    def _fn23():
        S['delay'] = step_off_cover
        cast = yield from cast_strike(DEMON_COVER, S['npc'], quiet)
        expect(cast).to_be(False)
        expect(S['walks']).to_equal([DEMON_COVER])
    test('movement back to cover is not cancelled by a second walk', _fn23)

    def _fn26():
        S['here'] = ARENA_COVER
        S['npc'] = FakeNpc(Tile(2597, 3168, 0), 2)
        S['delay'] = npc_leaves_lane
        cast = yield from cast_strike(ARENA_COVER, S['npc'], quiet)
        expect(cast).to_be(False)
        expect(S['walks']).to_equal([ARENA_COVER])
    test('a moving NPC is re-read before a pending cast is allowed to settle', _fn26)


def step_off_cover():
    S['here'] = DEMON_COVER.translate(1, 0)


def npc_leaves_lane():
    S['npc'] = FakeNpc(Tile(2594, 3166, 0), 2)


describe('guarded quest Strikes', _fn6)
