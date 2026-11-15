#include "pch.hpp"
#include "FleetDatabase.hpp"

#include <SQLiteCpp/SQLiteCpp.h>

namespace
{
    constexpr auto SCHEMA_VERSION = 2;
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
}

FleetDatabase::FleetDatabase(std::filesystem::path path)
    : m_path{std::move(path)}
{
}

void FleetDatabase::Append(FleetStream_e stream, std::string_view account, std::string_view time, std::string_view payload)
{
    EnsureOpen();

    auto transaction = SQLite::Transaction{*m_database};
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_records (account, stream, recorded_at, payload) VALUES (?, ?, ?, ?)"};
        statement.bind(1, std::string{account});
        statement.bind(2, std::string{StreamName(stream)});
        statement.bind(3, std::string{time});
        statement.bind(4, std::string{payload});
        statement.exec();
    }

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

    database->exec("PRAGMA journal_mode = WAL");
    database->exec("PRAGMA synchronous = NORMAL");
    database->exec("PRAGMA wal_autocheckpoint = 1000");

    if (version == 0)
    {
        auto transaction = SQLite::Transaction{*database};
        database->exec(
            "CREATE TABLE IF NOT EXISTS fleet_records ("
            "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
            "account TEXT NOT NULL, "
            "stream TEXT NOT NULL CHECK (stream IN ('account-data', 'experience', 'bank', 'inventory', 'equipment')), "
            "recorded_at TEXT NOT NULL, "
            "payload TEXT NOT NULL, "
            "source_key TEXT UNIQUE)");
        database->exec("CREATE INDEX IF NOT EXISTS fleet_records_latest ON fleet_records (account, stream, sequence DESC)");
        database->exec("CREATE INDEX IF NOT EXISTS fleet_records_history ON fleet_records (account, stream, recorded_at, sequence)");
        database->exec("PRAGMA user_version = 1");
        transaction.commit();
        version = 1;
    }

    if (version == 1)
    {
        auto transaction = SQLite::Transaction{*database};
        database->exec("CREATE INDEX IF NOT EXISTS fleet_records_stream_latest ON fleet_records (stream, account, sequence DESC)");
        database->exec(std::format("PRAGMA user_version = {}", SCHEMA_VERSION));
        transaction.commit();
    }

    m_database = std::move(database);
}
