#!/usr/bin/env python3
"""Local view of the fleet-tracking files, with optional launch and stop.

    python3 tools/fleet/server.py                          # http://127.0.0.1:8765, read-only
    python3 tools/fleet/server.py --config client.jsonc    # ... with Launch and Stop client

Reads the SQLite database from the repository root, and binds to loopback only.
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
import sqlite3
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from storage import connect_readonly, timestamp_from_unix_seconds

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GUI_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATABASE = os.path.join(ROOT, 'data', 'fleet.sqlite')
DATABASE_PATHS = [DEFAULT_DATABASE]
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


def _accounts(stream):
    """Every account with at least one record in the selected stream."""
    accounts = set()
    for path in DATABASE_PATHS:
        if not os.path.isfile(path):
            continue
        connection = connect_readonly(path)
        try:
            accounts.update(row[0] for row in connection.execute(
                'SELECT DISTINCT accounts.name FROM fleet_records AS records '
                'JOIN fleet_accounts AS accounts ON accounts.id = records.account_id '
                'JOIN fleet_streams AS streams ON streams.id = records.stream_id '
                'WHERE streams.name = ?', (stream,)))
        finally:
            connection.close()
    return sorted(accounts)


def _items(connection, table, record_id):
    return [
        {'id': item_id, 'name': name, 'qty': quantity}
        for item_id, name, quantity in connection.execute(
            f'SELECT items.item_id, names.name, items.quantity FROM {table} AS items '
            'JOIN fleet_item_names AS names ON names.id = items.name_id '
            'WHERE items.record_id = ? ORDER BY items.item_id',
            (record_id,))
    ]


def _record(connection, stream, account, sequence, recorded_at):
    """Rebuild the stable public JSON record from its normalized database rows."""
    record = {'time': timestamp_from_unix_seconds(recorded_at), 'account': account}

    if stream == 'account-data':
        row = connection.execute(
            'SELECT states.name, account_data.settled, account_data.pid, account_data.tile_x, account_data.tile_z, account_data.tile_level, '
            'account_data.destination_x, account_data.destination_z, account_data.destination_level, target_kinds.name, '
            'account_data.target_index, account_data.target_x, account_data.target_z, account_data.target_level, '
            'account_data.hp_current, account_data.hp_base, account_data.energy, account_data.prayer_current, account_data.prayer_base, '
            'account_data.special_attack_energy, account_data.special_attack_armed, account_data.running, account_data.moving, '
            'account_data.in_combat, account_data.weight, account_data.tick '
            'FROM fleet_account_data AS account_data '
            'JOIN fleet_states AS states ON states.id = account_data.state_id '
            'LEFT JOIN fleet_target_kinds AS target_kinds ON target_kinds.id = account_data.target_kind_id '
            'WHERE account_data.record_id = ?',
            (sequence,)).fetchone()
        if row is None:
            raise sqlite3.DatabaseError(f'account-data record {sequence} has no typed data row')

        def tile(x, z, level):
            return None if x is None else {'x': x, 'z': z, 'level': level}

        target_kind, target_index, target_x, target_z, target_level = row[9:14]
        target = None
        if target_kind in ('npc', 'player'):
            target = {'kind': target_kind, 'index': target_index}
        elif target_kind == 'tile':
            target = {'kind': target_kind, 'tile': tile(target_x, target_z, target_level)}

        record.update({
            'state': row[0],
            'settled': bool(row[1]),
            'pid': row[2],
            'tile': tile(*row[3:6]),
            'destination': tile(*row[6:9]),
            'target': target,
            'hp': None if row[14] is None else {'current': row[14], 'base': row[15]},
            'energy': row[16],
            'prayer': None if row[17] is None else {'current': row[17], 'base': row[18]},
            'specialAttack': None if row[19] is None else {'energy': row[19], 'armed': bool(row[20])},
            'running': None if row[21] is None else bool(row[21]),
            'moving': None if row[22] is None else bool(row[22]),
            'inCombat': None if row[23] is None else bool(row[23]),
            'weight': row[24],
            'tick': row[25],
        })
    elif stream == 'experience':
        row = connection.execute(
            'SELECT states.name, experience.settled FROM fleet_experience AS experience '
            'JOIN fleet_states AS states ON states.id = experience.state_id WHERE experience.record_id = ?',
            (sequence,)).fetchone()
        if row is None:
            raise sqlite3.DatabaseError(f'experience record {sequence} has no typed data row')
        skills = {
            skill: {'level': level, 'base': base, 'xp': xp}
            for skill, level, base, xp in connection.execute(
                'SELECT skills.name, experience_skills.level, experience_skills.base, experience_skills.xp '
                'FROM fleet_experience_skills AS experience_skills '
                'JOIN fleet_skills AS skills ON skills.id = experience_skills.skill_id '
                'WHERE experience_skills.record_id = ? ORDER BY experience_skills.ordinal',
                (sequence,))
        }
        record.update({'state': row[0], 'settled': bool(row[1]), 'skills': skills})
    elif stream == 'bank':
        exists = connection.execute('SELECT 1 FROM fleet_bank WHERE record_id = ?', (sequence,)).fetchone()
        if exists is None:
            raise sqlite3.DatabaseError(f'bank record {sequence} has no typed data row')
        record['items'] = _items(connection, 'fleet_bank_items', sequence)
    elif stream == 'inventory':
        row = connection.execute(
            'SELECT bank_open, used, free FROM fleet_inventory WHERE record_id = ?', (sequence,)).fetchone()
        if row is None:
            raise sqlite3.DatabaseError(f'inventory record {sequence} has no typed data row')
        record.update({'bankOpen': bool(row[0]), 'used': row[1], 'free': row[2]})
        record['items'] = _items(connection, 'fleet_inventory_items', sequence)
    elif stream == 'equipment':
        row = connection.execute(
            'SELECT used FROM fleet_equipment WHERE record_id = ?', (sequence,)).fetchone()
        if row is None:
            raise sqlite3.DatabaseError(f'equipment record {sequence} has no typed data row')
        record['used'] = row[0]
        record['items'] = _items(connection, 'fleet_equipment_items', sequence)
    else:
        raise ValueError(f'unknown fleet stream: {stream}')

    return record


def _latest(stream):
    """The latest record in each account/stream, ordered by sequence within each database."""
    latest = {}
    latest_times = {}
    for path in DATABASE_PATHS:
        if not os.path.isfile(path):
            continue
        connection = connect_readonly(path)
        try:
            rows = connection.execute(
                'SELECT accounts.name, records.sequence, records.recorded_at '
                'FROM fleet_records AS records '
                'JOIN fleet_accounts AS accounts ON accounts.id = records.account_id '
                'JOIN fleet_streams AS streams ON streams.id = records.stream_id '
                'WHERE streams.name = ? AND records.sequence = ('
                'SELECT MAX(latest.sequence) FROM fleet_records AS latest '
                'WHERE latest.stream_id = records.stream_id AND latest.account_id = records.account_id)',
                (stream,))
            for account, sequence, recorded_at in rows:
                if account not in latest_times or recorded_at > latest_times[account]:
                    latest[account] = _record(connection, stream, account, sequence, recorded_at)
                    latest_times[account] = recorded_at
        finally:
            connection.close()
    return latest


def _history(stream, account, limit):
    """Recent records in stable order, including ties at the same second."""
    records = []
    for path_order, path in enumerate(DATABASE_PATHS):
        if not os.path.isfile(path):
            continue
        connection = connect_readonly(path)
        try:
            rows = connection.execute(
                'SELECT records.recorded_at, records.sequence FROM fleet_records AS records '
                'JOIN fleet_accounts AS accounts ON accounts.id = records.account_id '
                'JOIN fleet_streams AS streams ON streams.id = records.stream_id '
                'WHERE streams.name = ? AND accounts.name = ? ORDER BY records.sequence DESC LIMIT ?',
                (stream, account, limit)).fetchall()
            records.extend(
                (row[0], path_order, row[1], _record(connection, stream, account, row[1], row[0]))
                for row in reversed(rows))
        finally:
            connection.close()

    records.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
    return [entry[3] for entry in records[-limit:]]


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
    for account in _accounts('experience'):
        # Status lines are written on login, logout and so on, so the window needs room for them too.
        history = _history('experience', account, 200)
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


def account_data():
    """The latest account data, including session changes that clear gameplay fields."""
    return {'accounts': _latest('account-data')}


def banks():
    """Every item across the accounts' latest bank snapshot, with how many each account holds."""
    items = {}
    accounts = 0
    for account, record in _latest('bank').items():
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
        return {'accounts': _accounts('inventory')}

    inventory_record = _latest('inventory').get(account)
    equipment_record = _latest('equipment').get(account)

    return {'account': account, 'inventory': inventory_record, 'equipment': equipment_record}




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


def _accounts_total():
    """Every account file the configured clients would load, for the in-game count's denominator."""
    total = 0
    for config in CONTROL_CONFIGS:
        try:
            with open(config) as handle:
                text = handle.read()
        except OSError:
            continue
        # The config is JSONC; the one key needed is quoted and on its own line.
        for line in text.splitlines():
            if '"accountsDirectory"' in line and ':' in line:
                folder = line.split(':', 1)[1].strip().strip(',').strip().strip('"')
                total += len(glob.glob(os.path.join(ROOT, folder, '*.jsonc')))
    return total


def _in_game():
    """Accounts whose latest status line says they are in game."""
    return sum(record.get('state') == 'ingame' for record in _latest('experience').values())


def _strip_json_comments(text):
    """Remove JSONC comments without treating comment markers inside strings as syntax."""
    output = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        character = text[index]
        if in_string:
            output.append(character)
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue

        if character == '"':
            in_string = True
            output.append(character)
            index += 1
            continue
        if text.startswith('//', index):
            newline = text.find('\n', index)
            if newline == -1:
                break
            output.append('\n')
            index = newline + 1
            continue
        if text.startswith('/*', index):
            end = text.find('*/', index + 2)
            if end == -1:
                raise ValueError('unterminated block comment')
            output.extend('\n' for character in text[index:end + 2] if character == '\n')
            index = end + 2
            continue

        output.append(character)
        index += 1

    return ''.join(output)


def _database_for_config(config_path):
    with open(config_path, encoding='utf-8') as config_file:
        config = json.loads(_strip_json_comments(config_file.read()))
    if not isinstance(config, dict) or not isinstance(config.get('scripting', {}), dict):
        raise ValueError(f'{config_path}: expected a scripting object')
    path = config.get('scripting', {}).get('fleetDatabasePath', 'data/fleet.sqlite')
    if not isinstance(path, str) or not path:
        raise ValueError(f'{config_path}: scripting.fleetDatabasePath must be a nonempty file path')
    return os.path.abspath(os.path.join(ROOT, path))


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
            'accountsTotal': _accounts_total() if CONTROL_CONFIGS else 0,
            'accountsInGame': _in_game() if CONTROL_CONFIGS else 0,
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

        try:
            if path in ('/', '/index.html'):
                with open(os.path.join(GUI_DIR, 'index.html'), 'rb') as handle:
                    self._send(200, handle.read(), 'text/html; charset=utf-8')
            elif path == '/api/experience':
                self._send(200, experience())
            elif path == '/api/account-data':
                self._send(200, account_data())
            elif path == '/api/bank':
                self._send(200, banks())
            elif path == '/api/inventory':
                self._send(200, inventory(query.get('account', [None])[0]))
            elif path == '/api/control':
                self._send(200, control_state())
            else:
                self._send(404, {'error': 'not found'})
        except (sqlite3.Error, json.JSONDecodeError, OSError) as error:
            self._send(500, {'error': f'fleet database read failed: {error}'})

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
    global CONTROL_CONFIGS, DATABASE_PATHS
    parser = argparse.ArgumentParser(description='Local SQLite fleet view, with optional client control.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('FLEET_PORT', '8765')))
    parser.add_argument('--database', action='append', metavar='PATH',
                        help='SQLite database to read (repeatable; defaults to data/fleet.sqlite)')
    parser.add_argument('--config', nargs='+', metavar='CLIENT_JSONC',
                        help='client configs; reads their configured databases, and Launch runs one process per config')
    args = parser.parse_args()

    if args.config or args.database:
        DATABASE_PATHS = []

    if args.config:
        for name in args.config:
            config = os.path.abspath(name)
            if not os.path.isfile(config):
                parser.error(f'{name}: no such client config')
            CONTROL_CONFIGS.append(config)
            try:
                DATABASE_PATHS.append(_database_for_config(config))
            except (OSError, ValueError, json.JSONDecodeError) as error:
                parser.error(str(error))
        _adopt()

    if args.database:
        DATABASE_PATHS.extend(os.path.abspath(path) for path in args.database)
    if not args.config and not args.database:
        DATABASE_PATHS = [DEFAULT_DATABASE]
    else:
        DATABASE_PATHS = list(dict.fromkeys(DATABASE_PATHS))

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    mode = f'control: {", ".join(os.path.basename(c) for c in CONTROL_CONFIGS)}' if CONTROL_CONFIGS else 'read-only'
    print(f'Fleet view on http://127.0.0.1:{args.port}  ({mode})')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
