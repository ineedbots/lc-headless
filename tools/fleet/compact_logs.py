#!/usr/bin/env python3
"""Trim the fleet-tracking journals and client console logs in place.

The writers open their files with O_APPEND for every line (std::ios::app), and the
console logs are shell `>>` redirects, so rewriting a file at offset 0 and truncating
it keeps the same inode and the next append lands at the new end. Nothing needs to be
stopped, and the fleet page keeps reading the newest lines.

    python3 tools/fleet/compact_logs.py --dry-run
    python3 tools/fleet/compact_logs.py

The experience/inventory views only read the last few hundred records, so keeping a
couple of days of lines is plenty.
"""

import argparse
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# directory -> lines to keep per account file
JOURNALS = {
    'experience': 3000,
    'inventory': 3000,
    'bank': 1000,
    'equipment': 1000,
}

# Console logs: keep the last N bytes, cut on a line boundary.
CONSOLE_KEEP_BYTES = 20 * 1024 * 1024


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def keep_tail_lines(path, keep, dry_run):
    data = open(path, 'rb').read()
    lines = data.splitlines(keepends=True)
    if len(lines) <= keep:
        return 0
    out = b''.join(lines[-keep:])
    if not dry_run:
        with open(path, 'r+b') as handle:
            handle.seek(0)
            handle.write(out)
            handle.truncate(len(out))
    return len(data) - len(out)


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
    args = parser.parse_args()
    keep_bytes = args.console_mb * 1024 * 1024

    total = 0
    for directory, keep in JOURNALS.items():
        base = os.path.join(ROOT, directory)
        if not os.path.isdir(base):
            continue
        saved = 0
        for name in sorted(os.listdir(base)):
            if not name.endswith('.jsonl'):
                continue
            saved += keep_tail_lines(os.path.join(base, name), keep, args.dry_run)
        total += saved
        print(f'{directory:11} kept {keep:5} lines/file   freed {human(saved)}')

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
