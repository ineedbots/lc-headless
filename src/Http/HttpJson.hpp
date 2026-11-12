#pragma once
#include "HttpResponse_s.hpp"
#include <nlohmann/json.hpp>

// Kept in the HTTP adapter; application and transport interfaces use owned values.
class HttpJson
{
public:
    HttpJson() = delete;
    [[nodiscard]] static HttpResponse_s Response(unsigned status, const nlohmann::json& body);
};
