#include "pch.hpp"

#include "../Support/TempFolder.hpp"
#include "Accounts/FleetDatabase.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    using Clock = std::chrono::steady_clock;

    FleetExperienceLog_s Record(std::string account, std::string time, s32 xp)
    {
        return {
            .time = std::move(time),
            .account = std::move(account),
            .state = "ingame",
            .settled = true,
            .skills = {{"attack", {.level = 1, .base = 1, .xp = xp}}}};
    }

    std::size_t RecordCount(SQLite::Database& database)
    {
        auto statement = SQLite::Statement{database, "SELECT COUNT(*) FROM fleet_records"};
        REQUIRE(statement.executeStep());
        return static_cast<std::size_t>(statement.getColumn(0).getInt64());
    }
}

TEST_CASE("FleetDatabase creates typed stream tables and preserves insertion order", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database"};
    const auto path = folder.GetPath() / "fleet.sqlite";

    {
        auto database = FleetDatabase{path};
        database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1));
        database.Append(Record("bot1", "2026-01-01T00:00:00Z", 2));
    }

    {
        auto database = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
        auto version = SQLite::Statement{database, "PRAGMA user_version"};
        REQUIRE(version.executeStep());
        CHECK(version.getColumn(0).getInt() == 3);
        CHECK(RecordCount(database) == 2);

        auto columns = SQLite::Statement{database, "PRAGMA table_info(fleet_records)"};
        auto hasPayload = false;
        while (columns.executeStep())
        {
            hasPayload = hasPayload || columns.getColumn(1).getString() == "payload";
        }

        CHECK_FALSE(hasPayload);
        auto rows = SQLite::Statement{database,
                                      "SELECT records.sequence, accounts.name, skills.xp FROM fleet_records AS records "
                                      "JOIN fleet_accounts AS accounts ON accounts.id = records.account_id "
                                      "JOIN fleet_experience_skills AS skills ON skills.record_id = records.sequence "
                                      "ORDER BY records.sequence"};
        REQUIRE(rows.executeStep());
        CHECK(rows.getColumn(0).getInt64() == 1);
        CHECK(rows.getColumn(1).getString() == "bot1");
        CHECK(rows.getColumn(2).getInt() == 1);
        REQUIRE(rows.executeStep());
        CHECK(rows.getColumn(0).getInt64() == 2);
        CHECK(rows.getColumn(2).getInt() == 2);
    }

    auto reopened = FleetDatabase{path};
    reopened.Append(Record("bot1", "2026-01-01T00:00:00Z", 3));
    auto database = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(database) == 3);
}

TEST_CASE("FleetDatabase rolls back a snapshot when child rows fail", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-rollback"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};
    database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1));

    auto external = SQLite::Database{path.string(), SQLite::OPEN_READWRITE};
    external.exec(
        "CREATE TRIGGER reject_skill BEFORE INSERT ON fleet_experience_skills "
        "BEGIN SELECT RAISE(ABORT, 'test rejection'); END");
    CHECK_THROWS(database.Append(Record("bot2", "2026-01-01T00:01:00Z", 2)));
    CHECK(RecordCount(external) == 1);

    {
        auto accounts = SQLite::Statement{external, "SELECT COUNT(*) FROM fleet_accounts"};
        REQUIRE(accounts.executeStep());
        CHECK(accounts.getColumn(0).getInt() == 1);
    }

    external.exec("DROP TRIGGER reject_skill");
    database.Append(Record("bot2", "2026-01-01T00:02:00Z", 3));
    CHECK(RecordCount(external) == 2);
}

TEST_CASE("FleetDatabase bounds write lock waits and accepts a later retry", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-contention"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};
    database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1));

    auto blocker = SQLite::Database{path.string(), SQLite::OPEN_READWRITE};
    blocker.exec("BEGIN IMMEDIATE");
    const auto start = Clock::now();
    CHECK_THROWS(database.Append(Record("bot1", "2026-01-01T00:01:00Z", 2)));
    CHECK(Clock::now() - start < 1s);
    blocker.exec("ROLLBACK");

    CHECK_NOTHROW(database.Append(Record("bot1", "2026-01-01T00:02:00Z", 3)));
}

TEST_CASE("FleetDatabase writers can commit while a fleet reader holds a WAL snapshot", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-reader"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};
    database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1));

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    auto snapshot = SQLite::Statement{reader, "SELECT sequence FROM fleet_records ORDER BY sequence"};
    REQUIRE(snapshot.executeStep());
    CHECK_NOTHROW(database.Append(Record("bot1", "2026-01-01T00:01:00Z", 2)));

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

    first.Append(Record("bot1", "2026-01-01T00:00:00Z", 1));
    second.Append(Record("bot2", "2026-01-01T00:00:00Z", 2));

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    auto records = SQLite::Statement{reader,
                                     "SELECT accounts.name, skills.xp FROM fleet_records AS records "
                                     "JOIN fleet_accounts AS accounts ON accounts.id = records.account_id "
                                     "JOIN fleet_experience_skills AS skills ON skills.record_id = records.sequence "
                                     "ORDER BY records.sequence"};
    REQUIRE(records.executeStep());
    CHECK(records.getColumn(0).getString() == "bot1");
    CHECK(records.getColumn(1).getInt() == 1);
    REQUIRE(records.executeStep());
    CHECK(records.getColumn(0).getString() == "bot2");
    CHECK(records.getColumn(1).getInt() == 2);
}

TEST_CASE("FleetDatabase rejects existing generic and newer schemas without changing them", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-version"};
    const auto path = folder.GetPath() / "prior.sqlite";
    {
        auto prior = SQLite::Database{path.string(), SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE};
        prior.exec("CREATE TABLE fleet_records (sequence INTEGER PRIMARY KEY, payload TEXT NOT NULL)");
        prior.exec("INSERT INTO fleet_records VALUES (1, 'keep me')");
        prior.exec("PRAGMA user_version = 2");
    }

    auto database = FleetDatabase{path};
    CHECK_THROWS_WITH(database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1)), Catch::Matchers::ContainsSubstring("unsupported"));
    {
        auto prior = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
        auto payload = SQLite::Statement{prior, "SELECT payload FROM fleet_records"};
        REQUIRE(payload.executeStep());
        CHECK(payload.getColumn(0).getString() == "keep me");
    }

    const auto futurePath = folder.GetPath() / "future.sqlite";
    {
        auto future = SQLite::Database{futurePath.string(), SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE};
        future.exec("PRAGMA user_version = 99");
    }

    auto future = FleetDatabase{futurePath};
    CHECK_THROWS_WITH(
        future.Append(Record("bot1", "2026-01-01T00:00:00Z", 1)),
        Catch::Matchers::ContainsSubstring("newer than supported"));
}

TEST_CASE("FleetDatabase refuses an unversioned schema", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-unversioned"};
    const auto path = folder.GetPath() / "unversioned.sqlite";
    {
        auto database = SQLite::Database{path.string(), SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE};
        database.exec("CREATE TABLE retained (value TEXT)");
    }

    auto database = FleetDatabase{path};
    CHECK_THROWS_WITH(database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1)), Catch::Matchers::ContainsSubstring("unversioned schema"));
}

TEST_CASE("FleetDatabase enforces optional account data field groups", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-field-groups"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};
    database.Append(FleetAccountDataLog_s{
        .time = "2026-01-01T00:00:00Z",
        .account = "bot1",
        .state = "ingame"});

    auto external = SQLite::Database{path.string(), SQLite::OPEN_READWRITE};
    CHECK_THROWS(external.exec("UPDATE fleet_account_data SET target_index = 1"));
    CHECK_THROWS(external.exec("UPDATE fleet_account_data SET special_attack_energy = 50"));
}

TEST_CASE("FleetDatabase releases failed initialization and can open a repaired path", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-recovery"};
    folder.WriteFile("fleet.sqlite", "not a database");
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path};

    CHECK_THROWS(database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1)));
    REQUIRE(std::filesystem::remove(path));
    CHECK_NOTHROW(database.Append(Record("bot1", "2026-01-01T00:01:00Z", 2)));

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(reader) == 1);
}
