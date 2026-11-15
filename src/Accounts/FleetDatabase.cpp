#include "pch.hpp"
#include "FleetDatabase.hpp"

#include <SQLiteCpp/SQLiteCpp.h>
#include <nlohmann/json.hpp>

namespace
{
    constexpr auto SCHEMA_VERSION = 3;
    constexpr auto BUSY_TIMEOUT_MS = 25;

    std::string PathToUtf8(const std::filesystem::path& path)
    {
        const auto text = path.u8string();
        return {reinterpret_cast<const char*>(text.data()), text.size()};
    }

    std::string_view StreamName(FleetStream_e stream)
    {
        switch (stream)
        {
        case FleetStream_e::AccountData:
            return "account-data";
        case FleetStream_e::Experience:
            return "experience";
        case FleetStream_e::Bank:
            return "bank";
        case FleetStream_e::Inventory:
            return "inventory";
        case FleetStream_e::Equipment:
            return "equipment";
        }

        throw std::invalid_argument{"unknown fleet stream"};
    }

    std::string SanitizeUtf8(std::string_view text)
    {
        const auto encoded = nlohmann::json(std::string{text}).dump(-1, ' ', false, nlohmann::json::error_handler_t::replace);
        return nlohmann::json::parse(encoded).get<std::string>();
    }

    s64 InsertRecord(SQLite::Database& database, std::string_view account, FleetStream_e stream, std::string_view time)
    {
        {
            auto statement = SQLite::Statement{database, "INSERT INTO fleet_accounts (name) VALUES (?) ON CONFLICT (name) DO NOTHING"};
            statement.bind(1, std::string{account});
            statement.exec();
        }

        auto accountId = s64{};
        {
            auto statement = SQLite::Statement{database, "SELECT id FROM fleet_accounts WHERE name = ?"};
            statement.bind(1, std::string{account});
            if (!statement.executeStep())
            {
                throw std::runtime_error{"could not find fleet account after insert"};
            }

            accountId = statement.getColumn(0).getInt64();
        }

        auto statement = SQLite::Statement{database, "INSERT INTO fleet_records (account_id, stream, recorded_at) VALUES (?, ?, ?)"};
        statement.bind(1, accountId);
        statement.bind(2, std::string{StreamName(stream)});
        statement.bind(3, std::string{time});
        statement.exec();
        return database.getLastInsertRowid();
    }

    void BindOptionalInteger(SQLite::Statement& statement, int index, const std::optional<s32>& value)
    {
        if (value)
        {
            statement.bind(index, static_cast<s64>(*value));
        }
        else
        {
            statement.bind(index);
        }
    }

    void BindOptionalBool(SQLite::Statement& statement, int index, const std::optional<bool>& value)
    {
        if (value)
        {
            statement.bind(index, static_cast<s32>(*value));
        }
        else
        {
            statement.bind(index);
        }
    }

    void BindTile(SQLite::Statement& statement, int index, const std::optional<FleetLogTile_s>& tile)
    {
        if (tile)
        {
            statement.bind(index, static_cast<s64>(tile->x));
            statement.bind(index + 1, static_cast<s64>(tile->z));
            statement.bind(index + 2, static_cast<s64>(tile->level));
        }
        else
        {
            statement.bind(index);
            statement.bind(index + 1);
            statement.bind(index + 2);
        }
    }

    void BindStat(SQLite::Statement& statement, int index, const std::optional<FleetLogStat_s>& stat)
    {
        if (stat)
        {
            statement.bind(index, static_cast<s64>(stat->current));
            statement.bind(index + 1, static_cast<s64>(stat->base));
        }
        else
        {
            statement.bind(index);
            statement.bind(index + 1);
        }
    }

    void InsertItems(SQLite::Database& database, std::string_view table, s64 recordId, const std::vector<FleetItem_s>& items)
    {
        const auto query = std::format("INSERT INTO {} (record_id, item_id, name, quantity) VALUES (?, ?, ?, ?)", table);
        auto statement = SQLite::Statement{database, query};
        for (const auto& item : items)
        {
            statement.bind(1, recordId);
            statement.bind(2, static_cast<s64>(item.id));
            statement.bind(3, SanitizeUtf8(item.name));
            statement.bind(4, static_cast<s64>(item.qty));
            statement.exec();
            statement.reset();
        }
    }
}

FleetDatabase::FleetDatabase(std::filesystem::path path)
    : m_path{std::move(path)}
{
}

void FleetDatabase::Append(const FleetAccountDataLog_s& record)
{
    EnsureOpen();

    auto transaction = SQLite::Transaction{*m_database};
    const auto recordId = InsertRecord(*m_database, record.account, FleetStream_e::AccountData, record.time);
    auto statement = SQLite::Statement{*m_database,
                                       "INSERT INTO fleet_account_data ("
                                       "record_id, state, settled, pid, tile_x, tile_z, tile_level, destination_x, destination_z, destination_level, "
                                       "target_kind, target_index, target_x, target_z, target_level, hp_current, hp_base, energy, prayer_current, prayer_base, "
                                       "special_attack_energy, special_attack_armed, running, moving, in_combat, weight, tick) "
                                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"};
    statement.bind(1, recordId);
    statement.bind(2, record.state);
    statement.bind(3, static_cast<s32>(record.settled));
    BindOptionalInteger(statement, 4, record.pid);
    BindTile(statement, 5, record.tile);
    BindTile(statement, 8, record.destination);
    if (record.target)
    {
        statement.bind(11, record.target->kind);
        BindOptionalInteger(statement, 12, record.target->index);
        BindTile(statement, 13, record.target->tile);
    }
    else
    {
        statement.bind(11);
        statement.bind(12);
        statement.bind(13);
        statement.bind(14);
        statement.bind(15);
    }

    BindStat(statement, 16, record.hp);
    BindOptionalInteger(statement, 18, record.energy);
    BindStat(statement, 19, record.prayer);
    if (record.specialAttack)
    {
        statement.bind(21, static_cast<s64>(record.specialAttack->energy));
        statement.bind(22, static_cast<s32>(record.specialAttack->armed));
    }
    else
    {
        statement.bind(21);
        statement.bind(22);
    }

    BindOptionalBool(statement, 23, record.running);
    BindOptionalBool(statement, 24, record.moving);
    BindOptionalBool(statement, 25, record.inCombat);
    BindOptionalInteger(statement, 26, record.weight);
    statement.bind(27, static_cast<s64>(record.tick));
    statement.exec();
    transaction.commit();
}

void FleetDatabase::Append(const FleetExperienceLog_s& record)
{
    EnsureOpen();

    auto transaction = SQLite::Transaction{*m_database};
    const auto recordId = InsertRecord(*m_database, record.account, FleetStream_e::Experience, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_experience (record_id, state, settled) VALUES (?, ?, ?)"};
        statement.bind(1, recordId);
        statement.bind(2, record.state);
        statement.bind(3, static_cast<s32>(record.settled));
        statement.exec();
    }

    auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_experience_skills (record_id, skill, ordinal, level, base, xp) VALUES (?, ?, ?, ?, ?, ?)"};
    for (std::size_t i = 0; i < record.skills.size(); ++i)
    {
        const auto& [name, skill] = record.skills[i];
        statement.bind(1, recordId);
        statement.bind(2, name);
        statement.bind(3, static_cast<s64>(i));
        statement.bind(4, static_cast<s32>(skill.level));
        statement.bind(5, static_cast<s32>(skill.base));
        statement.bind(6, static_cast<s64>(skill.xp));
        statement.exec();
        statement.reset();
    }

    transaction.commit();
}

void FleetDatabase::Append(const FleetBankLog_s& record)
{
    EnsureOpen();

    auto transaction = SQLite::Transaction{*m_database};
    const auto recordId = InsertRecord(*m_database, record.account, FleetStream_e::Bank, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_bank (record_id) VALUES (?)"};
        statement.bind(1, recordId);
        statement.exec();
    }

    InsertItems(*m_database, "fleet_bank_items", recordId, record.items);
    transaction.commit();
}

void FleetDatabase::Append(const FleetInventoryLog_s& record)
{
    EnsureOpen();

    auto transaction = SQLite::Transaction{*m_database};
    const auto recordId = InsertRecord(*m_database, record.account, FleetStream_e::Inventory, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_inventory (record_id, bank_open, used, free) VALUES (?, ?, ?, ?)"};
        statement.bind(1, recordId);
        statement.bind(2, static_cast<s32>(record.bankOpen));
        statement.bind(3, static_cast<s64>(record.used));
        statement.bind(4, static_cast<s64>(record.free));
        statement.exec();
    }

    InsertItems(*m_database, "fleet_inventory_items", recordId, record.items);
    transaction.commit();
}

void FleetDatabase::Append(const FleetEquipmentLog_s& record)
{
    EnsureOpen();

    auto transaction = SQLite::Transaction{*m_database};
    const auto recordId = InsertRecord(*m_database, record.account, FleetStream_e::Equipment, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_equipment (record_id, used) VALUES (?, ?)"};
        statement.bind(1, recordId);
        statement.bind(2, static_cast<s64>(record.used));
        statement.exec();
    }

    InsertItems(*m_database, "fleet_equipment_items", recordId, record.items);
    transaction.commit();
}

void FleetDatabase::EnsureOpen()
{
    if (m_database)
    {
        return;
    }

    if (!m_path.parent_path().empty())
    {
        std::filesystem::create_directories(m_path.parent_path());
    }

    auto database = std::make_unique<SQLite::Database>(PathToUtf8(m_path), SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE);
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
        database->exec(
            "CREATE TABLE fleet_records ("
            "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
            "account_id INTEGER NOT NULL REFERENCES fleet_accounts(id), "
            "stream TEXT NOT NULL CHECK (stream IN ('account-data', 'experience', 'bank', 'inventory', 'equipment')), "
            "recorded_at TEXT NOT NULL)");
        database->exec("CREATE INDEX fleet_records_latest ON fleet_records (account_id, stream, sequence DESC)");
        database->exec("CREATE INDEX fleet_records_history ON fleet_records (account_id, stream, recorded_at, sequence)");
        database->exec("CREATE INDEX fleet_records_stream_latest ON fleet_records (stream, account_id, sequence DESC)");
        database->exec(
            "CREATE TABLE fleet_account_data ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "state TEXT NOT NULL, "
            "settled INTEGER NOT NULL CHECK (settled IN (0, 1)), "
            "pid INTEGER, "
            "tile_x INTEGER, tile_z INTEGER, tile_level INTEGER, "
            "destination_x INTEGER, destination_z INTEGER, destination_level INTEGER, "
            "target_kind TEXT, target_index INTEGER, target_x INTEGER, target_z INTEGER, target_level INTEGER, "
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
            "CHECK ((target_kind IS NULL AND target_index IS NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
            "(target_kind IS NOT NULL AND target_kind IN ('npc', 'player') AND target_index IS NOT NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
            "(target_kind IS NOT NULL AND target_kind = 'tile' AND target_index IS NULL AND target_x IS NOT NULL AND target_z IS NOT NULL AND target_level IS NOT NULL)))");
        database->exec(
            "CREATE TABLE fleet_experience ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "state TEXT NOT NULL, "
            "settled INTEGER NOT NULL CHECK (settled IN (0, 1)))");
        database->exec(
            "CREATE TABLE fleet_experience_skills ("
            "record_id INTEGER NOT NULL REFERENCES fleet_experience(record_id) ON DELETE CASCADE, "
            "skill TEXT NOT NULL, "
            "ordinal INTEGER NOT NULL CHECK (ordinal >= 0), "
            "level INTEGER NOT NULL, "
            "base INTEGER NOT NULL, "
            "xp INTEGER NOT NULL CHECK (xp >= 0), "
            "PRIMARY KEY (record_id, skill), "
            "UNIQUE (record_id, ordinal))");
        database->exec(
            "CREATE TABLE fleet_bank ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE)");
        database->exec(
            "CREATE TABLE fleet_bank_items ("
            "record_id INTEGER NOT NULL REFERENCES fleet_bank(record_id) ON DELETE CASCADE, "
            "item_id INTEGER NOT NULL, "
            "name TEXT NOT NULL, "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id))");
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
            "name TEXT NOT NULL, "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id))");
        database->exec(
            "CREATE TABLE fleet_equipment ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "used INTEGER NOT NULL CHECK (used >= 0))");
        database->exec(
            "CREATE TABLE fleet_equipment_items ("
            "record_id INTEGER NOT NULL REFERENCES fleet_equipment(record_id) ON DELETE CASCADE, "
            "item_id INTEGER NOT NULL, "
            "name TEXT NOT NULL, "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id))");
        database->exec(std::format("PRAGMA user_version = {}", SCHEMA_VERSION));
        transaction.commit();
    }

    m_database = std::move(database);
}
