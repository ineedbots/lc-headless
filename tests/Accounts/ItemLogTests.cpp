#include "pch.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/TempFolder.hpp"

#include "Accounts/ItemLog.hpp"
#include "Cache/GameCache_s.hpp"
#include "Console/LogLevel_e.hpp"
#include "Game/State/GameState_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = ItemLog::Clock;

    constexpr auto BACKPACK = u16{3214};
    constexpr auto BANK_BACKPACK = u16{5382};
    constexpr auto EQUIPMENT = u16{1688};
    constexpr auto BANK_ROOT = u16{5292};
    constexpr auto COINS = s32{995};
    constexpr auto CAKE = s32{1891};
    constexpr auto PLATEBODY = s32{1127};

    std::vector<std::string> ReadLines(const std::filesystem::path& path)
    {
        auto lines = std::vector<std::string>{};
        auto file = std::ifstream{path, std::ios::binary};
        auto text = std::string{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
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

        return lines;
    }

    std::shared_ptr<const GameCache_s> MakeCache()
    {
        auto cache = GameCache_s{};
        cache.inventoryComponent = BACKPACK;
        cache.bankInventoryComponent = BANK_BACKPACK;
        cache.equipmentComponent = EQUIPMENT;
        cache.bankComponent = BANK_BACKPACK;
        cache.inventorySize = 28;
        cache.components[BANK_ROOT] = IfComponent_s{.id = BANK_ROOT, .root = BANK_ROOT, .type = ComponentType_e::Layer};
        cache.components[BANK_BACKPACK] = IfComponent_s{.id = BANK_BACKPACK, .root = BANK_ROOT, .type = ComponentType_e::Inv};
        cache.objs.resize(static_cast<std::size_t>(CAKE) + 1);
        cache.objs[COINS] = ObjType_s{.id = COINS, .name = "Coins"};
        cache.objs[CAKE] = ObjType_s{.id = CAKE, .name = "Cake"};
        cache.objs[PLATEBODY] = ObjType_s{.id = PLATEBODY, .name = "Iron platebody"};
        return std::make_shared<const GameCache_s>(std::move(cache));
    }

    std::vector<Item_s> Slots(std::vector<Item_s> items, std::size_t size)
    {
        items.resize(size, Item_s{.id = -1, .count = 0});
        return items;
    }

    GameState_s WithBackpack(std::vector<Item_s> items)
    {
        auto state = GameState_s{};
        state.placed = true;
        state.inventories[BACKPACK] = Inventory_s{.com = BACKPACK, .slots = Slots(std::move(items), 28), .tick = 1};
        return state;
    }

    GameState_s WithEquipment(std::vector<Item_s> items)
    {
        auto state = GameState_s{};
        state.placed = true;
        state.inventories[EQUIPMENT] = Inventory_s{.com = EQUIPMENT, .slots = Slots(std::move(items), 11), .tick = 1};
        return state;
    }

    struct ItemFixture
    {
        explicit ItemFixture(ItemLog::Kind_e kind = ItemLog::Kind_e::Backpack, std::chrono::seconds interval = 5s)
            : cache{MakeCache()}
            , folder{"rs2004-item-log-tests"}
            , log{*cache, capture.GetLogger(), "s18", folder.GetPath() / (kind == ItemLog::Kind_e::Backpack ? "inventory" : "equipment"), kind, interval}
        {
        }

        [[nodiscard]] std::filesystem::path Path() const { return log.GetPath(); }
        [[nodiscard]] std::vector<std::string> Lines() const { return ReadLines(Path()); }

        std::shared_ptr<const GameCache_s> cache;
        TempFolder folder;
        LogCapture capture;
        ItemLog log;
    };
}

TEST_CASE("ItemLog groups a backpack by item and records what changed", "[ItemLog]")
{
    SECTION("the first step groups the same item across slots")
    {
        auto fixture = ItemFixture{};
        fixture.log.Step(Clock::now(), WithBackpack({{.id = CAKE, .count = 1}, {.id = CAKE, .count = 1}, {.id = COINS, .count = 61}}));

        const auto lines = fixture.Lines();
        REQUIRE(lines.size() == 1);
        // Cake twice in one slot each, so two occupied slots but a single 2-count entry.
        CHECK(lines.front().find(R"("used":3)") != std::string::npos);
        CHECK(lines.front().find(R"("free":25)") != std::string::npos);
        CHECK(lines.front().find(R"({"id":995,"name":"Coins","qty":61})") != std::string::npos);
        CHECK(lines.front().find(R"({"id":1891,"name":"Cake","qty":2})") != std::string::npos);
        CHECK(lines.front().find(R"("bankOpen":false)") != std::string::npos);
    }

    SECTION("free comes from the cache, even when the packet holds only filled slots")
    {
        auto fixture = ItemFixture{};
        auto state = GameState_s{};
        state.placed = true;
        // Ten filled slots and no padding, as the server sends it.
        state.inventories[BACKPACK] = Inventory_s{.com = BACKPACK, .slots = [] {
            auto slots = std::vector<Item_s>{};
            for (auto i = 0; i < 10; ++i)
            {
                slots.push_back({.id = CAKE, .count = 1});
            }
            return slots;
        }(), .tick = 1};

        fixture.log.Step(Clock::now(), state);

        const auto lines = fixture.Lines();
        REQUIRE(lines.size() == 1);
        CHECK(lines.front().find(R"("used":10)") != std::string::npos);
        CHECK(lines.front().find(R"("free":18)") != std::string::npos);
    }

    SECTION("an unchanged backpack writes nothing more")
    {
        auto fixture = ItemFixture{};
        const auto state = WithBackpack({{.id = CAKE, .count = 1}});
        const auto start = Clock::now();
        fixture.log.Step(start, state);
        fixture.log.Step(start + 1min, state);
        CHECK(fixture.Lines().size() == 1);
    }

    SECTION("a change is held until the interval passes")
    {
        auto fixture = ItemFixture{ItemLog::Kind_e::Backpack, 5s};
        const auto start = Clock::now();
        fixture.log.Step(start, WithBackpack({{.id = CAKE, .count = 1}}));
        fixture.log.Step(start + 1s, WithBackpack({{.id = CAKE, .count = 2}}));
        REQUIRE(fixture.Lines().size() == 1);

        fixture.log.Step(start + 6s, WithBackpack({{.id = CAKE, .count = 2}}));
        REQUIRE(fixture.Lines().size() == 2);
        CHECK(fixture.Lines().back().find(R"("qty":2)") != std::string::npos);
    }

    SECTION("the bank's own backpack is recorded while it is open")
    {
        auto fixture = ItemFixture{};
        auto state = WithBackpack({{.id = CAKE, .count = 5}});
        state.interfaces.mainModal = BANK_ROOT;
        state.inventories[BANK_BACKPACK] = Inventory_s{.com = BANK_BACKPACK, .slots = {{.id = CAKE, .count = 900}}, .tick = 2};

        fixture.log.Step(Clock::now(), state);

        REQUIRE(fixture.Lines().size() == 1);
        CHECK(fixture.Lines().front().find(R"("bankOpen":true)") != std::string::npos);
        CHECK(fixture.Lines().front().find(R"("qty":900)") != std::string::npos);
    }

    SECTION("an emptied backpack is recorded as empty")
    {
        auto fixture = ItemFixture{};
        const auto start = Clock::now();
        fixture.log.Step(start, WithBackpack({{.id = CAKE, .count = 3}}));
        fixture.log.Step(start + 10s, WithBackpack({}));

        REQUIRE(fixture.Lines().size() == 2);
        CHECK(fixture.Lines().back().find(R"("used":0)") != std::string::npos);
        CHECK(fixture.Lines().back().find(R"("items":[])") != std::string::npos);
    }

    SECTION("nothing is written before the backpack's contents arrive")
    {
        auto fixture = ItemFixture{};
        fixture.log.Step(Clock::now(), GameState_s{});
        CHECK_FALSE(std::filesystem::exists(fixture.Path()));
    }
}

TEST_CASE("ItemLog records worn equipment in its own file", "[ItemLog][Equipment]")
{
    SECTION("it is written at once, without bankOpen")
    {
        auto fixture = ItemFixture{ItemLog::Kind_e::Equipment, 0s};
        fixture.log.Step(Clock::now(), WithEquipment({{.id = PLATEBODY, .count = 1}}));

        REQUIRE(fixture.Lines().size() == 1);
        CHECK(fixture.Path().filename() == "s18.jsonl");
        CHECK(fixture.Path().parent_path().filename() == "equipment");
        CHECK(fixture.Lines().front().find(R"("used":1)") != std::string::npos);
        CHECK(fixture.Lines().front().find(R"("name":"Iron platebody")") != std::string::npos);
        // No bankOpen and no free: equipment has neither.
        CHECK(fixture.Lines().front().find("bankOpen") == std::string::npos);
        CHECK(fixture.Lines().front().find("free") == std::string::npos);
    }

    SECTION("only a change is written, at a zero interval, every step otherwise")
    {
        auto fixture = ItemFixture{ItemLog::Kind_e::Equipment, 0s};
        const auto start = Clock::now();
        fixture.log.Step(start, WithEquipment({{.id = PLATEBODY, .count = 1}}));
        fixture.log.Step(start + 1s, WithEquipment({{.id = PLATEBODY, .count = 1}}));
        fixture.log.Step(start + 2s, WithEquipment({}));

        CHECK(fixture.Lines().size() == 2);
        CHECK(fixture.Lines().back().find(R"("used":0)") != std::string::npos);
    }

    SECTION("the backpack file doesn't hold equipment")
    {
        auto backpack = ItemFixture{ItemLog::Kind_e::Backpack, 0s};
        auto state = WithBackpack({{.id = CAKE, .count = 1}});
        state.inventories[EQUIPMENT] = Inventory_s{.com = EQUIPMENT, .slots = {{.id = PLATEBODY, .count = 1}}};
        backpack.log.Step(Clock::now(), state);

        CHECK(backpack.Lines().front().find("Iron platebody") == std::string::npos);
    }

    SECTION("a folder that can't be written warns once, and never throws")
    {
        auto fixture = ItemFixture{ItemLog::Kind_e::Equipment, 0s};
        std::ofstream{fixture.folder.GetPath() / "equipment"} << "not a folder";
        auto blocked = ItemLog{*fixture.cache, fixture.capture.GetLogger(), "s18", fixture.folder.GetPath() / "equipment", ItemLog::Kind_e::Equipment, 0s};

        CHECK_NOTHROW(blocked.Step(Clock::now(), WithEquipment({{.id = PLATEBODY, .count = 1}})));
        CHECK_NOTHROW(blocked.Step(Clock::now(), WithEquipment({{.id = PLATEBODY, .count = 2}})));

        const auto warnings = std::ranges::count_if(fixture.capture.GetEntries(), [](const CapturedLog_s& entry)
        {
            return entry.level == LogLevel_e::Warning && entry.message.find("worn equipment wasn't saved") != std::string::npos;
        });
        CHECK(warnings == 1);
    }
}
