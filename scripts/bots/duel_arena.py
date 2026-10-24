# Trains melee in unstaked duels at the Duel Arena, challenging other players in the lobby every five seconds and
# fighting the duel out: rs2b0t's DuelArena (MIT, see thirdparty/rs2b0t). It trains the lower of Attack and Strength
# to their targets, then Defence, and stops when all three are reached. Its clue helper mode stands in the lobby for
# a partner's clue duel.

import time

from bots.duelarena.logic import DUEL_CHALLENGE_ANCHOR, DUEL_LOBBY_CENTER_RADIUS, DUEL_NEGOTIATION_TIMEOUT_MS, MAX_CENTER_SEEK_ATTEMPTS
from bots.duelarena.logic import MAX_FIGHT_ATTEMPTS, ChallengeCadence, begin_fight_signal, busy_message, can_attempt_duel_fight
from bots.duelarena.logic import can_seek_fight_center, challenge_candidate, challenge_result, duel_inviter, duel_requester_available
from bots.duelarena.logic import duel_targets_reached, exact_training_mode, fight_arena_center, has_exact_melee_styles
from bots.duelarena.logic import negotiation_expired, observe_fight_signal, should_center_duel_lobby, sort_challenge_targets
from bots.duelarena.logic import target_melee_style
from rs2004.catalogs import ContinueDialog

SETTINGS = {
    'mode': SettingDef('string', 'Train', 'Mode', options=['Train', 'Clue helper']),
    'partner': SettingDef('string', '', 'Clue solver partner', show_if={'key': 'mode', 'any_of': ['Clue helper']}),
    'target_attack': SettingDef('number', 99, 'Target Attack level', 1, 99,
                                help='trains the lower of Attack and Strength while either is below its target; Attack wins ties; Defence trains only after both reach theirs'),
    'target_strength': SettingDef('number', 99, 'Target Strength level', 1, 99,
                                  help='trains the lower of Attack and Strength while either is below its target; Attack wins ties; Defence trains only after both reach theirs'),
    'target_defence': SettingDef('number', 1, 'Target Defence level', 1, 99,
                                 help='opt in above 1; trained only after Attack and Strength both reach their targets; the equipped weapon must offer exact Attack, Strength, and Defensive styles'),
}

CHALLENGE_RESULT_WAIT_MS = 1500
DUEL_XP_SKILLS = ['attack', 'strength', 'defence', 'hitpoints']


def now_ms():
    return time.time() * 1000


def same_name(a, b):
    return a is not None and a.strip().lower() == b.strip().lower()


def player_in(area, player):
    tile = player.tile()
    return tile.level == 0 and tile.x >= area.min_x and tile.x <= area.max_x and tile.z >= area.min_z and tile.z <= area.max_z


def no_modal():
    return reader.main_modal() == -1


class CloseWin(Task):
    def __init__(self, bot):
        Task.__init__(self, label='close win')
        self.bot = bot

    def validate(self):
        return duel.win_open()

    def execute(self):
        self.bot.status = 'collecting victory'
        closed = yield from duel.close_win()
        if not closed:
            self.bot.log('could not close the Duel Arena victory screen — retrying')


class CompleteTargets(Task):
    def __init__(self, bot):
        Task.__init__(self, label='complete targets')
        self.bot = bot

    def validate(self):
        return self.bot.ready_to_complete()

    def execute(self):
        self.bot.complete_targets()


class Negotiate(Task):
    def __init__(self, bot):
        Task.__init__(self, label='negotiate')
        self.bot = bot
        self.opened_at = 0

    def validate(self):
        if not duel.active():
            self.opened_at = 0
            return False
        if self.opened_at == 0:
            self.opened_at = now_ms()
        return True

    def execute(self):
        bot = self.bot
        bot.note_partner()
        if negotiation_expired(self.opened_at, now_ms()):
            partner = duel.partner()
            bot.status = 'cancelling stalled duel'
            bot.log(f"duel handshake with {partner or 'the other player'} exceeded {DUEL_NEGOTIATION_TIMEOUT_MS // 1000}s — cancelling instead of waiting forever")
            cancelled = yield from duel.cancel()
            if not cancelled:
                bot.log('could not close the stalled duel screen — retrying after a fresh deadline')
            bot.cancel_negotiation(partner, now_ms())
            self.opened_at = 0
            return
        if duel.waiting_for_other():
            bot.status = 'waiting for opponent to accept'
            yield from execution.delay_ticks(1)
            return
        bot.status = 'accepting duel options' if duel.offer_open() else 'confirming duel'
        before = reader.main_modal()
        if not duel.accept():
            bot.log(f'could not click accept on Duel Arena modal {before} — retrying')
            yield from execution.delay_ticks(1)
            return
        yield from execution.delay_until(lambda: reader.main_modal() != before or duel.waiting_for_other(), 3000)


class TravelToArena(Task):
    def __init__(self, bot):
        Task.__init__(self, label='travel to arena')
        self.bot = bot

    def validate(self):
        tile = game.tile()
        return no_modal() and tile is not None and fight_arena_at(tile) is None and not in_duel_challenge_area(tile)

    def execute(self):
        bot = self.bot
        bot.status = 'walking to Al Kharid Duel Arena'
        bot.log('walking to the Duel Arena challenge area')
        arrived = yield from traversal.walk_resilient(DUEL_CHALLENGE_ANCHOR, radius=8, attempts=5, timeout_ms=300000, log=lambda m: bot.log(f'  {m}'))
        if not arrived:
            bot.log('Duel Arena walk did not arrive — the walker will retry')


class SetTrainingStyle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='set training style')
        self.bot = bot
        self.last_fail_log_at = 0

    def validate(self):
        tile = game.tile()
        bot = self.bot
        return no_modal() and tile is not None and (in_duel_challenge_area(tile) or fight_arena_at(tile) is not None) \
            and (not bot.has_melee_training_styles() or not bot.exact_style_selected())

    def _log_now(self):
        if now_ms() >= self.last_fail_log_at:
            self.last_fail_log_at = now_ms() + 30000
            return True
        return False

    def execute(self):
        bot = self.bot
        if not bot.has_melee_training_styles():
            bot.status = 'equip a melee weapon'
            if self._log_now():
                bot.log('the current combat interface must offer exact Attack and Strength styles, plus Defence while that goal is outstanding — equip a suitable melee weapon before dueling')
            yield from execution.delay_ticks(1)
            return
        style = bot.desired_style()
        bot.status = f'setting {style} style'
        if bot.exact_style_mode() is None:
            bot.status = f'equip a weapon with {style} style'
            if self._log_now():
                bot.log(f'{style} is unavailable on the current combat interface — refusing to train the wrong stat; equip a melee weapon that offers {style}')
            yield from execution.delay_ticks(1)
            return
        game.set_combat_style(style)
        selected = yield from execution.delay_until(lambda: bot.exact_style_selected(), 3000)
        if selected:
            bot.log(f"combat style set to {style} (Attack {skills.level('attack')}/{bot.target_attack}, Strength {skills.level('strength')}/{bot.target_strength}, "
                    + f"Defence {skills.level('defence')}/{bot.target_defence})")
        elif self._log_now():
            bot.log(f'could not set {style} style (combat tab not ready?) — retrying')


class FightOpponent(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight opponent')
        self.bot = bot

    def validate(self):
        return fight_arena_at(game.tile()) is not None and not game.in_combat()

    def execute(self):
        bot = self.bot
        arena = fight_arena_at(game.tile())
        if arena is None:
            return
        opponent = bot.opponent_in(arena)
        if opponent is None:
            if bot.can_seek_opponent():
                yield from bot.seek_opponent(arena)
            else:
                bot.report_center_seek_exhausted()
                yield from execution.delay_ticks(1)
            return
        if not bot.can_attempt_fight(opponent):
            if bot.fight_attempts_exhausted():
                bot.report_fight_attempts_exhausted(opponent)
            else:
                bot.status = 'waiting for duel countdown'
            yield from execution.delay_ticks(1)
            return
        bot.remember_opponent(opponent.name)
        bot.fight_attempts += 1
        attempt = bot.fight_attempts
        bot.status = f"fighting {opponent.name or 'opponent'}"
        if not duel.fight(opponent):
            bot.log(f'could not send Fight to {opponent.name or f"player {opponent.index}"} (attempt {attempt}/{MAX_FIGHT_ATTEMPTS})')
            yield from execution.delay_ticks(1)
            return
        yield from execution.delay_until_ticks(lambda: game.in_combat() or fight_arena_at(game.tile()) is None or duel.win_open(), 4)


class AcceptInvitation(Task):
    def __init__(self, bot):
        Task.__init__(self, label='accept invitation')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return no_modal() and in_duel_challenge_area(game.tile()) and bot.has_melee_training_styles() and bot.pending_inviter() is not None

    def execute(self):
        bot = self.bot
        inviter = bot.pending_inviter()
        if inviter is None:
            return
        bot.remember_opponent(inviter.name)
        bot.status = f"accepting {inviter.name or 'duel request'}"
        bot.log(f'accepting duel request from {inviter.name or f"player {inviter.index}"}')
        sent_at = now_ms()
        mark = game_messages.mark()
        dispatched = duel.challenge(inviter)
        opened = False
        if dispatched:
            opened = yield from execution.delay_until(lambda: duel.active() or game_messages.saw_since(mark, busy_message), CHALLENGE_RESULT_WAIT_MS)
        result = challenge_result(dispatched, opened and duel.active(), game_messages.saw_since(mark, busy_message))
        bot.consume_inviter(inviter.name)
        bot.cadence.record(result, sent_at)
        if result != 'interface':
            bot.abandon_opponent(inviter.name)
            if result == 'sent':
                bot.log('duel-request interface did not open — treating the reciprocal Challenge as a fresh request and moving on')
            elif result == 'busy':
                bot.log(f"{inviter.name or 'duel requester'} became busy — trying another bot immediately")
            else:
                bot.log('duel-request acceptance did not dispatch — dropping the stale request so later bots are not starved')
            return
        bot.note_partner()


class CenterLobby(Task):
    def __init__(self, bot):
        Task.__init__(self, label='center lobby')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return no_modal() and bot.has_melee_training_styles() and should_center_duel_lobby(game.tile(), len(bot.challenge_targets()))

    def execute(self):
        self.bot.status = 'moving to find duelists'
        yield from direct_navigator.walk_to(DUEL_CHALLENGE_ANCHOR, DUEL_LOBBY_CENTER_RADIUS, 12000)


class SendChallenge(Task):
    def __init__(self, bot):
        Task.__init__(self, label='send challenge')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return no_modal() and in_duel_challenge_area(game.tile()) and bot.has_melee_training_styles() and bot.cadence.ready(now_ms()) \
            and len(bot.challenge_targets()) > 0

    def execute(self):
        bot = self.bot
        target = bot.next_challenge_target()
        if target is None:
            bot.status = 'waiting for another duelist'
            return
        sent_at = now_ms()
        mark = game_messages.mark()
        bot.remember_opponent(target.name)
        bot.status = f"challenging {target.name or 'player'}"
        if not duel.challenge(target):
            bot.cadence.record('failed', sent_at)
            return
        yield from execution.delay_until(lambda: duel.active() or game_messages.saw_since(mark, busy_message), CHALLENGE_RESULT_WAIT_MS)
        if duel.active():
            bot.cadence.record('interface', sent_at)
            bot.note_partner()
            return
        if game_messages.saw_since(mark, busy_message):
            bot.cadence.record('busy', sent_at)
            bot.log(f"{target.name or 'target'} is busy — trying another bot immediately")
            return
        bot.cadence.record('sent', sent_at)
        bot.log(f'duel request sent to {target.name or f"player {target.index}"}; next invite in 5s')


class DuelArena(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.opponent = None
        self.invite_queue = []
        self.challenge_cursor = 0
        self.cadence = ChallengeCadence()
        self.duels = 0
        self.fight_pen = None
        self.fight_signal = begin_fight_signal(None)
        self.fight_attempts = 0
        self.fight_exhaustion_logged = False
        self.center_seek_attempts = 0
        self.center_seek_exhaustion_logged = False
        yield from execution.delay_until(lambda: game.scene_ready(), 0)
        s = self.settings
        self.mode = s.str('mode', 'Train')
        if self.mode == 'Clue helper':
            partner = s.str('partner', '').strip()
            if not partner or clue_duel_name(partner) == clue_duel_name(game.my_name()):
                self.request_finish('set a clue solver partner')
                return
            self.partner = partner
            self.status = f'helping {partner} with clues'
            self.add(ContinueDialog(), ClueDuelHelper(partner, lambda m: self.log(m)))
            return
        self.target_attack = s.num('target_attack', 99)
        self.target_strength = s.num('target_strength', 99)
        self.target_defence = s.num('target_defence', 1)
        self.started_at = time.time()
        self.xp_at_start = self.training_xp()
        self.on('chat_message', self.heard)
        self.log(f'Duel Arena trainer starting — melee only; targets Attack {self.target_attack}, Strength {self.target_strength}, '
                 + f'Defence {self.target_defence}; challenges every 5s')
        self.on('tick', lambda e: self.observe_fight_state())
        self.observe_fight_state()
        self.add(ContinueDialog(), CloseWin(self), CompleteTargets(self), Negotiate(self), TravelToArena(self), SetTrainingStyle(self), FightOpponent(self),
                 AcceptInvitation(self), CenterLobby(self), SendChallenge(self))

    def heard(self, line):
        inviter = duel_inviter(line)
        if inviter is not None and len([name for name in self.invite_queue if same_name(name, inviter)]) == 0:
            self.invite_queue.append(inviter)
            self.log(f'duel request received from {inviter}')

    def on_stop(self, reason):
        self.reset_fight_round()

    def recovery_anchor(self):
        return DUEL_CHALLENGE_ANCHOR

    def on_progress_report(self):
        if self.mode == 'Clue helper':
            return {'Status': self.status, 'Partner': self.partner}
        minutes = (time.time() - self.started_at) / 60
        gained = max(0, self.training_xp() - self.xp_at_start)
        return {
            'Status': self.status,
            'Attack': f"{skills.level('attack')}/{self.target_attack}",
            'Strength': f"{skills.level('strength')}/{self.target_strength}",
            'Defence': f"{skills.level('defence')}/{self.target_defence}",
            'Style': self.desired_style(),
            'Opponent': self.opponent or '-',
            'Duels': self.duels,
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }

    def training_xp(self):
        return sum([skills.xp(skill) for skill in DUEL_XP_SKILLS])

    # The style

    def desired_style(self):
        return target_melee_style(skills.level('attack'), skills.level('strength'), skills.level('defence'), self.target_attack, self.target_strength,
                                  self.target_defence)

    def exact_style_mode(self):
        """A style is valid only when the combat interface trains that stat."""
        style = self.desired_style()
        return exact_training_mode(style, game.combat_style_resolution(style))

    def exact_style_selected(self):
        mode = self.exact_style_mode()
        return mode is not None and game.combat_mode() == mode

    def has_melee_training_styles(self):
        # Exact Attack and Strength are the guard against a ranged interface; Defence counts only while its opt-in
        # goal is outstanding.
        return has_exact_melee_styles(game.combat_style_resolution('attack'), game.combat_style_resolution('strength'),
                                      game.combat_style_resolution('defence'), skills.level('defence') < self.target_defence)

    def targets_reached(self):
        return duel_targets_reached(skills.level('attack'), skills.level('strength'), skills.level('defence'), self.target_attack, self.target_strength,
                                    self.target_defence)

    def ready_to_complete(self):
        return self.targets_reached() and self.fight_pen is None and self.opponent is None and not duel.active()

    def complete_targets(self):
        self.status = 'targets reached'
        self.log(f"targets reached — Attack {skills.level('attack')}/{self.target_attack}, Strength {skills.level('strength')}/{self.target_strength}, "
                 + f"Defence {skills.level('defence')}/{self.target_defence}; stopping")
        self.request_finish('Duel Arena targets reached')

    # Opponents and invitations

    def note_partner(self):
        partner = duel.partner()
        if partner is None:
            return
        self.consume_inviter(partner)
        if not same_name(self.opponent, partner):
            self.opponent = partner
            self.log(f'negotiating a duel with {partner}')

    def pending_inviter(self):
        while len(self.invite_queue) > 0:
            name = self.invite_queue[0]
            player = players.query().name(name).nearest()
            if player is not None and duel_requester_available(player.tile(), player.in_combat):
                return player
            self.invite_queue.pop(0)
            self.log(f'duel requester {name} is no longer free in the challenge area — dropping stale request')
        return None

    def consume_inviter(self, name):
        if name is None:
            return
        self.invite_queue = [value for value in self.invite_queue if not same_name(value, name)]

    def challenge_targets(self):
        return sort_challenge_targets(players.query().where(lambda p: p.name is not None and not p.in_combat and in_duel_challenge_area(p.tile())).results(),
                                      game.combat_level())

    def next_challenge_target(self):
        choice = challenge_candidate(self.challenge_targets(), self.challenge_cursor)
        if choice is None:
            return None
        self.challenge_cursor = choice[1]
        return choice[0]

    def remember_opponent(self, name):
        if name is not None:
            self.opponent = name

    def abandon_opponent(self, name):
        if name is None or same_name(self.opponent, name):
            self.opponent = None

    def cancel_negotiation(self, name, cancelled_at):
        self.consume_inviter(name)
        self.abandon_opponent(name)
        self.cadence.record('sent', cancelled_at)

    def opponent_in(self, area):
        if self.opponent is None:
            return None
        for player in players.query().where(lambda p: player_in(area, p)).results():
            if same_name(player.name, self.opponent):
                return player
        return None

    # The fight

    def can_attempt_fight(self, opponent):
        return can_attempt_duel_fight(game.tile(), opponent.tile(), self.fight_signal.phase == 'ready', game.in_combat(), self.fight_attempts)

    def seek_opponent(self, area):
        self.status = 'moving to find opponent'
        self.center_seek_attempts += 1
        yield from direct_navigator.walk_to(fight_arena_center(area), 2, 12000)

    def can_seek_opponent(self):
        return can_seek_fight_center(self.center_seek_attempts)

    def report_center_seek_exhausted(self):
        self.status = 'waiting for opponent in arena'
        if not self.center_seek_exhaustion_logged:
            self.center_seek_exhaustion_logged = True
            self.log(f'opponent is still outside the visible scene after {MAX_CENTER_SEEK_ATTEMPTS} center seeks — waiting without injecting more walks')

    def fight_attempts_exhausted(self):
        return self.fight_attempts >= MAX_FIGHT_ATTEMPTS

    def report_fight_attempts_exhausted(self, opponent):
        self.status = f"Fight unavailable for {opponent.name or 'opponent'}"
        if not self.fight_exhaustion_logged:
            self.fight_exhaustion_logged = True
            self.log(f'Fight did not start after {MAX_FIGHT_ATTEMPTS} attempts against {opponent.name or f"player {opponent.index}"} — refusing to spam player operations')

    def observe_fight_state(self):
        if not game.scene_ready() or game.tile() is None:
            return
        next_pen = fight_arena_at(game.tile())
        if next_pen is not self.fight_pen:
            previous = self.fight_pen
            self.fight_pen = next_pen
            self.fight_signal = begin_fight_signal(game.overhead_text())
            self.fight_attempts = 0
            self.fight_exhaustion_logged = False
            self.center_seek_attempts = 0
            self.center_seek_exhaustion_logged = False
            if previous is not None and next_pen is None:
                self.duels += 1
                self.opponent = None
                self.cadence.reset()
                self.log(f"duel complete #{self.duels} — Attack {skills.level('attack')}, Strength {skills.level('strength')}, Defence {skills.level('defence')}")
        elif next_pen is not None:
            self.fight_signal = observe_fight_signal(self.fight_signal, game.overhead_text())

    def reset_fight_round(self):
        self.fight_pen = None
        self.fight_signal = begin_fight_signal(None)
        self.fight_attempts = 0
        self.fight_exhaustion_logged = False
        self.center_seek_attempts = 0
        self.center_seek_exhaustion_logged = False


BOT = define_bot(
    name='Duel Arena Combat Trainer',
    create=DuelArena,
    description='Walks to the Al Kharid Duel Arena, pairs with other players, accepts both no-stake screens, fights with melee, and trains Attack/Strength plus opt-in Defence toward configured target levels',
    category='Combat',
    tags=['duel arena', 'pvp', 'attack', 'strength', 'defence', 'multibox'],
    settings_schema=SETTINGS,
)
