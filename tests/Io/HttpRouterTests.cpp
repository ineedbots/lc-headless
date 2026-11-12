#include "pch.hpp"
#include "Http/HttpRouter.hpp"
#include "Http/HttpResponses.hpp"
#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    HttpDecodeResult Status(std::string_view)
    {
        return ApplicationRequestPayload{GetApplicationStatus_s{}};
    }
    HttpDecodeResult Echo(std::string_view body)
    {
        return ApplicationRequestPayload{ExecuteConsoleCommand_s{std::string{body}}};
    }
}

TEST_CASE("HTTP router registers new endpoints and multiple methods without transport changes", "[Http][HttpRouter]")
{
    auto router = HttpRouter{{
        {.method = "GET", .path = "/api/v1/future", .decode = Status},
        {.method = "POST", .path = "/api/v1/future", .requiresJson = true, .decode = Echo},
        {.method = "GET", .path = "/api/v1/other", .decode = Status},
    }};
    auto get = router.Match("GET", "/api/v1/future", "");
    REQUIRE(std::holds_alternative<HttpRoute_s>(get));
    auto snapshot = std::get<HttpRoute_s>(get).decode("");
    CHECK(std::holds_alternative<GetApplicationStatus_s>(std::get<ApplicationRequestPayload>(snapshot)));
    auto post = router.Match("POST", "/api/v1/future", "Application/JSON; charset=utf-8");
    REQUIRE(std::holds_alternative<HttpRoute_s>(post));
    auto decoded = std::get<HttpRoute_s>(post).decode("owned body");
    CHECK(std::get<ExecuteConsoleCommand_s>(std::get<ApplicationRequestPayload>(decoded)).command == "owned body");
    auto unsupported = router.Match("DELETE", "/api/v1/future", "");
    REQUIRE(std::holds_alternative<HttpResponse_s>(unsupported));
    CHECK(std::get<HttpResponse_s>(unsupported).status == 405);
    CHECK(std::get<HttpResponse_s>(unsupported).allow == "GET, POST");
    CHECK(std::get<HttpResponse_s>(router.Match("POST", "/api/v1/future", "text/plain")).status == 415);
    CHECK(std::get<HttpResponse_s>(router.Match("GET", "/api/v1/future?x=1", "")).status == 400);
    CHECK(std::get<HttpResponse_s>(router.Match("GET", "/api/v1/missing", "")).status == 404);
}

TEST_CASE("HTTP route registration rejects ambiguity and invalid descriptors", "[Http][HttpRouter]")
{
    const auto route = HttpRoute_s{.method = "GET", .path = "/api/v1/future", .decode = Status};
    CHECK_THROWS_AS((HttpRouter{{route, route}}), std::invalid_argument);
    CHECK_THROWS_AS((HttpRouter{{{.method = "GET", .path = "relative", .decode = Status}}}), std::invalid_argument);
    CHECK_THROWS_AS((HttpRouter{{{.method = "GET", .path = "/future?query", .decode = Status}}}), std::invalid_argument);
    CHECK_THROWS_AS((HttpRouter{{{.method = "GET", .path = "/future"}}}), std::invalid_argument);
    CHECK_THROWS_AS((HttpRouter{{{.path = "/future", .decode = Status}}}), std::invalid_argument);
}

TEST_CASE("Matched routes own their metadata through deferred body reads", "[Http][HttpRouter]")
{
    auto matched = []
    {
        auto path = std::string{"/api/v1/temporary"};
        auto router = HttpRouter{{{.method = "POST", .path = path, .decode = Echo}}};
        return router.Match("POST", path, "");
    }();
    const auto& route = std::get<HttpRoute_s>(matched);
    CHECK(route.path == "/api/v1/temporary");
    CHECK(route.method == "POST");
    auto result = route.decode("later body");
    CHECK(std::get<ExecuteConsoleCommand_s>(std::get<ApplicationRequestPayload>(result)).command == "later body");
}

TEST_CASE("Default HTTP endpoints decode owned requests and retain the existing contract", "[Http][HttpRouter]")
{
    auto router = HttpRouter{};
    auto match = router.Match("POST", "/api/v1/console/commands", "application/json");
    const auto& route = std::get<HttpRoute_s>(match);
    auto command = route.decode(R"({"command":"@main status"})");
    CHECK(std::get<ExecuteConsoleCommand_s>(std::get<ApplicationRequestPayload>(command)).command == "@main status");
    for (const auto body : {R"({"command":""})", R"({"command":"help","extra":1})", R"({"command":10})", R"({"command":"help\nquit"})", "bad json"})
    {
        auto decoded = route.decode(body);
        REQUIRE(std::holds_alternative<HttpResponse_s>(decoded));
        CHECK(std::get<HttpResponse_s>(decoded).status == 400);
        CHECK_FALSE(std::get<HttpResponse_s>(decoded).close);
    }
    CHECK(std::get<HttpResponse_s>(router.Match("GET", "/api/v1/console/commands", "")).allow == "POST");
    CHECK(std::get<HttpResponse_s>(router.Match("POST", "/api/v1/status", "")).allow == "GET");
}

TEST_CASE("HTTP result serialization dispatches by payload type and preserves error mappings", "[Http][HttpRouter]")
{
    for (const auto& [outcome, expected] : std::vector<std::pair<std::string, unsigned>>{
             {"completed", 200}, {"partial", 200}, {"rejected", 422}, {"failed", 500}, {"cancelled", 503}})
    {
        const auto response = HttpResponses::Complete({.id = 42, .outcome = outcome, .errorCode = "test_error", .payload = ConsoleCommandResult_s{.output = "line\n", .recipients = {{"main", "failed", "handler_failed"}}}});
        CHECK(response.status == expected);
        const auto body = nlohmann::json::parse(response.body);
        CHECK(body["requestId"] == "42");
        CHECK(body["outcome"] == outcome);
        CHECK(body["recipients"][0]["errorCode"] == "handler_failed");
        CHECK(body["error"]["code"] == "test_error");
    }
    const auto status = HttpResponses::Complete({.id = 43, .payload = ApplicationStatus_s{.uptimeMs = 123, .accounts = {{"main", true, false, "in game"}}}});
    const auto body = nlohmann::json::parse(status.body);
    CHECK(status.status == 200);
    CHECK(body["application"]["uptimeMs"] == 123);
    CHECK(body["accounts"][0]["name"] == "main");
    CHECK_FALSE(body.contains("output"));
    const auto result = CompletedApplicationRequest_s{.id = 44, .payload = ConsoleCommandResult_s{.output = "final output", .outputTruncated = true}};
    const auto expired = HttpResponses::Timeout(44, true, &result);
    const auto error = nlohmann::json::parse(expired.body);
    CHECK(expired.status == 504);
    CHECK(error["executionStarted"] == true);
    CHECK(error["output"] == "final output");
    CHECK(error["outputTruncated"] == true);
}
