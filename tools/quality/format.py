"""Check authored C++ with the pinned formatter; pass --fix to apply formatting."""

import argparse
from pathlib import Path
import re
import subprocess
import sys


VERSION = '19.1.5'
ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fix', action='store_true')
    parser.add_argument('--clang-format', default='clang-format')
    args = parser.parse_args()
    try:
        version = subprocess.check_output([args.clang_format, '--version'], text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f'Cannot run clang-format: {error}', file=sys.stderr)
        return 2
    if not re.search(r'\bversion ' + re.escape(VERSION) + r'(?![\d.])', version):
        print(f'Requires clang-format {VERSION}; found {version.strip()}', file=sys.stderr)
        return 2
    files = sorted(path for folder in ('src', 'tests') for path in (ROOT / folder).rglob('*')
                   if path.suffix in ('.cpp', '.hpp'))
    failed = 0
    for path in files:
        command = [args.clang_format, '--style=file', '--fallback-style=none']
        command += ['-i'] if args.fix else ['--dry-run', '--Werror']
        result = subprocess.run(command + [str(path)], cwd=ROOT)
        failed += result.returncode != 0
    print(f'{len(files)} C++ files checked; {failed} failed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
