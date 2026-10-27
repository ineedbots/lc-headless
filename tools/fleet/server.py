#!/usr/bin/env python3
"""Local view of the fleet-tracking files, with optional launch and stop.

    python3 tools/fleet/server.py                          # http://127.0.0.1:8765, read-only
    python3 tools/fleet/server.py --config client.jsonc    # ... with Launch and Stop client

Reads experience/, bank/, inventory/ and equipment/ from the repository root, and binds to loopback only.
Without --config it starts and stops nothing; with it, the page launches one client process per config and
stops the ones it launched. Ctrl+C ends the page, not the clients.

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
    """Every account's status and skills, and what it is earning an hour from its settled in-game samples."""
    accounts = {}
    for path in sorted(glob.glob(os.path.join(EXPERIENCE_DIR, '*.jsonl'))):
        account = os.path.basename(path)[:-len('.jsonl')]
        # Status lines are written on login, logout and so on, so the window needs room for them too.
        history = _read_jsonl(path, limit=200)
        if not history:
            continue

        # Rates come only from settled in-game samples; a status line or a logged-out sample has no XP run.
        samples = [record for record in history if record.get('state') == 'ingame' and record.get('settled')]
        latest = history[-1]
        skills = samples[-1] if samples else latest
        accounts[account] = {
            'state': latest.get('state', 'unknown'),
            'stateTime': latest.get('time'),
            'time': skills.get('time'),
            'levels': {skill: skills.get('skills', {}).get(skill, {}).get('level', 0) for skill in SKILLS},
            'xp': {skill: skills.get('skills', {}).get(skill, {}).get('xp', 0) for skill in SKILLS},
            # A logged-out account keeps its last levels, but not a rate that looks live.
            'rates': _rate(samples) if latest.get('state') == 'ingame' and latest.get('settled') else {},
            'samples': len(samples),
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




# ---- the clients: launch and stop, only with --config ----

# One absolute client config per process, from --config. Empty in read-only mode.
CONTROL_CONFIGS = []
BINARY_NAME = 'Rs2004Headless'
# SIGINT is the client's graceful path. A second one, like a second Ctrl+C, logs every account out at once
# when the first hasn't finished, which matters when the server refuses a logout in combat. SIGKILL is only
# for one that outlives both.
SECOND_INTERRUPT_SECONDS = 10
STOP_TIMEOUT_SECONDS = 40

# config path -> {'pid', 'startedAt'} for every client this page launched or adopted.
RUNNING = {}
# config path -> Popen, for the ones this page launched, so they can be waited on and reaped.
PROCESSES = {}
# '', 'launching' or 'stopping'; otherwise the state is derived from RUNNING.
TRANSITION = ''
ERROR = ''
STATE_LOCK = threading.RLock()


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


def _is_our_client(pid, config):
    """Whether the process is alive and is that config's client, so an unrelated pid is never adopted."""
    if not pid or not os.path.isdir(f'/proc/{pid}'):
        return False
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as handle:
            arguments = [part.decode(errors='replace') for part in handle.read().split(b'\0') if part]
    except OSError:
        return False
    executable = os.path.basename(arguments[0]) if arguments else ''
    return executable == BINARY_NAME and any(os.path.abspath(argument) == config for argument in arguments[1:])


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


def _write_pidfile():
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(PID_FILE, 'w') as handle:
            json.dump({'processes': [{'pid': entry['pid'], 'config': config, 'startedAt': entry['startedAt']} for config, entry in RUNNING.items()]}, handle)
    except OSError:
        pass


def _remove_pidfile():
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def _adopt():
    """Take over clients this page launched before it was restarted, if their pidfile still names them."""
    try:
        with open(PID_FILE) as handle:
            saved = json.load(handle)
    except (OSError, ValueError):
        return

    entries = saved.get('processes') if isinstance(saved, dict) else None
    if not isinstance(entries, list):
        _remove_pidfile()
        return

    adopted = False
    for entry in entries:
        config = entry.get('config')
        pid = entry.get('pid')
        if config in CONTROL_CONFIGS and _is_our_client(pid, config):
            RUNNING[config] = {'pid': pid, 'startedAt': entry.get('startedAt') or time.time()}
            adopted = True

    if adopted:
        _write_pidfile()
    else:
        _remove_pidfile()


def _prune():
    """Drop clients that have exited, so the counts and the pidfile never name a dead process."""
    changed = False
    for config, entry in list(RUNNING.items()):
        if not _alive(entry['pid']):
            del RUNNING[config]
            changed = True
    if changed:
        with STATE_LOCK:
            _write_pidfile()


def control_state():
    with STATE_LOCK:
        _prune()
        status = TRANSITION or ('running' if RUNNING else 'idle')
        uptime = None
        if RUNNING:
            uptime = int(time.time() - min(entry['startedAt'] for entry in RUNNING.values()))
        processes = sorted(
            ({'config': os.path.basename(config), 'pid': entry['pid'], 'uptimeSeconds': int(time.time() - entry['startedAt'])}
             for config, entry in RUNNING.items()),
            key=lambda item: item['config'])
        return {
            'control': bool(CONTROL_CONFIGS),
            'status': status,
            'running': len(RUNNING),
            'total': len(CONTROL_CONFIGS),
            'uptimeSeconds': uptime,
            'processes': processes,
            'error': ERROR,
        }


def launch_clients():
    global TRANSITION, ERROR
    if not CONTROL_CONFIGS:
        return 403, {'error': 'read-only: start with --config <client.jsonc> ... to launch clients'}

    state = control_state()
    if state['running'] or state['status'] in ('launching', 'stopping'):
        return 409, {**state, 'error': 'clients are already running' if state['running'] else f"busy: {state['status']}"}

    binary = find_binary()
    if binary is None:
        return 500, {**state, 'error': f'{BINARY_NAME} not found: build it, or put it on PATH'}

    with STATE_LOCK:
        TRANSITION = 'launching'
        ERROR = ''

    started = []
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        for config in CONTROL_CONFIGS:
            stem = os.path.splitext(os.path.basename(config))[0]
            log = open(os.path.join(LOGS_DIR, f'fleet-{stem}.log'), 'ab')
            try:
                process = subprocess.Popen([binary, config, '--raw-console'], cwd=ROOT, stdin=subprocess.DEVNULL,
                                           stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            finally:
                log.close()
            PROCESSES[config] = process
            RUNNING[config] = {'pid': process.pid, 'startedAt': time.time()}
            started.append(config)
    except OSError as error:
        for config in started:
            _signal(RUNNING[config]['pid'], signal.SIGKILL)
            try:
                PROCESSES[config].wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                pass
            RUNNING.pop(config, None)
            PROCESSES.pop(config, None)
        with STATE_LOCK:
            TRANSITION = ''
            ERROR = f'could not start a client: {error}'
        return 500, control_state()

    with STATE_LOCK:
        TRANSITION = ''
        _write_pidfile()
    return 200, control_state()


def stop_clients():
    global TRANSITION, ERROR
    if not CONTROL_CONFIGS:
        return 403, {'error': 'read-only: start with --config <client.jsonc> ... to stop clients'}

    state = control_state()
    if not state['running']:
        return 409, {**state, 'error': 'no client is running'}

    with STATE_LOCK:
        TRANSITION = 'stopping'
        ERROR = ''

    for entry in list(RUNNING.values()):
        if not _signal(entry['pid'], signal.SIGINT):
            with STATE_LOCK:
                TRANSITION = ''
                ERROR = 'could not signal a client'
            return 500, control_state()

    threading.Thread(target=_wait_stopped, daemon=True).start()
    return 202, control_state()


def _signal(pid, number):
    try:
        os.killpg(pid, number)
        return True
    except OSError:
        try:
            os.kill(pid, number)
            return True
        except OSError:
            return False


def _wait_stopped():
    """Wait for SIGINT's graceful logout, then make sure every client is gone, then report idle."""
    global TRANSITION, ERROR
    pids = [(config, entry['pid']) for config, entry in list(RUNNING.items())]
    started = time.time()
    deadline = started + STOP_TIMEOUT_SECONDS
    second_sent = False

    while time.time() < deadline and any(_alive(pid) for _, pid in pids):
        if not second_sent and time.time() - started >= SECOND_INTERRUPT_SECONDS:
            # Like the second Ctrl+C: log every account out now rather than wait for a combat lockout.
            second_sent = True
            for _, pid in pids:
                _signal(pid, signal.SIGINT)
        time.sleep(0.25)

    for _, pid in pids:
        if _alive(pid):
            _signal(pid, signal.SIGKILL)

    for config, _ in pids:
        process = PROCESSES.pop(config, None)
        if process is not None:
            try:
                process.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                pass
        RUNNING.pop(config, None)

    with STATE_LOCK:
        TRANSITION = ''
        ERROR = ''
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
            code, payload = launch_clients()
            self._send(code, payload)
        elif path == '/api/stop':
            code, payload = stop_clients()
            self._send(code, payload)
        else:
            self._send(404, {'error': 'not found'})


def main():
    global CONTROL_CONFIGS
    parser = argparse.ArgumentParser(description='Local view of the fleet-tracking files, with optional client control.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('FLEET_PORT', '8765')))
    parser.add_argument('--config', nargs='+', metavar='CLIENT_JSONC',
                        help='client configs; Launch runs one process per config, Stop stops them all')
    args = parser.parse_args()

    if args.config:
        for name in args.config:
            config = os.path.abspath(name)
            if not os.path.isfile(config):
                parser.error(f'{name}: no such client config')
            CONTROL_CONFIGS.append(config)
        _adopt()

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    mode = f'control: {", ".join(os.path.basename(c) for c in CONTROL_CONFIGS)}' if CONTROL_CONFIGS else 'read-only'
    print(f'Fleet view on http://127.0.0.1:{args.port}  ({mode})')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
