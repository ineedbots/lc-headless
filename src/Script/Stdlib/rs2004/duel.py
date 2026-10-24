"""The Duel Arena: the challenge, the rules-and-stake screen, the confirm screen and the win screen, the fight pens,
and the clue duel's lobby, handshake, search and helper. Mirrors rs2b0t's api/duel/Duel.ts and ClueDuel.ts (MIT,
see thirdparty/rs2b0t).

    duel.challenge(player)
    if duel.offer_open() and duel.partner() == 'bob':
        duel.accept()

Each screen is found by its text, not by id: the rules-and-stake screen says "Dueling with:", the confirm screen
"Before the duel starts:", and the win screen "The Spoils:". The stake inventories are found as trade's are: yours
offers "Remove". The rules are varp 286 (dueloptions); duelstatus (varp 285) never reaches the client.
"""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs, players
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.traversal import traversal

__all__ = [
    'duel', 'parse_duel_partner_header', 'DUEL_FIGHT_ARENAS', 'fight_arena_at', 'in_duel_challenge_area', 'DuelOffers',
    'CLUE_DUEL_LOBBY', 'CLUE_DUEL_OPTIONS', 'clue_duel_name', 'leave_clue_duel', 'ClueDuelHandshake', 'ClueDuelSearch',
    'ClueDuelHelper', 'DUEL_OPTIONS_VARP',
]

# 2004scape's Duel Arena sets "Challenge" as player op 1 in the lobby and "Fight" as op 2 in a pen.
CHALLENGE_OP = 1
FIGHT_OP = 2
# dueloptions: the rules both players have agreed, a bit each.
DUEL_OPTIONS_VARP = 286

_SELECT_TEXT = 'dueling with'
_CONFIRM_TEXT = 'before the duel starts:'
_WIN_TEXT = 'the spoils:'
_WAITING_TEXT = 'waiting for other player'
_OBSTACLES_TEXT = 'Obstacles'


def parse_duel_partner_header(header):
    """The name in the rules screen's "Dueling with: name", or None while it's empty."""
    if header is None:
        return None
    name = header.strip()
    if name.lower().startswith(_SELECT_TEXT):
        name = name[len(_SELECT_TEXT):].strip()
        if name.startswith(':'):
            name = name[1:].strip()
    return name if name else None


def _texts(root):
    return _core.get_texts(root) if root >= 0 else []


def _has_text(root, start):
    for text in _texts(root):
        if text.strip().lower().startswith(start):
            return True
    return False


class DuelOffers:
    """The two stakes, as InvItems, and whether the server has sent both (ready)."""

    def __init__(self, ready, mine, theirs):
        self.ready = ready
        self.mine = mine
        self.theirs = theirs

    def __repr__(self):
        return f'DuelOffers({self.ready}, {self.mine}, {self.theirs})'


class _Duel:
    """The no-stake Duel Arena handshake and the player ops. Both players accept the rules screen and then the
    confirm screen; the first to click waits on "Waiting for other player..."."""

    def _main(self):
        return _core.get_main_modal()

    def offer_open(self):
        return _has_text(self._main(), _SELECT_TEXT)

    def confirm_open(self):
        return _has_text(self._main(), _CONFIRM_TEXT)

    def win_open(self):
        return _has_text(self._main(), _WIN_TEXT)

    def active(self):
        return self.offer_open() or self.confirm_open()

    def partner(self):
        """The other player's name, from the rules screen, or None."""
        if not self.offer_open():
            return None
        for text in _texts(self._main()):
            if text.strip().lower().startswith(_SELECT_TEXT):
                return parse_duel_partner_header(text)
        return None

    def waiting_for_other(self):
        """You've accepted the screen, and the other player hasn't yet."""
        return self.active() and _has_text(self._main(), _WAITING_TEXT)

    def offers(self):
        """The stakes on the rules screen. On the confirm screen they're text, so ready means both say "Absolutely
        nothing!", the only stake a clue duel takes."""
        main = self._main()
        if self.offer_open():
            mine = -1
            theirs = -1
            for com, type, x, options in _core.get_inventories(main):
                if type != 'inv':
                    continue
                first = ''
                for option in options:
                    if option is not None:
                        first = option.lower()
                        break
                if first.startswith('remove'):
                    mine = com
                elif theirs == -1:
                    theirs = com
            ready = mine != -1 and theirs != -1 and _core.has_inventory(mine) and _core.has_inventory(theirs)
            return DuelOffers(ready, _core.get_inventory(mine) if mine != -1 else [], _core.get_inventory(theirs) if theirs != -1 else [])
        if self.confirm_open():
            nothing = _core.find_components('Absolutely nothing!', None, main)
            return DuelOffers(len(nothing) >= 2, [], [])
        return DuelOffers(False, [], [])

    def options(self):
        """The agreed rules, varp 286."""
        return reader.varp(DUEL_OPTIONS_VARP)

    def challenge(self, player):
        return player.interact(CHALLENGE_OP)

    def fight(self, player):
        return player.interact(FIGHT_OP)

    def accept(self):
        if not self.active():
            return False
        return _core.click_text('Accept', self._main())

    def toggle_obstacles(self):
        """Clicks the rules screen's Obstacles box: the button nearest its label."""
        main = self._main()
        if not self.offer_open():
            return False
        labels = _core.find_components(_OBSTACLES_TEXT, None, main)
        if len(labels) == 0:
            return False
        label = labels[0]
        best = None
        best_distance = -1
        for component in _core.find_components(None, None, main):
            if component.button is None or component.id == label.id:
                continue
            dx = (component.x + component.width // 2) - label.x
            dy = (component.y + component.height // 2) - (label.y + label.height // 2)
            distance = dx * dx + dy * dy
            if best is None or distance < best_distance:
                best = component
                best_distance = distance
        return best is not None and _core.click_component(best.id)

    def cancel(self):
        """Closes the rules or confirm screen. Use with yield from."""
        if not self.active():
            return False
        closed = yield from modals.close()
        return closed and not self.active()

    def close_win(self):
        """Closes the win screen. Use with yield from."""
        if not self.win_open():
            return False
        closed = yield from modals.close()
        return closed


duel = _Duel()

def _pen(min_x, max_x, min_z, max_z):
    return Record({'min_x': min_x, 'max_x': max_x, 'min_z': min_z, 'max_z': max_z})


# Why: the six 25x15 fight pens come from duel_arena_fight_zones and duel_arena_obstacle_fight_zones.
# Why: other duels share the scene, so a player in one pen must only target the other player in that pen.
DUEL_FIGHT_ARENAS = [
    _pen(3333, 3357, 3244, 3258),
    _pen(3364, 3388, 3225, 3239),
    _pen(3333, 3357, 3206, 3220),
    _pen(3364, 3388, 3244, 3258),
    _pen(3333, 3357, 3225, 3239),
    _pen(3364, 3388, 3206, 3220),
]


def fight_arena_at(tile):
    """The pen the tile is in, a Record of min_x, max_x, min_z and max_z, or None."""
    if tile is None or tile.level != 0:
        return None
    for area in DUEL_FIGHT_ARENAS:
        if tile.x >= area.min_x and tile.x <= area.max_x and tile.z >= area.min_z and tile.z <= area.max_z:
            return area
    return None


def in_duel_challenge_area(tile):
    """Whether the tile is in the arena's grounds, where a challenge can be sent, and not in a pen."""
    return tile is not None and tile.level == 0 and tile.x >= 3328 and tile.x <= 3393 and tile.z >= 3203 and tile.z <= 3325 \
        and fight_arena_at(tile) is None


# The clue duel (ClueDuel.ts)

CLUE_DUEL_LOBBY = Tile(3368, 3274, 0)
# The rules a clue duel takes: obstacles, and nothing else.
CLUE_DUEL_OPTIONS = 1024


def clue_duel_name(name):
    return (name or '').replace('_', ' ').strip().lower()


def _now():
    return _core.step_time()


def leave_clue_duel(log):
    """Forfeits a clue duel from inside its pen. Use with yield from."""
    if fight_arena_at(game.tile()) is None:
        return True
    log('forfeiting the clue duel')
    exit = locs.query().action('Forfeit').nearest()
    if exit is None or not exit.interact('Forfeit'):
        return False
    asked = yield from execution.delay_until(lambda: len([o for o in chat_dialog.options() if o.strip() == 'Yes']) > 0, 6000)
    if not asked:
        return False
    yield from chat_dialog.choose_option('Yes')
    left = yield from execution.delay_until(lambda: fight_arena_at(game.tile()) is None, 10000)
    return left


class ClueDuelHandshake:
    """Challenges partner and takes the duel through both screens, staking nothing with obstacles on. The
    initiator sets the rules; either side cancels a duel with the wrong partner, a stake, other rules, or one
    that stalls."""

    def __init__(self, partner, initiator, log):
        self.partner = partner
        self.initiator = initiator
        self.log = log
        self.opened_at = 0
        self.challenged_at = -1000000000
        self.option_sent_at = -1000000000

    def tick(self):
        """One step. False when the duel was rejected. Use with yield from."""
        if not duel.active():
            self.opened_at = 0
            if _now() - self.challenged_at < 5000:
                return True
            wanted = clue_duel_name(self.partner)
            other = players.query().where(lambda p: clue_duel_name(p.name) == wanted and not p.in_combat and in_duel_challenge_area(p.tile())).nearest()
            if other is None:
                return True
            self.challenged_at = _now()
            duel.challenge(other)
            return True
        if not self.opened_at:
            self.opened_at = _now()
        offers = duel.offers()
        if (duel.offer_open() and clue_duel_name(duel.partner()) != clue_duel_name(self.partner)) or len(offers.mine) > 0 or len(offers.theirs) > 0 \
                or _now() - self.opened_at >= 30000:
            self.log('rejecting a mismatched, staked or stalled clue duel')
            yield from duel.cancel()
            return False
        if not offers.ready:
            return True
        options = duel.options()
        if duel.offer_open() and options == 0:
            if self.initiator and _now() - self.option_sent_at >= 5000:
                self.option_sent_at = _now()
                duel.toggle_obstacles()
            return True
        if options != CLUE_DUEL_OPTIONS:
            self.log('rejecting unsafe clue duel rules')
            yield from duel.cancel()
            return False
        if not duel.waiting_for_other():
            duel.accept()
        return True


class ClueDuelSearch:
    """Finds a player in the lobby to take a clue duel with, trying each at most once a minute."""

    def __init__(self, log, tried=None):
        self.log = log
        self.tried = tried if tried is not None else {}
        self.handshake = None
        self.selected_at = 0

    def tick(self):
        """One step. Use with yield from."""
        now = _now()
        if self.handshake is not None and now - self.selected_at >= 30000:
            if duel.active():
                yield from duel.cancel()
            self.handshake = None
        if self.handshake is None:
            local = clue_duel_name(game.my_name())
            candidates = players.query().where(lambda p: clue_duel_name(p.name) != '' and clue_duel_name(p.name) != local
                                               and not p.in_combat and in_duel_challenge_area(p.tile())
                                               and now - self.tried.get(clue_duel_name(p.name), -1000000000) >= 60000).results()
            player = None
            if duel.active():
                partner = clue_duel_name(duel.partner())
                for p in candidates:
                    if clue_duel_name(p.name) == partner:
                        player = p
                        break
            else:
                candidates.sort(key=lambda p: (self.tried.get(clue_duel_name(p.name), 0), p.distance()))
                player = candidates[0] if candidates else None
            if player is None:
                if duel.active():
                    yield from duel.cancel()
                return
            self.selected_at = now
            self.tried[clue_duel_name(player.name)] = now
            self.handshake = ClueDuelHandshake(player.name, True, self.log)
            self.log(f'trying an unstaked obstacle duel with {player.name}')
        kept = yield from self.handshake.tick()
        if not kept:
            self.handshake = None


class ClueDuelHelper:
    """A task for the account helping another's clue duel: waits in the lobby, takes partner's challenge, and
    forfeits a duel that runs three minutes."""

    def __init__(self, partner, log):
        self.handshake = ClueDuelHandshake(partner, False, log)
        self.log = log
        self.entered_at = 0
        self.label = 'clue duel helper'

    def validate(self):
        return True

    def execute(self):
        if fight_arena_at(game.tile()) is not None:
            if not self.entered_at:
                self.entered_at = _now()
            if _now() - self.entered_at >= 180000:
                yield from leave_clue_duel(self.log)
            return
        self.entered_at = 0
        if duel.win_open():
            yield from duel.close_win()
            return
        if duel.active():
            yield from self.handshake.tick()
            return
        here = game.tile()
        if here is None or max(abs(here.x - CLUE_DUEL_LOBBY.x), abs(here.z - CLUE_DUEL_LOBBY.z)) > 4:
            yield from traversal.walk_resilient(CLUE_DUEL_LOBBY, radius=3, attempts=3, timeout_ms=60000, log=self.log)
            return
        yield from self.handshake.tick()
