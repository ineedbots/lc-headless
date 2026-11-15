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
        auto database = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
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

    auto reopened = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
    reopened.Append(Record("bot1", "2026-01-01T00:00:00Z", 3));
    auto database = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(database) == 3);
}

TEST_CASE("FleetDatabase rolls back a snapshot when child rows fail", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-rollback"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
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
    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
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
    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
    database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1));

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    auto snapshot = SQLite::Statement{reader, "SELECT sequence FROM fleet_records ORDER BY sequence"};
    REQUIRE(snapshot.executeStep());
    CHECK_NOTHROW(database.Append(Record("bot1", "2026-01-01T00:01:00Z", 2)));

    auto count = SQLite::Statement{reader, "SELECT COUNT(*) FROM fleet_records"};
    REQUIRE(count.executeStep());
    CHECK(count.getColumn(0).getInt64() == 1);
}

TEST_CASE("FleetDatabase batches background writes into fewer commits", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-batch"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Background};
    auto completions = std::vector<std::future<void>>{};

    for (auto i = 0; i < 8; ++i)
    {
        auto completion = database.Enqueue(Record("bot1", std::format("2026-01-01T00:00:0{}Z", i), i));
        REQUIRE(completion);
        completions.push_back(std::move(*completion));
    }

    database.Flush();
    for (auto& completion : completions)
    {
        CHECK_NOTHROW(completion.get());
    }

    CHECK(database.GetCommittedBatchCount() < completions.size());
    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(reader) == completions.size());
}

TEST_CASE("Independent background FleetDatabase writers recover from concurrent SQLite locks", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-concurrent-writers"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    {
        auto seed = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
        seed.Append(Record("seed", "2026-01-01T00:00:00Z", 0));
    }

    constexpr auto WRITER_COUNT = 4;
    constexpr auto RECORDS_PER_WRITER = 16;
    struct Pending_s
    {
        std::size_t writer;
        FleetExperienceLog_s record;
        std::future<void> completion;
    };

    auto writers = std::vector<std::unique_ptr<FleetDatabase>>{};
    for (auto i = 0; i < WRITER_COUNT; ++i)
    {
        writers.push_back(std::make_unique<FleetDatabase>(path, FleetDatabase::Mode_e::Background));
    }

    auto pending = std::vector<Pending_s>{};
    const auto start = Clock::now();
    for (auto writer = std::size_t{}; writer < WRITER_COUNT; ++writer)
    {
        for (auto i = 0; i < RECORDS_PER_WRITER; ++i)
        {
            auto record = Record(std::format("process{}-bot{}", writer, i), std::format("2026-01-01T00:00:{:02}Z", i), static_cast<s32>(i));
            auto completion = writers[writer]->Enqueue(record);
            REQUIRE(completion);
            pending.push_back({writer, std::move(record), std::move(*completion)});
        }
    }

    for (const auto& writer : writers)
    {
        writer->Flush();
    }

    auto failed = std::vector<std::pair<std::size_t, FleetExperienceLog_s>>{};
    for (auto& write : pending)
    {
        try
        {
            write.completion.get();
        }
        catch (const std::exception&)
        {
            failed.emplace_back(write.writer, std::move(write.record));
        }
    }

    for (const auto& [writer, record] : failed)
    {
        CHECK_NOTHROW(writers[writer]->Append(record));
    }

    const auto elapsed = Clock::now() - start;
    INFO(std::format("{} independent writers committed {} account records in {} ms", WRITER_COUNT, WRITER_COUNT * RECORDS_PER_WRITER, std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count()));
    CHECK(elapsed < 5s);

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(reader) == 1 + WRITER_COUNT * RECORDS_PER_WRITER);
}

TEST_CASE("FleetDatabase drains accepted writes when its background worker stops", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-shutdown"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto completions = std::vector<std::future<void>>{};

    {
        auto database = FleetDatabase{path, FleetDatabase::Mode_e::Background};
        for (auto i = 0; i < 8; ++i)
        {
            auto completion = database.Enqueue(Record("bot1", std::format("2026-01-01T00:00:0{}Z", i), i));
            REQUIRE(completion);
            completions.push_back(std::move(*completion));
        }
    }

    for (auto& completion : completions)
    {
        CHECK_NOTHROW(completion.get());
    }

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(reader) == completions.size());
}

TEST_CASE("FleetDatabase background enqueue does not wait on a busy writer", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-background-contention"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Background};
    database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1));

    auto blocker = SQLite::Database{path.string(), SQLite::OPEN_READWRITE};
    blocker.exec("BEGIN IMMEDIATE");
    auto completions = std::vector<std::future<void>>{};
    const auto start = Clock::now();
    for (auto i = 0; i < 32; ++i)
    {
        auto completion = database.Enqueue(Record("bot1", std::format("2026-01-01T00:00:{:02}Z", i), i));
        REQUIRE(completion);
        completions.push_back(std::move(*completion));
    }

    CHECK(Clock::now() - start < 100ms);
    database.Flush();
    for (auto& completion : completions)
    {
        CHECK_THROWS(completion.get());
    }

    blocker.exec("ROLLBACK");
    auto retry = database.Enqueue(Record("bot1", "2026-01-01T00:01:00Z", 33));
    REQUIRE(retry);
    database.Flush();
    CHECK_NOTHROW(retry->get());
}

TEST_CASE("FleetDatabase rejects writes when its bounded queue is full", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-queue-limit"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Background};
    database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1));

    auto blocker = SQLite::Database{path.string(), SQLite::OPEN_READWRITE};
    blocker.exec("BEGIN IMMEDIATE");
    const auto record = Record("bot1", "2026-01-01T00:00:01Z", 2);
    auto completions = std::vector<std::future<void>>{};
    auto rejected = false;
    for (auto i = std::size_t{}; i < FleetDatabase::MAX_PENDING_WRITES + 16; ++i)
    {
        auto completion = database.Enqueue(record);
        if (!completion)
        {
            rejected = true;
            break;
        }

        completions.push_back(std::move(*completion));
    }

    CHECK(rejected);
    CHECK(completions.size() <= FleetDatabase::MAX_PENDING_WRITES);
    database.Flush();
    for (auto& completion : completions)
    {
        CHECK_THROWS(completion.get());
    }

    blocker.exec("ROLLBACK");
}

TEST_CASE("Independent FleetDatabase connections share records by commit sequence", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-shared"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto first = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
    auto second = FleetDatabase{path, FleetDatabase::Mode_e::Inline};

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

    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
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

    auto future = FleetDatabase{futurePath, FleetDatabase::Mode_e::Inline};
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

    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
    CHECK_THROWS_WITH(database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1)), Catch::Matchers::ContainsSubstring("unversioned schema"));
}

TEST_CASE("FleetDatabase enforces optional account data field groups", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-database-field-groups"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Inline};
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
    auto database = FleetDatabase{path, FleetDatabase::Mode_e::Inline};

    CHECK_THROWS(database.Append(Record("bot1", "2026-01-01T00:00:00Z", 1)));
    REQUIRE(std::filesystem::remove(path));
    CHECK_NOTHROW(database.Append(Record("bot1", "2026-01-01T00:01:00Z", 2)));

    auto reader = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    CHECK(RecordCount(reader) == 1);
}
