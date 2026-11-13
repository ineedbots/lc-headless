#include "pch.hpp"

#include "../Support/LogCapture.hpp"
#include "../Support/TempFolder.hpp"
#include "Accounts/AccountReporting.hpp"
#include "Accounts/Type/FleetBankLog_s.hpp"
#include "Application/Events/ApplicationEventBridge.hpp"
#include "Application/Events/ApplicationEventPublisher.hpp"
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

    Json LastRecord(const std::filesystem::path& path)
    {
        auto file = std::ifstream{path};
        auto line = std::string{};
        auto last = std::string{};
        while (std::getline(file, line))
        {
            last = line;
        }
        return Json::parse(last);
    }
}

TEST_CASE("Fleet journal writes publish matching live events through account reporting", "[FleetEvents][Events]")
{
    const auto folder = TempFolder{"rs2004-fleet-events"};
    auto capture = LogCapture{};
    auto config = Config_s{};
    config.scripting.experienceDirectory = (folder.GetPath() / "experience").string();
    config.scripting.experienceIntervalMinutes = 1min;
    config.scripting.bankLogDirectory = (folder.GetPath() / "bank").string();
    config.scripting.inventoryDirectory = (folder.GetPath() / "inventory").string();
    config.scripting.inventoryIntervalSeconds = 5s;
    config.scripting.equipmentDirectory = (folder.GetPath() / "equipment").string();
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
        CHECK(event["payload"] == LastRecord(folder.GetPath() / name / "bot1.jsonl"));
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

    REQUIRE(bridge->Publish("bot2", FleetBankLog_s{R"({"items":[]})"}));
    Drain(*bridge);
    CHECK_FALSE(bridge->Front(client));

    // Fleet records are live only, including after subscribing again.
    bridge->Enqueue(client, R"({"version":1,"type":"subscribe","id":"later","events":["fleet.bank"]})");
    Drain(*bridge);
    Take(*bridge, client);
    CHECK(Take(*bridge, client)["events"].empty());
    REQUIRE(bridge->Publish("bot2", FleetBankLog_s{R"({"items":[]})"}));
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
    config.scripting.experienceDirectory.clear();
    config.scripting.bankLogDirectory.clear();
    config.scripting.inventoryDirectory.clear();
    config.scripting.equipmentDirectory.clear();
    SECTION("disabled")
    {
    }
    SECTION("write failure")
    {
        const auto blocker = folder.GetPath() / "file";
        FileUtils::AppendText(blocker, "not a directory");
        config.scripting.experienceDirectory = blocker.string();
        config.scripting.inventoryDirectory = blocker.string();
        config.scripting.equipmentDirectory = blocker.string();
        config.scripting.bankLogDirectory = blocker.string();
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

TEST_CASE("Fleet events validate bounded JSON before journal admission", "[FleetEvents][Events]")
{
    auto bridge = ApplicationEventBridge{{"bot1"}};
    CHECK_FALSE(bridge.Publish("bot1", FleetBankLog_s{"{"}));
    CHECK_FALSE(bridge.Publish("bot1", FleetBankLog_s{"[]"}));
    CHECK_FALSE(bridge.Publish("bot1", FleetBankLog_s{Json{{"name", std::string(8192, 'x')}}.dump()}));
    CHECK_FALSE(bridge.Publish("bot1", FleetBankLog_s{Json{{"name", std::string(2000, '\x01')}}.dump()}));
    CHECK_FALSE(bridge.HasIncoming());
}
