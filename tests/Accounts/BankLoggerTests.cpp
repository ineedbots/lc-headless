#include "pch.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/TempFolder.hpp"
#include "../Support/FleetDatabaseReader.hpp"

#include "Accounts/BankLogger.hpp"
#include "Cache/Type/GameCache_s.hpp"
#include "Console/Type/LogLevel_e.hpp"
#include "Game/State/Type/GameState_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    constexpr auto BANK_ROOT = u16{5292};
    constexpr auto BANK_ITEMS = u16{5382};
    constexpr auto COINS = s32{995};
    constexpr auto BONES = s32{526};

    std::size_t CountRecords(const std::filesystem::path& path, std::string_view account = "s18")
    {
        return ReadFleetRecords(path, "bank", account).size();
    }

    // The cache needs a bank component, the interface that holds it, and the two items themselves.
    std::shared_ptr<const GameCache_s> MakeBankCache(std::string_view coinName = "Coins")
    {
        auto cache = GameCache_s{};
        cache.bankComponent = BANK_ITEMS;
        cache.components[BANK_ROOT] = IfComponent_s{.id = BANK_ROOT, .root = BANK_ROOT, .type = ComponentType_e::Layer};
        cache.components[BANK_ITEMS] = IfComponent_s{.id = BANK_ITEMS, .root = BANK_ROOT, .type = ComponentType_e::Inv};

        // The object list is indexed by id, so every id below the highest needs an entry.
        cache.objs.resize(static_cast<std::size_t>(COINS) + 1);
        cache.objs[COINS] = ObjType_s{.id = COINS, .name = coinName};
        cache.objs[BONES] = ObjType_s{.id = BONES, .name = "Bones"};
        return std::make_shared<const GameCache_s>(std::move(cache));
    }

    GameState_s OpenBank(std::vector<Item_s> items)
    {
        auto state = GameState_s{};
        state.placed = true;
        state.interfaces.mainModal = BANK_ROOT;
        state.inventories[BANK_ITEMS] = Inventory_s{.com = BANK_ITEMS, .slots = std::move(items)};
        return state;
    }

    struct BankFixture
    {
        BankFixture()
            : cache{MakeBankCache()}
            , folder{"rs2004-bank-logger-tests"}
            , database{std::make_shared<FleetDatabase>(folder.GetPath() / "fleet.sqlite", FleetDatabase::Mode_e::Inline)}
            , log{*cache, capture.GetLogger(), "s18", database}
        {
        }

        [[nodiscard]] std::filesystem::path Records() const
        {
            return database->GetPath();
        }
        // The bank as it is now: the last record.
        [[nodiscard]] std::string Latest() const
        {
            const auto records = ReadFleetPayloads(Records(), "bank", "s18");
            return records.empty() ? std::string{} : records.back();
        }

        std::shared_ptr<const GameCache_s> cache;
        TempFolder folder;
        std::shared_ptr<FleetDatabase> database;
        LogCapture capture;
        BankLogger log;
    };
}

TEST_CASE("BankLogger writes escaped item names as one valid JSON line", "[BankLogger]")
{
    auto name = std::string{"Coins \"\\\xc3\xa9"};
    for (auto value = 0; value < 32; ++value)
    {
        name += static_cast<char>(value);
    }

    name += '\xff';
    const auto cache = MakeBankCache(name);
    const auto folder = TempFolder{"rs2004-bank-json-tests"};
    auto capture = LogCapture{};
    const auto databasePath = folder.GetPath() / "fleet.sqlite";
    auto log = BankLogger{*cache, capture.GetLogger(), "test", std::make_shared<FleetDatabase>(databasePath, FleetDatabase::Mode_e::Inline)};
    log.Step(OpenBank({{.id = COINS, .count = 2}, {.id = COINS, .count = 3}}));

    const auto records = ReadFleetPayloads(databasePath, "bank", "test");
    REQUIRE(records.size() == 1);

    const auto record = nlohmann::json::parse(records.front());
    CHECK(record.size() == 3);
    CHECK(record["account"] == "test");
    CHECK(record["items"] == nlohmann::json::array({{{"id", COINS}, {"name", name.substr(0, name.size() - 1) + "\xef\xbf\xbd"}, {"qty", 5}}}));
}

TEST_CASE("BankLogger writes the bank's contents each time one opens", "[BankLogger]")
{
    SECTION("nothing is written before a bank opens")
    {
        auto fixture = BankFixture{};
        auto state = GameState_s{};
        state.placed = true;
        fixture.log.Step(state);

        CHECK_FALSE(std::filesystem::exists(fixture.Records()));
    }

    SECTION("each item is written with its id, name and count, and empty slots are left out")
    {
        auto fixture = BankFixture{};
        fixture.log.Step(OpenBank({{.id = COINS, .count = 1234}, {.id = BONES, .count = 5}, {.id = -1, .count = 0}}));

        const auto latest = fixture.Latest();
        CHECK(latest.find(R"("account":"s18")") != std::string::npos);
        CHECK(latest.find(R"({"id":995,"name":"Coins","qty":1234})") != std::string::npos);
        CHECK(latest.find(R"({"id":526,"name":"Bones","qty":5})") != std::string::npos);
        CHECK(latest.find(R"("id":-1)") == std::string::npos);
    }

    SECTION("waits for the bank inventory after the bank opens")
    {
        auto fixture = BankFixture{};
        auto state = GameState_s{};
        state.placed = true;
        state.interfaces.mainModal = BANK_ROOT;
        fixture.log.Step(state);
        CHECK_FALSE(std::filesystem::exists(fixture.Records()));

        state.inventories[BANK_ITEMS] = Inventory_s{.com = BANK_ITEMS, .slots = {{.id = COINS, .count = 7}}};
        fixture.log.Step(state);

        CHECK(CountRecords(fixture.Records()) == 1);
        CHECK(fixture.Latest().find(R"("qty":7)") != std::string::npos);
    }

    SECTION("staying open records once, and a reopen records again")
    {
        auto fixture = BankFixture{};
        fixture.log.Step(OpenBank({{.id = COINS, .count = 10}}));
        fixture.log.Step(OpenBank({{.id = COINS, .count = 99}}));

        CHECK(CountRecords(fixture.Records()) == 1);
        // Still open: a deposit doesn't rewrite the record.
        CHECK(fixture.Latest().find(R"("qty":10)") != std::string::npos);

        auto closed = GameState_s{};
        closed.placed = true;
        fixture.log.Step(closed);
        fixture.log.Step(OpenBank({{.id = COINS, .count = 20}}));

        CHECK(CountRecords(fixture.Records()) == 2);
        CHECK(fixture.Latest().find(R"("qty":20)") != std::string::npos);
    }

    SECTION("the same item in two slots is one entry with the count added up")
    {
        auto fixture = BankFixture{};
        fixture.log.Step(OpenBank({{.id = COINS, .count = 10}, {.id = COINS, .count = 5}}));

        CHECK(CountRecords(fixture.Records()) == 1);
        CHECK(fixture.Latest().find(R"({"id":995,"name":"Coins","qty":15})") != std::string::npos);
        CHECK(fixture.Latest().find(R"("qty":10)") == std::string::npos);
    }

    SECTION("an empty bank is recorded as an empty list")
    {
        auto fixture = BankFixture{};
        fixture.log.Step(OpenBank({}));
        CHECK(fixture.Latest().find(R"("items":[])") != std::string::npos);
    }

    SECTION("the main modal has to be the bank's root")
    {
        auto fixture = BankFixture{};
        auto state = OpenBank({{.id = COINS, .count = 3}});
        state.interfaces.mainModal = 1234;
        fixture.log.Step(state);

        CHECK_FALSE(std::filesystem::exists(fixture.Records()));
    }

    SECTION("the log line names the contents")
    {
        auto fixture = BankFixture{};
        fixture.log.Step(OpenBank({{.id = COINS, .count = 1234}, {.id = BONES, .count = 5}}));
        CHECK(std::ranges::any_of(fixture.capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Info && entry.message == "Bank (open): Bones x5, Coins x1234";
        }));
    }

    SECTION("a folder that can't be written warns once, and never throws")
    {
        auto fixture = BankFixture{};
        // A file where the folder should be.
        const auto blockedPath = fixture.folder.GetPath() / "blocked.sqlite";
        std::ofstream{blockedPath} << "not a database";
        auto blocked = BankLogger{*fixture.cache, fixture.capture.GetLogger(), "s18", std::make_shared<FleetDatabase>(blockedPath, FleetDatabase::Mode_e::Inline)};

        CHECK_NOTHROW(blocked.Step(OpenBank({{.id = COINS, .count = 1}})));
        auto closed = GameState_s{};
        closed.placed = true;
        blocked.Step(closed);
        CHECK_NOTHROW(blocked.Step(OpenBank({{.id = COINS, .count = 2}})));

        const auto warnings = std::ranges::count_if(fixture.capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Warning && entry.message.find("bank wasn't saved") != std::string::npos;
        });
        CHECK(warnings == 1);
    }
}

TEST_CASE("BankLogger preserves each open snapshot while a write is pending", "[BankLogger]")
{
    const auto folder = TempFolder{"rs2004-bank-pending-snapshots"};
    const auto path = folder.GetPath() / "fleet.sqlite";
    auto database = std::make_shared<FleetDatabase>(path, FleetDatabase::Mode_e::Background);
    database->Append(FleetBankLog_s{
        .time = "2026-01-01T00:00:00Z",
        .account = "init"});

    auto blocker = SQLite::Database{path.string(), SQLite::OPEN_READWRITE};
    blocker.exec("BEGIN IMMEDIATE");
    const auto cache = MakeBankCache();
    auto capture = LogCapture{};
    auto log = BankLogger{*cache, capture.GetLogger(), "s18", database};
    log.Step(OpenBank({{.id = COINS, .count = 10}}));

    auto closed = GameState_s{};
    closed.placed = true;
    log.Step(closed);
    log.Step(OpenBank({{.id = COINS, .count = 20}}));
    log.Step(closed);
    blocker.exec("ROLLBACK");
    log.Flush();

    const auto records = ReadFleetPayloads(path, "bank", "s18");
    REQUIRE(records.size() == 2);
    CHECK(nlohmann::json::parse(records[0])["items"][0]["qty"] == 10);
    CHECK(nlohmann::json::parse(records[1])["items"][0]["qty"] == 20);
}
