#include "pch.hpp"

#include "../Support/TempFolder.hpp"
#include "Database/FleetRecordStore.hpp"
#include "Database/Type/FleetRecord.hpp"
#include "Accounts/Reporting/Type/FleetExperienceLog_s.hpp"

#include <SQLiteCpp/SQLiteCpp.h>
#include <catch2/catch_test_macros.hpp>

TEST_CASE("Fleet record stores roll back an entire batch and reuse dictionary values after failure", "[FleetDatabase]")
{
    const auto folder = TempFolder{"rs2004-fleet-record-store"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto store = FleetRecordStore{path};
    const auto record = FleetExperienceLog_s{
        .time = "2026-01-01T00:00:00Z",
        .account = "bot1",
        .state = "ingame",
        .settled = true,
        .skills = {{"attack", {.level = 1, .base = 1, .xp = 10}}}};
    auto invalid = record;
    invalid.skills.front().second.xp = -1;

    const auto failedBatch = std::array<FleetRecord, 2>{record, invalid};
    CHECK_THROWS(store.WriteBatch(failedBatch));

    auto database = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    {
        auto count = SQLite::Statement{database, "SELECT COUNT(*) FROM fleet_records"};
        REQUIRE(count.executeStep());
        CHECK(count.getColumn(0).getInt() == 0);
    }

    const auto retry = std::array<FleetRecord, 1>{record};
    CHECK_NOTHROW(store.WriteBatch(retry));

    auto rows = SQLite::Statement{database, "SELECT xp FROM fleet_experience_skills"};
    REQUIRE(rows.executeStep());
    CHECK(rows.getColumn(0).getInt() == 10);
    CHECK_FALSE(rows.executeStep());
}
