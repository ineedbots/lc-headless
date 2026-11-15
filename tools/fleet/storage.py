"""SQLite schema and read helpers shared by the fleet page and benchmark."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 3
STREAMS = ('account-data', 'experience', 'bank', 'inventory', 'equipment')

CREATE_SCHEMA = (
    "CREATE TABLE fleet_accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
    "CREATE TABLE fleet_records ("
    "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
    "account_id INTEGER NOT NULL REFERENCES fleet_accounts(id), "
    "stream TEXT NOT NULL CHECK (stream IN ('account-data', 'experience', 'bank', 'inventory', 'equipment')), "
    "recorded_at TEXT NOT NULL)",
    "CREATE INDEX fleet_records_latest ON fleet_records (account_id, stream, sequence DESC)",
    "CREATE INDEX fleet_records_history ON fleet_records (account_id, stream, recorded_at, sequence)",
    "CREATE INDEX fleet_records_stream_latest ON fleet_records (stream, account_id, sequence DESC)",
    "CREATE TABLE fleet_account_data ("
    "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
    "state TEXT NOT NULL, settled INTEGER NOT NULL CHECK (settled IN (0, 1)), pid INTEGER, "
    "tile_x INTEGER, tile_z INTEGER, tile_level INTEGER, "
    "destination_x INTEGER, destination_z INTEGER, destination_level INTEGER, "
    "target_kind TEXT, target_index INTEGER, target_x INTEGER, target_z INTEGER, target_level INTEGER, "
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
    "CHECK ((target_kind IS NULL AND target_index IS NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
    "(target_kind IS NOT NULL AND target_kind IN ('npc', 'player') AND target_index IS NOT NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
    "(target_kind IS NOT NULL AND target_kind = 'tile' AND target_index IS NULL AND target_x IS NOT NULL AND target_z IS NOT NULL AND target_level IS NOT NULL)))",
    "CREATE TABLE fleet_experience ("
    "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
    "state TEXT NOT NULL, settled INTEGER NOT NULL CHECK (settled IN (0, 1)))",
    "CREATE TABLE fleet_experience_skills ("
    "record_id INTEGER NOT NULL REFERENCES fleet_experience(record_id) ON DELETE CASCADE, "
    "skill TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK (ordinal >= 0), "
    "level INTEGER NOT NULL, base INTEGER NOT NULL, xp INTEGER NOT NULL CHECK (xp >= 0), "
    "PRIMARY KEY (record_id, skill), UNIQUE (record_id, ordinal))",
    "CREATE TABLE fleet_bank (record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE)",
    "CREATE TABLE fleet_bank_items ("
    "record_id INTEGER NOT NULL REFERENCES fleet_bank(record_id) ON DELETE CASCADE, "
    "item_id INTEGER NOT NULL, name TEXT NOT NULL, quantity INTEGER NOT NULL CHECK (quantity > 0), "
    "PRIMARY KEY (record_id, item_id))",
    "CREATE TABLE fleet_inventory ("
    "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
    "bank_open INTEGER NOT NULL CHECK (bank_open IN (0, 1)), "
    "used INTEGER NOT NULL CHECK (used >= 0), free INTEGER NOT NULL CHECK (free >= 0))",
    "CREATE TABLE fleet_inventory_items ("
    "record_id INTEGER NOT NULL REFERENCES fleet_inventory(record_id) ON DELETE CASCADE, "
    "item_id INTEGER NOT NULL, name TEXT NOT NULL, quantity INTEGER NOT NULL CHECK (quantity > 0), "
    "PRIMARY KEY (record_id, item_id))",
    "CREATE TABLE fleet_equipment ("
    "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
    "used INTEGER NOT NULL CHECK (used >= 0))",
    "CREATE TABLE fleet_equipment_items ("
    "record_id INTEGER NOT NULL REFERENCES fleet_equipment(record_id) ON DELETE CASCADE, "
    "item_id INTEGER NOT NULL, name TEXT NOT NULL, quantity INTEGER NOT NULL CHECK (quantity > 0), "
    "PRIMARY KEY (record_id, item_id))",
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
