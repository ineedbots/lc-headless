#include "pch.hpp"
#include "ConsoleCommandsEndpoint.hpp"

#include "../../Application/Type/ConsoleCommandResult_s.hpp"
#include "../../Application/Type/ExecuteConsoleCommand_s.hpp"
#include "../../Console/CommandExecution.hpp"
#include "../../Application/Type/CompletedApplicationRequest_s.hpp"
#include "../../Application/Type/ApplicationOperations_s.hpp"
#include "../Type/HttpRoute_s.hpp"
#include "../Type/HttpEndpointRequest_s.hpp"
#include "../Type/HttpResponse_s.hpp"
#include "../../Utils/StringUtils.hpp"
#include "../HttpJson.hpp"
#include "../HttpResponses.hpp"

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
    auto body = nlohmann::json{{"requestId", std::to_string(result.id)}, {"outcome", result.outcome}, {"output", command.output}, {"outputTruncated", command.outputTruncated}, {"executionStarted", command.executionStarted}, {"recipients", nlohmann::json::array()}};
    for (const auto& recipient : command.recipients)
    {
        auto item = nlohmann::json{{"account", recipient.account}, {"outcome", recipient.outcome}};
        if (!recipient.errorCode.empty())
        {
            item["errorCode"] = recipient.errorCode;
        }

        body["recipients"].push_back(std::move(item));
    }

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

    if (!result.errorCode.empty())
    {
        body["error"] = {{"code", result.errorCode}, {"message", result.errorCode}};
    }

    return HttpJson::Response(code, body);
}
