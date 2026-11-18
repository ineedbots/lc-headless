#pragma once

#include <nlohmann/json.hpp>

struct HttpSettings_s
{
    static constexpr auto PORT_RANGE = std::pair<s64, s64>{1, 65535};
    static constexpr auto REQUEST_TIMEOUT_MS_RANGE = std::pair<s64, s64>{100, 120000};
    static constexpr auto PENDING_REQUESTS_RANGE = std::pair<s64, s64>{1, 1024};
    static constexpr auto REQUEST_BODY_BYTES_RANGE = std::pair<s64, s64>{1, 1048576};
    static constexpr auto OUTPUT_BYTES_RANGE = std::pair<s64, s64>{1, 16777216};

    std::string host;
    s64 port = 8080;
    std::chrono::milliseconds requestTimeoutMs = 30000ms;
    s64 maxPendingRequests = 64;
    s64 maxRequestBodyBytes = 16384;
    s64 maxOutputBytes = 1048576;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(HttpSettings_s, host, port, requestTimeoutMs, maxPendingRequests, maxRequestBodyBytes, maxOutputBytes)
