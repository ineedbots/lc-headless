"""Clue duels validate partner, stakes and rules against actual duel screen readers."""

import rs2004.duel as arena
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_dialogue_workflows import DialogueWorld


class Player:
    def __init__(self, world, name, distance=1):
        self.world = world
        self.name = name
        self.dist = distance
        self.in_combat = False
        self.position = arena.CLUE_DUEL_LOBBY

    def tile(self):
        return self.position

    def distance(self):
        return self.dist

    def interact(self, op):
        self.world.challenges.append((self.name, op))
        return True


class DuelWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.now = 10000
        self.mode = 'offer'
        self.partner = 'Alice'
        self.rules = arena.CLUE_DUEL_OPTIONS
        self.ready = True
        self.waiting = False
        self.mine = []
        self.theirs = []
        self.position = arena.CLUE_DUEL_LOBBY
        self.challenges = []
        self.scene = []
        self.obstacles_label = FakeModule(id=500, button=None, x=10, y=10, height=10)
        self.checkbox = FakeModule(id=501, button='ok', x=25, y=10, width=10, height=10)

    def __enter__(self):
        DialogueWorld.__enter__(self)
        self.duel_saved = (arena._core, arena.reader, arena.game, arena.players)
        arena._core = self
        arena.reader = FakeModule(varp=lambda id: self.rules)
        arena.game = FakeModule(tile=lambda: self.position, my_name=lambda: 'My Bot')
        arena.players = FakeModule(query=lambda: EntityQuery(self.players, lambda p: True))
        return self

    def __exit__(self, *args):
        arena._core, arena.reader, arena.game, arena.players = self.duel_saved
        DialogueWorld.__exit__(self, *args)

    def players(self, ids, names, radius, layer):
        return list(self.scene)

    def get_main_modal(self):
        return 200 if self.mode is not None else -1

    def get_texts(self, root):
        texts = []
        if self.mode == 'offer':
            texts = ['Dueling with: ' + self.partner]
        elif self.mode == 'confirm':
            texts = ['Before the duel starts:']
        elif self.mode == 'win':
            texts = ['The Spoils:']
        if self.waiting:
            texts.append('Waiting for other player...')
        return texts

    def get_inventories(self, root):
        return [(101, 'inv', 0, ['Remove']), (102, 'inv', 200, [])]

    def get_inventory(self, com):
        return self.mine if com == 101 else self.theirs

    def has_inventory(self, com):
        return self.ready

    def find_components(self, text, button, root):
        if text == 'Absolutely nothing!':
            return [self.checkbox, self.checkbox] if self.ready else []
        if text == 'Obstacles':
            return [self.obstacles_label]
        return [self.obstacles_label, self.checkbox,
                FakeModule(id=502, button='ok', x=200, y=200, width=10, height=10)]

    def click_component(self, com):
        self.clicks.append(com)
        self.pending = 'rules'
        return True

    def click_text(self, text, root):
        assert text == 'Accept'
        self.clicks.append((self.mode, text))
        return True

    def advance(self):
        if self.respond and self.pending == 'rules':
            self.rules = arena.CLUE_DUEL_OPTIONS
            self.pending = None
        if self.respond and self.pending == 'page':
            self.mode = None
        DialogueWorld.advance(self)

    def handshake(self, initiator=True):
        return arena.ClueDuelHandshake('Alice', initiator, self.logs.append)


def test_handshake_accepts_only_unstaked_obstacle_rules_on_both_screens():
    with DuelWorld() as world:
        handshake = world.handshake()
        assert world.run(handshake.tick())
        world.mode = 'confirm'
        assert world.run(handshake.tick())
        assert world.clicks == [('offer', 'Accept'), ('confirm', 'Accept')]


def test_handshake_rejects_wrong_partner_or_stake_on_either_side():
    for reason in ['partner', 'mine', 'theirs']:
        with DuelWorld() as world:
            if reason == 'partner':
                world.partner = 'Eve'
            elif reason == 'mine':
                world.mine = [FakeModule(id=995, count=1)]
            else:
                world.theirs = [FakeModule(id=995, count=1)]
            assert world.run(world.handshake().tick()) is False
            assert world.mode is None
            assert world.clicks == ['close']


def test_handshake_waits_for_both_stake_inventories_before_accepting():
    with DuelWorld() as world:
        world.ready = False
        assert world.run(world.handshake().tick())
        assert world.clicks == []
        world.mode = 'confirm'
        assert world.run(world.handshake().tick())
        assert world.clicks == []


def test_initiator_sets_obstacles_then_waits_for_server_acknowledgement():
    with DuelWorld() as world:
        world.rules = 0
        handshake = world.handshake()
        assert world.run(handshake.tick())
        assert world.clicks == [501]
        assert world.rules == 0
        assert world.run(handshake.tick())
        assert world.clicks == [501]
        world.advance()
        assert world.run(handshake.tick())
        assert world.clicks == [501, ('offer', 'Accept')]


def test_receiver_does_not_change_rules_or_accept_until_initiator_sets_them():
    with DuelWorld() as world:
        world.rules = 0
        assert world.run(world.handshake(initiator=False).tick())
        assert world.clicks == []


def test_unsafe_rules_are_rejected_on_offer_and_confirm_screens():
    for screen in ['offer', 'confirm']:
        with DuelWorld() as world:
            world.mode = screen
            world.rules = arena.CLUE_DUEL_OPTIONS | 1
            assert world.run(world.handshake().tick()) is False
            assert world.mode is None and world.clicks == ['close']
            assert world.logs[-1] == 'rejecting unsafe clue duel rules'


def test_already_accepted_screen_is_not_clicked_again_while_partner_waits():
    with DuelWorld() as world:
        world.waiting = True
        assert world.run(world.handshake().tick())
        assert world.clicks == []


def test_stalled_handshake_is_cancelled_after_timeout():
    with DuelWorld() as world:
        world.ready = False
        handshake = world.handshake()
        assert world.run(handshake.tick())
        world.now += 30000
        assert world.run(handshake.tick()) is False
        assert world.mode is None and world.clicks == ['close']


def test_challenge_normalizes_partner_name_and_throttles_repeat_requests():
    with DuelWorld() as world:
        world.mode = None
        world.scene = [Player(world, ' ALICE ')]
        handshake = world.handshake()
        assert world.run(handshake.tick())
        assert world.run(handshake.tick())
        assert world.challenges == [(' ALICE ', arena.CHALLENGE_OP)]
        world.now += 5000
        assert world.run(handshake.tick())
        assert len(world.challenges) == 2


def test_challenge_ignores_partner_in_combat_or_inside_fight_pen():
    for fighting in [True, False]:
        with DuelWorld() as world:
            world.mode = None
            player = Player(world, 'Alice')
            if fighting:
                player.in_combat = True
            else:
                player.position = Tile(3333, 3244)
            world.scene = [player]
            assert world.run(world.handshake().tick())
            assert world.challenges == []


def test_search_skips_self_busy_players_and_recently_tried_names():
    with DuelWorld() as world:
        world.mode = None
        alice = Player(world, 'Alice', 3)
        bob = Player(world, 'Bob', 1)
        busy = Player(world, 'Busy', 1)
        busy.in_combat = True
        world.scene = [Player(world, 'My_Bot'), busy, bob, alice]
        search = arena.ClueDuelSearch(world.logs.append, tried={'bob': world.now})
        world.run(search.tick())
        assert search.handshake.partner == 'Alice'
        assert world.challenges == [('Alice', arena.CHALLENGE_OP)]
        assert search.tried['alice'] == world.now


def test_search_uses_incoming_partner_instead_of_nearest_player():
    with DuelWorld() as world:
        world.scene = [Player(world, 'Bob', 1), Player(world, 'Alice', 4)]
        search = arena.ClueDuelSearch(world.logs.append)
        world.run(search.tick())
        assert search.handshake.partner == 'Alice'
        assert world.clicks == [('offer', 'Accept')]


def test_search_declines_unknown_incoming_partner():
    with DuelWorld() as world:
        world.partner = 'Eve'
        world.scene = [Player(world, 'Alice')]
        search = arena.ClueDuelSearch(world.logs.append)
        world.run(search.tick())
        assert search.handshake is None
        assert world.mode is None and world.clicks == ['close']


def test_search_releases_timed_out_partner_and_tries_someone_else():
    with DuelWorld() as world:
        world.mode = None
        world.scene = [Player(world, 'Alice', 1), Player(world, 'Bob', 2)]
        search = arena.ClueDuelSearch(world.logs.append)
        world.run(search.tick())
        assert search.handshake.partner == 'Alice'
        world.now += 30000
        world.run(search.tick())
        assert search.handshake.partner == 'Bob'
        assert world.challenges[-1] == ('Bob', arena.CHALLENGE_OP)


def test_cancel_and_win_close_wait_for_server_modal_change():
    with DuelWorld() as world:
        assert world.run(arena.duel.cancel())
        assert world.mode is None
        assert world.run(arena.duel.cancel()) is False
        world.mode = 'win'
        assert world.run(arena.duel.close_win())
        assert world.mode is None
        assert world.run(arena.duel.close_win()) is False


def test_duel_accept_without_active_screen_does_not_click():
    with DuelWorld() as world:
        world.mode = None
        assert not arena.duel.accept()
        offers = arena.duel.offers()
        assert not offers.ready and offers.mine == [] and offers.theirs == []
        assert world.clicks == []
