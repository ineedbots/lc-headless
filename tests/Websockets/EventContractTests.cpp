#include "pch.hpp"

#include "Accounts/Reporting/Type/ProgressReport_s.hpp"
#include "Accounts/Type/AccountLogout_s.hpp"
#include "Application/Type/ApplicationStarted_s.hpp"
#include "Database/Type/FleetAccountDataLog_s.hpp"
#include "Database/Type/FleetBankLog_s.hpp"
#include "Database/Type/FleetEquipmentLog_s.hpp"
#include "Database/Type/FleetExperienceLog_s.hpp"
#include "Database/Type/FleetInventoryLog_s.hpp"
#include "Script/Type/PublishedScriptEvent_s.hpp"
#include "Websockets/Events/EventLimits.hpp"
#include "Websockets/Events/EventProtocol.hpp"
#include "Websockets/Events/FleetLogEvent.hpp"
#include "Websockets/Events/Definitions/AccountProgressEvent.hpp"
#include "Websockets/Events/Type/ApplicationEvent_s.hpp"
#include "Websockets/Events/Type/ApplicationEvents_s.hpp"
#include "Websockets/Events/Type/EventScope_e.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    using Json = nlohmann::json;

    struct EventContract_s
    {
        ApplicationEventPayload payload;
        std::string_view name;
        Json expected;
    };
}

TEST_CASE("Registered event envelopes preserve each public payload schema and empty value shape", "[Events]")
{
    const auto contracts = std::vector<EventContract_s>{
        {ProgressReport_s{60s, {}}, "account.progress", {{"runTimeSeconds", 60}, {"rows", Json::array()}}},
        {AccountLogout_s{false}, "account.logout", {{"confirmed", false}}},
        {ApplicationStarted_s{}, "application.started", Json::object()},
        {PublishedScriptEvent_s{"custom", "null"}, "script.event", {{"name", "custom"}, {"data", nullptr}}},
        {FleetBankLog_s{.time = "time", .account = "bot"}, "fleet.bank", {{"time", "time"}, {"account", "bot"}, {"items", Json::array()}}},
        {FleetEquipmentLog_s{.time = "time", .account = "bot"}, "fleet.equipment", {{"time", "time"}, {"account", "bot"}, {"used", 0}, {"items", Json::array()}}},
        {FleetInventoryLog_s{.time = "time", .account = "bot"}, "fleet.inventory", {{"time", "time"}, {"account", "bot"}, {"bankOpen", false}, {"used", 0}, {"free", 0}, {"items", Json::array()}}},
        {FleetExperienceLog_s{.time = "time", .account = "bot", .state = "connecting"}, "fleet.experience", {{"time", "time"}, {"account", "bot"}, {"state", "connecting"}, {"settled", false}, {"skills", Json::object()}}},
        {FleetAccountDataLog_s{.time = "time", .account = "bot", .state = "connecting"}, "fleet.account-data", {{"time", "time"}, {"account", "bot"}, {"state", "connecting"}, {"settled", false}, {"tick", 0}, {"pid", nullptr}, {"tile", nullptr}, {"destination", nullptr}, {"target", nullptr}, {"hp", nullptr}, {"energy", nullptr}, {"prayer", nullptr}, {"specialAttack", nullptr}, {"running", nullptr}, {"moving", nullptr}, {"inCombat", nullptr}, {"weight", nullptr}}}};
    REQUIRE(contracts.size() == ApplicationEvents_s::NAMES.size());

    for (const auto& contract : contracts)
    {
        INFO(contract.name);
        CHECK(EventProtocol::Name(contract.payload) == contract.name);
        REQUIRE(EventProtocol::ValidateAndMeasureOwnedBytes(contract.payload));

        const auto account = contract.name == "application.started" ? std::nullopt : std::optional<std::string>{"bot"};
        const auto event = ApplicationEvent_s{.account = account, .payload = contract.payload, .timestamp = {}};
        const auto text = EventProtocol::Encode(event, "instance", 7);
        const auto expected = Json{
            {"version", 1}, {"type", "event"}, {"event", contract.name}, {"account", account ? Json(*account) : Json(nullptr)}, {"instance", "instance"}, {"sequence", 7}, {"timestamp", "1970-01-01T00:00:00Z"}, {"payload", contract.expected}};
        CHECK(Json::parse(text) == expected);
        CHECK(text.size() <= EventProtocol::MaxEnvelopeBytes(contract.payload));
        CHECK(EventProtocol::Scope(contract.payload) == (account ? EventScope_e::Account : EventScope_e::Global));
    }
}

TEST_CASE("Fleet event adapters preserve escaping and UTF-8 replacement in full envelopes", "[Events]")
{
    const auto record = FleetBankLog_s{
        .time = "time", .account = "bot", .items = {{.id = 1, .name = "quote\" slash\\ newline\n invalid\xff", .qty = 2}}};
    const auto event = ApplicationEvent_s{.account = "bot", .payload = record};
    const auto value = Json::parse(EventProtocol::Encode(event, "instance", 1));
    CHECK(value["payload"]["items"] == Json::array({{{"id", 1}, {"name", "quote\" slash\\ newline\n invalid\xef\xbf\xbd"}, {"qty", 2}}}));
}

TEST_CASE("Event accounting validates payload limits independently of full envelope limits", "[Events]")
{
    auto report = ProgressReport_s{1s, {{"", std::string(AccountProgressEvent::MAX_TOTAL_ROW_TEXT_BYTES, 'x')}}};
    REQUIRE(AccountProgressEvent::ValidateAndMeasureOwnedBytes(report));
    const auto event = ApplicationEvent_s{.account = "bot", .payload = report};
    CHECK(EventProtocol::Encode(event, "instance", 1).size() <= AccountProgressEvent::MAX_ENVELOPE_BYTES);

    report.rows.front().second.push_back('x');
    CHECK_FALSE(AccountProgressEvent::ValidateAndMeasureOwnedBytes(report));
    report.rows.assign(AccountProgressEvent::MAX_ROWS, {"", ""});
    CHECK(AccountProgressEvent::ValidateAndMeasureOwnedBytes(report));
    report.rows.emplace_back("", "");
    CHECK_FALSE(AccountProgressEvent::ValidateAndMeasureOwnedBytes(report));

    auto json = nlohmann::ordered_json{{"text", ""}};
    const auto budget = EventLimits::MAX_EVENT_ENVELOPE_BYTES - FleetLogEvent::ENVELOPE_RESERVE_BYTES;
    const auto overhead = json.dump().size();
    json["text"] = std::string(budget - overhead, 'x');
    REQUIRE(FleetLogEvent::ValidateAndMeasureJsonBytes(json));
    CHECK(*FleetLogEvent::ValidateAndMeasureJsonBytes(json) == budget);
    json["text"].get_ref<std::string&>().push_back('x');
    CHECK_FALSE(FleetLogEvent::ValidateAndMeasureJsonBytes(json));
}
