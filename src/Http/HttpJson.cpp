#include "pch.hpp"
#include "HttpJson.hpp"

#include "Type/HttpError_s.hpp"
#include "Type/HttpResponse_s.hpp"
#include "Application/Type/CompletedApplicationRequest_s.hpp"

#include <nlohmann/json.hpp>

HttpResponse_s HttpJson::Response(unsigned status, const nlohmann::json& body)
{
    return {.status = status, .body = body.dump(-1, ' ', false, nlohmann::json::error_handler_t::replace)};
}

HttpResponse_s HttpJson::CompletedResponse(unsigned status, nlohmann::json body, const CompletedApplicationRequest_s& result)
{
    body["requestId"] = std::to_string(result.id);

    if (!result.errorCode.empty())
    {
        body["error"] = HttpError_s{result.errorCode, result.errorCode};
    }

    return Response(status, body);
}
