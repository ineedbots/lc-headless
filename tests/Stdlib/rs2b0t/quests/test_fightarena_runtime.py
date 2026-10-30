"""Fight Arena's open-field fallback, from a live run where the Khazard Scorpion sat behind the cover rock for every
lure and no Strike was cast in 20 minutes."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.navigation import reachability
from rs2004.quests.defs.fightarena import fights
from rs2004.quests.defs.fightarena.fights import FA_FIGHT, fight_rounds
from rs2004.quests.strike_combat import ARENA_COVER
from rs2004.tabs import prayer
from rs2004.traversal import traversal

SCORPION_AT = Tile(2594, 3159, 0)


class Arena:
    def __init__(self):
        self.here = ARENA_COVER
        self.tick = 0
        self.casts = []
        self.walks = []
        self.alive = True
        self.scorpion = Fake(id=FA_FIGHT.scorpion.npc_id, size=2, tile=lambda: SCORPION_AT, network_tile=lambda: SCORPION_AT,
                             targets_another_player=lambda: False, targets_me=lambda: True, actions=lambda: ['Attack'], distance=lambda: 8)

    def game_tick(self):
        self.tick += 1
        return self.tick

    def tile(self):
        return self.here

    def scorpions(self):
        return [self.scorpion] if self.alive else []

    def walk(self, dest, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(dest)
        self.here = Tile(2596, 3162, 0)
        return True
        yield

    def cover(self, spot, log, lure_target=None):
        self.here = ARENA_COVER
        return True
        yield

    def cast(self, spot, target, log, lane=True):
        self.casts.append(spot)
        if len(self.casts) >= 2:
            self.alive = False
        return True
        yield

    def in_sight(self, a, b, size=1):
        # The rock stands between the cover and the scorpion; anywhere else sees it.
        return a != ARENA_COVER


def ready(log):
    return True
    yield


def casts_in_the_open():
    arena = Arena()
    spy_on(game, 'tick', arena.game_tick)
    spy_on(game, 'tile', arena.tile)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(npcs, 'query', querying(arena.scorpions))
    spy_on(skills, 'level', returns=70)
    spy_on(prayer, 'active', returns=True)
    spy_on(prayer, 'points', returns=40)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(sustain, 'run', instant_ticks)
    spy_on(inventory, 'items', returns=[])
    spy_on(traversal, 'walk_resilient', arena.walk)
    spy_on(reachability, 'line_of_sight', arena.in_sight)
    patch(execution, 'delay_ticks', instant_ticks)
    patch(execution, 'delay_until_ticks', instant_until_ticks)
    patch(fights, 'ready_strikes', ready)
    patch(fights, 'take_strike_cover', arena.cover)
    patch(fights, 'cast_strike', arena.cast)
    outcome = yield from fight_rounds(FA_FIGHT.scorpion, lambda message: None)
    expect(outcome).to_be('won')
    expect(len(arena.walks)).to_be_greater_than(0)
    expect([spot == ARENA_COVER for spot in arena.casts]).to_equal([False, False])


test('a beast that never comes round the rock is fought in the open under the prayer', casts_in_the_open)


class BesideCover(Arena):
    """Bouncer, three tiles wide, beside the cover: in sight, but his origin is off the lane."""

    def __init__(self):
        Arena.__init__(self)
        at = Tile(2596, 3167, 0)
        self.lanes = []
        self.scorpion = Fake(id=FA_FIGHT.bouncer.npc_id, size=3, tile=lambda: at, network_tile=lambda: at,
                             targets_another_player=lambda: False, targets_me=lambda: True, actions=lambda: ['Attack'], distance=lambda: 2)

    def cast(self, spot, target, log, lane=True):
        self.lanes.append(lane)
        return Arena.cast(self, spot, target, log)

    def in_sight(self, a, b, size=1):
        return True


def hits_beside_the_cover():
    arena = BesideCover()
    spy_on(game, 'tick', arena.game_tick)
    spy_on(game, 'tile', arena.tile)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(npcs, 'query', querying(arena.scorpions))
    spy_on(skills, 'level', returns=70)
    spy_on(prayer, 'active', returns=True)
    spy_on(prayer, 'points', returns=40)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(sustain, 'run', instant_ticks)
    spy_on(inventory, 'items', returns=[])
    spy_on(traversal, 'walk_resilient', arena.walk)
    spy_on(reachability, 'line_of_sight', arena.in_sight)
    patch(execution, 'delay_ticks', instant_ticks)
    patch(execution, 'delay_until_ticks', instant_until_ticks)
    patch(fights, 'ready_strikes', ready)
    patch(fights, 'take_strike_cover', arena.cover)
    patch(fights, 'cast_strike', arena.cast)
    outcome = yield from fight_rounds(FA_FIGHT.bouncer, lambda message: None)
    expect(outcome).to_be('won')
    expect(arena.walks).to_equal([])
    expect(arena.casts).to_equal([ARENA_COVER, ARENA_COVER])
    expect(arena.lanes).to_equal([False, False])


test('a wide beast beside the cover is hit without the lane once the lures fail', hits_beside_the_cover)


def pockets():
    from rs2004.quests.defs.fightarena import fightarena
    from rs2004.quests.defs.fightarena.areas import FA_TILE, walled_in
    expect(fightarena.resume_at).to_be(walled_in)
    for tile in [FA_TILE.ARENA_CENTRE, FA_TILE.DOOR1_INSIDE, Tile(2599, 3143, 0)]:
        expect(walled_in(tile), str(tile)).to_be(True)
    for tile in [FA_TILE.DOOR1_OUTSIDE, FA_TILE.YANILLE_BANK, FA_TILE.LADY_SERVIL]:
        expect(walled_in(tile), str(tile)).to_be(False)


test('a restart in the arena, its cells or its building resumes there before any banking', pockets)
