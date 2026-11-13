#pragma once

#include "../Type/HttpRoute_s.hpp"

#include "../../Application/Type/ApplicationStatus_s.hpp"
#include "../../Application/Type/CompletedApplicationRequest_s.hpp"
#include "../Type/HttpResponse_s.hpp"
#include "../Type/HttpEndpointRequest_s.hpp"

class ApplicationStatusEndpoint
{
public:
    ApplicationStatusEndpoint() = delete;
    using Payload = ApplicationStatus_s;
    [[nodiscard]] static HttpRoute_s Route();
    [[nodiscard]] static HttpResponse_s Respond(const CompletedApplicationRequest_s& result, const ApplicationStatus_s& status);

private:
    static HttpDecodeResult Decode(const HttpEndpointRequest_s& request);
};
