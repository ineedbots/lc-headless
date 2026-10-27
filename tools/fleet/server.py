#!/usr/bin/env python3
"""Local view of the fleet-tracking files, with optional launch and stop.

    python3 tools/fleet/server.py                          # http://127.0.0.1:8765, read-only
    python3 tools/fleet/server.py --config client.jsonc    # ... with Launch and Stop client

Reads experience/, bank/, inventory/ and equipment/ from the repository root, and binds to loopback only.
Without --config it starts and stops nothing; with it, the page may launch one client process and stop the
one it launched. Ctrl+C ends the page, not the client.

Stdlib only.
"""

import argparse
import glob
import json
import os
import shutil
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GUI_DIR = os.path.dirname(os.path.abspath(__file__))

EXPERIENCE_DIR = os.path.join(ROOT, 'experience')
BANK_DIR = os.path.join(ROOT, 'bank')
INVENTORY_DIR = os.path.join(ROOT, 'inventory')
EQUIPMENT_DIR = os.path.join(ROOT, 'equipment')
LOGS_DIR = os.path.join(ROOT, 'logs')
LOG_FILE = os.path.join(LOGS_DIR, 'fleet.log')
PID_FILE = os.path.join(LOGS_DIR, 'fleet.pid')
BINARY_NAME = 'Rs2004Headless'
# SIGINT is the client's graceful path. A second one, like a second Ctrl+C, logs every account out at once
# when the first hasn't finished, which matters when the server refuses a logout in combat. SIGKILL is only
# for one that outlives both.
SECOND_INTERRUPT_SECONDS = 10
STOP_TIMEOUT_SECONDS = 40

# The client writes these, in this order (src/Accounts/ExperienceLog.cpp).
SKILLS = [
    'attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer', 'magic',
    'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
    'smithing', 'mining', 'herblore', 'agility', 'thieving', 'runecraft',
]

# The rate covers at most this many minutes back from the newest sample, and needs at least this long.
RATE_WINDOW_MINUTES = 15
MIN_RATE_SECONDS = 60


def _read_jsonl(path, limit=None):
    """Every complete line of a JSONL file, newest last. A line being written is skipped."""
    records = []
    try:
        with open(path, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return records[-limit:] if limit else records


def _latest(directory):
    """The last record in each <account>.jsonl in a directory, by account."""
    latest = {}
    for path in sorted(glob.glob(os.path.join(directory, '*.jsonl'))):
        account = os.path.basename(path)[:-len('.jsonl')]
        records = _read_jsonl(path, limit=1)
        if records:
            latest[account] = records[-1]
    return latest


def _parse_time(text):
    try:
        return time.mktime(time.strptime(text, '%Y-%m-%dT%H:%M:%SZ')) - time.timezone
    except (TypeError, ValueError, KeyError):
        return None


def _rate(history):
    """XP an hour per skill over the newest continuous run, or {} until there are two samples worth using.

    A relogin rewinds XP, so the run stops at the first sample where any skill went down."""
    if len(history) < 2:
        return {}

    run = [history[-1]]
    for record in reversed(history[:-1]):
        newest = run[-1]
        rewound = any(record.get('skills', {}).get(skill, {}).get('xp', 0) > newest.get('skills', {}).get(skill, {}).get('xp', 0) for skill in SKILLS)
        if rewound:
            break
        run.append(record)
        if len(run) >= RATE_WINDOW_MINUTES + 1:
            break

    oldest = run[-1]
    newest = run[0]
    start = _parse_time(oldest.get('time'))
    end = _parse_time(newest.get('time'))
    if start is None or end is None:
        return {}

    seconds = end - start
    if seconds < MIN_RATE_SECONDS:
        return {}

    hours = seconds / 3600.0
    return {
        skill: int((newest.get('skills', {}).get(skill, {}).get('xp', 0) - oldest.get('skills', {}).get(skill, {}).get('xp', 0)) / hours)
        for skill in SKILLS
    }


def experience():
    """Every account's skills, and what it is earning an hour, from the end of its log."""
    accounts = {}
    for path in sorted(glob.glob(os.path.join(EXPERIENCE_DIR, '*.jsonl'))):
        account = os.path.basename(path)[:-len('.jsonl')]
        # Enough for the whole rate window; the file itself may hold days.
        history = _read_jsonl(path, limit=RATE_WINDOW_MINUTES + 1)
        if not history:
            continue

        latest = history[-1]
        accounts[account] = {
            'time': latest.get('time'),
            'levels': {skill: latest.get('skills', {}).get(skill, {}).get('level', 0) for skill in SKILLS},
            'xp': {skill: latest.get('skills', {}).get(skill, {}).get('xp', 0) for skill in SKILLS},
            'rates': _rate(history),
            'samples': len(history),
        }

    return {'accounts': accounts, 'skills': SKILLS}


def banks():
    """Every item across the accounts' latest bank snapshot, with how many each account holds."""
    items = {}
    accounts = 0
    for account, record in _latest(BANK_DIR).items():
        accounts += 1
        for item in record.get('items', []):
            item_id = item.get('id')
            if item_id is None:
                continue
            entry = items.setdefault(item_id, {'id': item_id, 'name': item.get('name') or f'#{item_id}', 'total': 0, 'accounts': {}})
            entry['total'] += int(item.get('qty', 0) or 0)
            entry['accounts'][account] = entry['accounts'].get(account, 0) + int(item.get('qty', 0) or 0)

    return {'accounts': accounts, 'items': sorted(items.values(), key=lambda entry: -entry['total'])}


def inventory(account=None):
    """The backpack, and the worn equipment, for one account (or the names of the accounts there are)."""
    if not account:
        names = [os.path.basename(path)[:-len('.jsonl')] for path in sorted(glob.glob(os.path.join(INVENTORY_DIR, '*.jsonl')))]
        return {'accounts': names}

    def read(directory):
        records = _read_jsonl(os.path.join(directory, account + '.jsonl'), limit=1)
        return records[-1] if records else None

    return {'account': account, 'inventory': read(INVENTORY_DIR), 'equipment': read(EQUIPMENT_DIR)}




# ---- the client: launch and stop, only with --config ----

# The client config, absolute, or None in read-only mode.
CONTROL_CONFIG = None
# Set while this page has a client running or stopping: {'pid', 'status', 'startedAt', 'error'}.
STATE = {'status': 'idle', 'pid': None, 'startedAt': None, 'error': ''}
STATE_LOCK = threading.Lock()
# The Popen for a client this page launched, so it can wait on and reap it. None for an adopted one.
PROCESS = None


def find_binary():
    """The built client: beside the repository, in a preset's build folder, or on PATH."""
    candidates = [os.path.join(ROOT, BINARY_NAME)]
    for config in ('Release', 'Debug'):
        candidates.append(os.path.join(ROOT, 'build', config, BINARY_NAME))
    for preset in sorted(glob.glob(os.path.join(ROOT, 'build', '*'))):
        if os.path.isdir(preset):
            candidates.append(os.path.join(preset, BINARY_NAME))
            for config in ('Release', 'Debug'):
                candidates.append(os.path.join(preset, config, BINARY_NAME))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return shutil.which(BINARY_NAME)


def _is_our_client(pid):
    """Whether the process is alive and is this config's client, so an unrelated pid is never adopted."""
    if not pid or not os.path.isdir(f'/proc/{pid}'):
        return False
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as handle:
            arguments = [part.decode(errors='replace') for part in handle.read().split(b'\0') if part]
    except OSError:
        return False
    executable = os.path.basename(arguments[0]) if arguments else ''
    return executable == BINARY_NAME and any(os.path.abspath(argument) == CONTROL_CONFIG for argument in arguments[1:])


def _alive(pid):
    """Alive, not merely present: a child that has exited but not been reaped is a zombie, not a client."""
    try:
        with open(f'/proc/{pid}/stat') as handle:
            # The state is the field after the parenthesised command name, which may itself hold spaces.
            fields = handle.read().rsplit(')', 1)[-1].split()
            if fields and fields[0] == 'Z':
                return False
    except OSError:
        return False

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _write_pidfile(pid):
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(PID_FILE, 'w') as handle:
            json.dump({'pid': pid, 'config': CONTROL_CONFIG, 'startedAt': time.time()}, handle)
    except OSError:
        pass


def _remove_pidfile():
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def _adopt():
    """Take over a client this page launched before it was restarted, if its pidfile still names one."""
    global PROCESS
    try:
        with open(PID_FILE) as handle:
            saved = json.load(handle)
    except (OSError, ValueError):
        return

    pid = saved.get('pid')
    if _is_our_client(pid) and saved.get('config') == CONTROL_CONFIG:
        with STATE_LOCK:
            STATE.update({'status': 'running', 'pid': pid, 'startedAt': saved.get('startedAt'), 'error': ''})
    else:
        _remove_pidfile()


def control_state():
    with STATE_LOCK:
        state = dict(STATE)

    if state['status'] in ('running', 'stopping') and state['pid'] and not _alive(state['pid']):
        # It exited without the page noticing, such as a crash: report idle and let Launch work.
        cleared = False
        with STATE_LOCK:
            if STATE['pid'] == state['pid']:
                STATE.update({'status': 'idle', 'pid': None, 'startedAt': None})
                cleared = True
        if cleared:
            _remove_pidfile()
        state = {'status': 'idle', 'pid': None, 'startedAt': None, 'error': state.get('error', '')}

    uptime = None
    if state['startedAt'] and state['status'] in ('running', 'stopping'):
        uptime = int(time.time() - state['startedAt'])

    return {
        'control': bool(CONTROL_CONFIG),
        'status': state['status'],
        'pid': state['pid'],
        'uptimeSeconds': uptime,
        'config': os.path.basename(CONTROL_CONFIG) if CONTROL_CONFIG else None,
        'error': state.get('error') or '',
    }


def launch_client():
    global PROCESS
    if not CONTROL_CONFIG:
        return 403, {'error': 'read-only: start with --config <client.jsonc> to launch a client'}

    state = control_state()
    if state['status'] != 'idle':
        return 409, {**state, 'error': f"a client is already {state['status']}"}

    binary = find_binary()
    if binary is None:
        return 500, {'error': f'{BINARY_NAME} not found: build it, or put it on PATH'}

    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        log = open(LOG_FILE, 'ab')
        with STATE_LOCK:
            STATE.update({'status': 'launching', 'pid': None, 'startedAt': time.time(), 'error': ''})
        try:
            process = subprocess.Popen([binary, CONTROL_CONFIG, '--raw-console'], cwd=ROOT, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        finally:
            log.close()
    except OSError as error:
        with STATE_LOCK:
            STATE.update({'status': 'idle', 'pid': None, 'startedAt': None, 'error': str(error)})
        return 500, {**control_state(), 'error': f'could not start the client: {error}'}

    PROCESS = process
    _write_pidfile(process.pid)
    with STATE_LOCK:
        STATE.update({'status': 'running', 'pid': process.pid, 'startedAt': time.time(), 'error': ''})
    return 200, control_state()


def stop_client():
    global PROCESS
    if not CONTROL_CONFIG:
        return 403, {'error': 'read-only: start with --config <client.jsonc> to stop a client'}

    state = control_state()
    if state['status'] != 'running' or not state['pid']:
        return 409, {**state, 'error': 'no client is running'}

    pid = state['pid']
    with STATE_LOCK:
        STATE.update({'status': 'stopping', 'error': ''})

    try:
        os.killpg(pid, signal.SIGINT)
    except OSError:
        try:
            os.kill(pid, signal.SIGINT)
        except OSError as error:
            with STATE_LOCK:
                STATE.update({'status': 'running', 'error': f'could not signal the client: {error}'})
            return 500, control_state()

    threading.Thread(target=_wait_stopped, args=(pid,), daemon=True).start()
    return 202, control_state()


def _wait_stopped(pid):
    """Wait for SIGINT's graceful logout, then make sure it is gone, then report idle."""
    global PROCESS
    with STATE_LOCK:
        process = PROCESS

    started = time.time()
    deadline = started + STOP_TIMEOUT_SECONDS
    second_sent = False
    while time.time() < deadline and _alive(pid):
        if not second_sent and time.time() - started >= SECOND_INTERRUPT_SECONDS:
            # Like the second Ctrl+C: log every account out now rather than wait for a combat lockout.
            second_sent = True
            try:
                os.killpg(pid, signal.SIGINT)
            except OSError:
                try:
                    os.kill(pid, signal.SIGINT)
                except OSError:
                    pass
        time.sleep(0.25)

    if _alive(pid):
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        deadline = time.time() + 5
        while time.time() < deadline and _alive(pid):
            time.sleep(0.1)

    if process is not None:
        try:
            process.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            pass

    PROCESS = None
    with STATE_LOCK:
        if STATE['pid'] == pid:
            STATE.update({'status': 'idle', 'pid': None, 'startedAt': None, 'error': ''})
            _remove_pidfile()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, content_type='application/json'):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ('/', '/index.html'):
            with open(os.path.join(GUI_DIR, 'index.html'), 'rb') as handle:
                self._send(200, handle.read(), 'text/html; charset=utf-8')
        elif path == '/api/experience':
            self._send(200, experience())
        elif path == '/api/bank':
            self._send(200, banks())
        elif path == '/api/inventory':
            self._send(200, inventory(query.get('account', [None])[0]))
        elif path == '/api/control':
            self._send(200, control_state())
        else:
            self._send(404, {'error': 'not found'})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get('Content-Length', '0'))
        if length:
            self.rfile.read(length)

        if path == '/api/launch':
            code, payload = launch_client()
            self._send(code, payload)
        elif path == '/api/stop':
            code, payload = stop_client()
            self._send(code, payload)
        else:
            self._send(404, {'error': 'not found'})


def main():
    global CONTROL_CONFIG
    parser = argparse.ArgumentParser(description='Local view of the fleet-tracking files, with optional client control.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('FLEET_PORT', '8765')))
    parser.add_argument('--config', metavar='CLIENT_JSONC',
                        help='the client config Launch runs; without it the page is read-only')
    args = parser.parse_args()

    if args.config:
        config = os.path.abspath(args.config)
        if not os.path.isfile(config):
            parser.error(f'{args.config}: no such client config')
        CONTROL_CONFIG = config
        _adopt()

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    mode = f'control: {os.path.basename(CONTROL_CONFIG)}' if CONTROL_CONFIG else 'read-only'
    print(f'Fleet view on http://127.0.0.1:{args.port}  ({mode})')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
