#pragma once

#include "../Type/HttpRoute_s.hpp"

class ConsoleCommandsEndpoint
{
public:
    ConsoleCommandsEndpoint() = delete;
    [[nodiscard]] static HttpRoute_s Route();
    [[nodiscard]] static HttpResponse_s Respond(u64 id, std::string_view outcome, std::string_view errorCode, const ConsoleCommandResult_s& command);

private:
    static HttpDecodeResult Decode(const HttpEndpointRequest_s& request);
};
