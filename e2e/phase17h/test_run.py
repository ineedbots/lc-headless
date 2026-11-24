"""Check independent coverage, prerequisites and the local members-only snapshot."""

import ast
import contextlib
import io
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run as scenario
from phase17h_cases import CASES, POINTS, initial_points, prerequisite_flags, preparation_flags, preparation_items

harness = scenario.harness


class Phase17hTests(unittest.TestCase):
    def test_cases_cover_registered_quests_once(self):
        expected = ['upass', 'regicide']
        expected = set(expected)
        self.assertEqual(len(CASES), 2)
        self.assertEqual(set(CASES.values()), expected)
        self.assertEqual(harness.case_batches(list(CASES), scenario.SUITE), [list(CASES)])
        source = ast.parse((harness.REPO / 'src/Script/Stdlib/rs2004/catalogs/_quests.py').read_text())
        records = {row['id']: row for row in ast.literal_eval(next(node.value for node in source.body if isinstance(node, ast.Assign)))}
        for case, quest in CASES.items():
            with self.subTest(quest=quest):
                settings = scenario.account_settings(case, 'c17test')
                self.assertEqual(settings['quests'], [quest])
                self.assertEqual(POINTS[quest], records[quest]['quest_points'])
                self.assertEqual(settings['e2e_expected_qp'], initial_points(quest) + records[quest]['quest_points'])
                prerequisites = {row[0] for row in prerequisite_flags(quest)}
                self.assertNotIn(quest, prerequisites)
                self.assertTrue(set(records[quest]['requirements'].get('quests', [])).issubset(prerequisites))
                self.assertEqual(initial_points(quest), sum(records[id]['quest_points'] for id in prerequisites))
                for id in prerequisites:
                    self.assertTrue(set(records[id]['requirements'].get('quests', [])).issubset(prerequisites))
                self.assertGreaterEqual(initial_points(quest), records[quest]['requirements'].get('min_quest_points', 0))

    def test_real_aio_selection_keeps_each_queue_to_its_target(self):
        module_spec = importlib.util.spec_from_file_location('quest_selection', harness.REPO / 'scripts/bots/aioquester/quest_selection.py')
        selection = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(selection)
        source = ast.parse((harness.REPO / 'src/Script/Stdlib/rs2004/catalogs/_quests.py').read_text())
        catalog = ast.literal_eval(next(node.value for node in source.body if isinstance(node, ast.Assign)))
        records = []
        for row in catalog:
            requirements = row['requirements']
            records.append(SimpleNamespace(id=row['id'], quest_points=row['quest_points'], requirements=SimpleNamespace(
                quests=requirements.get('quests', []),
                skills=[SimpleNamespace(**skill) for skill in requirements.get('skills', [])],
                min_quest_points=requirements.get('min_quest_points', 0))))
        for quest in CASES.values():
            with self.subTest(quest=quest):
                completed = {row[0] for row in prerequisite_flags(quest)}
                picked = selection.plan_quest_selection([quest], [], records, completed, initial_points(quest))
                self.assertEqual(picked, {quest})

    def test_preparation_does_not_advance_any_target(self):
        for quest in CASES.values():
            self.assertEqual(preparation_flags(quest), [])
            self.assertNotIn(quest, {row[0] for row in prerequisite_flags(quest)})

    def test_preparation_supplies_match_the_dungeon_profile(self):
        for quest in CASES.values():
            supplies = {name: count for symbol, name, count in preparation_items(quest)}
            self.assertEqual(supplies['Shortbow'], 1)
            self.assertEqual(supplies['Bronze arrow'], 500)
            self.assertEqual(initial_points(quest), 9 if quest == 'regicide' else 4)
        self.assertEqual(dict((name, count) for symbol, name, count in preparation_items('regicide'))['Shark'], 1000)
        self.assertEqual(scenario.account_settings('rg', '')['food'], 'Shark')

    def test_nonmembers_and_existing_characters_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            server = Path(temporary)
            (server / 'data/config').mkdir(parents=True)
            world = {'node': {'production': False, 'members': False}, 'login': {'enabled': False}}
            harness.write_json(server / 'data/config/world.json', world)
            with self.assertRaisesRegex(ValueError, 'members content'):
                harness.validate_characters(server, 'c17test', scenario.SUITE)
            world['node']['members'] = True
            harness.write_json(server / 'data/config/world.json', world)
            saves = server / 'data/players/main'
            saves.mkdir(parents=True)
            save = saves / ('c17test' + next(iter(CASES)) + '.sav')
            save.write_bytes(b'preserve')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                harness.validate_characters(server, 'c17test', scenario.SUITE)
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
                                   prefix='c17test', cache_dir=folder, nav_dir=folder,
                                   natural_run=False, server_port=80, operator_port=8097)
            with patch.object(harness, 'public_key', return_value={}), patch.object(harness, 'git_sha', return_value='sha'), contextlib.redirect_stdout(io.StringIO()):
                harness.prepare(args, scenario.SUITE)
            manifest = harness.read_json(args.run_dir / 'manifest.json')
            self.assertEqual(manifest['suite'], 'phase17h')
            self.assertEqual(len(manifest['accounts']), 2)
            for case, name in manifest['accounts'].items():
                account = harness.read_json(args.run_dir / 'accounts' / (name + '.jsonc'))
                seed = harness.read_json(args.run_dir / 'seed-accounts' / (name + '.jsonc'))
                self.assertEqual(account['password'], seed['password'])
                self.assertEqual(account['script']['settings']['AIOQuester']['quests'], [CASES[case]])
                self.assertEqual(seed['script']['settings'], {'kind': case, 'target': CASES[case]})
            for name in ['seed.py', 'phase17h_cases.py', 'live_quester.py', 'result_policy.py', 'seed_helpers.py', 'bots/aio_quester.py']:
                self.assertIn(name, manifest['scripts_sha256'])


if __name__ == '__main__':
    unittest.main()
