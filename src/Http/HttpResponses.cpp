#include "pch.hpp"
#include "HttpResponses.hpp"

#include "Type/HttpResponse_s.hpp"
#include "../Application/Type/CompletedApplicationRequest_s.hpp"
#include "../Application/Type/ConsoleCommandResult_s.hpp"
#include "HttpEndpoints.hpp"
#include "HttpJson.hpp"
#include "HttpPayloadJson.hpp"
#include "Type/HttpError_s.hpp"

#include <nlohmann/json.hpp>

HttpResponse_s HttpResponses::Error(unsigned status, std::string_view code, std::string_view message, std::optional<u64> id, bool close)
{
    auto body = nlohmann::json{{"error", HttpError_s{std::string{code}, std::string{message}}}};
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
        return HttpEndpoints::Catalog::Respond(result, payload);
    }, result.payload);
}

HttpResponse_s HttpResponses::Timeout(u64 id, bool executionStarted, const CompletedApplicationRequest_s* result)
{
    auto body = nlohmann::json{{"requestId", std::to_string(id)}, {"outcome", "cancelled"}, {"error", HttpError_s{"deadline_exceeded", "Request expired; execution effects may already have occurred"}}, {"executionStarted", executionStarted}};
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
