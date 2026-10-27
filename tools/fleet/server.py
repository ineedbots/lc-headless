#!/usr/bin/env python3
"""Local, read-only view of the fleet-tracking files.

    python3 tools/fleet/server.py            # http://127.0.0.1:8765

Reads experience/, bank/, inventory/ and equipment/ from the repository root. It starts nothing, controls
nothing and binds to loopback only; it is a view of files the client writes. Ctrl+C ends it.

Stdlib only.
"""

import argparse
import glob
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GUI_DIR = os.path.dirname(os.path.abspath(__file__))

EXPERIENCE_DIR = os.path.join(ROOT, 'experience')
BANK_DIR = os.path.join(ROOT, 'bank')
INVENTORY_DIR = os.path.join(ROOT, 'inventory')
EQUIPMENT_DIR = os.path.join(ROOT, 'equipment')

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
        else:
            self._send(404, {'error': 'not found'})


def main():
    parser = argparse.ArgumentParser(description='Local read-only view of the fleet-tracking files.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('FLEET_PORT', '8765')))
    args = parser.parse_args()

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Fleet view on http://127.0.0.1:{args.port}  (read-only)')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
