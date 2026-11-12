#pragma once

#include "../Type/HttpRoute_s.hpp"

class ApplicationStatusEndpoint
{
public:
    ApplicationStatusEndpoint() = delete;
    [[nodiscard]] static HttpRoute_s Route();
    [[nodiscard]] static HttpResponse_s Respond(u64 id, const ApplicationStatus_s& status, std::string_view errorCode);

private:
    static HttpDecodeResult Decode(const HttpEndpointRequest_s& request);
};
