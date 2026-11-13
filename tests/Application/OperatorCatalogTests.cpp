#include "pch.hpp"

#include "Accounts/AccountControl.hpp"
#include "Accounts/Type/AccountStatus_s.hpp"
#include "Accounts/Type/ProgressReport_s.hpp"
#include "Application/Events/ApplicationEventBridge.hpp"
#include "Application/Events/EventLimits.hpp"
#include "Application/Events/Type/EventCatalog_s.hpp"
#include "Application/Events/Type/ApplicationEvent_s.hpp"
#include "Application/Type/OperationCatalog_s.hpp"
#include "Application/Type/ApplicationRequestContext_s.hpp"
#include "Application/Type/RequestControl_s.hpp"
#include "Console/CommandExecution.hpp"
#include "Http/HttpRouter.hpp"
#include "Http/Type/HttpEndpointCatalog_s.hpp"
#include "Http/Type/HttpRoute_s.hpp"
#include "Http/Type/HttpRouteMatch_s.hpp"
#include "Http/Type/HttpEndpointRequest_s.hpp"
#include "Http/Type/HttpResponse_s.hpp"
#include "Application/Type/ApplicationStatus_s.hpp"
#include "Application/Type/GetApplicationStatus_s.hpp"
#include "Application/Type/CompletedApplicationRequest_s.hpp"
#include "Application/Type/ApplicationOperations_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    class TestControl : public AccountControl
    {
    public:
        void HandleCommand(std::string_view, std::shared_ptr<CommandExecution>) override
        {
            FAIL("Query operation dispatched a command");
        }
        std::size_t GetAccountCount() const override
        {
            return 3;
        }
        AccountStatus_s GetAccountStatus(std::size_t) const override
        {
            return {"bot", true, false, "in game"};
        }
    };

    struct CountRequest_s
    {
        std::size_t multiplier;
    };

    struct CountResult_s
    {
        std::size_t count;
    };

    class CountOperation
    {
    public:
        using Payload = CountRequest_s;
        using Result = CountResult_s;
        static std::optional<Result> Execute(const ApplicationRequestContext_s& context, const std::shared_ptr<RequestControl_s>&, const Payload& request)
        {
            return Result{context.runner.GetAccountCount() * request.multiplier};
        }
    };

    class FutureEndpoint
    {
    public:
        using Payload = ApplicationStatus_s;
        static HttpRoute_s Route()
        {
            return {.method = "GET", .path = "/future/{name}", .decode = Decode};
        }
        static HttpDecodeResult Decode(const HttpEndpointRequest_s&)
        {
            return ApplicationRequestPayload{GetApplicationStatus_s{}};
        }
        static HttpResponse_s Respond(const CompletedApplicationRequest_s& result, const Payload& payload)
        {
            return {.status = 201, .body = std::to_string(result.id) + ":" + std::to_string(payload.accounts.size())};
        }
    };

    class AlternateEndpoint : public FutureEndpoint
    {
    public:
        static HttpRoute_s Route()
        {
            return {.method = "GET", .path = "/alternate", .decode = Decode};
        }
        static HttpResponse_s Respond(const CompletedApplicationRequest_s&, const Payload&)
        {
            return {.status = 202, .body = "alternate"};
        }
    };

    class UpgradeEndpoint
    {
    public:
        static HttpRoute_s Route()
        {
            return {.method = "GET", .path = "/future/events", .webSocket = true};
        }
    };

    class FirstEvent
    {
    public:
        using Payload = int;
        static constexpr std::string_view NAME = "test.first";
        static constexpr bool RETAINS_LATEST = true;
        static constexpr std::size_t MAX_SERIALIZED_BYTES = EventLimits::MAX_EVENT_BYTES;
    };

    class SecondEvent
    {
    public:
        using Payload = bool;
        static constexpr std::string_view NAME = "test.second";
        static constexpr bool RETAINS_LATEST = true;
        static constexpr std::size_t MAX_SERIALIZED_BYTES = EventLimits::MAX_EVENT_BYTES;
    };

    class DuplicateEvent : public SecondEvent
    {
    public:
        static constexpr std::string_view NAME = FirstEvent::NAME;
    };

    class OversizedEvent : public FirstEvent
    {
    public:
        static constexpr std::size_t MAX_SERIALIZED_BYTES = EventLimits::MAX_EVENT_BYTES + 1;
    };
}

TEST_CASE("Operation catalogs admit unrelated typed operations through the common execution adapter", "[Http][RequestProcessor]")
{
    using Catalog = OperationCatalog_s<CountOperation>;
    auto control = TestControl{};
    const auto context = ApplicationRequestContext_s{control, std::chrono::steady_clock::now(), 1024};
    auto request = Catalog::Payload{CountRequest_s{7}};
    const auto result = std::visit([&](const auto& payload) -> Catalog::Result
    {
        return *Catalog::Execute(context, std::make_shared<RequestControl_s>(), payload);
    }, request);
    CHECK(std::get<CountResult_s>(result).count == 21);
}

TEST_CASE("Endpoint catalogs register REST and upgrade routes with their result adapters", "[Http][HttpRouter]")
{
    using Catalog = HttpEndpointCatalog_s<FutureEndpoint, AlternateEndpoint, UpgradeEndpoint>;
    const auto router = HttpRouter{Catalog::Routes()};
    auto match = router.Match("GET", "/future/alice", "");
    REQUIRE(std::holds_alternative<HttpRouteMatch_s>(match));
    CHECK(std::get<HttpRouteMatch_s>(match).request.pathParameters.at("name") == "alice");
    const auto decoded = std::get<HttpRouteMatch_s>(match).Decode("");
    CHECK(std::holds_alternative<GetApplicationStatus_s>(std::get<ApplicationRequestPayload>(decoded)));
    const auto upgrade = router.Match("GET", "/future/events", "");
    REQUIRE(std::holds_alternative<HttpRouteMatch_s>(upgrade));
    CHECK(std::get<HttpRouteMatch_s>(upgrade).route.webSocket);

    const auto response = Catalog::Respond(CompletedApplicationRequest_s{.id = 91}, ApplicationStatus_s{});
    CHECK(response.status == 201);
    CHECK(response.body == "91:0");
    const auto alternate = router.Match("GET", "/alternate", "");
    const auto& route = std::get<HttpRouteMatch_s>(alternate).route;
    REQUIRE(route.respond);
    const auto ownResponse = route.respond({.id = 91, .payload = ApplicationStatus_s{}});
    REQUIRE(ownResponse);
    CHECK(ownResponse->status == 202);
    CHECK(ownResponse->body == "alternate");
    CHECK_FALSE(route.respond({.id = 91, .outcome = "cancelled"}));
}

TEST_CASE("Event catalogs validate names and account for every retained event in the snapshot budget", "[Events]")
{
    using Catalog = EventCatalog_s<FirstEvent, SecondEvent>;
    STATIC_REQUIRE(Catalog::IsValid());
    STATIC_REQUIRE(Catalog::FitsSnapshot(15));
    STATIC_REQUIRE_FALSE(Catalog::FitsSnapshot(16));
    STATIC_REQUIRE_FALSE(Catalog::FitsSnapshot(0, EventLimits::SNAPSHOT_OVERHEAD_BYTES - 1));
    STATIC_REQUIRE_FALSE((EventCatalog_s<FirstEvent, DuplicateEvent>::IsValid()));
    STATIC_REQUIRE_FALSE(EventCatalog_s<OversizedEvent>::IsValid());
    CHECK(Catalog::IsKnown("test.second"));
    CHECK_FALSE(Catalog::IsKnown("unknown"));
    CHECK(std::holds_alternative<bool>(Catalog::Payload{true}));
}

TEST_CASE("Typed publication validates borrowed payloads and journals an owned copy", "[Events]")
{
    auto bridge = ApplicationEventBridge{{"bot"}};
    const auto client = bridge.Connect();
    auto report = ProgressReport_s{60s, {{"reports", "original"}}};
    REQUIRE(bridge.Publish("bot", report));
    report.rows[0].second = "changed";
    bridge.Enqueue(client, R"({"version":1,"type":"subscribe","id":"s","events":["account.progress"]})");
    bridge.Service();
    REQUIRE(bridge.Front(client));
    bridge.Pop(client);
    REQUIRE(bridge.Front(client));
    const auto snapshot = nlohmann::json::parse(*bridge.Front(client));
    CHECK(snapshot["events"][0]["payload"]["rows"][0][1] == "original");
    CHECK_FALSE(bridge.Publish("bot", ProgressReport_s{1s, {{"oversized", std::string(4097, 'x')}}}));
    CHECK(bridge.GetDiagnostics().publisherResets == 1);
    bridge.Stop();
    CHECK_FALSE(bridge.Publish("bot", report));
    CHECK(bridge.GetDiagnostics().publisherResets == 1);
}
