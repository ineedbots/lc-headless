#!/usr/bin/env python3
"""Maintain SQLite fleet databases and trim client console logs.

Stop clients before maintenance. Database history is not automatically trimmed;
the tool checkpoints WAL files and can optionally reclaim unused database pages.

    python3 tools/fleet/compact_logs.py --database data/fleet.sqlite --dry-run
    python3 tools/fleet/compact_logs.py --database data/fleet.sqlite --vacuum
"""

import argparse
import os
import sqlite3
from contextlib import closing

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Console logs: keep the last N bytes, cut on a line boundary.
CONSOLE_KEEP_BYTES = 20 * 1024 * 1024


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def keep_tail_bytes(path, keep, dry_run):
    size = _size(path)
    if size <= keep:
        return 0
    with open(path, 'rb') as handle:
        handle.seek(size - keep)
        data = handle.read()
    cut = data.find(b'\n')
    out = data[cut + 1:] if cut != -1 else b''
    if not dry_run:
        with open(path, 'r+b') as handle:
            handle.seek(0)
            handle.write(out)
            handle.truncate(len(out))
    return size - len(out)


def human(n):
    for unit in ['B', 'K', 'M', 'G']:
        if abs(n) < 1024 or unit == 'G':
            return f'{n:.0f}{unit}' if unit == 'B' else f'{n/1:.0f}{unit}'
        n /= 1024
    return f'{n}B'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--console-mb', type=int, default=20, help='megabytes of console log to keep')
    parser.add_argument('--database', action='append', metavar='PATH',
                        help='SQLite fleet database to checkpoint (repeatable; default: data/fleet.sqlite)')
    parser.add_argument('--vacuum', action='store_true', help='reclaim free pages after checkpointing')
    args = parser.parse_args()
    keep_bytes = args.console_mb * 1024 * 1024

    total = 0
    databases = args.database or [os.path.join(ROOT, 'data', 'fleet.sqlite')]
    for path in databases:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            print(f'{path}: database not found; skipped')
            continue
        before = _size(path) + _size(path + '-wal')
        if args.dry_run:
            print(f'{path}: would checkpoint WAL' + (' and vacuum' if args.vacuum else ''))
            continue

        with closing(sqlite3.connect(path, timeout=1.0)) as database:
            database.execute('PRAGMA busy_timeout = 1000')
            checkpoint = database.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            if checkpoint[0] != 0:
                raise RuntimeError(f'{path}: WAL checkpoint is busy; stop all clients and retry')
            if args.vacuum:
                database.execute('VACUUM')
        after = _size(path) + _size(path + '-wal')
        saved = max(0, before - after)
        total += saved
        print(f'{path}: checkpointed' + (', vacuumed' if args.vacuum else '') + f'; freed {human(saved)}')

    logs = os.path.join(ROOT, 'logs')
    if os.path.isdir(logs):
        saved = 0
        for name in sorted(os.listdir(logs)):
            if not name.endswith('.log'):
                continue
            saved += keep_tail_bytes(os.path.join(logs, name), keep_bytes, args.dry_run)
        total += saved
        print(f'{"logs":11} kept {args.console_mb:5} MB/file      freed {human(saved)}')

    print(('would free ' if args.dry_run else 'freed ') + human(total))


if __name__ == '__main__':
    main()
