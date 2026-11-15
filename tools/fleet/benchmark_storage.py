#!/usr/bin/env python3
"""Compare representative JSONL and SQLite fleet write/query costs on local temporary data."""

import argparse
import datetime
import json
import math
import os
import sqlite3
import statistics
import tempfile
import time

import server
from storage import create_schema

STREAMS = ('account-data', 'experience', 'bank', 'inventory', 'equipment')
SKILLS = (
    'attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer', 'magic',
    'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
    'smithing', 'mining', 'herblore', 'agility', 'thieving', 'runecraft',
)


def _payload(stream, account, index):
    timestamp = datetime.datetime(2026, 1, 1) + datetime.timedelta(seconds=index)
    record = {
        'time': timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'account': account,
        'state': 'ingame',
        'settled': True,
    }
    if stream == 'experience':
        record['skills'] = {
            skill: {'level': 75, 'base': 75, 'xp': 1210421 + index}
            for skill in SKILLS
        }
    elif stream == 'bank':
        record['items'] = [
            {'id': item_id, 'name': f'Item {item_id}', 'qty': 100 + index}
            for item_id in range(100)
        ]
    elif stream == 'inventory':
        record.update({
            'bankOpen': False,
            'used': 24,
            'free': 4,
            'items': [
                {'id': item_id, 'name': f'Item {item_id}', 'qty': 1 + index}
                for item_id in range(24)
            ],
        })
    elif stream == 'equipment':
        record['items'] = [
            {'id': item_id, 'name': f'Item {item_id}', 'qty': 1}
            for item_id in range(12)
        ]
    else:
        record.update({
            'pid': 42,
            'tile': {'x': 3200 + index, 'z': 3201, 'level': 0},
            'destination': None,
            'target': None,
            'hp': {'current': 90, 'base': 99},
            'energy': 80,
            'prayer': {'current': 60, 'base': 70},
            'specialAttack': {'energy': 750, 'armed': False},
            'running': True,
            'moving': False,
            'inCombat': False,
            'weight': 5,
            'tick': index,
        })
    return json.dumps(record, separators=(',', ':')).encode('utf-8')


def _legacy_tail(path, count):
    try:
        with open(path, 'rb') as handle:
            handle.seek(0, 2)
            position = handle.tell()
            block = b''
            while position > 0 and block.count(b'\n') <= count:
                step = min(65536, position)
                position -= step
                handle.seek(position)
                block = handle.read(step) + block
        return [
            json.loads(line.decode('utf-8', 'replace'))
            for line in block.split(b'\n')[-count:]
            if line.strip()
        ]
    except OSError:
        return []


def _percentile(samples, fraction):
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def _report(label, samples):
    median = statistics.median(samples) / 1_000
    p95 = _percentile(samples, 0.95) / 1_000
    print(f'{label}: median {median:.1f} us, p95 {p95:.1f} us')


def _run(args):
    accounts = [f'bot{index:02}' for index in range(args.accounts)]
    with tempfile.TemporaryDirectory(prefix='fleet-storage-benchmark-') as temporary:
        root = os.path.join(temporary, 'legacy')
        database_path = os.path.join(temporary, 'fleet.sqlite')
        legacy_paths = {}
        os.makedirs(root)
        for stream in STREAMS:
            directory = os.path.join(root, stream)
            os.makedirs(directory)
            for account in accounts:
                legacy_paths[stream, account] = os.path.join(directory, f'{account}.jsonl')

        writer = sqlite3.connect(database_path, timeout=0.025)
        writer.execute('PRAGMA busy_timeout = 25')
        writer.execute('PRAGMA journal_mode = WAL')
        writer.execute('PRAGMA synchronous = NORMAL')
        create_schema(writer)
        writer.close()
        writers = {
            account: sqlite3.connect(database_path, timeout=0.025, isolation_level=None)
            for account in accounts
        }
        for database in writers.values():
            database.execute('PRAGMA busy_timeout = 25')
            database.execute('PRAGMA synchronous = NORMAL')

        durations = {'JSONL': [], 'SQLite': []}
        for index in range(args.records):
            timestamp = (datetime.datetime(2026, 1, 1) + datetime.timedelta(seconds=index)).strftime('%Y-%m-%dT%H:%M:%SZ')
            for account in accounts:
                database = writers[account]
                for stream in STREAMS:
                    payload = _payload(stream, account, index)
                    start = time.perf_counter_ns()
                    with open(legacy_paths[stream, account], 'ab') as handle:
                        handle.write(payload + b'\n')
                    durations['JSONL'].append(time.perf_counter_ns() - start)

                    start = time.perf_counter_ns()
                    database.execute('BEGIN IMMEDIATE')
                    database.execute(
                        'INSERT INTO fleet_records (account, stream, recorded_at, payload) VALUES (?, ?, ?, ?)',
                        (account, stream, timestamp, payload.decode('utf-8')))
                    database.commit()
                    durations['SQLite'].append(time.perf_counter_ns() - start)

        for database in writers.values():
            database.close()
        maintenance = sqlite3.connect(database_path, timeout=0.025)
        maintenance.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        maintenance.close()

        server.DATABASE_PATHS = [database_path]

        def legacy_latest():
            return {
                stream: {
                    account: _legacy_tail(legacy_paths[stream, account], 1)
                    for account in accounts
                }
                for stream in STREAMS
            }

        def sqlite_latest():
            return {stream: server._latest(stream) for stream in STREAMS}

        def legacy_history():
            return _legacy_tail(legacy_paths['experience', accounts[0]], 200)

        def sqlite_history():
            return server._history('experience', accounts[0], 200)

        for name, function in (
            ('JSONL latest all streams', legacy_latest),
            ('SQLite latest all streams', sqlite_latest),
            ('JSONL XP history (200)', legacy_history),
            ('SQLite XP history (200)', sqlite_history),
        ):
            samples = []
            for _ in range(args.queries):
                start = time.perf_counter_ns()
                function()
                samples.append(time.perf_counter_ns() - start)
            _report(name, samples)

        legacy_bytes = sum(os.path.getsize(path) for path in legacy_paths.values())
        database_bytes = os.path.getsize(database_path)
        print(f'Writes: {len(durations["JSONL"]):,} records per format')
        _report('JSONL append', durations['JSONL'])
        _report('SQLite transaction', durations['SQLite'])
        print(f'JSONL growth: {legacy_bytes:,} bytes')
        print(f'SQLite growth after WAL checkpoint: {database_bytes:,} bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accounts', type=int, default=45)
    parser.add_argument('--records', type=int, default=100, help='records per account and stream')
    parser.add_argument('--queries', type=int, default=10)
    args = parser.parse_args()
    if args.accounts < 1 or args.records < 1 or args.queries < 1:
        parser.error('accounts, records and queries must be positive')
    _run(args)


if __name__ == '__main__':
    main()
