"""Phase 16's queue configuration and shared fresh-completion guarantees."""

import ast
import contextlib
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run as scenario
import individual

harness = scenario.harness
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from result_policy import completion_passed


class Phase16Tests(unittest.TestCase):
    def test_both_gangs_earn_the_full_f2p_queue_and_its_points(self):
        source = ast.parse((harness.REPO / 'src/Script/Stdlib/rs2004/catalogs/_quests.py').read_text())
        rows = ast.literal_eval(next(node.value for node in source.body if isinstance(node, ast.Assign)))
        records = {row['id']: row for row in rows}
        self.assertEqual(len(set(scenario.QUESTS)), 18)
        self.assertEqual(sum(records[id]['quest_points'] for id in scenario.QUESTS), 39)
        self.assertLess(records['blackknight']['requirements']['min_quest_points'], 39 - records['blackknight']['quest_points'])
        self.assertEqual(records['dragon']['requirements']['min_quest_points'], 32)
        for case, other, gang in [('ph', 'ba', 'phoenix'), ('ba', 'ph', 'blackarm')]:
            settings = scenario.account_settings(case, 'g16test')
            self.assertEqual(settings['quests'], scenario.QUESTS)
            self.assertEqual(settings['arrav_gang'], gang)
            self.assertEqual(settings['arrav_partner'], 'g16test' + other)
            self.assertEqual(settings['e2e_expected_qp'], 39)

    def test_preparation_uses_fresh_accounts_and_a_self_contained_snapshot(self):
        root = harness.REPO / 'build/e2e-unit'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            folder = Path(temporary).resolve()
            self.assertTrue(folder.is_relative_to(root.resolve()))
            server = folder / 'server'
            (server / 'data/config').mkdir(parents=True)
            (server / 'data/players/main').mkdir(parents=True)
            (server / 'src').mkdir()
            (server / 'src/app.ts').touch()
            harness.write_json(server / 'data/config/world.json', {'node': {'production': False, 'members': False}, 'login': {'enabled': False}})
            client = folder / 'client'
            client.write_bytes(b'executable')
            args = SimpleNamespace(server_dir=server, run_dir=folder / 'run', client=client,
                                   prefix='g16test', cache_dir=folder, nav_dir=folder,
                                   natural_run=True, server_port=80, operator_port=8093)
            with patch.object(harness, 'public_key', return_value={}), patch.object(harness, 'git_sha', return_value='sha'), contextlib.redirect_stdout(io.StringIO()):
                harness.prepare(args, scenario.SUITE)
            manifest = harness.read_json(args.run_dir / 'manifest.json')
            self.assertEqual(manifest['accounts'], {'ph': 'g16testph', 'ba': 'g16testba'})
            self.assertEqual(manifest['suite'], 'phase16')
            for case, name in manifest['accounts'].items():
                settings = harness.read_json(args.run_dir / 'accounts' / (name + '.jsonc'))['script']['settings']['AIOQuester']
                self.assertFalse(settings['e2e_infinite_run'])
                self.assertEqual(settings['quests'], scenario.QUESTS)
            for name in ['live_quester.py', 'result_policy.py', 'seed_helpers.py', 'seed.py', 'bots/aio_quester.py']:
                self.assertTrue((args.run_dir / 'scripts' / name).is_file())
                self.assertIn(name, manifest['scripts_sha256'])
            (server / 'data/players/main/g16otherba.sav').write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                harness.validate_fresh(server, folder / 'another', 'g16other', scenario.SUITE)
            args.command = 'run'
            with patch.object(harness.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
                with self.assertRaisesRegex(ValueError, 'different e2e suite'):
                    harness.execute(args, dict(scenario.SUITE, name='another-suite'))

    def test_only_a_complete_earned_queue_with_zero_deaths_passes(self):
        journal = {id: 'complete' for id in scenario.QUESTS}
        args = dict(journal=journal, initial_done=[], completed=18, deaths=0,
                    summary={'done': 18, 'total': 18, 'stuck': 0}, qp=39, expected_qp=39)
        self.assertTrue(completion_passed(**args))
        for change in [dict(completed=17), dict(deaths=1), dict(qp=38), dict(journal={}),
                       dict(initial_done=list(journal), completed=0),
                       dict(journal=dict(journal, dragon='in_progress')),
                       dict(summary={'done': 17, 'total': 18, 'stuck': 1})]:
            with self.subTest(change=change):
                self.assertFalse(completion_passed(**dict(args, **change)))
        # A resume must earn every remaining quest; its earlier work stays explicit.
        self.assertTrue(completion_passed(**dict(args, initial_done=['cook'], completed=17)))
        self.assertFalse(completion_passed(**dict(args, initial_done=['cook'], completed=16)))
        self.assertFalse(completion_passed({'ikov': 'complete'}, ['ikov'], 0, 0, {'done': 1, 'total': 1, 'stuck': 0}, 1, 0))


class IndividualTests(unittest.TestCase):
    def test_every_quest_has_its_own_account_and_arrav_partners_share_a_batch(self):
        from phase16_cases import CASES, POINTS, initial_points, prerequisite_flags
        self.assertEqual(len(CASES), 19)
        self.assertEqual(set(CASES.values()), set(scenario.QUESTS))
        self.assertEqual(list(CASES.values()).count('blackarmgang'), 2)
        groups = harness.case_batches(list(CASES), individual.SUITE)
        self.assertEqual([len(group) for group in groups], [10, 9])
        self.assertTrue(any({'ph', 'ba'}.issubset(group) for group in groups))
        for case, quest in CASES.items():
            settings = individual.account_settings(case, 'f16test')
            self.assertEqual(settings['quests'], [quest])
            self.assertEqual(settings['e2e_expected_qp'], initial_points(quest) + POINTS[quest])
            self.assertNotIn(quest, [row[0] for row in prerequisite_flags(quest)])
        self.assertEqual(initial_points('blackknight'), 12)
        self.assertEqual(initial_points('dragon'), 32)
        self.assertEqual(harness.case_batches(['ph', 'ba'], individual.SUITE), [['ph', 'ba']])
        with self.assertRaisesRegex(ValueError, 'share a client'):
            harness.case_batches(['ph', 'ba'], dict(individual.SUITE, groups=[list(CASES)[:13], list(CASES)[13:]]))

    def test_multi_client_launch_starts_both_batches_and_combines_verified_results(self):
        self.exercise_launch(False)

    def test_failed_batch_stops_the_other_owned_client_and_cannot_pass(self):
        self.exercise_launch(True)

    def exercise_launch(self, fail):
        root = harness.REPO / 'build/e2e-unit'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            folder = Path(temporary).resolve()
            self.assertTrue(folder.is_relative_to(root.resolve()))
            run_dir = folder / 'run'
            run_dir.mkdir()
            (run_dir / 'seed-accounts').mkdir()
            (run_dir / 'scripts').mkdir()
            session = run_dir / 'session'
            session.mkdir()
            manifest = {'server': str(folder), 'accounts': {case: 'f16test' + case for case in individual.CASES}}
            for name in manifest['accounts'].values():
                harness.write_json(run_dir / 'seed-accounts' / (name + '.jsonc'), {})
            harness.write_json(run_dir / 'client.json', {'scripting': {}, 'client': {}, 'http': {'port': 8095}})
            client = folder / 'client'
            client.write_bytes(b'executable')
            args = SimpleNamespace(operator_port=None, timeout_minutes=1)
            events = []
            processes = []

            class Process:
                finished = False

                def poll(self):
                    return 0 if self.finished else None

                def wait(self, timeout):
                    events.append('wait')
                    self.finished = True
                    return 1 if fail else 0

            def launch(command, **kwargs):
                events.append('launch')
                config = harness.read_json(Path(command[1]))
                names = [path.stem for path in Path(config['scripting']['accountsDirectory']).glob('*.jsonc')]
                self.assertLessEqual(len(names), 16)
                rows = [{'case': name[-2:], 'name': name, 'passed': True} for name in names]
                Path(config['client']['logFile']).write_text('\n'.join('E2E_SEEDED ' + harness.json.dumps(row) for row in rows))
                process = Process()
                processes.append(process)
                return process

            with patch.object(harness.subprocess, 'Popen', side_effect=launch), patch.object(harness, 'git_sha', return_value='sha'), patch.object(harness, 'request_shutdown') as shutdown, contextlib.redirect_stdout(io.StringIO()):
                if fail:
                    with self.assertRaisesRegex(ValueError, 'not a pass'):
                        harness.run_clients(args, individual.SUITE, manifest, run_dir, session, list(individual.CASES), client, True)
                    shutdown.assert_called_once()
                    self.assertIs(shutdown.call_args.args[0], processes[1])
                else:
                    result = harness.run_clients(args, individual.SUITE, manifest, run_dir, session, list(individual.CASES), client, True)
                    self.assertEqual(set(result), set(individual.CASES))
                    shutdown.assert_not_called()
                    ports = [harness.read_json(path)['http']['port'] for path in sorted(session.glob('batch-*/client.json'))]
                    self.assertEqual(ports, [8095, 8096])
            self.assertEqual(events[:3], ['launch', 'launch', 'wait'])


if __name__ == '__main__':
    unittest.main()
