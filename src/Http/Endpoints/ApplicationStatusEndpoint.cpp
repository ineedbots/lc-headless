#include "pch.hpp"
#include "ApplicationStatusEndpoint.hpp"
#include "../HttpJson.hpp"

HttpRoute_s ApplicationStatusEndpoint::Route()
{
    return {.method = "GET", .path = "/api/v1/status", .decode = Decode};
}

HttpDecodeResult ApplicationStatusEndpoint::Decode(const HttpEndpointRequest_s&)
{
    return ApplicationRequestPayload{GetApplicationStatus_s{}};
}

HttpResponse_s ApplicationStatusEndpoint::Respond(u64 id, const ApplicationStatus_s& status, std::string_view errorCode)
{
    auto body = nlohmann::json{{"requestId", std::to_string(id)},
                               {"application", {{"state", status.state}, {"uptimeMs", status.uptimeMs}}},
                               {"accounts", nlohmann::json::array()}};
    for (const auto& account : status.accounts)
    {
        body["accounts"].push_back({{"name", account.name}, {"started", account.started}, {"finished", account.finished}, {"status", account.status}});
    }

    if (!errorCode.empty())
    {
        body["error"] = {{"code", errorCode}, {"message", errorCode}};
    }

    return HttpJson::Response(200, body);
}
