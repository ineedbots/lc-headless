#include "pch.hpp"
#include "ConsoleCommandsEndpoint.hpp"

#include "../../Application/Requests/Type/ConsoleCommandResult_s.hpp"
#include "../../Application/Requests/Type/ExecuteConsoleCommand_s.hpp"
#include "../../Application/Requests/Type/CompletedApplicationRequest_s.hpp"
#include "../../Application/Requests/Type/ApplicationOperations_s.hpp"
#include "../Type/HttpRoute_s.hpp"
#include "../Type/HttpEndpointRequest_s.hpp"
#include "../Type/HttpResponse_s.hpp"
#include "../../Utils/StringUtils.hpp"
#include "../HttpJson.hpp"
#include "../HttpResponses.hpp"

#include <nlohmann/json.hpp>

HttpRoute_s ConsoleCommandsEndpoint::Route()
{
    return {.method = "POST", .path = "/api/v1/console/commands", .requiresJson = true, .decode = Decode};
}

HttpDecodeResult ConsoleCommandsEndpoint::Decode(const HttpEndpointRequest_s& request)
{
    const auto value = nlohmann::json::parse(request.body, nullptr, false);
    if (!value.is_object() || value.size() != 1 || !value.contains("command") || !value["command"].is_string())
    {
        return HttpResponses::Error(400, "invalid_command", "Expected one command string");
    }

    auto line = value["command"].get<std::string>();
    if (StringUtils::Trim(line).empty() ||
        line.find_first_of(std::string{"\r\n\0", 3}) != std::string::npos)
    {
        return HttpResponses::Error(400, "invalid_command", "Expected a nonempty single line command");
    }

    return ApplicationRequestPayload{ExecuteConsoleCommand_s{std::move(line)}};
}

HttpResponse_s ConsoleCommandsEndpoint::Respond(const CompletedApplicationRequest_s& result, const ConsoleCommandResult_s& command)
{
    auto body = nlohmann::json(command);
    body["outcome"] = result.outcome;

    auto code = 200u;
    if (result.outcome == "rejected")
    {
        code = 422;
    }
    else if (result.outcome == "failed")
    {
        code = 500;
    }
    else if (result.outcome == "cancelled")
    {
        code = 503;
    }

    return HttpJson::CompletedResponse(code, std::move(body), result);
}
