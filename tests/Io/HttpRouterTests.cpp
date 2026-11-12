#include "pch.hpp"
#include "Http/HttpRouter.hpp"
#include "Http/HttpResponses.hpp"
#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    HttpDecodeResult Status(const HttpEndpointRequest_s&)
    {
        return ApplicationRequestPayload{GetApplicationStatus_s{}};
    }

    HttpDecodeResult Echo(const HttpEndpointRequest_s& request)
    {
        return ApplicationRequestPayload{ExecuteConsoleCommand_s{request.body}};
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
    REQUIRE(std::holds_alternative<HttpRouteMatch_s>(get));

    auto snapshot = std::get<HttpRouteMatch_s>(get).Decode("");
    CHECK(std::holds_alternative<GetApplicationStatus_s>(std::get<ApplicationRequestPayload>(snapshot)));

    auto post = router.Match("POST", "/api/v1/future", "Application/JSON; charset=utf-8");
    REQUIRE(std::holds_alternative<HttpRouteMatch_s>(post));

    auto decoded = std::get<HttpRouteMatch_s>(post).Decode("owned body");
    CHECK(std::get<ExecuteConsoleCommand_s>(std::get<ApplicationRequestPayload>(decoded)).command == "owned body");

    auto unsupported = router.Match("DELETE", "/api/v1/future", "");
    REQUIRE(std::holds_alternative<HttpResponse_s>(unsupported));
    CHECK(std::get<HttpResponse_s>(unsupported).status == 405);
    CHECK(std::get<HttpResponse_s>(unsupported).allow == "GET, POST");
    CHECK(std::get<HttpResponse_s>(router.Match("POST", "/api/v1/future", "text/plain")).status == 415);
    CHECK(std::get<HttpRouteMatch_s>(router.Match("GET", "/api/v1/future?x=1", "")).request.queryParameters.at("x") == std::vector<std::string>{"1"});
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

    auto& route = std::get<HttpRouteMatch_s>(matched);
    CHECK(route.route.path == "/api/v1/temporary");
    CHECK(route.route.method == "POST");

    auto result = route.Decode("later body");
    CHECK(std::get<ExecuteConsoleCommand_s>(std::get<ApplicationRequestPayload>(result)).command == "later body");
}

TEST_CASE("Default HTTP endpoints decode owned requests and retain the existing contract", "[Http][HttpRouter]")
{
    auto router = HttpRouter{};
    auto match = router.Match("POST", "/api/v1/console/commands", "application/json");
    auto& route = std::get<HttpRouteMatch_s>(match);
    auto command = route.Decode(R"({"command":"@main status"})");
    CHECK(std::get<ExecuteConsoleCommand_s>(std::get<ApplicationRequestPayload>(command)).command == "@main status");

    for (const auto body : {R"({"command":""})", R"({"command":"help","extra":1})", R"({"command":10})", R"({"command":"help\nquit"})", "bad json"})
    {
        auto decoded = route.Decode(body);
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

TEST_CASE("HTTP templates extract multiple path parameters and decoded query values", "[Http][HttpRouter]")
{
    auto router = HttpRouter{{{.method = "GET", .path = "/api/v1/status/{id}/items/{name}", .decode = Status}}};
    auto result = router.Match("GET", "/api/v1/status/1/items/caf%C3%A9?something=1&tag=one&tag=two&flag&empty=&text=a+b%2Bc&literal=a%26b%3Dc", "");
    REQUIRE(std::holds_alternative<HttpRouteMatch_s>(result));

    const auto& request = std::get<HttpRouteMatch_s>(result).request;
    CHECK(request.pathParameters.at("id") == "1");
    CHECK(request.pathParameters.at("name") == "caf\xc3\xa9");
    CHECK(request.queryParameters.at("something") == std::vector<std::string>{"1"});
    CHECK(request.queryParameters.at("tag") == std::vector<std::string>{"one", "two"});
    CHECK(request.queryParameters.at("flag") == std::vector<std::string>{""});
    CHECK(request.queryParameters.at("empty") == std::vector<std::string>{""});
    CHECK(request.queryParameters.at("text") == std::vector<std::string>{"a b+c"});
    CHECK(request.queryParameters.at("literal") == std::vector<std::string>{"a&b=c"});
}

TEST_CASE("HTTP path decoding preserves segment boundaries and separates the query before decoding", "[Http][HttpRouter]")
{
    auto router = HttpRouter{{{.method = "GET", .path = "/items/{id}", .decode = Status}}};
    for (const auto& [target, expected] : std::vector<std::pair<std::string, std::string>>{
             {"/items/a%2Fb", "a/b"}, {"/items/a+b", "a+b"}, {"/items/a%3Fb", "a?b"}, {"/items/%252F", "%2F"}, {"/items/1&something=1", "1&something=1"}})
    {
        const auto result = router.Match("GET", target, "");
        REQUIRE(std::holds_alternative<HttpRouteMatch_s>(result));

        const auto& request = std::get<HttpRouteMatch_s>(result).request;
        CHECK(request.pathParameters.at("id") == expected);
        CHECK(request.queryParameters.empty());
    }

    CHECK(std::get<HttpResponse_s>(router.Match("GET", "/items/a/b", "")).status == 404);
    CHECK(std::get<HttpResponse_s>(router.Match("GET", "/items/", "")).status == 404);
    CHECK(std::get<HttpResponse_s>(router.Match("GET", "/items/a/", "")).status == 404);
}

TEST_CASE("Literal HTTP routes take priority independent of registration order with deterministic fallback", "[Http][HttpRouter]")
{
    for (const auto reverse : {false, true})
    {
        auto routes = std::vector<HttpRoute_s>{
            {.method = "GET", .path = "/items/{id}", .decode = Status},
            {.method = "POST", .path = "/items/latest", .decode = Echo},
            {.method = "GET", .path = "/items/{id}/detail", .decode = Status},
            {.method = "GET", .path = "/items/latest/summary", .decode = Status}};
        if (reverse)
        {
            std::ranges::reverse(routes);
        }

        auto router = HttpRouter{std::move(routes)};
        CHECK(std::get<HttpRouteMatch_s>(router.Match("POST", "/items/latest", "")).request.pathParameters.empty());

        const auto wrongMethod = std::get<HttpResponse_s>(router.Match("GET", "/items/latest", ""));
        CHECK(wrongMethod.status == 405);
        CHECK(wrongMethod.allow == "POST");

        const auto fallback = router.Match("GET", "/items/latest/detail", "");
        REQUIRE(std::holds_alternative<HttpRouteMatch_s>(fallback));
        CHECK(std::get<HttpRouteMatch_s>(fallback).request.pathParameters.at("id") == "latest");
    }
}

TEST_CASE("HTTP template methods retain their own parameter names and reject equivalent registrations", "[Http][HttpRouter]")
{
    auto router = HttpRouter{{{.method = "GET", .path = "/status/{id}", .decode = Status},
                              {.method = "POST", .path = "/status/{account}", .decode = Echo}}};
    CHECK(std::get<HttpRouteMatch_s>(router.Match("GET", "/status/1", "")).request.pathParameters.at("id") == "1");
    CHECK(std::get<HttpRouteMatch_s>(router.Match("POST", "/status/1", "")).request.pathParameters.at("account") == "1");
    CHECK(std::get<HttpResponse_s>(router.Match("PUT", "/status/1?something=1", "")).allow == "GET, POST");
    CHECK_THROWS_AS((HttpRouter{{{.method = "GET", .path = "/status/{id}", .decode = Status},
                                 {.method = "GET", .path = "/status/{other}", .decode = Status}}}),
                    std::invalid_argument);
    for (const auto pattern : {"/a/{}", "/a/{9id}", "/a/{bad-name}", "/a/pre{id}", "/a/{id}/b/{id}", "/a/{id", "/a/id}", "/a/{id}}", "/a/#fragment"})
    {
        INFO(pattern);
        CHECK_THROWS_AS((HttpRouter{{{.method = "GET", .path = pattern, .decode = Status}}}), std::invalid_argument);
    }
}

TEST_CASE("HTTP router rejects malformed escapes controls fragments and invalid UTF8 before admission", "[Http][HttpRouter]")
{
    auto router = HttpRouter{{{.method = "GET", .path = "/status/{id}", .decode = Status}}};
    for (const auto target : {"/status/%", "/status/%0", "/status/%GG", "/status/%00", "/status/%0D", "/status/%7F",
                              "/status/%C0%AF", "/status/%ED%A0%80", "/status/%F4%90%80%80", "/status/%E2%82", "/status/%80",
                              "/status/1?x=%", "/status/1?x=%FF", "/status/1?%00=value", "/status/1?=empty", "/status/1#fragment", "relative", "/status/a b"})
    {
        INFO(target);

        const auto result = router.Match("GET", target, "");
        REQUIRE(std::holds_alternative<HttpResponse_s>(result));

        const auto& response = std::get<HttpResponse_s>(result);
        CHECK(response.status == 400);
        CHECK(nlohmann::json::parse(response.body)["error"]["code"] == "invalid_target");
    }
}

TEST_CASE("HTTP matched parameter values remain owned while body reading is deferred", "[Http][HttpRouter]")
{
    auto result = []
    {
        auto router = HttpRouter{{{.method = "POST", .path = "/status/{id}", .decode = Echo}}};
        auto url = std::string{"/status/alice%20smith?tag=one&%74ag=two&empty=&"};
        return router.Match("POST", url, "");
    }();

    auto& match = std::get<HttpRouteMatch_s>(result);
    CHECK(match.request.pathParameters.at("id") == "alice smith");
    CHECK(match.request.queryParameters.at("tag") == std::vector<std::string>{"one", "two"});

    auto payload = match.Decode("later body");
    CHECK(std::get<ExecuteConsoleCommand_s>(std::get<ApplicationRequestPayload>(payload)).command == "later body");
    CHECK(match.request.pathParameters.at("id") == "alice smith");
}

TEST_CASE("HTTP router handles the root path empty queries and UTF8 range boundaries", "[Http][HttpRouter]")
{
    auto router = HttpRouter{{{.method = "GET", .path = "/", .decode = Status}, {.method = "GET", .path = "/{id}", .decode = Status}}};
    CHECK(std::get<HttpRouteMatch_s>(router.Match("GET", "/?&&", "")).request.queryParameters.empty());

    for (const auto target : {"/%C2%80", "/%E0%A0%80", "/%ED%9F%BF", "/%EE%80%80", "/%F0%90%80%80", "/%F4%8F%BF%BF"})
    {
        CHECK(std::holds_alternative<HttpRouteMatch_s>(router.Match("GET", target, "")));
    }

    CHECK(std::holds_alternative<HttpRouteMatch_s>(HttpRouter{}.Match("GET", "/api/v1/%73tatus?something=1", "")));
}
