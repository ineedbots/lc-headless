#include "pch.hpp"

#include "Http/Endpoints/ApplicationStatusEndpoint.hpp"
#include "Http/Endpoints/ConsoleCommandsEndpoint.hpp"
#include "Http/Type/HttpEndpointRequest_s.hpp"
#include "Http/Type/HttpResponse_s.hpp"
#include "Application/Type/ApplicationStatus_s.hpp"
#include "Application/Type/CompletedApplicationRequest_s.hpp"
#include "Application/Type/ConsoleCommandResult_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <nlohmann/json.hpp>

TEST_CASE("Status endpoint responses preserve empty accounts and optional error metadata", "[Http]")
{
    auto result = CompletedApplicationRequest_s{.id = std::numeric_limits<u64>::max()};
    auto expected = nlohmann::json{
        {"requestId", "18446744073709551615"},
        {"application", {{"state", "running"}, {"uptimeMs", 0}}},
        {"accounts", nlohmann::json::array()}};

    SECTION("success")
    {
    }

    SECTION("error")
    {
        result.errorCode = "snapshot_failed";
        expected["error"] = {{"code", "snapshot_failed"}, {"message", "snapshot_failed"}};
    }

    const auto response = ApplicationStatusEndpoint::Respond(result, ApplicationStatus_s{});
    CHECK(response.status == 200);
    CHECK(nlohmann::json::parse(response.body) == expected);
}

TEST_CASE("Command endpoint response schemas preserve outcomes statuses and escaped output", "[Http]")
{
    const auto [outcome, status] = GENERATE(
        std::pair{"completed", 200u},
        std::pair{"rejected", 422u},
        std::pair{"failed", 500u},
        std::pair{"cancelled", 503u});
    auto result = CompletedApplicationRequest_s{.id = 42, .outcome = outcome};
    const auto command = ConsoleCommandResult_s{.output = "quoted \"text\"\n\\path", .executionStarted = true};
    auto expected = nlohmann::json{
        {"requestId", "42"}, {"outcome", outcome}, {"output", command.output}, {"outputTruncated", false}, {"executionStarted", true}, {"recipients", nlohmann::json::array()}};

    SECTION("without error")
    {
    }

    SECTION("with error")
    {
        result.errorCode = "command_error";
        expected["error"] = {{"code", "command_error"}, {"message", "command_error"}};
    }

    const auto response = ConsoleCommandsEndpoint::Respond(result, command);
    CHECK(response.status == status);
    CHECK(nlohmann::json::parse(response.body) == expected);
}

TEST_CASE("Command endpoint validation rejects null and extra fields with its existing error schema", "[Http]")
{
    const auto body = GENERATE("null", "{}", R"({"command":null})", R"({"command":"ok","extra":true})");
    const auto route = ConsoleCommandsEndpoint::Route();
    const auto decoded = route.decode(HttpEndpointRequest_s{.body = body});
    REQUIRE(std::holds_alternative<HttpResponse_s>(decoded));
    const auto& response = std::get<HttpResponse_s>(decoded);
    CHECK(response.status == 400);
    CHECK(nlohmann::json::parse(response.body) == nlohmann::json{{"error", {{"code", "invalid_command"}, {"message", "Expected one command string"}}}});
}
