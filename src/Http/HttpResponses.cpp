#include "pch.hpp"
#include "HttpResponses.hpp"
#include "Endpoints/ApplicationStatusEndpoint.hpp"
#include "Endpoints/ConsoleCommandsEndpoint.hpp"
#include "HttpJson.hpp"

HttpResponse_s HttpResponses::Error(unsigned status, std::string_view code, std::string_view message, std::optional<u64> id, bool close)
{
    auto body = nlohmann::json{{"error", {{"code", code}, {"message", message}}}};
    if (id)
    {
        body["requestId"] = std::to_string(*id);
    }
    auto response = HttpJson::Response(status, body);
    response.close = close;
    return response;
}

HttpResponse_s HttpResponses::Complete(const CompletedApplicationRequest_s& result)
{
    return std::visit([&](const auto& payload)
    {
        return CompletePayload(result, payload);
    }, result.payload);
}

HttpResponse_s HttpResponses::CompletePayload(const CompletedApplicationRequest_s& result, const ApplicationStatus_s& payload)
{
    return ApplicationStatusEndpoint::Respond(result.id, payload, result.errorCode);
}

HttpResponse_s HttpResponses::CompletePayload(const CompletedApplicationRequest_s& result, const ConsoleCommandResult_s& payload)
{
    return ConsoleCommandsEndpoint::Respond(result.id, result.outcome, result.errorCode, payload);
}

HttpResponse_s HttpResponses::Timeout(u64 id, bool executionStarted, const CompletedApplicationRequest_s* result)
{
    auto body = nlohmann::json{{"requestId", std::to_string(id)}, {"outcome", "cancelled"}, {"error", {{"code", "deadline_exceeded"}, {"message", "Request expired; execution effects may already have occurred"}}}, {"executionStarted", executionStarted}};
    if (result)
    {
        if (const auto command = std::get_if<ConsoleCommandResult_s>(&result->payload))
        {
            body["output"] = command->output;
            body["outputTruncated"] = command->outputTruncated;
        }
    }
    return HttpJson::Response(504, body);
}
