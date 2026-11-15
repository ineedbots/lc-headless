import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

import import_jsonl
import server
from storage import SCHEMA_VERSION, create_schema


class FleetDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database_path = os.path.join(self.temporary.name, 'fleet records.sqlite')
        self.previous_paths = server.DATABASE_PATHS
        server.DATABASE_PATHS = [self.database_path]
        self.addCleanup(setattr, server, 'DATABASE_PATHS', self.previous_paths)

    def test_latest_and_history_use_sequence_for_same_second(self):
        with closing(sqlite3.connect(self.database_path)) as database, database:
            create_schema(database)
            for value in (1, 2):
                payload = json.dumps({'account': 'worker', 'time': '2026-01-01T00:00:00Z', 'value': value})
                database.execute(
                    'INSERT INTO fleet_records (account, stream, recorded_at, payload) VALUES (?, ?, ?, ?)',
                    ('worker', 'experience', '2026-01-01T00:00:00Z', payload))
            database.execute(
                'INSERT INTO fleet_records (account, stream, recorded_at, payload) VALUES (?, ?, ?, ?)',
                ('other', 'experience', '2026-01-01T00:00:00Z', '{"account":"other","value":3}'))

        latest = server._latest('experience')
        self.assertEqual(latest['worker']['value'], 2)
        self.assertEqual(latest['other']['value'], 3)
        self.assertEqual(
            [record['value'] for record in server._history('experience', 'worker', 10)],
            [1, 2])
        connection = server.connect_readonly(self.database_path)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute('DELETE FROM fleet_records')
        finally:
            connection.close()

    def test_legacy_import_is_repeatable_and_leaves_sources_intact(self):
        legacy_root = os.path.join(self.temporary.name, 'legacy')
        experience = os.path.join(legacy_root, 'experience')
        os.makedirs(experience)
        source = os.path.join(experience, 'worker.jsonl')
        contents = (
            '{"time":"2026-01-01T00:00:00Z","account":"worker","state":"ingame"}\n'
            '{"time":\n'
            '{"time":"2026-01-01T00:01:00Z","state":"logged out"}\n')
        with open(source, 'w', encoding='utf-8') as journal:
            journal.write(contents)

        with closing(sqlite3.connect(self.database_path)) as database, database:
            database.execute('PRAGMA journal_mode = WAL')
            create_schema(database)
            self.assertEqual(import_jsonl.import_file(database, legacy_root, source, 'experience'), (2, 1))
            self.assertEqual(import_jsonl.import_file(database, legacy_root, source, 'experience'), (0, 3))
            rows = database.execute(
                'SELECT account, stream, payload FROM fleet_records ORDER BY sequence').fetchall()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], 'worker')
        self.assertEqual(rows[1][1], 'experience')
        self.assertEqual(json.loads(rows[1][2])['account'], 'worker')
        with open(source, encoding='utf-8') as journal:
            self.assertEqual(journal.read(), contents)

    def test_schema_upgrade_preserves_records_and_old_readers_can_open(self):
        with closing(sqlite3.connect(self.database_path)) as database, database:
            create_schema(database)
            database.execute(
                'INSERT INTO fleet_records (account, stream, recorded_at, payload) VALUES (?, ?, ?, ?)',
                ('worker', 'experience', '2026-01-01T00:00:00Z', '{"account":"worker"}'))
            database.execute('DROP INDEX fleet_records_stream_latest')
            database.execute('PRAGMA user_version = 1')

        old_reader = server.connect_readonly(self.database_path)
        old_reader.close()

        with closing(sqlite3.connect(self.database_path)) as database, database:
            create_schema(database)
            self.assertEqual(database.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
            self.assertIsNotNone(database.execute('SELECT payload FROM fleet_records').fetchone())
            self.assertIsNotNone(database.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'fleet_records_stream_latest'").fetchone())

    def test_config_database_path_parser_ignores_comments_outside_strings(self):
        config_path = os.path.join(self.temporary.name, 'client.jsonc')
        with open(config_path, 'w', encoding='utf-8') as config:
            config.write('{"scripting":{"fleetDatabasePath":"data/fleet//live.sqlite"} /* comment */}')

        self.assertEqual(
            server._database_for_config(config_path),
            os.path.abspath(os.path.join(server.ROOT, 'data', 'fleet//live.sqlite')))


if __name__ == '__main__':
    unittest.main()
