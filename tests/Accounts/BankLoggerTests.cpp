#include "pch.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/TempFolder.hpp"

#include "Accounts/BankLogger.hpp"
#include "Cache/GameCache_s.hpp"
#include "Console/LogLevel_e.hpp"
#include "Game/State/GameState_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto BANK_ROOT = u16{5292};
    constexpr auto BANK_ITEMS = u16{5382};
    constexpr auto COINS = s32{995};
    constexpr auto BONES = s32{526};

    std::string ReadFile(const std::filesystem::path& path)
    {
        auto file = std::ifstream{path, std::ios::binary};
        return std::string{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
    }

    std::size_t CountLines(std::string_view text)
    {
        return static_cast<std::size_t>(std::ranges::count(text, '\n'));
    }

    // The cache needs a bank component, the interface that holds it, and the two items themselves.
    std::shared_ptr<const GameCache_s> MakeBankCache()
    {
        auto cache = GameCache_s{};
        cache.bankComponent = BANK_ITEMS;
        cache.components[BANK_ROOT] = IfComponent_s{.id = BANK_ROOT, .root = BANK_ROOT, .type = ComponentType_e::Layer};
        cache.components[BANK_ITEMS] = IfComponent_s{.id = BANK_ITEMS, .root = BANK_ROOT, .type = ComponentType_e::Inv};

        // The object list is indexed by id, so every id below the highest needs an entry.
        cache.objs.resize(static_cast<std::size_t>(COINS) + 1);
        cache.objs[COINS] = ObjType_s{.id = COINS, .name = "Coins"};
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
            , log{*cache, capture.GetLogger(), "s18", folder.GetPath() / "bank"}
        {
        }

        [[nodiscard]] std::filesystem::path Records() const { return folder.GetPath() / "bank" / "s18.jsonl"; }
        // The bank as it is now: the last record.
        [[nodiscard]] std::string Latest() const
        {
            auto lines = std::vector<std::string>{};
            auto text = ReadFile(Records());
            auto start = std::size_t{0};
            while (start < text.size())
            {
                const auto end = text.find('\n', start);
                if (end == std::string::npos)
                {
                    break;
                }

                lines.push_back(text.substr(start, end - start));
                start = end + 1;
            }

            return lines.empty() ? std::string{} : lines.back();
        }

        std::shared_ptr<const GameCache_s> cache;
        TempFolder folder;
        LogCapture capture;
        BankLogger log;
    };
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
        CHECK_FALSE(std::filesystem::exists(fixture.folder.GetPath() / "bank" / "s18.json"));
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

    SECTION("staying open records once, and a reopen records again")
    {
        auto fixture = BankFixture{};
        fixture.log.Step(OpenBank({{.id = COINS, .count = 10}}));
        fixture.log.Step(OpenBank({{.id = COINS, .count = 99}}));

        CHECK(CountLines(ReadFile(fixture.Records())) == 1);
        // Still open: a deposit doesn't rewrite the record.
        CHECK(fixture.Latest().find(R"("qty":10)") != std::string::npos);

        auto closed = GameState_s{};
        closed.placed = true;
        fixture.log.Step(closed);
        fixture.log.Step(OpenBank({{.id = COINS, .count = 20}}));

        CHECK(CountLines(ReadFile(fixture.Records())) == 2);
        CHECK(fixture.Latest().find(R"("qty":20)") != std::string::npos);
    }

    SECTION("the same item in two slots is one entry with the count added up")
    {
        auto fixture = BankFixture{};
        fixture.log.Step(OpenBank({{.id = COINS, .count = 10}, {.id = COINS, .count = 5}}));

        CHECK(CountLines(ReadFile(fixture.Records())) == 1);
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
        std::ofstream{fixture.folder.GetPath() / "bank"} << "not a folder";
        auto blocked = BankLogger{*fixture.cache, fixture.capture.GetLogger(), "s18", fixture.folder.GetPath() / "bank"};

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
