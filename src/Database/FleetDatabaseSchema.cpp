#include "pch.hpp"
#include "FleetDatabaseSchema.hpp"

#include <SQLiteCpp/SQLiteCpp.h>

namespace
{
    constexpr auto SCHEMA_VERSION = 5;
    constexpr auto BUSY_TIMEOUT_MS = 25;

    std::string PathToUtf8(const std::filesystem::path& path)
    {
        const auto text = path.u8string();
        return {reinterpret_cast<const char*>(text.data()), text.size()};
    }
}

std::unique_ptr<SQLite::Database> FleetDatabaseSchema::Open(const std::filesystem::path& path)
{
    if (!path.parent_path().empty())
    {
        std::filesystem::create_directories(path.parent_path());
    }

    auto database = std::make_unique<SQLite::Database>(PathToUtf8(path), SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE);
    database->exec(std::format("PRAGMA busy_timeout = {}", BUSY_TIMEOUT_MS));
    database->exec("PRAGMA foreign_keys = ON");

    auto version = 0;
    {
        auto versionStatement = SQLite::Statement{*database, "PRAGMA user_version"};
        if (!versionStatement.executeStep())
        {
            throw std::runtime_error{"could not read fleet database schema version"};
        }

        version = versionStatement.getColumn(0).getInt();
    }

    if (version > SCHEMA_VERSION)
    {
        throw std::runtime_error{std::format("fleet database schema version {} is newer than supported version {}", version, SCHEMA_VERSION)};
    }

    if (version != 0 && version != SCHEMA_VERSION)
    {
        throw std::runtime_error{std::format("fleet database schema version {} is unsupported; use a new database file", version)};
    }

    if (version == 0)
    {
        auto tables = SQLite::Statement{*database, "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"};
        if (!tables.executeStep())
        {
            throw std::runtime_error{"could not inspect fleet database schema"};
        }

        if (tables.getColumn(0).getInt() != 0)
        {
            throw std::runtime_error{"fleet database has an unversioned schema; use a new database file"};
        }
    }

    database->exec("PRAGMA journal_mode = WAL");
    database->exec("PRAGMA synchronous = NORMAL");
    database->exec("PRAGMA wal_autocheckpoint = 1000");

    if (version == 0)
    {
        auto transaction = SQLite::Transaction{*database};
        database->exec(
            "CREATE TABLE fleet_accounts ("
            "id INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL UNIQUE)");
        database->exec("CREATE TABLE fleet_streams (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec(
            "CREATE TABLE fleet_records ("
            "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
            "account_id INTEGER NOT NULL REFERENCES fleet_accounts(id), "
            "stream_id INTEGER NOT NULL REFERENCES fleet_streams(id), "
            "recorded_at INTEGER NOT NULL)");
        database->exec("CREATE INDEX fleet_records_latest ON fleet_records (account_id, stream_id, sequence DESC)");
        database->exec("CREATE INDEX fleet_records_history ON fleet_records (account_id, stream_id, recorded_at, sequence)");
        database->exec("CREATE INDEX fleet_records_stream_latest ON fleet_records (stream_id, account_id, sequence DESC)");
        database->exec("CREATE TABLE fleet_item_names (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec("CREATE TABLE fleet_states (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec("CREATE TABLE fleet_target_kinds (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec("INSERT INTO fleet_target_kinds (id, name) VALUES (1, 'npc'), (2, 'player'), (3, 'tile')");
        database->exec("CREATE TABLE fleet_skills (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec(
            "CREATE TABLE fleet_account_data ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "state_id INTEGER NOT NULL REFERENCES fleet_states(id), "
            "settled INTEGER NOT NULL CHECK (settled IN (0, 1)), "
            "pid INTEGER, "
            "tile_x INTEGER, tile_z INTEGER, tile_level INTEGER, "
            "destination_x INTEGER, destination_z INTEGER, destination_level INTEGER, "
            "target_kind_id INTEGER REFERENCES fleet_target_kinds(id), target_index INTEGER, target_x INTEGER, target_z INTEGER, target_level INTEGER, "
            "hp_current INTEGER, hp_base INTEGER, "
            "energy INTEGER CHECK (energy BETWEEN 0 AND 100), "
            "prayer_current INTEGER, prayer_base INTEGER, "
            "special_attack_energy INTEGER CHECK (special_attack_energy BETWEEN 0 AND 1000), "
            "special_attack_armed INTEGER CHECK (special_attack_armed IN (0, 1)), "
            "running INTEGER CHECK (running IN (0, 1)), "
            "moving INTEGER CHECK (moving IN (0, 1)), "
            "in_combat INTEGER CHECK (in_combat IN (0, 1)), "
            "weight INTEGER, "
            "tick INTEGER NOT NULL CHECK (tick >= 0), "
            "CHECK ((tile_x IS NULL AND tile_z IS NULL AND tile_level IS NULL) OR (tile_x IS NOT NULL AND tile_z IS NOT NULL AND tile_level IS NOT NULL)), "
            "CHECK ((destination_x IS NULL AND destination_z IS NULL AND destination_level IS NULL) OR (destination_x IS NOT NULL AND destination_z IS NOT NULL AND destination_level IS NOT NULL)), "
            "CHECK ((hp_current IS NULL AND hp_base IS NULL) OR (hp_current IS NOT NULL AND hp_base IS NOT NULL)), "
            "CHECK ((prayer_current IS NULL AND prayer_base IS NULL) OR (prayer_current IS NOT NULL AND prayer_base IS NOT NULL)), "
            "CHECK ((special_attack_energy IS NULL AND special_attack_armed IS NULL) OR "
            "(special_attack_energy IS NOT NULL AND special_attack_armed IS NOT NULL)), "
            "CHECK ((target_kind_id IS NULL AND target_index IS NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
            "(target_kind_id IS NOT NULL AND target_kind_id IN (1, 2) AND target_index IS NOT NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
            "(target_kind_id IS NOT NULL AND target_kind_id = 3 AND target_index IS NULL AND target_x IS NOT NULL AND target_z IS NOT NULL AND target_level IS NOT NULL)))");
        database->exec(
            "CREATE TABLE fleet_experience ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "state_id INTEGER NOT NULL REFERENCES fleet_states(id), "
            "settled INTEGER NOT NULL CHECK (settled IN (0, 1)))");
        database->exec(
            "CREATE TABLE fleet_experience_skills ("
            "record_id INTEGER NOT NULL REFERENCES fleet_experience(record_id) ON DELETE CASCADE, "
            "skill_id INTEGER NOT NULL REFERENCES fleet_skills(id), "
            "ordinal INTEGER NOT NULL CHECK (ordinal >= 0), "
            "level INTEGER NOT NULL, "
            "base INTEGER NOT NULL, "
            "xp INTEGER NOT NULL CHECK (xp >= 0), "
            "PRIMARY KEY (record_id, skill_id), "
            "UNIQUE (record_id, ordinal)) WITHOUT ROWID");
        database->exec(
            "CREATE TABLE fleet_bank ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE)");
        database->exec(
            "CREATE TABLE fleet_bank_items ("
            "record_id INTEGER NOT NULL REFERENCES fleet_bank(record_id) ON DELETE CASCADE, "
            "item_id INTEGER NOT NULL, "
            "name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID");
        database->exec(
            "CREATE TABLE fleet_inventory ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "bank_open INTEGER NOT NULL CHECK (bank_open IN (0, 1)), "
            "used INTEGER NOT NULL CHECK (used >= 0), "
            "free INTEGER NOT NULL CHECK (free >= 0))");
        database->exec(
            "CREATE TABLE fleet_inventory_items ("
            "record_id INTEGER NOT NULL REFERENCES fleet_inventory(record_id) ON DELETE CASCADE, "
            "item_id INTEGER NOT NULL, "
            "name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID");
        database->exec(
            "CREATE TABLE fleet_equipment ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "used INTEGER NOT NULL CHECK (used >= 0))");
        database->exec(
            "CREATE TABLE fleet_equipment_items ("
            "record_id INTEGER NOT NULL REFERENCES fleet_equipment(record_id) ON DELETE CASCADE, "
            "item_id INTEGER NOT NULL, "
            "name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID");
        database->exec(std::format("PRAGMA user_version = {}", SCHEMA_VERSION));
        transaction.commit();
    }

    return database;
}
