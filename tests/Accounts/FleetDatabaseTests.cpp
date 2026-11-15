#include "pch.hpp"

#include "../Support/TempFolder.hpp"
#include "Accounts/FleetDatabase.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    using Clock = std::chrono::steady_clock;

    std::size_t RecordCount(SQLite::Database& database)
    {
        auto statement = SQLite::Statement{database, "SELECT COUNT(*) FROM fleet_records"};
        REQUIRE(statement.executeStep());
        return static_cast<std::size_t>(statement.getColumn(0).getInt64());
    }
}

TEST_CASE("FleetDatabase versions its schema and preserves deterministic insertion order", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    const auto first = R"({"time":"2026-01-01T00:00:00Z","account":"bot1","value":1})"sv;
    const auto second = R"({"time":"2026-01-01T00:00:00Z","account":"bot1","value":2})"sv;

    {
        auto database = FleetDatabase{path};
        database.Append(FleetStream_e::Experience, "bot1", "2026-01-01T00:00:00Z", first);
        database.Append(FleetStream_e::Experience, "bot1", "2026-01-01T00:00:00Z", second);
    }

    {
        auto database = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
        auto version = SQLite::Statement{database, "PRAGMA user_version"};
        REQUIRE(version.executeStep());
        CHECK(version.getColumn(0).getInt() == 2);
        CHECK(RecordCount(database) == 2);

        auto records = SQLite::Statement{database, "SELECT payload FROM fleet_records ORDER BY sequence"};
        REQUIRE(records.executeStep());
        CHECK(records.getColumn(0).getString() == first);
        REQUIRE(records.executeStep());
        CHECK(records.getColumn(0).getString() == second);

        auto indexes = SQLite::Statement{database, "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' AND name LIKE 'fleet_records_%'"};
        REQUIRE(indexes.executeStep());
        CHECK(indexes.getColumn(0).getInt() == 3);
    }

    auto reopened = FleetDatabase{path};
    reopened.Append(FleetStream_e::Inventory, "bot1", "2026-01-01T00:00:00Z", first);
    auto database = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(database) == 3);
}

TEST_CASE("FleetDatabase rolls back failed snapshots and recovers after the cause is removed", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-rollback"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};
    database.Append(FleetStream_e::Bank, "bot1", "2026-01-01T00:00:00Z", R"({"items":[]})");

    auto external = SQLite::Database{path.string(), SQLite::OPEN_READWRITE};
    external.exec(
        "CREATE TRIGGER reject_snapshot BEFORE INSERT ON fleet_records "
        "BEGIN SELECT RAISE(ABORT, 'test rejection'); END");
    CHECK_THROWS(database.Append(FleetStream_e::Bank, "bot1", "2026-01-01T00:01:00Z", R"({"items":[1]})"));
    CHECK(RecordCount(external) == 1);

    external.exec("DROP TRIGGER reject_snapshot");
    database.Append(FleetStream_e::Bank, "bot1", "2026-01-01T00:02:00Z", R"({"items":[]})");
    CHECK(RecordCount(external) == 2);
}

TEST_CASE("FleetDatabase bounds write lock waits and accepts a later retry", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-contention"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};
    database.Append(FleetStream_e::AccountData, "bot1", "2026-01-01T00:00:00Z", R"({"state":"ingame"})");

    auto blocker = SQLite::Database{path.string(), SQLite::OPEN_READWRITE};
    blocker.exec("BEGIN IMMEDIATE");
    const auto start = Clock::now();
    CHECK_THROWS(database.Append(FleetStream_e::AccountData, "bot1", "2026-01-01T00:01:00Z", R"({"state":"logged out"})"));
    CHECK(Clock::now() - start < 1s);
    blocker.exec("ROLLBACK");

    CHECK_NOTHROW(database.Append(FleetStream_e::AccountData, "bot1", "2026-01-01T00:02:00Z", R"({"state":"logged out"})"));
}

TEST_CASE("FleetDatabase writers can commit while a fleet reader holds a WAL snapshot", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-reader"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};
    database.Append(FleetStream_e::Inventory, "bot1", "2026-01-01T00:00:00Z", R"({"items":[]})");

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    auto snapshot = SQLite::Statement{reader, "SELECT payload FROM fleet_records ORDER BY sequence"};
    REQUIRE(snapshot.executeStep());
    CHECK_NOTHROW(database.Append(FleetStream_e::Inventory, "bot1", "2026-01-01T00:01:00Z", R"({"items":[1]})"));

    auto count = SQLite::Statement{reader, "SELECT COUNT(*) FROM fleet_records"};
    REQUIRE(count.executeStep());
    CHECK(count.getColumn(0).getInt64() == 1);
}

TEST_CASE("Independent FleetDatabase connections share records by commit sequence", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-shared"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto first = FleetDatabase{path};
    auto second = FleetDatabase{path};

    first.Append(FleetStream_e::Bank, "bot1", "2026-01-01T00:00:00Z", R"({"items":[1]})");
    second.Append(FleetStream_e::Bank, "bot2", "2026-01-01T00:00:00Z", R"({"items":[2]})");

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    auto records = SQLite::Statement{reader, "SELECT account, payload FROM fleet_records ORDER BY sequence"};
    REQUIRE(records.executeStep());
    CHECK(records.getColumn(0).getString() == "bot1");
    REQUIRE(records.executeStep());
    CHECK(records.getColumn(0).getString() == "bot2");
}

TEST_CASE("FleetDatabase refuses a schema version from a newer client", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-version"};
    const auto path = folder.GetPath() / "future.sqlite";
    {
        auto database = SQLite::Database{path.string(), SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE};
        database.exec("PRAGMA user_version = 99");
    }

    auto database = FleetDatabase{path};
    CHECK_THROWS_WITH(database.Append(FleetStream_e::Experience, "bot1", "2026-01-01T00:00:00Z", R"({})"), Catch::Matchers::ContainsSubstring("newer than supported"));
}

TEST_CASE("FleetDatabase upgrades the prior schema without losing its records", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-upgrade"};
    const auto path = folder.GetPath() / "prior.sqlite";
    {
        auto prior = SQLite::Database{path.string(), SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE};
        prior.exec(
            "CREATE TABLE fleet_records ("
            "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
            "account TEXT NOT NULL, "
            "stream TEXT NOT NULL CHECK (stream IN ('account-data', 'experience', 'bank', 'inventory', 'equipment')), "
            "recorded_at TEXT NOT NULL, "
            "payload TEXT NOT NULL, "
            "source_key TEXT UNIQUE)");
        prior.exec("CREATE INDEX fleet_records_latest ON fleet_records (account, stream, sequence DESC)");
        prior.exec("CREATE INDEX fleet_records_history ON fleet_records (account, stream, recorded_at, sequence)");
        prior.exec("INSERT INTO fleet_records (account, stream, recorded_at, payload) VALUES ('bot1', 'experience', '2026-01-01T00:00:00Z', '{}')");
        prior.exec("PRAGMA user_version = 1");
    }

    auto database = FleetDatabase{path};
    database.Append(FleetStream_e::Experience, "bot1", "2026-01-01T00:01:00Z", R"({"settled":true})");

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    auto version = SQLite::Statement{reader, "PRAGMA user_version"};
    REQUIRE(version.executeStep());
    CHECK(version.getColumn(0).getInt() == 2);
    CHECK(RecordCount(reader) == 2);
}

TEST_CASE("FleetDatabase releases failed initialization and can open a repaired path", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-recovery"};
    folder.WriteFile("fleet.sqlite", "not a database");
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};

    CHECK_THROWS(database.Append(FleetStream_e::Experience, "bot1", "2026-01-01T00:00:00Z", R"({})"));
    REQUIRE(std::filesystem::remove(path));
    CHECK_NOTHROW(database.Append(FleetStream_e::Experience, "bot1", "2026-01-01T00:01:00Z", R"({})"));

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(reader) == 1);
}
