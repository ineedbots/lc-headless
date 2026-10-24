"""rs2b0t's test/scripts/DuelArena/DuelArenaLogic.test.ts and the parser half of duelInterface.test.ts (MIT, see
thirdparty/rs2b0t), on spec.py's describe, test and expect. DuelArena.test.ts and the rest of duelInterface.test.ts
replace the client's facades, which pocketpy can't; rs2004.duel finds its screens by text."""

from rs2004.catalogs import Record
from bots.duelarena.logic import CHALLENGE_INTERVAL_MS, DUEL_CHALLENGE_ANCHOR, DUEL_LOBBY_CENTER_RADIUS, DUEL_NEGOTIATION_TIMEOUT_MS
from bots.duelarena.logic import MAX_CENTER_SEEK_ATTEMPTS, MAX_FIGHT_ATTEMPTS, ChallengeCadence, begin_fight_signal, busy_message
from bots.duelarena.logic import can_attempt_duel_fight, can_seek_fight_center, challenge_candidate, challenge_result, confirmed_incoming_invite
from bots.duelarena.logic import duel_inviter, duel_requester_available, duel_targets_reached, exact_training_mode, fight_arena_center
from bots.duelarena.logic import has_exact_melee_styles, negotiation_expired, observe_fight_signal, should_center_duel_lobby
from bots.duelarena.logic import sort_challenge_targets, target_melee_style
import bots.duel_arena as duel_arena

A = DUEL_CHALLENGE_ANCHOR


def every_pen():
    expect(len(DUEL_FIGHT_ARENAS)).to_be(6)
    for arena in DUEL_FIGHT_ARENAS:
        tile = Tile(arena.min_x, arena.max_z, 0)
        expect(fight_arena_at(tile)).to_be(arena)
        expect(in_duel_challenge_area(tile)).to_be(False)


def centers():
    for arena in DUEL_FIGHT_ARENAS:
        center = fight_arena_center(arena)
        expect(fight_arena_at(center)).to_be(arena)
        expect(max(center.x - arena.min_x, arena.max_x - center.x)).to_be_less_than_or_equal(12)
        expect(max(center.z - arena.min_z, arena.max_z - center.z)).to_be_less_than_or_equal(12)


def boundaries():
    arena = DUEL_FIGHT_ARENAS[0]
    expect(fight_arena_at(Tile(arena.max_x, arena.max_z, 0))).to_be(arena)
    expect(fight_arena_at(Tile(arena.max_x + 1, arena.max_z, 0))).to_be_null()
    expect(fight_arena_at(Tile(arena.max_x, arena.max_z + 1, 0))).to_be_null()
    expect(fight_arena_at(Tile(arena.min_x, arena.min_z, 1))).to_be_null()


def centering():
    arena = DUEL_FIGHT_ARENAS[0]
    away = Tile(A.x + DUEL_LOBBY_CENTER_RADIUS + 1, A.z, 0)
    expect(should_center_duel_lobby(away, 0)).to_be(True)
    expect(should_center_duel_lobby(A, 0)).to_be(False)
    expect(should_center_duel_lobby(away, 1)).to_be(False)
    expect(should_center_duel_lobby(Tile(arena.min_x, arena.min_z, 0), 0)).to_be(False)


describe('Duel Arena geography', lambda: [
    test('the lobby anchor is challengable and never classified as a fight pen', lambda: [
        expect(in_duel_challenge_area(A)).to_be(True),
        expect(fight_arena_at(A)).to_be_null(),
    ]),
    test('all six server fight pens are classified independently', every_pen),
    test('each pen center sees every possible spawn within twelve tiles', centers),
    test('honours inclusive pen boundaries without claiming adjacent lobby tiles', boundaries),
    test('rejects unrelated world tiles and upper planes', lambda: [
        expect(in_duel_challenge_area(Tile(3222, 3218, 0))).to_be(False),
        expect(in_duel_challenge_area(Tile(A.x, A.z, 1))).to_be(False),
        expect(fight_arena_at(None)).to_be_null(),
    ]),
    test('centers only a targetless bot outside the shared lobby scene', centering),
])


def res(requested, effective, mode):
    return Record({'requested': requested, 'effective': effective, 'mode': mode})


ATTACK = res('attack', 'attack', 0)
STRENGTH = res('strength', 'strength', 1)
DEFENCE = res('defence', 'defence', 3)

describe('target-driven melee style', lambda: [
    test('trains the lower of Attack and Strength while either is below target', lambda: [
        expect(target_melee_style(20, 40, 1, 99, 99, 1)).to_be('attack'),
        expect(target_melee_style(40, 20, 1, 99, 99, 1)).to_be('strength'),
        expect(target_melee_style(60, 60, 1, 70, 99, 1)).to_be('attack'),
        expect(target_melee_style(60, 60, 1, 99, 70, 1)).to_be('attack'),
    ]),
    test('levels the pair from 1/1 to 30/30 before finishing 99', lambda: [
        expect(target_melee_style(1, 1, 1, 30, 99, 1)).to_be('attack'),
        expect(target_melee_style(29, 29, 1, 30, 99, 1)).to_be('attack'),
        expect(target_melee_style(30, 29, 1, 30, 99, 1)).to_be('strength'),
        expect(target_melee_style(30, 98, 1, 30, 99, 1)).to_be('strength'),
        expect(target_melee_style(30, 99, 1, 30, 99, 1)).to_be('attack'),
    ]),
    test('withholds Defence until Attack and Strength both reach their targets', lambda: [
        expect(target_melee_style(60, 60, 1, 70, 70, 50)).to_be('attack'),
        expect(target_melee_style(69, 69, 1, 70, 70, 50)).to_be('attack'),
        expect(target_melee_style(70, 70, 1, 70, 70, 50)).to_be('defence'),
        expect(target_melee_style(99, 99, 1, 99, 99, 2)).to_be('defence'),
    ]),
    test('defaults Defence to complete and preserves Attack, Strength, Defence tie priority', lambda: [
        expect(target_melee_style(1, 1, 1, 99, 99, 1)).to_be('attack'),
        expect(target_melee_style(99, 98, 1, 99, 99, 1)).to_be('strength'),
        expect(target_melee_style(90, 80, 70, 99, 99, 89)).to_be('strength'),
        expect(target_melee_style(80, 90, 70, 99, 99, 89)).to_be('attack'),
        expect(target_melee_style(99, 99, 1, 99, 99, 2)).to_be('defence'),
        expect(target_melee_style(120, 120, 120, 99, 99, 99)).to_be('attack'),
    ]),
    test('accepts exact Defence and rejects every wrong-stat fallback', lambda: [
        expect(exact_training_mode('attack', ATTACK)).to_be(0),
        expect(exact_training_mode('strength', STRENGTH)).to_be(1),
        expect(exact_training_mode('defence', DEFENCE)).to_be(3),
        expect(exact_training_mode('attack', res('attack', 'defence', 3))).to_be_null(),
        expect(exact_training_mode('strength', res('strength', 'controlled', 2))).to_be_null(),
        expect(exact_training_mode('defence', res('defence', 'controlled', 2))).to_be_null(),
        expect(exact_training_mode('attack', None)).to_be_null(),
    ]),
    test('requires exact Defence only while its opt-in target remains outstanding', lambda: [
        expect(has_exact_melee_styles(ATTACK, STRENGTH, None, False)).to_be(True),
        expect(has_exact_melee_styles(ATTACK, STRENGTH, DEFENCE, True)).to_be(True),
        expect(has_exact_melee_styles(ATTACK, STRENGTH, None, True)).to_be(False),
        expect(has_exact_melee_styles(ATTACK, None, DEFENCE, False)).to_be(False),
        expect(has_exact_melee_styles(ATTACK, res('strength', 'defence', 2), DEFENCE, True)).to_be(False),
    ]),
    test('finishes only after all three configured targets are reached', lambda: [
        expect(duel_targets_reached(5, 5, 1, 5, 5, 1)).to_be(True),
        expect(duel_targets_reached(6, 7, 9, 5, 5, 8)).to_be(True),
        expect(duel_targets_reached(4, 99, 99, 5, 5, 5)).to_be(False),
        expect(duel_targets_reached(99, 4, 99, 5, 5, 5)).to_be(False),
        expect(duel_targets_reached(99, 99, 4, 5, 5, 5)).to_be(False),
    ]),
])

PEN = DUEL_FIGHT_ARENAS[0]
OTHER = DUEL_FIGHT_ARENAS[1]
SELF_TILE = Tile(PEN.min_x, PEN.min_z, 0)
OPPONENT_TILE = Tile(PEN.max_x, PEN.max_z, 0)
OTHER_TILE = Tile(OTHER.min_x, OTHER.min_z, 0)


def ready(self_tile=None, opponent_tile=None, fight_started=True, in_combat=False, attempts=0):
    return can_attempt_duel_fight(self_tile or SELF_TILE, opponent_tile or OPPONENT_TILE, fight_started, in_combat, attempts)


def fresh_signal():
    signal = begin_fight_signal('FIGHT!')
    signal = observe_fight_signal(signal, 'FIGHT!')
    expect(signal.phase).to_be('await-3')
    signal = observe_fight_signal(signal, None)
    signal = observe_fight_signal(signal, 'FIGHT!')
    expect(signal.phase).to_be('await-3')
    signal = observe_fight_signal(signal, '3')
    expect(signal.phase).to_be('await-2')
    signal = observe_fight_signal(signal, '2')
    signal = observe_fight_signal(signal, '1')
    signal = observe_fight_signal(signal, ' fight! ')
    expect(signal.phase).to_be('ready')
    expect(observe_fight_signal(signal, None)).to_be(signal)


def rejects_disorder():
    signal = begin_fight_signal(None)
    for text in ['2', '1', 'FIGHT!']:
        signal = observe_fight_signal(signal, text)
    expect(signal.phase).to_be('await-3')
    signal = observe_fight_signal(signal, '3')
    expect(observe_fight_signal(signal, '3')).to_be(signal)
    signal = observe_fight_signal(signal, '1')
    signal = observe_fight_signal(signal, 'FIGHT!')
    expect(signal.phase).to_be('await-3')
    signal = observe_fight_signal(signal, '3')
    signal = observe_fight_signal(signal, 'hello')
    signal = observe_fight_signal(signal, '2')
    expect(signal.phase).to_be('await-3')


def restarts():
    signal = begin_fight_signal(None)
    for text in ['3', '2', '3', '2', '1', 'FIGHT!']:
        signal = observe_fight_signal(signal, text)
    expect(signal.phase).to_be('ready')


describe('observable fight gate', lambda: [
    test('arms only on the FIGHT signal while both remembered opponents occupy the same pen', lambda: [
        expect(ready()).to_be(True),
        expect(ready(fight_started=False)).to_be(False),
        expect(ready(self_tile=A)).to_be(False),
        expect(ready(opponent_tile=OTHER_TILE)).to_be(False),
        expect(ready(opponent_tile=A)).to_be(False),
    ]),
    test('requires a fresh FIGHT signal after entering a pen', fresh_signal),
    test('rejects skipped, repeated, reordered, and unrelated countdown text', rejects_disorder),
    test('restarts cleanly when a new three arrives out of order', restarts),
    test('never retries in combat or beyond the bounded Fight budget', lambda: [
        expect(ready(in_combat=True)).to_be(False),
        expect(ready(attempts=MAX_FIGHT_ATTEMPTS - 1)).to_be(True),
        expect(ready(attempts=MAX_FIGHT_ATTEMPTS)).to_be(False),
    ]),
    test('bounds center seeks for an opponent outside the visible scene', lambda: [
        expect(can_seek_fight_center(0)).to_be(True),
        expect(can_seek_fight_center(MAX_CENTER_SEEK_ATTEMPTS - 1)).to_be(True),
        expect(can_seek_fight_center(MAX_CENTER_SEEK_ATTEMPTS)).to_be(False),
        expect(can_seek_fight_center(-1)).to_be(False),
    ]),
])


def line(type, username, text):
    return Record({'type': type, 'username': username, 'text': text})


describe('duel request parsing', lambda: [
    test('accepts the server duel-request chat type and display name', lambda: expect(duel_inviter(line('duel_request', 'Fresh Bot 7', 'wishes to duel with you.'))).to_be('Fresh Bot 7')),
    test('does not turn public spoofed text or nameless requests into player ops', lambda: [
        expect(duel_inviter(line('public', 'Spoofer', 'wishes to duel with you.'))).to_be_null(),
        expect(duel_inviter(line('duel_request', None, 'wishes to duel with you.'))).to_be_null(),
        expect(duel_inviter(line('duel_request', 'Bot', 'wishes to trade with you.'))).to_be_null(),
    ]),
    test('consumes an incoming request only after dispatch and interface confirmation', lambda: [
        expect(confirmed_incoming_invite(True, True)).to_be(True),
        expect(confirmed_incoming_invite(False, True)).to_be(False),
        expect(confirmed_incoming_invite(True, False)).to_be(False),
        expect(confirmed_incoming_invite(False, False)).to_be(False),
    ]),
    test('classifies every terminal reciprocal Challenge outcome', lambda: [
        expect(challenge_result(False, False, False)).to_be('failed'),
        expect(challenge_result(True, True, False)).to_be('interface'),
        expect(challenge_result(True, False, True)).to_be('busy'),
        expect(challenge_result(True, False, False)).to_be('sent'),
    ]),
    test('expires a half-open negotiation at its bounded deadline', lambda: [
        expect(negotiation_expired(0, DUEL_NEGOTIATION_TIMEOUT_MS * 2)).to_be(False),
        expect(negotiation_expired(1000, 1000 + DUEL_NEGOTIATION_TIMEOUT_MS - 1)).to_be(False),
        expect(negotiation_expired(1000, 1000 + DUEL_NEGOTIATION_TIMEOUT_MS)).to_be(True),
    ]),
    test('drops requests after the sender enters a fight pen or combat', lambda: [
        expect(duel_requester_available(A, False)).to_be(True),
        expect(duel_requester_available(A, True)).to_be(False),
        expect(duel_requester_available(SELF_TILE, False)).to_be(False),
        expect(duel_requester_available(None, False)).to_be(False),
    ]),
])


def sent_waits():
    cadence = ChallengeCadence()
    cadence.record('sent', 1000)
    expect(cadence.ready(1000 + CHALLENGE_INTERVAL_MS - 1)).to_be(False)
    expect(cadence.remaining(1000)).to_be(CHALLENGE_INTERVAL_MS)
    expect(cadence.ready(1000 + CHALLENGE_INTERVAL_MS)).to_be(True)


def interface_waits():
    cadence = ChallengeCadence()
    cadence.record('interface', 1200)
    expect(cadence.ready(1200 + CHALLENGE_INTERVAL_MS - 1)).to_be(False)
    expect(cadence.ready(1200 + CHALLENGE_INTERVAL_MS)).to_be(True)


def retryable():
    for result in ['busy', 'failed']:
        cadence = ChallengeCadence()
        cadence.record('sent', 1000)
        cadence.record(result, 1200)
        expect(cadence.ready(1200)).to_be(True)
        expect(cadence.remaining(1200)).to_be(0)


def peer(index, combat_level):
    return Record({'index': index, 'combat_level': combat_level})


BOTS = ['a', 'b', 'c']

describe('challenge cadence and rotation', lambda: [
    test('waits exactly five wall-clock seconds after a sent invite', sent_waits),
    test('an opened interface preserves cadence across its transient modal gap', interface_waits),
    test('busy and failed outcomes remain immediately retryable', retryable),
    test('the exact server busy message is recognized', lambda: [
        expect(busy_message('Other player is busy at the moment.')).to_be(True),
        expect(busy_message('Other player is not busy at the moment.')).to_be(False),
    ]),
    test('round-robins candidates and handles empty/negative cursors', lambda: [
        expect(challenge_candidate(BOTS, 0)).to_equal(('a', 1)),
        expect(challenge_candidate(BOTS, 1)).to_equal(('b', 2)),
        expect(challenge_candidate(BOTS, 3)).to_equal(('a', 1)),
        expect(challenge_candidate(BOTS, -1)).to_equal(('c', 3)),
        expect(challenge_candidate([], 0)).to_be_null(),
    ]),
    test('prefers candidates closest to the bot combat level, then index order', lambda: expect(
        [p.index for p in sort_challenge_targets([peer(0, 20), peer(1, 100), peer(2, 55), peer(3, 59)], 60)]).to_equal([3, 2, 0, 1])),
])

describe('duel partner header', lambda: [
    test('parses the opponent label without inventing a missing partner', lambda: [
        expect(parse_duel_partner_header('Dueling with: Fresh Bot 7')).to_be('Fresh Bot 7'),
        expect(parse_duel_partner_header('Dueling with:')).to_be_null(),
        expect(parse_duel_partner_header(None)).to_be_null(),
    ]),
])

describe('DuelArena settings', lambda: [
    test('requires an explicit Defence goal above level one', lambda: [
        expect(duel_arena.SETTINGS['target_defence'].default).to_be(1),
        expect(duel_arena.SETTINGS['target_attack'].default).to_be(99),
        expect(duel_arena.SETTINGS['mode'].options).to_equal(['Train', 'Clue helper']),
    ]),
])
