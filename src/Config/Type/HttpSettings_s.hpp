#pragma once

#include <nlohmann/json.hpp>

struct HttpSettings_s
{
    std::string host;
    s64 port = 8080;
    std::chrono::milliseconds requestTimeoutMs = 30000ms;
    s64 maxPendingRequests = 64;
    s64 maxRequestBodyBytes = 16384;
    s64 maxOutputBytes = 1048576;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(HttpSettings_s, host, port, requestTimeoutMs, maxPendingRequests, maxRequestBodyBytes, maxOutputBytes)
