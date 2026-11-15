#!/usr/bin/env python3
"""Import legacy fleet JSONL journals into a SQLite fleet database without deleting them."""

import argparse
import glob
import json
import os
import sqlite3
import sys

from storage import STREAMS, create_schema

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _source_key(root, path, stream, line_number):
    relative = os.path.relpath(path, root).replace(os.sep, '/')
    return f'legacy:{stream}:{relative}:{line_number}'


def import_file(connection, root, path, stream):
    inserted = 0
    skipped = 0
    with open(path, encoding='utf-8', errors='replace') as source, connection:
        for line_number, line in enumerate(source, 1):
            payload = line.strip()
            if not payload:
                continue
            try:
                record = json.loads(payload)
            except json.JSONDecodeError as error:
                print(f'{path}:{line_number}: skipped malformed JSON ({error.msg})', file=sys.stderr)
                skipped += 1
                continue

            if not isinstance(record, dict) or not isinstance(record.get('time'), str):
                print(f'{path}:{line_number}: skipped record without an object shape and string time', file=sys.stderr)
                skipped += 1
                continue

            account = record.get('account')
            if not isinstance(account, str) or not account:
                account = os.path.basename(path)[:-len('.jsonl')]
                record['account'] = account
                payload = json.dumps(record, ensure_ascii=False, separators=(',', ':'))

            source_key = _source_key(root, path, stream, line_number)
            cursor = connection.execute(
                'INSERT OR IGNORE INTO fleet_records (account, stream, recorded_at, payload, source_key) '
                'VALUES (?, ?, ?, ?, ?)',
                (account, stream, record['time'], payload, source_key))
            inserted += cursor.rowcount
            skipped += cursor.rowcount == 0

    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=os.path.join(ROOT, 'data', 'fleet.sqlite'),
                        help='destination database (default: data/fleet.sqlite)')
    parser.add_argument('--legacy-root', default=ROOT,
                        help='directory containing the five legacy journal folders (default: repository root)')
    args = parser.parse_args()
    root = os.path.abspath(args.legacy_root)

    files = []
    for stream in STREAMS:
        files.extend((stream, path) for path in sorted(glob.glob(os.path.join(root, stream, '*.jsonl'))))
    if not files:
        print(f'No legacy JSONL journals found under {root}')
        return

    os.makedirs(os.path.dirname(os.path.abspath(args.database)), exist_ok=True)
    connection = sqlite3.connect(args.database, timeout=1.0)
    try:
        connection.execute('PRAGMA busy_timeout = 1000')
        create_schema(connection)
        connection.execute('PRAGMA journal_mode = WAL')
        connection.execute('PRAGMA synchronous = NORMAL')

        totals = {'inserted': 0, 'skipped': 0}
        for stream, path in files:
            inserted, skipped = import_file(connection, root, path, stream)
            totals['inserted'] += inserted
            totals['skipped'] += skipped
            print(f'{os.path.relpath(path, root)}: imported {inserted}, skipped {skipped}')

        print(f"Imported {totals['inserted']} records; skipped {totals['skipped']}. Source JSONL files were not changed.")
    finally:
        connection.close()


if __name__ == '__main__':
    main()
