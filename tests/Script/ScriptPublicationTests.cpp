#include "pch.hpp"

#include "../Support/Script/HostFixture.hpp"
#include "Application/Events/ApplicationEventBridge.hpp"
#include "Application/Events/Definitions/ScriptPublishedEvent.hpp"
#include "Application/Events/EventProtocol.hpp"
#include "Application/Events/Type/ApplicationEvent_s.hpp"
#include "Application/Type/ApplicationStarted_s.hpp"
#include "Script/Host/ScriptHost.hpp"
#include "Script/Type/PublishedScriptEvent_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    using Json = nlohmann::json;
    constexpr auto SUBSCRIBE = R"({"version":1,"type":"subscribe","id":"script","events":["script.event"],"accounts":["public_name"]})";

    Json Take(ApplicationEventBridge& bridge, u64 client)
    {
        const auto text = bridge.Front(client);
        REQUIRE(text);

        auto value = Json::parse(*text);
        bridge.Pop(client);
        return value;
    }
}

TEST_CASE("Python publishes owned live operator events with its configured account identity", "[ScriptHost][Events]")
{
    auto events = std::make_shared<ApplicationEventBridge>(std::vector<std::string>{"public_name"});
    const auto client = events->Connect();
    events->Enqueue(client, SUBSCRIBE);

    auto fixture = HostFixture{R"python(
assert publish_event('loaded')

def on_start():
    data = {'items': [1, 2], 'ok': True, 'none': None, 'tuple': (3, 4)}
    assert publish_event('bank.completed', data)
    data['items'].append(99)

def loop():
    return 600
)python",
                               ScriptHostOptions_s{.username = "private_username", .events = events, .accountName = "public_name"}};
    fixture.Step();
    CHECK_FALSE(events->Front(client));
    events->Service();
    CHECK(Take(*events, client)["type"] == "ack");
    CHECK(Take(*events, client)["events"].empty());

    const auto loaded = Take(*events, client);
    CHECK(loaded["event"] == "script.event");
    CHECK(loaded["account"] == "public_name");
    CHECK(loaded["payload"] == Json{{"name", "loaded"}, {"data", nullptr}});

    const auto event = Take(*events, client);
    CHECK(event["sequence"] == loaded["sequence"].get<u64>() + 1);
    CHECK(event["payload"] == Json{{"name", "bank.completed"}, {"data", {{"items", {1, 2}}, {"ok", true}, {"none", nullptr}, {"tuple", {3, 4}}}}});
    CHECK_FALSE(events->Front(client));
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);

    const auto fresh = events->Connect();
    events->Enqueue(fresh, SUBSCRIBE);
    events->Service();
    Take(*events, fresh);
    CHECK(Take(*events, fresh)["events"].empty());
}

TEST_CASE("Python event arguments are bounded and invalid values do not reset subscribers", "[ScriptHost][Events]")
{
    auto events = std::make_shared<ApplicationEventBridge>(std::vector<std::string>{"bot"});
    auto fixture = HostFixture{R"python(
def on_start():
    invalid = [('', None), ('x' * 65, None), ('bad name', None), ('line\nfeed', None), ('valid', 'x' * 4095)]
    for name, data in invalid:
        try:
            publish_event(name, data)
            assert False, 'invalid event accepted'
        except ValueError:
            pass
    try:
        publish_event(1)
        assert False
    except TypeError:
        pass
    try:
        publish_event('function', lambda: None)
        assert False
    except TypeError:
        pass
    data = None
    for i in range(17):
        data = [data]
    try:
        publish_event('deep', data)
        assert False
    except ValueError:
        pass
    assert publish_event('x' * 64, 'x' * 4094)
    data = None
    for i in range(16):
        data = [data]
    assert publish_event('depth.limit', data)

def loop():
    return 600
)python",
                               ScriptHostOptions_s{.events = events, .accountName = "bot"}};
    fixture.Step();
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
    CHECK(events->GetDiagnostics().publisherResets == 0);
    events->Service();
    CHECK(events->GetDiagnostics().publisherResets == 0);
    CHECK_FALSE(events->HasIncoming());
}

TEST_CASE("Python publication returns false when disabled stopping or over capacity", "[ScriptHost][Events]")
{
    const auto script = R"python(
def on_start():
    assert not publish_event('status', {'ready': True})
    log('>', 'refused')

def loop():
    return 600
)python";
    auto events = std::make_shared<ApplicationEventBridge>(std::vector<std::string>{"bot"});
    auto options = ScriptHostOptions_s{.events = events, .accountName = "bot"};

    SECTION("disabled")
    {
        options.events.reset();
    }

    SECTION("stopping")
    {
        events->Stop();
    }

    SECTION("over capacity")
    {
        for (std::size_t i = 0; i < ApplicationEventBridge::MAX_JOURNAL_BYTES / ApplicationEventBridge::MAX_EVENT_BYTES; ++i)
        {
            REQUIRE(events->Publish(ApplicationStarted_s{}));
        }
    }

    auto fixture = HostFixture{script, options};
    fixture.Step();
    CHECK(fixture.host->GetStatus() == ScriptStatus_e::Running);
    CHECK(fixture.GetScriptLines() == std::vector<std::string>{"refused"});
}

TEST_CASE("Script event definitions reject malformed and excessive JSON before admission", "[Events]")
{
    const auto serialize = [](std::string data)
    {
        const auto text = EventProtocol::Encode({.account = "public_name", .payload = PublishedScriptEvent_s{"valid", std::move(data)}}, "instance", 1);
        return Json::parse(text).at("payload");
    };

    // This call crosses the library boundary with a JSON value; diagnostics must match.
    CHECK(ScriptPublishedEvent::Serialize({"valid", "null"}) == serialize("null"));

    for (const auto json : {"{", "NaN", "[1,]", "", "{bad}"})
    {
        CHECK_FALSE(ScriptPublishedEvent::Measure({"valid", json}));
        CHECK_THROWS_AS(serialize(json), std::invalid_argument);
    }

    CHECK(ScriptPublishedEvent::Measure({"valid", "null"}));
    CHECK(ScriptPublishedEvent::Measure({"valid", R"({"text":"hello","list":[1,true,null]})"}));

    CHECK(serialize("null") == Json{{"name", "valid"}, {"data", nullptr}});
    CHECK(serialize(R"({"text":"hello","list":[1,true,null]})") ==
          Json{{"name", "valid"}, {"data", {{"text", "hello"}, {"list", {1, true, nullptr}}}}});

    const auto oversized = std::string(ScriptPublishedEvent::MAX_DATA_BYTES + 1, ' ');
    const auto tooDeep = std::string(ScriptPublishedEvent::MAX_DATA_DEPTH + 1, '[') + "0" + std::string(ScriptPublishedEvent::MAX_DATA_DEPTH + 1, ']');
    for (const auto& text : {oversized, tooDeep})
    {
        CHECK_FALSE(ScriptPublishedEvent::Measure({"valid", text}));
        CHECK_THROWS_AS(serialize(text), std::invalid_argument);
    }
}
