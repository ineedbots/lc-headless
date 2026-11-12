#pragma once
#include "../Application/ApplicationRequestBridge.hpp"
#include "HttpResponse_s.hpp"
#include "HttpEndpointRequest_s.hpp"

using HttpDecodeResult = std::variant<ApplicationRequestPayload, HttpResponse_s>;

// Decoders validate owned application values. They cannot dispatch application work.
struct HttpRoute_s
{
    using Decoder = HttpDecodeResult (*)(const HttpEndpointRequest_s& request);
    std::string method;
    std::string path;
    bool requiresJson = false;
    Decoder decode = nullptr;
};
