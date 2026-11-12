#pragma once

struct HttpSettings_s
{
    std::string host;
    s64 port = 8080;
    std::chrono::milliseconds requestTimeoutMs = 30000ms;
    s64 maxPendingRequests = 64;
    s64 maxRequestBodyBytes = 16384;
    s64 maxOutputBytes = 1048576;
};
