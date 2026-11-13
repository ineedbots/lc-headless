#pragma once

#include "../Type/HttpRoute_s.hpp"

#include "../../Application/Type/ConsoleCommandResult_s.hpp"
#include "../../Application/Type/CompletedApplicationRequest_s.hpp"
#include "../Type/HttpResponse_s.hpp"
#include "../Type/HttpEndpointRequest_s.hpp"

class ConsoleCommandsEndpoint
{
public:
    ConsoleCommandsEndpoint() = delete;
    using Payload = ConsoleCommandResult_s;
    [[nodiscard]] static HttpRoute_s Route();
    [[nodiscard]] static HttpResponse_s Respond(const CompletedApplicationRequest_s& result, const ConsoleCommandResult_s& command);

private:
    static HttpDecodeResult Decode(const HttpEndpointRequest_s& request);
};
