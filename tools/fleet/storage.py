"""SQLite schema and read helpers shared by the fleet page and importer."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2
MIN_READABLE_SCHEMA_VERSION = 1
STREAMS = ('account-data', 'experience', 'bank', 'inventory', 'equipment')

CREATE_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS fleet_records ("
    "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
    "account TEXT NOT NULL, "
    "stream TEXT NOT NULL CHECK (stream IN ('account-data', 'experience', 'bank', 'inventory', 'equipment')), "
    "recorded_at TEXT NOT NULL, "
    "payload TEXT NOT NULL, "
    "source_key TEXT UNIQUE)",
    "CREATE INDEX IF NOT EXISTS fleet_records_latest ON fleet_records (account, stream, sequence DESC)",
    "CREATE INDEX IF NOT EXISTS fleet_records_history ON fleet_records (account, stream, recorded_at, sequence)",
    "CREATE INDEX IF NOT EXISTS fleet_records_stream_latest ON fleet_records (stream, account, sequence DESC)",
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

    if version < MIN_READABLE_SCHEMA_VERSION or version > SCHEMA_VERSION:
        connection.close()
        raise sqlite3.DatabaseError(
            f'{path}: unsupported fleet database schema version {version}; supported versions are '
            f'{MIN_READABLE_SCHEMA_VERSION} to {SCHEMA_VERSION}')
    return connection


def create_schema(connection):
    """Create a new database schema or reject a database from a newer client."""
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    if version > SCHEMA_VERSION:
        raise sqlite3.DatabaseError(
            f'fleet database schema version {version} is newer than supported version {SCHEMA_VERSION}')
    if version == SCHEMA_VERSION:
        return

    with connection:
        for statement in CREATE_SCHEMA:
            connection.execute(statement)
        connection.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
