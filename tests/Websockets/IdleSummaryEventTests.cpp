#include "pch.hpp"

#include "Accounts/Reporting/Type/IdleSummaryNpc_s.hpp"
#include "Accounts/Reporting/Type/IdleSummary_s.hpp"
#include "Websockets/Events/ApplicationEventBridge.hpp"
#include "Websockets/Events/Definitions/AccountIdleSummaryEvent.hpp"
#include "Websockets/Events/EventLimits.hpp"
#include "Websockets/Events/EventProtocol.hpp"
#include "Websockets/Events/Type/ApplicationEvent_s.hpp"
#include "Websockets/Events/Type/ApplicationEvents_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    nlohmann::json Take(ApplicationEventBridge& bridge, u64 client)
    {
        const auto frame = bridge.Front(client);
        REQUIRE(frame);

        auto value = nlohmann::json::parse(*frame);
        bridge.Pop(client);
        return value;
    }

    void Drain(ApplicationEventBridge& bridge)
    {
        for (auto pass = 0; pass < 1024 && bridge.HasIncoming(); ++pass)
        {
            bridge.Service();
        }

        REQUIRE_FALSE(bridge.HasIncoming());
    }
}

TEST_CASE("Idle summary events serialize the sampled surroundings and interface IDs", "[Events][IdleSummary]")
{
    const auto summary = IdleSummary_s{
        .tick = 42, .pid = 7, .tile = {3200, 3201, 2}, .hitpoints = 8, .baseHitpoints = 10, .runEnergy = 75, .weight = -2, .players = 1, .npcs = 2, .groundItems = 3, .changedLocs = 4, .inventories = 5, .varps = 6, .nearestNpcs = {{9, 81, 3}}, .mainInterface = 100, .sideInterface = 101, .chatInterface = 102, .overlayInterface = 103};
    const auto value = nlohmann::json::parse(EventProtocol::Encode({.account = "bot", .payload = summary}, "instance", 1));
    const auto expected = nlohmann::json{
        {"tick", 42}, {"pid", 7}, {"tile", {{"x", 3200}, {"z", 3201}, {"level", 2}}}, {"hitpoints", {{"current", 8}, {"base", 10}}}, {"runEnergy", 75}, {"weight", -2}, {"inView", {{"players", 1}, {"npcs", 2}, {"groundItems", 3}, {"changedLocs", 4}, {"inventories", 5}, {"varps", 6}}}, {"nearestNpcs", {{{"index", 9}, {"type", 81}, {"distance", 3}}}}, {"interfaces", {{"main", 100}, {"side", 101}, {"chat", 102}, {"overlay", 103}}}};
    CHECK(value["event"] == "account.idle-summary");
    CHECK(value["account"] == "bot");
    CHECK(value["payload"] == expected);
}

TEST_CASE("Idle summary publication bounds NPC storage and fits the maximum fleet snapshot", "[Events][IdleSummary]")
{
    STATIC_REQUIRE(ApplicationEvents_s::FitsSnapshot(EventLimits::MAX_ACCOUNTS));

    auto summary = IdleSummary_s{
        .tick = std::numeric_limits<u64>::max(), .pid = std::numeric_limits<u16>::max(), .tile = {std::numeric_limits<s32>::min(), std::numeric_limits<s32>::min(), std::numeric_limits<s32>::min()}, .hitpoints = std::numeric_limits<s32>::min(), .baseHitpoints = std::numeric_limits<s32>::min(), .runEnergy = 255, .weight = std::numeric_limits<s32>::min(), .players = std::numeric_limits<std::size_t>::max(), .npcs = std::numeric_limits<std::size_t>::max(), .groundItems = std::numeric_limits<std::size_t>::max(), .changedLocs = std::numeric_limits<std::size_t>::max(), .inventories = std::numeric_limits<std::size_t>::max(), .varps = std::numeric_limits<std::size_t>::max(), .nearestNpcs = std::vector<IdleSummaryNpc_s>(IdleSummary_s::MAX_NEAREST_NPCS, {65535, 65535, std::numeric_limits<s32>::min()}), .mainInterface = std::numeric_limits<s32>::min(), .sideInterface = std::numeric_limits<s32>::min(), .chatInterface = std::numeric_limits<s32>::min(), .overlayInterface = std::numeric_limits<s32>::min()};
    REQUIRE(AccountIdleSummaryEvent::ValidateAndMeasureOwnedBytes(summary));

    const auto frame = EventProtocol::Encode({.account = std::string(EventLimits::MAX_ACCOUNT_BYTES, '\x01'), .payload = summary}, std::string(36, 'i'), std::numeric_limits<u64>::max());
    CHECK(frame.size() <= AccountIdleSummaryEvent::MAX_ENVELOPE_BYTES);
    summary.nearestNpcs.push_back({});
    CHECK_FALSE(AccountIdleSummaryEvent::ValidateAndMeasureOwnedBytes(summary));

    auto bridge = ApplicationEventBridge{{"bot"}};
    CHECK_FALSE(bridge.Publish("bot", summary));
    CHECK(bridge.GetDiagnostics().publisherResets == 1);
}

TEST_CASE("Idle summary subscriptions retain the latest sample and filter accounts", "[Events][IdleSummary]")
{
    auto bridge = ApplicationEventBridge{{"bot1", "bot2"}};
    REQUIRE(bridge.Publish("bot1", IdleSummary_s{.tick = 1}));
    REQUIRE(bridge.Publish("bot1", IdleSummary_s{.tick = 2}));
    REQUIRE(bridge.Publish("bot2", IdleSummary_s{.tick = 3}));

    const auto client = bridge.Connect();
    bridge.Enqueue(client, R"({"version":1,"type":"subscribe","id":"idle","events":["account.idle-summary"],"accounts":["bot1"]})");
    Drain(bridge);
    CHECK(Take(bridge, client)["type"] == "ack");

    const auto snapshot = Take(bridge, client);
    REQUIRE(snapshot["events"].size() == 1);
    CHECK(snapshot["events"][0]["event"] == "account.idle-summary");
    CHECK(snapshot["events"][0]["payload"]["tick"] == 2);
    REQUIRE(bridge.Publish("bot2", IdleSummary_s{.tick = 4}));
    REQUIRE(bridge.Publish("bot1", IdleSummary_s{.tick = 5}));
    Drain(bridge);
    CHECK(Take(bridge, client)["payload"]["tick"] == 5);
    CHECK_FALSE(bridge.Front(client));
}
