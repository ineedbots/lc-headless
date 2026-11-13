#include "pch.hpp"
#include "ApplicationStatusEndpoint.hpp"

#include "../../Application/Type/ApplicationStatus_s.hpp"
#include "../../Application/Type/GetApplicationStatus_s.hpp"
#include "../../Accounts/Type/AccountStatus_s.hpp"
#include "../../Application/Type/CompletedApplicationRequest_s.hpp"
#include "../../Application/Type/ApplicationOperations_s.hpp"
#include "../Type/HttpRoute_s.hpp"
#include "../Type/HttpEndpointRequest_s.hpp"
#include "../Type/HttpResponse_s.hpp"
#include "../HttpJson.hpp"

HttpRoute_s ApplicationStatusEndpoint::Route()
{
    return {.method = "GET", .path = "/api/v1/status", .decode = Decode};
}

HttpDecodeResult ApplicationStatusEndpoint::Decode(const HttpEndpointRequest_s&)
{
    return ApplicationRequestPayload{GetApplicationStatus_s{}};
}

HttpResponse_s ApplicationStatusEndpoint::Respond(const CompletedApplicationRequest_s& result, const ApplicationStatus_s& status)
{
    auto body = nlohmann::json{{"requestId", std::to_string(result.id)},
                               {"application", {{"state", status.state}, {"uptimeMs", status.uptimeMs}}},
                               {"accounts", nlohmann::json::array()}};
    for (const auto& account : status.accounts)
    {
        body["accounts"].push_back({{"name", account.name}, {"started", account.started}, {"finished", account.finished}, {"status", account.status}});
    }

    if (!result.errorCode.empty())
    {
        body["error"] = {{"code", result.errorCode}, {"message", result.errorCode}};
    }

    return HttpJson::Response(200, body);
}
