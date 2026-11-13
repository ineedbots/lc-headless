#include "pch.hpp"
#include "ApplicationStatusEndpoint.hpp"

#include "../../Application/Type/ApplicationStatus_s.hpp"
#include "../../Application/Type/GetApplicationStatus_s.hpp"
#include "../../Application/Type/CompletedApplicationRequest_s.hpp"
#include "../../Application/Type/ApplicationOperations_s.hpp"
#include "../Type/HttpRoute_s.hpp"
#include "../Type/HttpEndpointRequest_s.hpp"
#include "../Type/HttpResponse_s.hpp"
#include "../HttpJson.hpp"
#include "../HttpPayloadJson.hpp"
#include "../Type/HttpError_s.hpp"

#include <nlohmann/json.hpp>

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
    auto body = nlohmann::json(status);
    body["requestId"] = std::to_string(result.id);

    if (!result.errorCode.empty())
    {
        body["error"] = HttpError_s{result.errorCode, result.errorCode};
    }

    return HttpJson::Response(200, body);
}
