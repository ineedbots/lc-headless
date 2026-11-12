#pragma once

#include "../Application/ApplicationRequestBridge.hpp"
#include "HttpResponse_s.hpp"

class HttpResponses
{
public:
    HttpResponses() = delete;
    [[nodiscard]] static HttpResponse_s Error(unsigned status, std::string_view code, std::string_view message, std::optional<u64> id = {}, bool close = false);
    [[nodiscard]] static HttpResponse_s Complete(const CompletedApplicationRequest_s& result);
    [[nodiscard]] static HttpResponse_s Timeout(u64 id, bool executionStarted, const CompletedApplicationRequest_s* result = nullptr);

private:
    static HttpResponse_s CompletePayload(const CompletedApplicationRequest_s& result, const ApplicationStatus_s& payload);
    static HttpResponse_s CompletePayload(const CompletedApplicationRequest_s& result, const ConsoleCommandResult_s& payload);
};
