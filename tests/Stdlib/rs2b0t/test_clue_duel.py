"""rs2b0t's test/api/ai/clues: duelTravel.test.ts and duelDiscovery.test.ts (MIT, see thirdparty/rs2b0t), on
spec.py's describe, test and expect, with the facades patched as rs2b0t spies on them. rs2b0t mocks Date.now; here
the duel's clock and the leg's are patched to one fake clock that delay_ticks moves on."""

from rs2004 import duel as duel_module
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.clues import travel
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.travel import DUEL_CLUE_TILE, crosses_clue_duel, reset_clue_duel_search, walk_across_clue_duel
from rs2004.duel import ClueDuelHandshake, ClueDuelSearch, DuelOffers, duel

LOBBY = Tile(3368, 3274, 0)
WRONG = Tile(3340, 3230, 0)


def same(a, b):
    return a.x == b.x and a.z == b.z and a.level == b.level


def bag(partner):
    return Fake(str=lambda key, default='': partner if key == 'clue_duel_partner' else default)


class Arena:
    """duelTravel.test.ts's fixture: the leg with the handshake stubbed."""

    def __init__(self, start):
        self.tile = start
        self.walks = []
        self.challenges = 0
        self.forfeits = 0
        self.cancelled = 0
        self.pending = False

    def install(self):
        w = self
        reset_clue_duel_search()
        spy_on(game, 'tile', lambda: w.tile)
        spy_on(game, 'my_name', lambda: 'Solver')
        spy_on(settings_store, 'global_bag', lambda: bag('Helper'))
        spy_on(locs, 'query', querying(lambda: w.trapdoors()))
        spy_on(chat_dialog, 'options', lambda: ['Yes', 'No'])
        spy_on(chat_dialog, 'choose_option', lambda text: w.choose())
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(duel, 'active', lambda: True)
        spy_on(duel, 'cancel', lambda: w.cancel())
        spy_on(traversal, 'walk_resilient', lambda tile, **opts: w.walk(tile))
        spy_on(ClueDuelHandshake, 'tick', lambda *a: w.enter(DUEL_CLUE_TILE))
        return self

    def trapdoors(self):
        w = self
        return [Fake(id=3203, name='Trapdoor', actions=lambda: ['Forfeit'], tile=lambda: WRONG, distance=lambda: 1, interact=lambda op: w.forfeit())]

    def forfeit(self):
        self.forfeits += 1
        return True

    def choose(self):
        self.tile = LOBBY
        return True
        yield

    def cancel(self):
        self.cancelled += 1
        return True
        yield

    def walk(self, tile):
        self.walks.append(tile)
        self.tile = tile
        return True
        yield

    def enter(self, pen):
        self.challenges += 1
        self.tile = pen
        return True
        yield


def walk(dest=None, radius=0):
    return run_wait(walk_across_clue_duel(dest or DUEL_CLUE_TILE, radius, lambda m: None))


def restarted_in_pen():
    w = Arena(Tile(3368, 3250, 0)).install()
    expect(walk()).to_be(True)
    expect(w.challenges).to_be(0)
    expect(w.forfeits).to_be(0)
    expect(len(w.walks)).to_be(1)
    expect(same(w.walks[0], DUEL_CLUE_TILE)).to_be(True)


def from_lobby():
    w = Arena(LOBBY).install()
    expect(walk()).to_be(True)
    expect(w.challenges).to_be(1)
    expect([(t.x, t.z) for t in w.walks]).to_equal([(LOBBY.x, LOBBY.z), (DUEL_CLUE_TILE.x, DUEL_CLUE_TILE.z)])


def wrong_arena():
    w = Arena(LOBBY).install()
    spy_on(ClueDuelHandshake, 'tick', lambda *a: w.enter(WRONG))
    expect(walk()).to_be(False)
    expect(w.challenges).to_be(2)
    expect(w.forfeits).to_be(2)
    expect(same(w.tile, LOBBY)).to_be(True)
    expect(any([same(t, DUEL_CLUE_TILE) for t in w.walks])).to_be(False)


def leaving():
    w = Arena(DUEL_CLUE_TILE).install()
    bank_tile = Tile(3382, 3269, 0)
    expect(crosses_clue_duel(bank_tile)).to_be(True)
    expect(walk(bank_tile, 3)).to_be(True)
    expect(w.forfeits).to_be(1)
    expect(len(w.walks)).to_be(1)
    expect(same(w.walks[0], bank_tile)).to_be(True)


def interrupted():
    w = Arena(LOBBY).install()
    w.pending = True
    expect(walk()).to_be(False)
    expect(w.cancelled).to_be(1)
    expect(w.challenges).to_be(0)


def unset_helper():
    w = Arena(LOBBY).install()
    spy_on(settings_store, 'global_bag', lambda: bag(''))
    spy_on(ClueDuelSearch, 'tick', lambda *a: w.enter(DUEL_CLUE_TILE))
    expect(walk()).to_be(True)
    expect(w.challenges).to_be(1)
    expect([(t.x, t.z) for t in w.walks]).to_equal([(LOBBY.x, LOBBY.z), (DUEL_CLUE_TILE.x, DUEL_CLUE_TILE.z)])


def casket_after_forfeit():
    w = Arena(DUEL_CLUE_TILE).install()
    state = {'held': True, 'opened': False, 'checks': []}

    def open_casket(op):
        state['checks'].append((op, w.forfeits, same(w.tile, LOBBY)))
        state['held'] = False
        state['opened'] = True
        return True

    def pack():
        if not state['held']:
            return []
        return [Fake(id=3555, name='Casket (hard)', count=1, slot=0, noted=False, actions=lambda: ['Open'], interact=open_casket)]

    spy_on(inventory, 'items', pack)
    spy_on(inventory, 'count_by_id', lambda id: len([i for i in pack() if i.id == id]))
    spy_on(inventory, 'first', lambda name: None)
    spy_on(bank, 'is_open', lambda: False)
    spy_on(reader, 'main_modal', lambda: -1)
    spy_on(ground_items, 'query', querying(lambda: []))
    spy_on(chat_dialog, 'can_continue', lambda: False)
    spy_on(chat_dialog, 'is_open', lambda: False)
    spy_on(sustain, 'run', lambda: instant_until(lambda: True))
    expect(run_wait(ClueExecutor().solve_held_clue(lambda m: None))).to_be('done')
    expect(state['opened']).to_be(True)
    expect(state['checks']).to_equal([('Open', 1, True)])


describe('the duel arena leg', lambda: [
    test('a restarted solver already in the target arena walks directly to the dig', restarted_in_pen),
    test('entering from the lobby completes the named handshake before walking to the dig', from_lobby),
    test('wrong arena assignment forfeits and stops after two attempts', wrong_arena),
    test('leaving the arena forfeits before walking back to the bank', leaving),
    test('an event interruption cancels the negotiation before yielding', interrupted),
    test('an unset helper searches lobby players before walking to the dig', unset_helper),
    test('a casket obtained in the duel is opened only after forfeiting', casket_after_forfeit),
])


# Finding a partner (duelDiscovery.test.ts)

def player(name, index, distance, tile=None, in_combat=False):
    at = tile or LOBBY
    return Fake(name=name, index=index, distance=lambda: distance, tile=lambda: at, in_combat=in_combat, combat_level=100)


class Lobby:
    def __init__(self):
        self.tile = LOBBY
        self.now = 1000
        self.active = False
        self.confirm = False
        self.partner = ''
        self.options = 0
        self.stake = False
        self.players = [player('Nearby duelist', 2, 2)]
        self.challenges = []
        self.accepts = 0
        self.cancelled = 0
        self.toggles = []
        self.ignore = set()
        self.unsafe = set()
        self.event = False

    def install(self):
        w = self
        reset_clue_duel_search()
        patch(travel, '_now_ms', lambda: w.now)
        patch(duel_module, '_now', lambda: w.now)
        spy_on(game, 'tile', lambda: w.tile)
        spy_on(game, 'my_name', lambda: 'Solver')
        spy_on(players, 'query', querying(lambda: list(w.players)))
        spy_on(settings_store, 'global_bag', lambda: bag(''))
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: w.walk(dest))
        spy_on(event_signal, 'pending', lambda: w.event)
        patch(execution, 'delay_ticks', lambda n=1: w.tick(n))
        patch(execution, 'delay_until', instant_until)
        spy_on(sustain, 'run', lambda: instant_until(lambda: True))
        spy_on(duel, 'active', lambda: w.active)
        spy_on(duel, 'offer_open', lambda: w.active and not w.confirm)
        spy_on(duel, 'partner', lambda: w.partner)
        spy_on(duel, 'waiting_for_other', lambda: False)
        spy_on(duel, 'challenge', lambda p: w.challenge(p))
        spy_on(duel, 'offers', lambda: DuelOffers(True, [], [Fake(id=995, name='Coins', count=1)] if w.stake else []))
        spy_on(duel, 'options', lambda: w.options)
        spy_on(duel, 'toggle_obstacles', lambda: w.toggle())
        spy_on(duel, 'accept', lambda: w.accept())
        spy_on(duel, 'cancel', lambda: w.cancel())
        return self

    def walk(self, dest):
        self.tile = dest
        return True
        yield

    def tick(self, n):
        self.now += n * 600
        return None
        yield

    def challenge(self, p):
        self.challenges.append(p.name)
        if p.name not in self.ignore:
            self.active = True
            self.partner = p.name
            self.options = 0
            self.stake = p.name in self.unsafe
        return True

    def toggle(self):
        self.toggles.append(6732)
        self.options ^= 1024
        return True

    def accept(self):
        self.accepts += 1
        if self.confirm:
            self.tile = Tile(3368, 3250, 0)
            self.active = False
        else:
            self.confirm = True
        return True

    def cancel(self):
        self.cancelled += 1
        self.active = False
        return True
        yield


def no_helper():
    w = Lobby().install()
    expect(walk()).to_be(True)
    expect(w.challenges).to_equal(['Nearby duelist'])
    expect(w.toggles).to_equal([6732])
    expect(w.accepts).to_be(2)
    expect(same(w.tile, DUEL_CLUE_TILE)).to_be(True)


def excludes():
    w = Lobby().install()
    w.players = [player('Solver', 0, 0), player('Busy', 1, 1, LOBBY, True), player('Fighter', 3, 1, Tile(3370, 3250, 0)),
                 player('Outside', 4, 1, Tile(3300, 3274, 0))] + w.players
    expect(walk()).to_be(True)
    expect(w.challenges).to_equal(['Nearby duelist'])


def moves_on():
    w = Lobby().install()
    w.ignore.add('Nearby duelist')
    w.players.append(player('Willing duelist', 3, 4))
    expect(walk()).to_be(True)
    expect(w.challenges).to_contain('Willing duelist')
    expect(w.now >= 31000).to_be(True)


def staked():
    w = Lobby().install()
    w.unsafe.add('Nearby duelist')
    w.players.append(player('Willing duelist', 3, 4))
    expect(walk()).to_be(True)
    expect(w.cancelled).to_be(1)
    expect(w.accepts).to_be(2)
    expect(w.partner).to_be('Willing duelist')


def already_open():
    w = Lobby().install()
    w.active = True
    w.partner = 'Nearby duelist'
    expect(walk()).to_be(True)
    expect(w.challenges).to_equal([])
    expect(w.accepts).to_be(2)


def empty_lobby():
    w = Lobby().install()
    w.players = []
    names = ['Spade', 'Sextant', 'Watch', 'Chart']
    pack = [Fake(id=3554, name='Clue scroll (hard)', count=1, slot=0, noted=False)] + \
        [Fake(id=952 + i, name=names[i], count=1, slot=i + 1, noted=False) for i in range(4)]
    spy_on(inventory, 'items', lambda: list(pack))
    spy_on(inventory, 'first', lambda name: ([i for i in pack if i.name == name] + [None])[0])
    spy_on(inventory, 'count_by_id', lambda id: len([i for i in pack if i.id == id]))
    spy_on(bank, 'is_open', lambda: False)
    spy_on(reader, 'main_modal', lambda: -1)
    spy_on(chat_dialog, 'can_continue', lambda: False)
    spy_on(chat_dialog, 'is_open', lambda: False)
    executor = ClueExecutor()
    results = [run_wait(executor.solve_held_clue(lambda m: None)) for _ in range(3)]
    expect(results).to_equal(['yield', 'yield', 'yield'])
    expect(w.challenges).to_equal([])
    expect(same(w.tile, LOBBY)).to_be(True)
    expect(w.now >= 181000).to_be(True)


def farther_player():
    w = Lobby().install()
    w.ignore.add('Nearby duelist')
    w.ignore.add('Second idle player')
    w.players.extend([player('Second idle player', 3, 3), player('Willing duelist', 4, 4)])
    expect(walk()).to_be(True)
    expect(w.challenges).to_contain('Willing duelist')
    expect(w.partner).to_be('Willing duelist')


def remembers():
    w = Lobby().install()
    w.players = [player(f'Duellist {i}', i + 1, i + 1) for i in range(5)]
    for i in range(4):
        w.ignore.add(f'Duellist {i}')
    expect(walk()).to_be(False)
    expect(walk()).to_be(True)
    expect(w.partner).to_be('Duellist 4')


describe('finding a clue duel partner', lambda: [
    test('without a helper, challenges a lobby player, enables obstacles and completes both unstaked screens', no_helper),
    test('automatic discovery excludes self, busy players, arena fighters and players outside the lobby', excludes),
    test('an unanswered challenge moves on to another available player', moves_on),
    test('a staked offer is cancelled and another player is tried without accepting the stake', staked),
    test('an already open unstaked duel with an eligible lobby player can supply the clue entry', already_open),
    test('an empty lobby yields repeatedly without resetting or abandoning the held clue', empty_lobby),
    test('unanswered nearby players do not starve a farther willing player', farther_player),
    test('partner search remembers unanswered players across bounded lobby waits', remembers),
])
