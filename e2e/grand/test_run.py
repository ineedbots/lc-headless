"""Grand orchestration must gate execution and fail closed on partial evidence."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

spec = importlib.util.spec_from_file_location('grand_run', Path(__file__).with_name('run.py'))
grand = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grand)


class GrandRunTests(unittest.TestCase):
    def arguments(self, root):
        binary = root / 'source-client'
        binary.write_bytes(b'fake binary')
        return SimpleNamespace(run_dir=root / 'build/grand', client=binary, operator_port=8200,
                               server_dir=root / 'server', cache_dir=root / 'cache', nav_dir=root / 'nav',
                               server_port=80, natural_run=False, seed_timeout_minutes=45, timeout_minutes=720)

    def fixture(self, root, phase='16', passed=True):
        folder = root / ('phase' + phase)
        session = folder / 'sessions/one-run-fixture'
        session.mkdir(parents=True)
        grand.harness.write_json(folder / 'manifest.json', {'accounts': {'ph': 'scratchph'}})
        result = {'case': 'ph', 'name': 'Scratchph', 'passed': passed}
        lines = '2026-11-24T23:59:59Z INFO [scratchph] AIOQuester, queue: quest\n'
        lines += '2026-11-25T00:01:01Z INFO [scratchph] E2E_RESULT ' + json.dumps(result) + '\n'
        log = session / 'client.log'
        log.write_text(lines, encoding='utf-8')
        return log

    def test_phase_commands_cover_only_individual_suites_and_disjoint_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.arguments(Path(tmp))
            self.assertEqual(grand.PHASES, ['16'] + ['17' + letter for letter in 'abcdefghi'])
            ports = []
            for phase in grand.PHASES:
                command = grand.phase_command(args, phase, 'prepare')
                self.assertTrue(command[1].endswith('individual.py' if phase == '16' else 'run.py'))
                ports.append(int(command[command.index('--operator-port') + 1]))
                self.assertIn(str(args.run_dir / ('client.exe' if grand.sys.platform == 'win32' else 'client')), command)
            self.assertEqual(ports, list(range(8200, 8230, 3)))
            args.natural_run = True
            self.assertIn('--natural-run', grand.phase_command(args, '16', 'prepare'))
            self.assertEqual(grand.phase_command(args, '16', 'seed')[-1], '45')
            self.assertEqual(grand.phase_command(args, '16', 'run')[-1], '720')

    def orchestrate(self, seed_passed=True, launchers_passed=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.arguments(root)
            calls = []

            def launch(args, phase, command):
                calls.append((phase, command))
                return Mock(pid=123, wait=Mock(return_value=0), poll=Mock(return_value=0))

            def wait(args, children, stage):
                grand.harness.write_json(args.run_dir / 'status.json', {'stage': stage})
                return seed_passed if stage == 'seed' else launchers_passed

            with patch.object(grand, 'REPO', root), patch.object(grand, 'launch', side_effect=launch), \
                    patch.object(grand, 'wait_all', side_effect=wait), \
                    patch.object(grand, 'stop_children') as stop, \
                    patch.object(grand, 'collect', return_value={'passed': launchers_passed, 'rows': [], 'phase_errors': {}}) as collect, \
                    patch.object(grand.harness, 'git_sha', return_value='source'), contextlib.redirect_stdout(io.StringIO()):
                if seed_passed:
                    self.assertEqual(grand.run(args), 0 if launchers_passed else 1)
                    self.assertEqual([command for phase, command in calls], ['prepare'] * 10 + ['seed'] * 10 + ['run'] * 10)
                    collect.assert_called_once_with(args.run_dir, launchers_passed)
                    stop.assert_not_called()
                    self.assertEqual(grand.harness.read_json(args.run_dir / 'status.json')['stage'], 'complete')
                else:
                    with self.assertRaisesRegex(ValueError, 'no quests were launched'):
                        grand.run(args)
                    self.assertFalse(any(command == 'run' for phase, command in calls))
                    collect.assert_not_called()
                    stop.assert_called_once()
                    self.assertFalse(grand.harness.read_json(args.run_dir / 'status.json')['passed'])

    def test_all_seeds_finish_before_any_quest_is_launched(self):
        self.orchestrate()

    def test_seed_failure_withholds_all_quest_runs(self):
        self.orchestrate(seed_passed=False)

    def test_launcher_failure_keeps_aggregate_failed(self):
        self.orchestrate(launchers_passed=False)

    def test_elapsed_time_crosses_midnight_and_launcher_failure_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            with patch.object(grand, 'PHASES', ['16']):
                report = grand.collect(root, True)
                self.assertTrue(report['passed'])
                self.assertEqual(report['rows'][0]['elapsed_seconds'], 62)
                self.assertFalse(grand.collect(root, False)['passed'])

    def test_missing_failed_duplicate_and_wrong_account_results_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = self.fixture(root)
            original = log.read_text()
            variants = [original.split('2026-11-25')[0], original.replace('"passed": true', '"passed": false'),
                        original + original, original.replace('"Scratchph"', '"Somebodyelse"')]
            with patch.object(grand, 'PHASES', ['16']):
                for text in variants:
                    log.write_text(text)
                    self.assertFalse(grand.collect(root, True)['passed'])

    def test_restarted_session_is_not_uninterrupted_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            (root / 'phase16/sessions/two-run-restarted').mkdir()
            with patch.object(grand, 'PHASES', ['16']):
                report = grand.collect(root, True)
            self.assertFalse(report['passed'])
            self.assertIn('16', report['phase_errors'])

    def test_existing_or_outside_run_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.arguments(root)
            with patch.object(grand, 'REPO', root):
                args.run_dir.mkdir(parents=True)
                marker = args.run_dir / 'retain.txt'
                marker.write_text('retain')
                with self.assertRaises(FileExistsError):
                    grand.run(args)
                self.assertEqual(marker.read_text(), 'retain')
                args.run_dir = root / 'elsewhere'
                with self.assertRaisesRegex(ValueError, 'ignored build'):
                    grand.run(args)
                self.assertFalse(args.run_dir.exists())

    def test_interrupt_marks_run_failed_and_stops_owned_launchers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.arguments(root)
            child = Mock()
            child.wait.side_effect = KeyboardInterrupt
            with patch.object(grand, 'REPO', root), patch.object(grand, 'launch', return_value=child), \
                    patch.object(grand.harness, 'git_sha', return_value='source'), patch.object(grand, 'stop_children') as stop:
                with self.assertRaises(KeyboardInterrupt):
                    grand.run(args)
                stop.assert_called_once_with(args, {'16': child}, 'prepare')
                self.assertEqual(grand.harness.read_json(args.run_dir / 'status.json')['stage'], 'interrupted')

    def test_cleanup_refuses_an_unrelated_listener_and_only_stops_its_owned_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.arguments(Path(tmp))
            folder = args.run_dir / 'phase16'
            folder.mkdir(parents=True)
            grand.harness.write_json(folder / 'manifest.json', {'accounts': {'ph': 'scratchph'}, 'batches': [['ph']]})
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b'{"accounts":[{"name":"unrelated"}]}'
            child = Mock(pid=123, poll=Mock(return_value=None))
            with patch.object(grand.urllib.request, 'urlopen', return_value=response) as request, \
                    patch.object(grand.time, 'monotonic', side_effect=[0, 46]), \
                    patch.object(grand.sys, 'platform', 'win32'), patch.object(grand.subprocess, 'run') as terminate:
                grand.stop_children(args, {'16': child}, 'run')
            request.assert_called_once_with('http://127.0.0.1:8200/api/v1/status', timeout=3)
            terminate.assert_called_once_with(['taskkill', '/PID', '123', '/T', '/F'], capture_output=True,
                                              creationflags=grand.FLAGS)
            child.wait.assert_called_once()

    def test_cleanup_requests_quit_for_matching_accounts_before_forcing_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.arguments(Path(tmp))
            folder = args.run_dir / 'phase16'
            folder.mkdir(parents=True)
            grand.harness.write_json(folder / 'manifest.json', {'accounts': {'ph': 'scratchph'}, 'batches': [['ph']]})
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b'{"accounts":[{"name":"scratchph"}]}'
            child = Mock(pid=123, poll=Mock(side_effect=[None, 0, 0]))
            with patch.object(grand.urllib.request, 'urlopen', return_value=response) as request, \
                    patch.object(grand.time, 'monotonic', return_value=0), patch.object(grand.subprocess, 'run') as terminate:
                grand.stop_children(args, {'16': child}, 'run')
            self.assertEqual(request.call_count, 2)
            quit_request = request.call_args_list[1].args[0]
            self.assertEqual(quit_request.full_url, 'http://127.0.0.1:8200/api/v1/console/commands')
            self.assertEqual(json.loads(quit_request.data), {'command': 'quit'})
            terminate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
