"""Host-side safeguards; these tests never connect to a game server."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run as scenario

harness = scenario.harness
SUITE = scenario.SUITE


class RunTests(unittest.TestCase):
    def setUp(self):
        root = harness.REPO / 'build/e2e-unit'
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.folder = Path(self.temp.name).resolve()
        assert self.folder.is_relative_to(root.resolve())
        self.addCleanup(self.temp.cleanup)
        self.server = self.folder / 'server'
        (self.server / 'data/config').mkdir(parents=True)
        (self.server / 'data/players/main').mkdir(parents=True)
        self.world = {'node': {'production': False}, 'login': {'enabled': False}}
        harness.write_json(self.server / 'data/config/world.json', self.world)

    def test_existing_saves_or_run_directories_are_never_reseeded(self):
        run_dir = self.folder / 'run'
        harness.validate_fresh(self.server, run_dir, 'g17test', SUITE)
        save = self.server / 'data/players/main/g17testph.sav'
        save.write_bytes(b'keep this character')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            harness.validate_fresh(self.server, run_dir, 'g17test', SUITE)
        self.assertEqual(save.read_bytes(), b'keep this character')
        run_dir.mkdir()
        with self.assertRaisesRegex(ValueError, 'directory already exists'):
            harness.validate_fresh(self.server, run_dir, 'another', SUITE)

    def test_setup_requires_local_development_and_ignored_artifacts(self):
        for field in ['production', 'enabled']:
            self.world['node']['production'] = field == 'production'
            self.world['login']['enabled'] = field == 'enabled'
            harness.write_json(self.server / 'data/config/world.json', self.world)
            with self.assertRaisesRegex(ValueError, 'local development'):
                harness.validate_characters(self.server, 'g17test', SUITE)
        with self.assertRaisesRegex(ValueError, 'ignored build'):
            harness.validate_fresh(self.server, harness.REPO / 'e2e/untracked-run', 'g17test', SUITE)
        with self.assertRaisesRegex(ValueError, 'Prefix'):
            harness.validate_fresh(self.server, self.folder / 'run', 'too-long-prefix', SUITE)

    def test_process_exit_without_matching_success_records_is_not_a_pass(self):
        expected = {'ik': 'g17testik'}
        for row in [None, {'case': 'ik', 'name': 'g17testik', 'passed': False},
                    {'case': 'ik', 'name': 'anotheruser', 'passed': True}]:
            text = 'client exited normally\n' if row is None else 'INFO E2E_RESULT ' + json.dumps(row)
            with self.assertRaisesRegex(ValueError, 'missing or failed'):
                harness.results(text, 'E2E_RESULT ', expected)
        row = {'case': 'ik', 'name': 'G17testik', 'passed': True}
        self.assertEqual(harness.results('INFO E2E_RESULT ' + json.dumps(row), 'E2E_RESULT ', expected)['ik'], row)

    def test_repeated_seeding_and_unprepared_runs_never_launch_a_client(self):
        run_dir = self.folder / 'run'
        run_dir.mkdir()
        harness.write_json(run_dir / 'manifest.json', {'repo': str(harness.REPO), 'server': str(self.server), 'prefix': 'g17test'})
        (run_dir / 'seed-started').write_text('prior attempt', encoding='utf-8')
        args = SimpleNamespace(run_dir=run_dir, command='seed')
        with patch.object(harness.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            with self.assertRaisesRegex(ValueError, 'already attempted'):
                harness.execute(args, SUITE)
            args.command = 'run'
            with self.assertRaisesRegex(ValueError, 'Seed must finish'):
                harness.execute(args, SUITE)

    def test_prepared_accounts_use_only_the_fresh_paired_names(self):
        client = self.folder / 'client.exe'
        client.write_bytes(b'test executable')
        (self.server / 'src').mkdir()
        (self.server / 'src/app.ts').touch()
        args = SimpleNamespace(server_dir=self.server, run_dir=self.folder / 'run', client=client,
                               prefix='g17test', cache_dir=self.folder, nav_dir=self.folder,
                               natural_run=False, server_port=80, operator_port=8091)
        with patch.object(harness, 'public_key', return_value={'rsaModulus': '0x11', 'rsaExponent': '0x03'}), \
             patch.object(harness, 'git_sha', return_value='test-sha'), contextlib.redirect_stdout(io.StringIO()):
            harness.prepare(args, SUITE)
        accounts = [harness.read_json(path) for path in (args.run_dir / 'accounts').glob('*.jsonc')]
        self.assertEqual({a['username'] for a in accounts}, {'g17testph', 'g17testba', 'g17testik', 'g17testft'})
        self.assertEqual(len({a['password'] for a in accounts}), 4)
        for account in accounts:
            settings = account['script']['settings']['AIOQuester']
            case = account['username'][-2:]
            self.assertEqual(settings['quests'], [scenario.CASES[case]])
            if case in ['ph', 'ba']:
                self.assertEqual(settings['hero_partner'], 'g17test' + ('ba' if case == 'ph' else 'ph'))
        config = harness.read_json(args.run_dir / 'client.json')
        self.assertEqual(config['server']['host'], '127.0.0.1')
        self.assertEqual(config['login']['revision'], 289)


if __name__ == '__main__':
    unittest.main()
