"""DuelArena's pure decisions: rs2b0t's scripts/DuelArena/DuelArenaLogic.ts (MIT, see thirdparty/rs2b0t). The pens
and the challenge area are rs2004.duel's, passed through."""

DUEL_CHALLENGE_ANCHOR = Tile(3368, 3274, 0)
CHALLENGE_INTERVAL_MS = 5000
DUEL_NEGOTIATION_TIMEOUT_MS = 30000
DUEL_LOBBY_CENTER_RADIUS = 4
MAX_FIGHT_ATTEMPTS = 4
MAX_CENTER_SEEK_ATTEMPTS = 2


def busy_message(text):
    """The server's whole "Other player is busy at the moment." line."""
    line = text.strip().lower()
    if line.endswith('.'):
        line = line[:-1]
    return line == 'other player is busy at the moment'


def fight_arena_center(area):
    return Tile((area.min_x + area.max_x) // 2, (area.min_z + area.max_z) // 2, 0)


def duel_requester_available(tile, in_combat):
    return not in_combat and in_duel_challenge_area(tile)


def should_center_duel_lobby(tile, visible_targets):
    """The lobby is larger than one scene; converge only when nobody is visible."""
    if not in_duel_challenge_area(tile) or tile is None or visible_targets > 0:
        return False
    return max(abs(tile.x - DUEL_CHALLENGE_ANCHOR.x), abs(tile.z - DUEL_CHALLENGE_ANCHOR.z)) > DUEL_LOBBY_CENTER_RADIUS


def target_melee_style(attack_level, strength_level, defence_level, target_attack, target_strength, target_defence):
    """Trains the lower of Attack and Strength while either is below target, ties to Attack; Defence waits until
    both are done."""
    attack_below = attack_level < target_attack
    strength_below = strength_level < target_strength
    if attack_below and (not strength_below or attack_level <= strength_level):
        return 'attack'
    if strength_below:
        return 'strength'
    return 'defence' if defence_level < target_defence else 'attack'


def duel_targets_reached(attack_level, strength_level, defence_level, target_attack, target_strength, target_defence):
    return attack_level >= target_attack and strength_level >= target_strength and defence_level >= target_defence


def exact_training_mode(style, resolution):
    """The combat mode that trains style, or None; a fallback that would train another stat is never accepted."""
    return resolution.mode if resolution is not None and resolution.effective == style else None


def has_exact_melee_styles(attack, strength, defence, require_defence):
    """Whether the weapon trains Attack and Strength exactly, and Defence when it's still a goal. Accurate alone is
    no proof of melee: a ranged interface offers it too."""
    return exact_training_mode('attack', attack) is not None and exact_training_mode('strength', strength) is not None \
        and (not require_defence or exact_training_mode('defence', defence) is not None)


class FightSignalState:
    """How far the pen's 3, 2, 1, FIGHT! countdown has run ('await-3', 'await-2', 'await-1', 'await-fight' or
    'ready'), and the overhead text last seen."""

    def __init__(self, phase, last_text):
        self.phase = phase
        self.last_text = last_text


def _normalize_overhead(text):
    normalized = (text or '').strip().upper()
    return normalized if len(normalized) > 0 else None


def begin_fight_signal(self_chat):
    """Text already up on entering the pen is the baseline, never an event."""
    return FightSignalState('await-3', _normalize_overhead(self_chat))


def observe_fight_signal(state, self_chat):
    """Requires the server's exact 3, 2, 1, FIGHT! sequence, freshly seen."""
    if state.phase == 'ready':
        return state
    message = _normalize_overhead(self_chat)
    if message == state.last_text:
        return state
    phase = 'await-3'
    if message == '3':
        phase = 'await-2'
    elif state.phase == 'await-2' and message == '2':
        phase = 'await-1'
    elif state.phase == 'await-1' and message == '1':
        phase = 'await-fight'
    elif state.phase == 'await-fight' and message == 'FIGHT!':
        phase = 'ready'
    return FightSignalState(phase, message)


def can_seek_fight_center(attempts):
    return attempts >= 0 and attempts < MAX_CENTER_SEEK_ATTEMPTS


def can_attempt_duel_fight(self_tile, opponent_tile, fight_started, in_combat, attempts):
    """Fight goes out on the overhead FIGHT!, the duelstatus varp being server-only, with both players in one pen."""
    self_arena = fight_arena_at(self_tile)
    return self_arena is not None and fight_arena_at(opponent_tile) is self_arena and fight_started and not in_combat \
        and attempts >= 0 and attempts < MAX_FIGHT_ATTEMPTS


def confirmed_incoming_invite(dispatched, interface_opened):
    return dispatched and interface_opened


def challenge_result(dispatched, interface_opened, busy):
    """'failed', 'interface', 'busy' or 'sent'."""
    if not dispatched:
        return 'failed'
    if interface_opened:
        return 'interface'
    return 'busy' if busy else 'sent'


def negotiation_expired(opened_at, now):
    """A missing peer mustn't hold the two-screen handshake open forever."""
    return opened_at > 0 and now - opened_at >= DUEL_NEGOTIATION_TIMEOUT_MS


def duel_inviter(line):
    """The player a duel request line (a chat_message of type 'duel_request') names; public text is ignored."""
    text = (line.text or '').strip().lower()
    if text.endswith('.'):
        text = text[:-1]
    if line.type != 'duel_request' or text != 'wishes to duel with you':
        return None
    name = (line.username or '').strip()
    return name if len(name) > 0 else None


class ChallengeCadence:
    """A challenge every 5s of wall clock; a busy or failed one can go again at once."""

    def __init__(self):
        self.next_at = 0

    def ready(self, now):
        return now >= self.next_at

    def record(self, result, sent_at):
        # Why: the cadence holds across the brief gap between the handshake's screens, so no second Challenge goes out.
        self.next_at = sent_at + CHALLENGE_INTERVAL_MS if result == 'sent' or result == 'interface' else 0

    def remaining(self, now):
        return max(0, self.next_at - now)

    def reset(self):
        self.next_at = 0


def challenge_candidate(candidates, cursor):
    """(candidate, next_cursor) round robin, so a crowded lobby doesn't hammer one bot; None with none."""
    if len(candidates) == 0:
        return None
    index = ((int(cursor) % len(candidates)) + len(candidates)) % len(candidates)
    return (candidates[index], index + 1)


def sort_challenge_targets(candidates, combat_level):
    """Peers whose combat level is closest to the bot's first, index order breaking ties."""
    ranked = list(candidates)
    ranked.sort(key=lambda c: (abs(combat_level - c.combat_level), c.index))
    return ranked
