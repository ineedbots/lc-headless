"""Check independent coverage, prerequisites and the local members-only snapshot."""

import ast
import contextlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run as scenario
from phase17a_cases import CASES, POINTS, initial_points, prerequisite_flags

harness = scenario.harness


class Phase17aTests(unittest.TestCase):
    def test_cases_cover_the_twelve_registered_quests_once(self):
        expected = {'druid', 'drunkmonk', 'fluffs', 'junglepotion', 'cog', 'hazeelcult',
                    'ball', 'fishingcompo', 'murder', 'seaslug', 'priestperil', 'totem'}
        self.assertEqual(len(CASES), 12)
        self.assertEqual(set(CASES.values()), expected)
        self.assertEqual(harness.case_batches(list(CASES), scenario.SUITE), [list(CASES)])
        source = ast.parse((harness.REPO / 'src/Script/Stdlib/rs2004/catalogs/_quests.py').read_text())
        records = {row['id']: row for row in ast.literal_eval(next(node.value for node in source.body if isinstance(node, ast.Assign)))}
        for case, quest in CASES.items():
            with self.subTest(quest=quest):
                settings = scenario.account_settings(case, 'a17test')
                self.assertEqual(settings['quests'], [quest])
                self.assertEqual(POINTS[quest], records[quest]['quest_points'])
                self.assertEqual(settings['e2e_expected_qp'], initial_points(quest) + records[quest]['quest_points'])
                prerequisites = {row[0] for row in prerequisite_flags(quest)}
                self.assertNotIn(quest, prerequisites)
                self.assertTrue(set(records[quest]['requirements'].get('quests', [])).issubset(prerequisites))
                self.assertEqual(initial_points(quest), sum(records[id]['quest_points'] for id in prerequisites))
        self.assertEqual(initial_points('junglepotion'), 4)
        self.assertEqual(initial_points('priestperil'), 1)

    def test_nonmembers_and_existing_characters_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            server = Path(temporary)
            (server / 'data/config').mkdir(parents=True)
            world = {'node': {'production': False, 'members': False}, 'login': {'enabled': False}}
            harness.write_json(server / 'data/config/world.json', world)
            with self.assertRaisesRegex(ValueError, 'members content'):
                harness.validate_characters(server, 'a17test', scenario.SUITE)
            world['node']['members'] = True
            harness.write_json(server / 'data/config/world.json', world)
            saves = server / 'data/players/main'
            saves.mkdir(parents=True)
            save = saves / 'a17testjp.sav'
            save.write_bytes(b'preserve')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                harness.validate_characters(server, 'a17test', scenario.SUITE)
            self.assertEqual(save.read_bytes(), b'preserve')

    def test_snapshot_keeps_each_seed_and_quest_account_matched(self):
        root = harness.REPO / 'build/e2e-unit'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            folder = Path(temporary).resolve()
            server = folder / 'server'
            (server / 'data/config').mkdir(parents=True)
            (server / 'src').mkdir()
            (server / 'src/app.ts').touch()
            harness.write_json(server / 'data/config/world.json', {'node': {'production': False, 'members': True}, 'login': {'enabled': False}})
            client = folder / 'client'
            client.write_bytes(b'executable')
            args = SimpleNamespace(server_dir=server, run_dir=folder / 'run', client=client,
                                   prefix='a17test', cache_dir=folder, nav_dir=folder,
                                   natural_run=False, server_port=80, operator_port=8097)
            with patch.object(harness, 'public_key', return_value={}), patch.object(harness, 'git_sha', return_value='sha'), contextlib.redirect_stdout(io.StringIO()):
                harness.prepare(args, scenario.SUITE)
            manifest = harness.read_json(args.run_dir / 'manifest.json')
            self.assertEqual(manifest['suite'], 'phase17a')
            self.assertEqual(len(manifest['accounts']), 12)
            for case, name in manifest['accounts'].items():
                account = harness.read_json(args.run_dir / 'accounts' / (name + '.jsonc'))
                seed = harness.read_json(args.run_dir / 'seed-accounts' / (name + '.jsonc'))
                self.assertEqual(account['password'], seed['password'])
                self.assertEqual(account['script']['settings']['AIOQuester']['quests'], [CASES[case]])
                self.assertEqual(seed['script']['settings'], {'kind': case, 'target': CASES[case]})
            for name in ['seed.py', 'phase17a_cases.py', 'live_quester.py', 'result_policy.py', 'seed_helpers.py', 'bots/aio_quester.py']:
                self.assertIn(name, manifest['scripts_sha256'])


if __name__ == '__main__':
    unittest.main()
