#include "pch.hpp"

#include "Application/Events/ApplicationEventBridge.hpp"
#include "Application/Events/EventProtocol.hpp"
#include "Application/Events/Type/ApplicationEvent_s.hpp"
#include "Application/Events/Type/EventSubscription_s.hpp"
#include "Accounts/Type/ProgressReport_s.hpp"
#include "Accounts/Type/AccountLogout_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    using Json = nlohmann::json;

    std::string Subscribe(std::string id = "s", std::vector<std::string> accounts = {})
    {
        return Json{{"version", 1}, {"type", "subscribe"}, {"id", id}, {"events", {"account.progress"}}, {"accounts", accounts}}.dump();
    }

    Json Take(ApplicationEventBridge& bridge, u64 client)
    {
        const auto text = bridge.Front(client);
        REQUIRE(text);

        auto value = Json::parse(*text);
        bridge.Pop(client);
        return value;
    }

    void Drain(ApplicationEventBridge& bridge)
    {
        for (int pass = 0; pass < 1024 && bridge.HasIncoming(); ++pass)
        {
            bridge.Service();
        }

        REQUIRE_FALSE(bridge.HasIncoming());
    }
}

TEST_CASE("Event subscriptions take effect only at a safe point with coherent snapshots", "[Events]")
{
    auto bridge = ApplicationEventBridge{{"bot1", "bot2"}};
    const auto client = bridge.Connect();
    auto report = ProgressReport_s{60s, {{"Reports", "1"}}};
    REQUIRE(bridge.Publish("bot1", report));
    bridge.Enqueue(client, Subscribe("s", {"bot1"}));
    report.rows[0].second = "2";
    REQUIRE(bridge.Publish("bot1", report));
    REQUIRE(bridge.Publish("bot2", report));
    CHECK_FALSE(bridge.Front(client));
    CHECK(bridge.GetDiagnostics().subscriptions == 0);
    Drain(bridge);

    const auto ack = Take(bridge, client);
    const auto snapshot = Take(bridge, client);
    const auto event = Take(bridge, client);
    CHECK(ack["type"] == "ack");
    CHECK(ack["sequence"] == 1);
    CHECK(snapshot["sequence"] == ack["sequence"]);
    REQUIRE(snapshot["events"].size() == 1);
    CHECK(snapshot["events"][0]["payload"]["rows"][0][1] == "1");
    CHECK(event["sequence"] == 2);
    CHECK(event["payload"]["rows"][0][1] == "2");
    CHECK(event["payload"]["runTimeSeconds"] == 60);
    CHECK(event["instance"] == ack["instance"]);
    CHECK(event["timestamp"].get<std::string>().ends_with('Z'));
    CHECK_FALSE(bridge.Front(client));
}

TEST_CASE("Event subscriptions reject changes atomically and deduplicate overlapping filters", "[Events]")
{
    auto bridge = ApplicationEventBridge{{"bot1"}};
    const auto client = bridge.Connect();
    bridge.Enqueue(client, Subscribe());
    bridge.Enqueue(client, Subscribe());
    bridge.Enqueue(client, Subscribe("unknown", {"BOT1"}));
    bridge.Enqueue(client, Subscribe("overlap"));
    REQUIRE(bridge.Publish("bot1", ProgressReport_s{1s, {}}));
    bridge.Enqueue(client, R"({"version":1,"type":"unsubscribe","id":"s"})");
    REQUIRE(bridge.Publish("bot1", ProgressReport_s{2s, {}}));
    Drain(bridge);
    CHECK(Take(bridge, client)["type"] == "ack");
    CHECK(Take(bridge, client)["type"] == "snapshot");
    CHECK(Take(bridge, client)["type"] == "error");
    CHECK(Take(bridge, client)["type"] == "error");
    CHECK(Take(bridge, client)["type"] == "ack");
    CHECK(Take(bridge, client)["type"] == "snapshot");
    CHECK(Take(bridge, client)["sequence"] == 1);
    CHECK(Take(bridge, client)["action"] == "unsubscribe");
    CHECK(Take(bridge, client)["sequence"] == 2);
    CHECK_FALSE(bridge.Front(client));
    CHECK(bridge.GetDiagnostics().subscriptions == 1);
    CHECK(bridge.GetDiagnostics().rejectedSubscriptions == 2);
    bridge.Disconnect(client);
    CHECK(bridge.GetDiagnostics().connections == 0);
    CHECK(bridge.GetDiagnostics().subscriptions == 0);
}

TEST_CASE("Event protocol validates versions types fields identifiers and filter bounds", "[Events]")
{
    const auto invalid = std::vector<std::string>{
        "{", "[]", R"({"version":2})", R"({"version":1.0})", R"({"version":1,"type":"other","id":"s"})",
        R"({"version":1,"type":"subscribe","id":"","events":["account.progress"]})",
        R"({"version":1,"type":"subscribe","id":"s","events":["unknown"]})",
        R"({"version":1,"type":"subscribe","id":"s","events":[]})",
        R"({"version":1,"type":"subscribe","id":"s","events":["account.progress","account.progress"]})",
        R"({"version":1,"type":"subscribe","id":"s","events":["account.progress"],"accounts":["a","a"]})",
        R"({"version":1,"type":"subscribe","id":"s","events":["account.progress"],"accounts":7})",
        R"({"version":1,"type":"unsubscribe","id":"s","extra":true})"};

    for (const auto& text : invalid)
    {
        INFO(text);
        CHECK(std::holds_alternative<EventProtocolError_s>(EventProtocol::Decode(text)));
    }

    CHECK(std::holds_alternative<EventCommand_s>(EventProtocol::Decode(Subscribe())));
    CHECK(std::holds_alternative<EventProtocolError_s>(EventProtocol::Decode(Subscribe(std::string(65, 'a')))));
    CHECK(std::holds_alternative<EventProtocolError_s>(EventProtocol::Decode(Subscribe("s", std::vector<std::string>(17, "a")))));
    CHECK(Json::parse(EventProtocol::Error({}, "invalid_message"))["id"].is_null());
}

TEST_CASE("Event queues disconnect slow consumers and reset snapshots on publisher overflow", "[Events]")
{
    auto bridge = ApplicationEventBridge{{"bot1"}};
    const auto slow = bridge.Connect();
    const auto fast = bridge.Connect();
    bridge.Enqueue(slow, Subscribe());
    bridge.Enqueue(fast, Subscribe());
    Drain(bridge);
    Take(bridge, fast);
    Take(bridge, fast);

    for (int i = 0; i < 70; ++i)
    {
        REQUIRE(bridge.Publish("bot1", ProgressReport_s{1s, {{"i", std::to_string(i)}}}));
        Drain(bridge);
        CHECK(Take(bridge, fast)["type"] == "event");
    }

    CHECK(bridge.IsClosing(slow));
    CHECK_FALSE(bridge.IsClosing(fast));
    CHECK(bridge.GetDiagnostics().overflowDisconnects == 1);
    CHECK_FALSE(bridge.Publish("bot1", ProgressReport_s{1s, {{"huge", std::string(4097, 'x')}}}));
    CHECK(bridge.IsClosing(fast));
    CHECK(bridge.GetDiagnostics().publisherResets == 1);

    const auto fresh = bridge.Connect();
    bridge.Enqueue(fresh, Subscribe());
    Drain(bridge);
    Take(bridge, fresh);
    CHECK(Take(bridge, fresh)["events"].empty());
    bridge.Stop();
    CHECK(bridge.IsClosing(fresh));
    CHECK(bridge.Connect() == 0);
    CHECK_FALSE(bridge.HasIncoming());
}

TEST_CASE("Event fanout continues across passes in order with bounded journal admission", "[Events]")
{
    auto bridge = ApplicationEventBridge{{"bot1"}};
    auto clients = std::vector<u64>{};
    for (int i = 0; i < 128; ++i)
    {
        const auto client = bridge.Connect();
        REQUIRE(client != 0);
        clients.push_back(client);
        bridge.Enqueue(client, Subscribe());
    }

    CHECK(bridge.Connect() == 0);
    Drain(bridge);
    for (const auto client : clients)
    {
        Take(bridge, client);
        Take(bridge, client);
    }

    for (int i = 0; i < 4; ++i)
    {
        REQUIRE(bridge.Publish("bot1", ProgressReport_s{1s, {}}));
    }

    bridge.Service();
    CHECK(bridge.HasIncoming());
    Drain(bridge);
    for (const auto client : clients)
    {
        for (int i = 1; i <= 4; ++i)
        {
            CHECK(Take(bridge, client)["sequence"] == i);
        }
    }

    for (std::size_t i = 0; i < ApplicationEventBridge::MAX_JOURNAL_BYTES / ApplicationEventBridge::MAX_EVENT_BYTES; ++i)
    {
        REQUIRE(bridge.Publish("bot1", ProgressReport_s{1s, {}}));
    }

    CHECK_FALSE(bridge.Publish("bot1", ProgressReport_s{1s, {}}));
    CHECK(bridge.GetDiagnostics().journalBytes == 0);
    CHECK(bridge.GetDiagnostics().journalItems == 0);
    CHECK(bridge.GetDiagnostics().publisherResets == 1);
}

TEST_CASE("Event disconnect retires queued commands and new sessions cannot inherit old work", "[Events]")
{
    auto bridge = ApplicationEventBridge{{"bot1"}};
    const auto old = bridge.Connect();
    bridge.Enqueue(old, Subscribe());
    bridge.Disconnect(old);
    CHECK_FALSE(bridge.HasIncoming());

    const auto fresh = bridge.Connect();
    CHECK(fresh != old);
    bridge.Enqueue(old, Subscribe());
    REQUIRE(bridge.Publish("bot1", ProgressReport_s{1s, {}}));
    Drain(bridge);
    CHECK_FALSE(bridge.Front(fresh));
    CHECK(bridge.GetDiagnostics().subscriptions == 0);

    for (int i = 0; i < 17; ++i)
    {
        bridge.Enqueue(fresh, Subscribe(std::to_string(i)));
    }

    Drain(bridge);
    CHECK(bridge.GetDiagnostics().subscriptions == 16);
    CHECK(bridge.GetDiagnostics().rejectedSubscriptions == 1);
}

TEST_CASE("Logout events are ordered live notifications filtered by event and account", "[Events]")
{
    auto bridge = ApplicationEventBridge{{"bot1", "bot2"}};
    const auto client = bridge.Connect();
    const auto progress = bridge.Connect();
    bridge.Enqueue(client, R"({"version":1,"type":"subscribe","id":"logout","events":["account.logout"],"accounts":["bot1"]})");
    bridge.Enqueue(progress, Subscribe());
    REQUIRE(bridge.Publish({"bot1", AccountLogout_s{true}}));
    REQUIRE(bridge.Publish({"bot2", AccountLogout_s{true}}));
    REQUIRE(bridge.Publish("bot1", ProgressReport_s{60s, {}}));
    REQUIRE(bridge.Publish({"bot1", AccountLogout_s{false}}));
    Drain(bridge);

    CHECK(Take(bridge, client)["type"] == "ack");
    CHECK(Take(bridge, client)["events"].empty());
    const auto confirmed = Take(bridge, client);
    CHECK(confirmed["version"] == 1);
    CHECK(confirmed["type"] == "event");
    CHECK(confirmed["event"] == "account.logout");
    CHECK(confirmed["account"] == "bot1");
    CHECK_FALSE(confirmed["instance"].get<std::string>().empty());
    CHECK_FALSE(confirmed["timestamp"].get<std::string>().empty());
    CHECK(confirmed["sequence"] == 1);
    CHECK(confirmed["payload"] == Json{{"confirmed", true}});
    const auto forced = Take(bridge, client);
    CHECK(forced["sequence"] == 4);
    CHECK(forced["payload"] == Json{{"confirmed", false}});
    CHECK_FALSE(bridge.Front(client));
    Take(bridge, progress);
    Take(bridge, progress);
    CHECK(Take(bridge, progress)["event"] == "account.progress");
    CHECK_FALSE(bridge.Front(progress));

    // A mixed subscription sees the retained progress report, never an old logout.
    const auto fresh = bridge.Connect();
    bridge.Enqueue(fresh, R"({"version":1,"type":"subscribe","id":"both","events":["account.logout","account.progress"]})");
    Drain(bridge);
    CHECK(Take(bridge, fresh)["sequence"] == 4);
    const auto snapshot = Take(bridge, fresh);
    REQUIRE(snapshot["events"].size() == 1);
    CHECK(snapshot["events"][0]["event"] == "account.progress");
    CHECK(snapshot["events"][0]["sequence"] == 3);

    bridge.Enqueue(client, R"({"version":1,"type":"unsubscribe","id":"logout"})");
    REQUIRE(bridge.Publish({"bot1", AccountLogout_s{true}}));
    Drain(bridge);
    CHECK(Take(bridge, client)["action"] == "unsubscribe");
    CHECK_FALSE(bridge.Front(client));
    CHECK(Take(bridge, fresh)["event"] == "account.logout");
}
