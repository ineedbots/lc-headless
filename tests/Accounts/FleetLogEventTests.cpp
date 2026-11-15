#include "pch.hpp"

#include "../Support/LogCapture.hpp"
#include "../Support/TempFolder.hpp"
#include "../Support/FleetDatabaseReader.hpp"
#include "Accounts/AccountReporting.hpp"
#include "Accounts/Type/FleetBankLog_s.hpp"
#include "Application/Events/ApplicationEventBridge.hpp"
#include "Application/Events/ApplicationEventPublisher.hpp"
#include "Application/Events/Definitions/FleetBankEvent.hpp"
#include "Application/Events/EventProtocol.hpp"
#include "Cache/Type/GameCache_s.hpp"
#include "Cache/Type/IfComponent_s.hpp"
#include "Cache/Type/ObjType_s.hpp"
#include "Config/Type/AccountConfig_s.hpp"
#include "Config/Type/Config_s.hpp"
#include "Game/GameClient.hpp"
#include "Game/State/Type/GameState_s.hpp"
#include "Game/State/Type/Interfaces_s.hpp"
#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    using Json = nlohmann::json;

    void Drain(ApplicationEventBridge& bridge)
    {
        while (bridge.HasIncoming())
        {
            bridge.Service();
        }
    }

    Json Take(ApplicationEventBridge& bridge, u64 client)
    {
        const auto text = bridge.Front(client);
        REQUIRE(text);
        auto value = Json::parse(*text);
        bridge.Pop(client);
        return value;
    }

    Json LastRecord(const std::filesystem::path& path, std::string_view stream, std::string_view account)
    {
        const auto records = ReadFleetRecords(path, stream, account);
        REQUIRE_FALSE(records.empty());
        return records.back();
    }
}

TEST_CASE("Fleet journal writes publish matching live events through account reporting", "[FleetEvents][Events]")
{
    const auto folder = TempFolder{"rs2004-fleet-events"};
    auto capture = LogCapture{};
    auto config = Config_s{};
    config.scripting.fleetDatabasePath = (folder.GetPath() / "fleet.sqlite").string();
    config.scripting.accountDataLogEnabled = false;
    config.scripting.experienceIntervalMinutes = 1min;
    config.scripting.inventoryIntervalSeconds = 5s;
    auto cache = GameCache_s{};
    cache.bankComponent = 2;
    cache.inventoryComponent = 3;
    cache.equipmentComponent = 4;
    cache.inventorySize = 28;
    cache.components[1] = IfComponent_s{.id = 1, .root = 1, .type = ComponentType_e::Layer};
    cache.components[2] = IfComponent_s{.id = 2, .root = 1, .type = ComponentType_e::Inv};
    cache.objs.resize(1);
    cache.objs[0] = ObjType_s{.id = 0, .name = "Item \"\\\xff"};
    auto bridge = std::make_shared<ApplicationEventBridge>(std::vector<std::string>{"bot1", "bot2"});
    const auto client = bridge->Connect();
    bridge->Enqueue(client, R"({"version":1,"type":"subscribe","id":"fleet","events":["fleet.experience","fleet.bank","fleet.inventory","fleet.equipment"],"accounts":["bot1"]})");
    Drain(*bridge);
    CHECK(Take(*bridge, client)["type"] == "ack");
    CHECK(Take(*bridge, client)["events"].empty());
    auto reporting = AccountReporting{config, AccountConfig_s{.name = "bot1"}, cache, capture.GetLogger(), {}, bridge};
    const auto now = AccountReporting::Clock::now();
    auto state = GameState_s{};
    state.placed = true;
    state.tick = 1;
    state.interfaces.mainModal = 1;
    for (const auto com : {u16{2}, u16{3}, u16{4}})
    {
        state.inventories[com] = Inventory_s{.com = com, .slots = {{.id = 0, .count = 5}}};
    }
    reporting.ObserveSession(now, state, ClientStatus_e::InGame);
    reporting.SampleItems(now, state);
    Drain(*bridge);
    auto previous = u64{0};
    for (const auto name : {"experience", "bank", "inventory", "equipment"})
    {
        const auto event = Take(*bridge, client);
        CHECK(event["event"] == std::string{"fleet."} + name);
        CHECK(event["account"] == "bot1");
        CHECK(event["sequence"].get<u64>() > previous);
        previous = event["sequence"].get<u64>();
        CHECK(event["payload"] == LastRecord(folder.GetPath() / "fleet.sqlite", name, "bot1"));
    }
    reporting.ObserveSession(now, state, ClientStatus_e::InGame);
    reporting.SampleItems(now, state);
    Drain(*bridge);
    CHECK_FALSE(bridge->Front(client));

    // Backpack changes wait for the configured interval; equipment changes do not.
    state.inventories[3].slots[0].count = 6;
    state.inventories[4].slots[0].count = 7;
    reporting.SampleItems(now + 1s, state);
    Drain(*bridge);
    CHECK(Take(*bridge, client)["event"] == "fleet.equipment");
    CHECK_FALSE(bridge->Front(client));
    reporting.SampleItems(now + 5s, state);
    Drain(*bridge);
    CHECK(Take(*bridge, client)["event"] == "fleet.inventory");
    CHECK_FALSE(bridge->Front(client));

    state.interfaces.mainModal = -1;
    reporting.SampleItems(now + 10s, state);
    Drain(*bridge);
    CHECK(Take(*bridge, client)["event"] == "fleet.inventory");
    state.interfaces.mainModal = 1;
    reporting.SampleItems(now + 15s, state);
    Drain(*bridge);
    CHECK(Take(*bridge, client)["event"] == "fleet.bank");
    CHECK(Take(*bridge, client)["event"] == "fleet.inventory");

    reporting.ObserveSession(now + 59s, state, ClientStatus_e::InGame);
    Drain(*bridge);
    CHECK_FALSE(bridge->Front(client));
    reporting.ObserveSession(now + 60s, state, ClientStatus_e::InGame);
    Drain(*bridge);
    CHECK(Take(*bridge, client)["event"] == "fleet.experience");
    reporting.ObserveSession(now + 61s, state, ClientStatus_e::LoggedOut);
    Drain(*bridge);
    CHECK(Take(*bridge, client)["payload"]["state"] == "logged out");

    const auto bankRecord = FleetBankLog_s{.time = "2026-01-01T00:00:00Z", .account = "bot2"};
    REQUIRE(bridge->Publish("bot2", bankRecord));
    Drain(*bridge);
    CHECK_FALSE(bridge->Front(client));

    // Fleet records are live only, including after subscribing again.
    bridge->Enqueue(client, R"({"version":1,"type":"subscribe","id":"later","events":["fleet.bank"]})");
    Drain(*bridge);
    Take(*bridge, client);
    CHECK(Take(*bridge, client)["events"].empty());
    REQUIRE(bridge->Publish("bot2", bankRecord));
    Drain(*bridge);
    // The later subscription has no account filter.
    CHECK(Take(*bridge, client)["account"] == "bot2");
    CHECK_FALSE(bridge->Front(client));
}

TEST_CASE("Failed or disabled fleet journals do not publish events", "[FleetEvents][Events]")
{
    const auto folder = TempFolder{"rs2004-fleet-events-failure"};
    auto capture = LogCapture{};
    auto config = Config_s{};
    config.scripting.accountDataLogEnabled = false;
    config.scripting.experienceLogEnabled = false;
    config.scripting.bankLogEnabled = false;
    config.scripting.inventoryLogEnabled = false;
    config.scripting.equipmentLogEnabled = false;
    SECTION("disabled")
    {
    }
    SECTION("write failure")
    {
        const auto blocker = folder.GetPath() / "file";
        FileUtils::AppendText(blocker, "not a directory");
        config.scripting.fleetDatabasePath = blocker.string();
        config.scripting.experienceLogEnabled = true;
        config.scripting.inventoryLogEnabled = true;
        config.scripting.equipmentLogEnabled = true;
        config.scripting.bankLogEnabled = true;
    }
    auto bridge = std::make_shared<ApplicationEventBridge>(std::vector<std::string>{"bot1"});
    auto cache = GameCache_s{};
    cache.inventoryComponent = 3;
    cache.equipmentComponent = 4;
    cache.bankComponent = 2;
    cache.components[1] = IfComponent_s{.id = 1, .root = 1, .type = ComponentType_e::Layer};
    cache.components[2] = IfComponent_s{.id = 2, .root = 1, .type = ComponentType_e::Inv};
    auto reporting = AccountReporting{config, AccountConfig_s{.name = "bot1"}, cache, capture.GetLogger(), {}, bridge};
    reporting.ObserveSession(AccountReporting::Clock::now(), GameState_s{}, ClientStatus_e::Connecting);
    auto state = GameState_s{};
    state.placed = true;
    state.tick = 1;
    state.interfaces.mainModal = 1;
    for (const auto com : {u16{2}, u16{3}, u16{4}})
    {
        state.inventories[com] = Inventory_s{.com = com};
    }
    reporting.SampleItems(AccountReporting::Clock::now(), state);
    CHECK_FALSE(bridge->HasIncoming());
}

TEST_CASE("Fleet events bound typed payloads and replace invalid UTF-8", "[FleetEvents][Events]")
{
    const auto tooLarge = FleetBankLog_s{
        .time = "2026-01-01T00:00:00Z",
        .account = "bot1",
        .items = {{.id = 1, .name = std::string(8192, 'x'), .qty = 1}}};
    CHECK_FALSE(FleetBankEvent::Measure(tooLarge));

    const auto invalidUtf8 = FleetBankLog_s{
        .time = "2026-01-01T00:00:00Z",
        .account = "bot1",
        .items = {{.id = 1, .name = std::string{"bad\xff"}, .qty = 1}}};
    const auto serialized = FleetBankEvent::Serialize(invalidUtf8);
    CHECK(serialized["items"][0]["name"] == "bad\xef\xbf\xbd");
}
