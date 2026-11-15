import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

import server
from storage import SCHEMA_VERSION, create_schema


def insert_record(database, stream, account, timestamp, record):
    database.execute('INSERT INTO fleet_accounts (name) VALUES (?) ON CONFLICT (name) DO NOTHING', (account,))
    account_id = database.execute('SELECT id FROM fleet_accounts WHERE name = ?', (account,)).fetchone()[0]
    cursor = database.execute(
        'INSERT INTO fleet_records (account_id, stream, recorded_at) VALUES (?, ?, ?)',
        (account_id, stream, timestamp))
    record_id = cursor.lastrowid

    if stream == 'experience':
        database.execute(
            'INSERT INTO fleet_experience (record_id, state, settled) VALUES (?, ?, ?)',
            (record_id, record['state'], record['settled']))
        database.executemany(
            'INSERT INTO fleet_experience_skills (record_id, skill, ordinal, level, base, xp) VALUES (?, ?, ?, ?, ?, ?)',
            ((record_id, skill, index, values['level'], values['base'], values['xp'])
             for index, (skill, values) in enumerate(record.get('skills', {}).items())))
    elif stream == 'bank':
        database.execute('INSERT INTO fleet_bank (record_id) VALUES (?)', (record_id,))
        database.executemany(
            'INSERT INTO fleet_bank_items (record_id, item_id, name, quantity) VALUES (?, ?, ?, ?)',
            ((record_id, item['id'], item['name'], item['qty']) for item in record.get('items', [])))
    elif stream == 'inventory':
        database.execute(
            'INSERT INTO fleet_inventory (record_id, bank_open, used, free) VALUES (?, ?, ?, ?)',
            (record_id, record['bankOpen'], record['used'], record['free']))
        database.executemany(
            'INSERT INTO fleet_inventory_items (record_id, item_id, name, quantity) VALUES (?, ?, ?, ?)',
            ((record_id, item['id'], item['name'], item['qty']) for item in record.get('items', [])))
    elif stream == 'equipment':
        database.execute('INSERT INTO fleet_equipment (record_id, used) VALUES (?, ?)', (record_id, record['used']))
        database.executemany(
            'INSERT INTO fleet_equipment_items (record_id, item_id, name, quantity) VALUES (?, ?, ?, ?)',
            ((record_id, item['id'], item['name'], item['qty']) for item in record.get('items', [])))
    elif stream == 'account-data':
        tile = record.get('tile')
        destination = record.get('destination')
        target = record.get('target')
        target_tile = target.get('tile') if target else None
        hp = record.get('hp')
        prayer = record.get('prayer')
        special = record.get('specialAttack')
        fields = (
            record_id,
            record['state'],
            record['settled'],
            record.get('pid'),
            *(tile.values() if tile else (None, None, None)),
            *(destination.values() if destination else (None, None, None)),
            target.get('kind') if target else None,
            target.get('index') if target else None,
            *(target_tile.values() if target_tile else (None, None, None)),
            hp.get('current') if hp else None,
            hp.get('base') if hp else None,
            record.get('energy'),
            prayer.get('current') if prayer else None,
            prayer.get('base') if prayer else None,
            special.get('energy') if special else None,
            special.get('armed') if special else None,
            record.get('running'),
            record.get('moving'),
            record.get('inCombat'),
            record.get('weight'),
            record['tick'],
        )
        database.execute(
            'INSERT INTO fleet_account_data VALUES (' + ', '.join('?' for _ in fields) + ')',
            fields)
    else:
        raise ValueError(f'unknown stream {stream}')


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
            for xp in (1, 2):
                insert_record(database, 'experience', 'worker', '2026-01-01T00:00:00Z', {
                    'state': 'ingame', 'settled': True, 'skills': {'attack': {'level': 1, 'base': 1, 'xp': xp}}})
            insert_record(database, 'experience', 'other', '2026-01-01T00:00:00Z', {
                'state': 'logged out', 'settled': False, 'skills': {}})

        latest = server._latest('experience')
        self.assertEqual(latest['worker']['skills']['attack']['xp'], 2)
        self.assertEqual(latest['other']['state'], 'logged out')
        self.assertEqual(
            [record['skills']['attack']['xp'] for record in server._history('experience', 'worker', 10)],
            [1, 2])
        connection = server.connect_readonly(self.database_path)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute('DELETE FROM fleet_records')
        finally:
            connection.close()

    def test_latest_reconstructs_all_typed_stream_shapes(self):
        records = {
            'account-data': {
                'state': 'ingame', 'settled': True, 'pid': 42,
                'tile': {'x': 3200, 'z': 3201, 'level': 0},
                'destination': None, 'target': {'kind': 'npc', 'index': 17},
                'hp': {'current': 25, 'base': 30}, 'energy': 80,
                'prayer': {'current': 12, 'base': 20},
                'specialAttack': {'energy': 750, 'armed': False},
                'running': True, 'moving': False, 'inCombat': False,
                'weight': 5, 'tick': 123,
            },
            'experience': {
                'state': 'ingame', 'settled': True,
                'skills': {'attack': {'level': 31, 'base': 30, 'xp': 14848}},
            },
            'bank': {'items': [{'id': 995, 'name': 'Coins', 'qty': 109}]},
            'inventory': {
                'bankOpen': False, 'used': 1, 'free': 27,
                'items': [{'id': 995, 'name': 'Coins', 'qty': 109}],
            },
            'equipment': {
                'used': 1,
                'items': [{'id': 995, 'name': 'Coins', 'qty': 1}],
            },
        }
        with closing(sqlite3.connect(self.database_path)) as database, database:
            create_schema(database)
            for stream, record in records.items():
                insert_record(database, stream, 'worker', '2026-01-01T00:00:00Z', record)

        for stream, expected in records.items():
            actual = server._latest(stream)['worker']
            self.assertEqual({key: value for key, value in actual.items() if key not in ('time', 'account')}, expected)

    def test_schema_rejects_existing_generic_database_without_migration(self):
        with closing(sqlite3.connect(self.database_path)) as database, database:
            database.execute('CREATE TABLE fleet_records (sequence INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
            database.execute("INSERT INTO fleet_records VALUES (1, 'keep me')")
            database.execute('PRAGMA user_version = 2')

        with closing(sqlite3.connect(self.database_path)) as database:
            with self.assertRaisesRegex(sqlite3.DatabaseError, 'unsupported fleet database schema'):
                create_schema(database)

        with self.assertRaisesRegex(sqlite3.DatabaseError, 'unsupported fleet database schema version 2'):
            server.connect_readonly(self.database_path)

        with closing(sqlite3.connect(self.database_path)) as database:
            self.assertEqual(database.execute('SELECT payload FROM fleet_records').fetchone()[0], 'keep me')

    def test_schema_rejects_unversioned_tables(self):
        with closing(sqlite3.connect(self.database_path)) as database, database:
            database.execute('CREATE TABLE retained (value TEXT)')

        with closing(sqlite3.connect(self.database_path)) as database:
            with self.assertRaisesRegex(sqlite3.DatabaseError, 'unversioned schema'):
                create_schema(database)

    def test_config_database_path_parser_ignores_comments_outside_strings(self):
        config_path = os.path.join(self.temporary.name, 'client.jsonc')
        with open(config_path, 'w', encoding='utf-8') as config:
            config.write('{"scripting":{"fleetDatabasePath":"data/fleet//live.sqlite"} /* comment */}')

        self.assertEqual(
            server._database_for_config(config_path),
            os.path.abspath(os.path.join(server.ROOT, 'data', 'fleet//live.sqlite')))


if __name__ == '__main__':
    unittest.main()
