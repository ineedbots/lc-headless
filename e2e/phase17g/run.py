"""Prepare and execute the local-289 phase 17g acceptance runs (CPython 3.12+)."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent / 'scripts'
CASES = {'ph': 'hero', 'ba': 'hero', 'ik': 'ikov', 'ft': 'viking'}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def git_sha(directory):
    return subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def script_hashes(folder):
    return {path.relative_to(folder).as_posix(): digest(path) for path in sorted(folder.rglob('*.py'))}


def public_key(server):
    script = "const fs=require('node:fs'),c=require('node:crypto'); const k=c.createPublicKey(fs.readFileSync(process.argv[1])).export({format:'jwk'}); console.log(JSON.stringify({rsaModulus:'0x'+Buffer.from(k.n,'base64url').toString('hex'),rsaExponent:'0x'+Buffer.from(k.e,'base64url').toString('hex')}));"
    # World.ts decrypts with this file; a separately exported public.pem can be stale.
    # createPublicKey exports only n/e. Private key material never enters the run artifacts.
    return json.loads(subprocess.check_output(['node', '-e', script, str(server / 'data/config/private.pem')], text=True))


def validate_fresh(server, run_dir, prefix):
    if not re.fullmatch(r'[a-z][a-z0-9]{0,9}', prefix):
        raise ValueError('Prefix must be 1-10 lowercase letters/digits, starting with a letter.')
    if run_dir.exists():
        raise ValueError(f'Run directory already exists: {run_dir}. Use a fresh directory and prefix.')
    if run_dir == REPO / 'build' or not run_dir.is_relative_to(REPO / 'build'):
        raise ValueError('Run directory must be beneath this checkout\'s ignored build/ folder.')
    validate_characters(server, prefix)


def validate_characters(server, prefix):
    world = read_json(server / 'data/config/world.json')
    if world['node']['production'] or world['login']['enabled']:
        raise ValueError('Use the local development server with production=false and login.enabled=false.')
    if world['node'].get('members') is False:
        raise ValueError('These quests require members content on the local server.')
    for case in CASES:
        name = prefix + case
        if list((server / 'data/players').glob(f'*/{name}.sav')):
            raise ValueError(f'Scratch character already exists: {name}. Choose a new prefix.')


def prepare(args):
    server = args.server_dir.resolve()
    run_dir = args.run_dir.resolve()
    client = args.client.resolve()
    prefix = args.prefix or 'g17' + secrets.token_hex(3)
    validate_fresh(server, run_dir, prefix)
    for path in [client, args.cache_dir.resolve(), args.nav_dir.resolve(), server / 'src/app.ts']:
        if not path.exists():
            raise ValueError(f'Required path is missing: {path}')
    login = dict(public_key(server), revision=289, lowMemory=True)
    manifest = {'version': 1, 'repo': str(REPO), 'server': str(server), 'client': str(client),
                'client_sha': git_sha(REPO), 'engine_sha': git_sha(server), 'binary_sha256': digest(client),
                'tick_ms': 600, 'infinite_run': not args.natural_run, 'prefix': prefix,
                'accounts': {case: prefix + case for case in CASES}}
    run_dir.mkdir(parents=True)
    for folder in ['accounts', 'seed-accounts', 'scripts', 'sessions']:
        (run_dir / folder).mkdir()
    shutil.copytree(REPO / 'scripts/bots', run_dir / 'scripts/bots', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for path in SCRIPTS.glob('*.py'):
        shutil.copy2(path, run_dir / 'scripts' / path.name)
    manifest['scripts_sha256'] = script_hashes(run_dir / 'scripts')
    config = {'server': {'transport': 'ws', 'host': '127.0.0.1', 'port': args.server_port, 'origin': 'http://localhost'},
              'login': login, 'client': {'cacheDirectory': str(args.cache_dir.resolve()),
                                        'navDirectory': str(args.nav_dir.resolve()), 'logLevel': 'info'},
              'scripting': {'scriptsDirectory': str(run_dir / 'scripts'), 'accountsDirectory': str(run_dir / 'accounts'),
                            'progressDirectory': str(run_dir / 'progress'), 'fleetDatabasePath': str(run_dir / 'fleet.sqlite'),
                            'loginIntervalSeconds': 3, 'callTimeoutMs': 30000, 'connectAttempts': 10,
                            'minRetryDelaySeconds': 3, 'maxRetryDelaySeconds': 30, 'reloginDelaySeconds': 60,
                            'accountDataLogEnabled': True, 'experienceLogEnabled': True, 'bankLogEnabled': True,
                            'inventoryLogEnabled': True, 'equipmentLogEnabled': True},
              'http': {'host': '127.0.0.1', 'port': args.operator_port}}
    write_json(run_dir / 'client.json', config)
    for case, name in manifest['accounts'].items():
        partner = prefix + ('ba' if case == 'ph' else 'ph') if case in ['ph', 'ba'] else ''
        account = {'username': name, 'password': secrets.token_hex(8), 'randomEvents': True, 'stallMinutes': 25,
                   'runAuto': True, 'script': {'file': 'live_quester.py', 'progressReportMinutes': 1,
                   'settings': {'AIOQuester': {'quests': [CASES[case]], 'food': 'Lobster', 'verbose': True,
                   'loadout': '', 'arrav_gang': 'phoenix' if case == 'ph' else 'blackarm',
                   'hero_partner': partner, 'arrav_partner': partner, 'e2e_case': case,
                   'e2e_infinite_run': not args.natural_run}}}}
        write_json(run_dir / 'accounts' / f'{name}.jsonc', account)
        account['randomEvents'] = False
        account['script'] = {'file': 'seed.py', 'settings': {'kind': case}}
        write_json(run_dir / 'seed-accounts' / f'{name}.jsonc', account)
    write_json(run_dir / 'manifest.json', manifest)
    print(f'Prepared {run_dir}\nAccounts: {", ".join(manifest["accounts"].values())}\nNext: run.py seed --run-dir {run_dir}')


def results(text, marker, expected):
    found = {}
    for line in text.splitlines():
        if marker in line:
            row = json.loads(line.split(marker, 1)[1])
            found[row['case']] = row
    for case, name in expected.items():
        row = found.get(case)
        if row is None or row.get('passed') is not True or row.get('name', '').lower() != name:
            raise ValueError(f'{case}: missing or failed {marker.strip()} result. Inspect the session logs.')
    return found


def request_shutdown(process, port, names):
    if process.poll() is not None:
        return
    base = f'http://127.0.0.1:{port}/api/v1'
    try:
        with urllib.request.urlopen(base + '/status', timeout=3) as response:
            state = json.load(response)
        if {row['name'] for row in state['accounts']} != set(names):
            raise ValueError('Operator listener belongs to a different account set; refusing its quit command.')
        request = urllib.request.Request(base + '/console/commands', data=b'{"command":"quit"}',
                                         headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(request, timeout=3):
            pass
        process.wait(timeout=45)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f'Graceful shutdown unavailable: {error}', file=sys.stderr)
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def execute(args):
    run_dir = args.run_dir.resolve()
    manifest = read_json(run_dir / 'manifest.json')
    if manifest['repo'] != str(REPO):
        raise ValueError('Run belongs to a different checkout. Prepare a fresh run here.')
    seeded = run_dir / 'seed-complete.json'
    seeding = args.command == 'seed'
    if seeding:
        validate_characters(Path(manifest['server']), manifest['prefix'])
        if (run_dir / 'seed-started').exists():
            raise ValueError('Seeding was already attempted. Prepare fresh characters instead of reseeding progress.')
        with (run_dir / 'seed-started').open('x', encoding='utf-8') as file:
            file.write('Seeding is one-shot. A failed seed requires fresh characters.\n')
        cases = list(CASES)
    else:
        if not seeded.exists():
            raise ValueError('Seed must finish successfully before a quest run.')
        cases = args.cases or list(CASES)
    client = args.client.resolve() if args.client else Path(manifest['client'])
    expected = {case: manifest['accounts'][case] for case in cases}
    session = run_dir / 'sessions' / (time.strftime('%Y%m%dT%H%M%S') + '-' + args.command + '-' + secrets.token_hex(2))
    session.mkdir()
    account_dir = session / 'accounts'
    account_dir.mkdir()
    for name in expected.values():
        shutil.copy2(run_dir / ('seed-accounts' if seeding else 'accounts') / f'{name}.jsonc', account_dir)
    config = read_json(run_dir / 'client.json')
    config['scripting']['accountsDirectory'] = str(account_dir)
    config['scripting']['fleetDatabasePath'] = str(session / 'fleet.sqlite')
    config['client']['logFile'] = str(session / 'client.log')
    config['http']['port'] = args.operator_port or config['http']['port']
    write_json(session / 'client.json', config)
    write_json(session / 'version.json', {'client_sha': git_sha(REPO), 'engine_sha': git_sha(Path(manifest['server'])),
                                        'binary_sha256': digest(client), 'scripts_sha256': script_hashes(run_dir / 'scripts'), 'cases': cases})
    print(f'Session: {session}\nLog: {session / "client.log"}', flush=True)
    with (session / 'console.log').open('w', encoding='utf-8') as console_log:
        process = subprocess.Popen([str(client), str(session / 'client.json')], cwd=REPO, stdout=console_log,
                                   stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            code = process.wait(timeout=args.timeout_minutes * 60)
        except (KeyboardInterrupt, subprocess.TimeoutExpired):
            request_shutdown(process, config['http']['port'], expected.values())
            raise ValueError(f'Run interrupted or timed out; not a pass. Inspect {session}') from None
    if code != 0:
        raise ValueError(f'Client exited with {code}; not a pass. Inspect {session}')
    marker = 'E2E_SEEDED ' if seeding else 'E2E_RESULT '
    found = results((session / 'client.log').read_text(encoding='utf-8'), marker, expected)
    write_json(session / 'results.json', found)
    if seeding:
        write_json(seeded, found)
    print(f'PASS: {", ".join(expected.values())}. All selected accounts logged out cleanly.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('prepare', help='Create a fresh local-only run and four scratch accounts.')
    setup.add_argument('--run-dir', type=Path, required=True)
    setup.add_argument('--server-dir', type=Path, default=REPO.parent / '289server/engine')
    setup.add_argument('--prefix', help='Fresh lowercase prefix; default is random.')
    setup.add_argument('--client', type=Path, default=REPO / ('build/windows-msvc/Release/Rs2004Headless.exe' if sys.platform == 'win32' else 'build/linux-clang/Release/Rs2004Headless'))
    setup.add_argument('--cache-dir', type=Path, default=REPO / 'data/cache')
    setup.add_argument('--nav-dir', type=Path, default=REPO / 'data/nav')
    setup.add_argument('--server-port', type=int, default=80)
    setup.add_argument('--operator-port', type=int, default=8091)
    setup.add_argument('--natural-run', action='store_true', help='Omit the per-character infinite-run command.')
    for command in ['seed', 'run']:
        sub = commands.add_parser(command)
        sub.add_argument('--run-dir', type=Path, required=True)
        sub.add_argument('--client', type=Path, help='Use a rebuilt executable when resuming saved quest progress.')
        sub.add_argument('--operator-port', type=int)
        sub.add_argument('--timeout-minutes', type=float, default=240)
        if command == 'run':
            sub.add_argument('--cases', nargs='+', choices=CASES, help='Run only these unfinished cases; keep Hero partners together.')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            prepare(args)
        else:
            execute(args)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
