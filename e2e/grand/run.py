"""Run every individual quest phase concurrently against the local 289 server."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness

REPO = harness.REPO
PHASES = ['16'] + ['17' + letter for letter in 'abcdefghi']
PORT_STRIDE = 3
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def phase_command(args, phase, command):
    entry = REPO / ('e2e/phase' + phase) / ('individual.py' if phase == '16' else 'run.py')
    command_line = [sys.executable, str(entry), command, '--run-dir', str(args.run_dir / ('phase' + phase))]
    if command == 'prepare':
        command_line += ['--client', str(args.run_dir / ('client.exe' if sys.platform == 'win32' else 'client')),
                         '--operator-port', str(args.operator_port + PHASES.index(phase) * PORT_STRIDE),
                         '--server-dir', str(args.server_dir), '--server-port', str(args.server_port),
                         '--cache-dir', str(args.cache_dir), '--nav-dir', str(args.nav_dir)]
        if args.natural_run:
            command_line.append('--natural-run')
    else:
        timeout = args.seed_timeout_minutes if command == 'seed' else args.timeout_minutes
        command_line += ['--timeout-minutes', str(timeout)]
    return command_line


def launch(args, phase, command):
    with (args.run_dir / (phase + '-' + command + '-stdout.log')).open('w', encoding='utf-8') as out:
        with (args.run_dir / (phase + '-' + command + '-stderr.log')).open('w', encoding='utf-8') as err:
            child = subprocess.Popen(phase_command(args, phase, command), cwd=REPO, stdout=out, stderr=err,
                                     creationflags=FLAGS, start_new_session=sys.platform != 'win32')
    print(phase, command, 'pid', child.pid, flush=True)
    return child


def wait_all(args, children, stage):
    while True:
        rows = {phase: {'pid': child.pid, 'exit_code': child.poll()} for phase, child in children.items()}
        harness.write_json(args.run_dir / 'status.json',
                           {'stage': stage, 'updated_at_utc': utc_now(), 'phases': rows})
        if all(row['exit_code'] is not None for row in rows.values()):
            return all(row['exit_code'] == 0 for row in rows.values())
        time.sleep(5)


def phase_results(root, phase):
    folder = root / ('phase' + phase)
    manifest = harness.read_json(folder / 'manifest.json')
    sessions = list((folder / 'sessions').glob('*-run-*'))
    if len(sessions) != 1:
        raise ValueError('Expected exactly one quest session for phase ' + phase)
    accounts = manifest['accounts']
    starts, ends, results = {}, {}, {}
    for log in sessions[0].rglob('client.log'):
        for line in log.read_text(encoding='utf-8').splitlines():
            match = re.search(r'\[([^]]+)\] AIOQuester, queue:', line)
            if match:
                name = match[1].lower()
                if name not in accounts.values() or name in starts:
                    raise ValueError('Unknown or restarted queue: ' + name)
                starts[name] = line.split()[0]
            if 'E2E_RESULT ' in line:
                result = json.loads(line.split('E2E_RESULT ', 1)[1])
                case = result['case']
                if case not in accounts or case in results or result.get('name', '').lower() != accounts[case]:
                    raise ValueError('Unknown, mismatched or duplicate result: ' + case)
                results[case], ends[case] = result, line.split()[0]
    rows = []
    for case, name in accounts.items():
        result = results.get(case)
        row = {'phase': phase, 'case': case, 'account': name, 'result': result,
               'passed': bool(result and result.get('passed') is True and name in starts)}
        if result and name in starts:
            elapsed = (datetime.fromisoformat(ends[case]) - datetime.fromisoformat(starts[name])).total_seconds()
            if elapsed < 0:
                raise ValueError('Result predates queue start: ' + name)
            row.update(started_at_utc=starts[name], completed_at_utc=ends[case], elapsed_seconds=elapsed)
        rows.append(row)
    return rows


def collect(root, launchers_passed):
    rows, errors = [], {}
    for phase in PHASES:
        try:
            rows.extend(phase_results(root, phase))
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors[phase] = str(error)
    passed = bool(launchers_passed and not errors and rows and all(row['passed'] for row in rows))
    report = {'passed': passed, 'launchers_passed': launchers_passed, 'phase_errors': errors, 'rows': rows}
    harness.write_json(root / 'results.json', report)
    return report


def stop_children(args, children, stage):
    """Ask owned clients to quit, then stop any remaining owned launcher trees."""
    if stage != 'prepare':
        for phase, child in children.items():
            if child.poll() is not None:
                continue
            try:
                manifest = harness.read_json(args.run_dir / ('phase' + phase) / 'manifest.json')
                for index, batch in enumerate(manifest['batches']):
                    port = args.operator_port + PHASES.index(phase) * PORT_STRIDE + index
                    base = 'http://127.0.0.1:' + str(port) + '/api/v1'
                    with urllib.request.urlopen(base + '/status', timeout=3) as response:
                        state = json.load(response)
                    expected = {manifest['accounts'][case] for case in batch}
                    if {row['name'] for row in state['accounts']} != expected:
                        continue
                    request = urllib.request.Request(base + '/console/commands', data=b'{"command":"quit"}',
                                                     headers={'Content-Type': 'application/json'}, method='POST')
                    with urllib.request.urlopen(request, timeout=3):
                        pass
            except (OSError, ValueError, KeyError) as error:
                print('Shutdown request unavailable for phase', phase, ':', error, file=sys.stderr)
    deadline = time.monotonic() + 45
    while any(child.poll() is None for child in children.values()) and time.monotonic() < deadline:
        time.sleep(0.2)
    for child in children.values():
        if child.poll() is not None:
            continue
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True, creationflags=FLAGS)
        else:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        child.wait()


def run(args):
    root = args.run_dir
    if root == REPO / 'build' or not root.is_relative_to(REPO / 'build'):
        raise ValueError('Run directory must be beneath this checkout\'s ignored build/ folder.')
    if not 1 <= args.operator_port <= 65536 - len(PHASES) * PORT_STRIDE:
        raise ValueError('Operator port base must leave room for all 30 reserved ports.')
    if args.timeout_minutes <= 0 or args.seed_timeout_minutes <= 0:
        raise ValueError('Timeouts must be positive.')
    if not args.client.is_file():
        raise ValueError('Client executable is missing: ' + str(args.client))
    root.mkdir(parents=True, exist_ok=False)
    binary = root / ('client.exe' if sys.platform == 'win32' else 'client')
    shutil.copy2(args.client, binary)
    harness.write_json(root / 'provenance.json', {
        'client_sha': harness.git_sha(REPO), 'binary_sha256': harness.digest(binary),
        'scope': 'All individual phase16 and phase17a-i cases; optional phase16 full queues excluded',
        'started_at_utc': utc_now(), 'operator_port': args.operator_port,
        'seed_timeout_minutes': args.seed_timeout_minutes, 'timeout_minutes': args.timeout_minutes})
    children, stage = {}, 'prepare'
    try:
        for phase in PHASES:
            children = {phase: launch(args, phase, 'prepare')}
            if children[phase].wait() != 0:
                raise ValueError('Preparation failed: ' + phase)
        stage = 'seed'
        children = {}
        for phase in PHASES:
            children[phase] = launch(args, phase, 'seed')
        if not wait_all(args, children, stage):
            raise ValueError('Seed failed; no quests were launched. Inspect retained logs.')
        stage = 'run'
        children = {}
        for phase in PHASES:
            children[phase] = launch(args, phase, 'run')
        launchers_passed = wait_all(args, children, stage)
        report = collect(root, launchers_passed)
        status = harness.read_json(root / 'status.json')
        status.update(stage='complete', passed=report['passed'], updated_at_utc=utc_now(),
                      cases_passed=sum(row['passed'] for row in report['rows']), phase_errors=report['phase_errors'])
        harness.write_json(root / 'status.json', status)
        print('Grand run complete, passed:', report['passed'], flush=True)
        return 0 if report['passed'] else 1
    except (Exception, KeyboardInterrupt) as error:
        stop_children(args, children, stage)
        harness.write_json(root / 'status.json', {'stage': 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                           'failed_stage': stage, 'passed': False, 'error': str(error), 'updated_at_utc': utc_now()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--client', type=Path, default=REPO / ('build/windows-msvc/Release/Rs2004Headless.exe'
                                                            if sys.platform == 'win32' else 'build/linux-clang/Release/Rs2004Headless'))
    parser.add_argument('--server-dir', type=Path, default=REPO.parent / '289server/engine')
    parser.add_argument('--cache-dir', type=Path, default=REPO / 'data/cache')
    parser.add_argument('--nav-dir', type=Path, default=REPO / 'data/nav')
    parser.add_argument('--server-port', type=int, default=80)
    parser.add_argument('--operator-port', type=int, default=8200)
    parser.add_argument('--seed-timeout-minutes', type=float, default=45)
    parser.add_argument('--timeout-minutes', type=float, default=720)
    parser.add_argument('--natural-run', action='store_true')
    args = parser.parse_args()
    for name in ['run_dir', 'client', 'server_dir', 'cache_dir', 'nav_dir']:
        setattr(args, name, getattr(args, name).resolve())
    try:
        return run(args)
    except (OSError, ValueError, subprocess.SubprocessError, KeyboardInterrupt) as error:
        print('ERROR:', error or 'Interrupted; not a pass.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
