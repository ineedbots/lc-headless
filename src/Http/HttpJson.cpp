#include "pch.hpp"
#include "HttpJson.hpp"

HttpResponse_s HttpJson::Response(unsigned status, const nlohmann::json& body)
{
    return {.status = status, .body = body.dump(-1, ' ', false, nlohmann::json::error_handler_t::replace)};
}
