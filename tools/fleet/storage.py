"""SQLite schema and read helpers shared by the fleet page and benchmark."""

import datetime
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 5
STREAMS = ('account-data', 'experience', 'bank', 'inventory', 'equipment')

CREATE_SCHEMA = (
    "CREATE TABLE fleet_accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
    "CREATE TABLE fleet_streams (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
    "CREATE TABLE fleet_records ("
    "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
    "account_id INTEGER NOT NULL REFERENCES fleet_accounts(id), "
    "stream_id INTEGER NOT NULL REFERENCES fleet_streams(id), "
    "recorded_at INTEGER NOT NULL)",
    "CREATE INDEX fleet_records_latest ON fleet_records (account_id, stream_id, sequence DESC)",
    "CREATE INDEX fleet_records_history ON fleet_records (account_id, stream_id, recorded_at, sequence)",
    "CREATE INDEX fleet_records_stream_latest ON fleet_records (stream_id, account_id, sequence DESC)",
    "CREATE TABLE fleet_item_names (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
    "CREATE TABLE fleet_states (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
    "CREATE TABLE fleet_target_kinds (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
    "INSERT INTO fleet_target_kinds (id, name) VALUES (1, 'npc'), (2, 'player'), (3, 'tile')",
    "CREATE TABLE fleet_skills (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
    "CREATE TABLE fleet_account_data ("
    "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
    "state_id INTEGER NOT NULL REFERENCES fleet_states(id), settled INTEGER NOT NULL CHECK (settled IN (0, 1)), pid INTEGER, "
    "tile_x INTEGER, tile_z INTEGER, tile_level INTEGER, "
    "destination_x INTEGER, destination_z INTEGER, destination_level INTEGER, "
    "target_kind_id INTEGER REFERENCES fleet_target_kinds(id), target_index INTEGER, target_x INTEGER, target_z INTEGER, target_level INTEGER, "
    "hp_current INTEGER, hp_base INTEGER, energy INTEGER CHECK (energy BETWEEN 0 AND 100), "
    "prayer_current INTEGER, prayer_base INTEGER, "
    "special_attack_energy INTEGER CHECK (special_attack_energy BETWEEN 0 AND 1000), "
    "special_attack_armed INTEGER CHECK (special_attack_armed IN (0, 1)), "
    "running INTEGER CHECK (running IN (0, 1)), moving INTEGER CHECK (moving IN (0, 1)), "
    "in_combat INTEGER CHECK (in_combat IN (0, 1)), weight INTEGER, "
    "tick INTEGER NOT NULL CHECK (tick >= 0), "
    "CHECK ((tile_x IS NULL AND tile_z IS NULL AND tile_level IS NULL) OR "
    "(tile_x IS NOT NULL AND tile_z IS NOT NULL AND tile_level IS NOT NULL)), "
    "CHECK ((destination_x IS NULL AND destination_z IS NULL AND destination_level IS NULL) OR "
    "(destination_x IS NOT NULL AND destination_z IS NOT NULL AND destination_level IS NOT NULL)), "
    "CHECK ((hp_current IS NULL AND hp_base IS NULL) OR (hp_current IS NOT NULL AND hp_base IS NOT NULL)), "
    "CHECK ((prayer_current IS NULL AND prayer_base IS NULL) OR (prayer_current IS NOT NULL AND prayer_base IS NOT NULL)), "
    "CHECK ((special_attack_energy IS NULL AND special_attack_armed IS NULL) OR "
    "(special_attack_energy IS NOT NULL AND special_attack_armed IS NOT NULL)), "
    "CHECK ((target_kind_id IS NULL AND target_index IS NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
    "(target_kind_id IS NOT NULL AND target_kind_id IN (1, 2) AND target_index IS NOT NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
    "(target_kind_id IS NOT NULL AND target_kind_id = 3 AND target_index IS NULL AND target_x IS NOT NULL AND target_z IS NOT NULL AND target_level IS NOT NULL)))",
    "CREATE TABLE fleet_experience ("
    "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
    "state_id INTEGER NOT NULL REFERENCES fleet_states(id), settled INTEGER NOT NULL CHECK (settled IN (0, 1)))",
    "CREATE TABLE fleet_experience_skills ("
    "record_id INTEGER NOT NULL REFERENCES fleet_experience(record_id) ON DELETE CASCADE, "
    "skill_id INTEGER NOT NULL REFERENCES fleet_skills(id), ordinal INTEGER NOT NULL CHECK (ordinal >= 0), "
    "level INTEGER NOT NULL, base INTEGER NOT NULL, xp INTEGER NOT NULL CHECK (xp >= 0), "
    "PRIMARY KEY (record_id, skill_id), UNIQUE (record_id, ordinal)) WITHOUT ROWID",
    "CREATE TABLE fleet_bank (record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE)",
    "CREATE TABLE fleet_bank_items ("
    "record_id INTEGER NOT NULL REFERENCES fleet_bank(record_id) ON DELETE CASCADE, "
    "item_id INTEGER NOT NULL, name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
    "quantity INTEGER NOT NULL CHECK (quantity > 0), "
    "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID",
    "CREATE TABLE fleet_inventory ("
    "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
    "bank_open INTEGER NOT NULL CHECK (bank_open IN (0, 1)), "
    "used INTEGER NOT NULL CHECK (used >= 0), free INTEGER NOT NULL CHECK (free >= 0))",
    "CREATE TABLE fleet_inventory_items ("
    "record_id INTEGER NOT NULL REFERENCES fleet_inventory(record_id) ON DELETE CASCADE, "
    "item_id INTEGER NOT NULL, name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
    "quantity INTEGER NOT NULL CHECK (quantity > 0), "
    "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID",
    "CREATE TABLE fleet_equipment ("
    "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
    "used INTEGER NOT NULL CHECK (used >= 0))",
    "CREATE TABLE fleet_equipment_items ("
    "record_id INTEGER NOT NULL REFERENCES fleet_equipment(record_id) ON DELETE CASCADE, "
    "item_id INTEGER NOT NULL, name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
    "quantity INTEGER NOT NULL CHECK (quantity > 0), "
    "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID",
)


def connect_readonly(path):
    """Open an existing database without creating it or allowing writes."""
    uri = Path(path).resolve().as_uri() + '?mode=ro'
    connection = sqlite3.connect(uri, uri=True, timeout=0.1)
    try:
        version = connection.execute('PRAGMA user_version').fetchone()[0]
    except sqlite3.Error:
        connection.close()
        raise

    if version != SCHEMA_VERSION:
        connection.close()
        raise sqlite3.DatabaseError(
            f'{path}: unsupported fleet database schema version {version}; expected {SCHEMA_VERSION}')
    return connection


def create_schema(connection):
    """Create a fresh normalized schema and reject databases with an existing schema."""
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    if version == SCHEMA_VERSION:
        return
    if version != 0:
        raise sqlite3.DatabaseError(f'unsupported fleet database schema version {version}; expected {SCHEMA_VERSION}')

    tables = connection.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
    if tables:
        raise sqlite3.DatabaseError('fleet database has an unversioned schema; use a new database file')

    with connection:
        for statement in CREATE_SCHEMA:
            connection.execute(statement)
        connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')


def dictionary_id(connection, table, name, cache=None):
    """Return the shared dictionary ID for a name, creating it if needed."""
    if cache is not None and name in cache:
        return cache[name]

    connection.execute(
        f'INSERT INTO {table} (name) VALUES (?) ON CONFLICT (name) DO NOTHING', (name,))
    row = connection.execute(f'SELECT id FROM {table} WHERE name = ?', (name,)).fetchone()
    if row is None:
        raise sqlite3.DatabaseError(f'could not find fleet dictionary value after insert: {table}')
    name_id = row[0]
    if cache is not None:
        cache[name] = name_id
    return name_id


def item_name_id(connection, name, cache=None):
    """Return the shared dictionary ID for an item name, creating it if needed."""
    return dictionary_id(connection, 'fleet_item_names', name, cache)


def timestamp_to_unix_seconds(text):
    """Parse the fleet UTC timestamp format as whole Unix seconds."""
    value = datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
    if value.strftime('%Y-%m-%dT%H:%M:%SZ') != text:
        raise ValueError(f'invalid fleet timestamp: {text}')
    delta = value - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    return delta.days * 86400 + delta.seconds


def timestamp_from_unix_seconds(value):
    """Format whole Unix seconds as the stable public fleet timestamp."""
    return datetime.datetime.fromtimestamp(value, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
