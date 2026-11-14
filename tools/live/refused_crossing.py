"""Issue #37 acceptance script; run only on the isolated engine described in README.md."""

from rs2004.navigation import navigator
from rs2004.messages import game_messages
import _core
import json

START = Tile(3217, 3218, 0)
DEST = Tile(3216, 3218, 0)
PROBES = []

def report(message):
    log('WALK', _core.step_time(), game.tile(), message)
    if message.startswith('path:'):
        route = navigator.find_path(game.tile(), DEST, avoid_doors=[Tile(d[0], d[1], 0) for d in traversal._avoid_doors], use_teleport_catalog=False)
        PROBES.append(route.raw)
        log('ROUTE_PROBE', json.dumps(route.raw))

def loop():
    chat.command('tele 0,50,50,17,18')
    arrived = yield from execution.delay_until(lambda: game.tile() == START, 10000)
    assert arrived, 'setup teleport failed'
    yield from execution.delay_ticks(3)
    log('START', game.tile(), 'DEST', DEST)
    mark = game_messages.mark()
    started = _core.step_time()
    ok = yield from traversal.walk_to(DEST, radius=0, timeout_ms=90000, use_teleport_catalog=False, bank_item_counts={}, log=report)
    log('RESULT', ok, traversal.last_outcome, game.tile(), 'elapsed_ms', _core.step_time() - started, 'avoids', traversal._avoid_doors)
    log('MESSAGES', [(m.seq, m.text) for m in game_messages.since(mark)])
    assert len(PROBES) == 2, 'expected the initial route and one replan'
    first = [w['transport'] for w in PROBES[0]['waypoints'] if w.get('transport') is not None]
    second = [w['transport'] for w in PROBES[1]['waypoints'] if w.get('transport') is not None]
    assert len(first) == 1 and first[0]['loc_id'] == 1516, 'primary crossing was not planned'
    assert len(second) == 1 and second[0]['loc_id'] == 1519, 'alternate crossing was not planned'
    assert traversal._avoid_doors == [[3217, 3218]], 'primary crossing was not excluded'
    assert game_messages.saw_since(mark, 'The door is locked.'), 'server refusal missing'
    assert ok and traversal.last_outcome == 'arrived' and game.tile() == DEST, 'did not arrive'
    log('PASS issue37: refused primary, excluded it, replanned once, arrived via alternate')
    stop_account()
