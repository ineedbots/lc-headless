#pragma once

#include "../../Application/ApplicationRequestBridge.hpp"
#include "HttpResponse_s.hpp"
#include "HttpEndpointRequest_s.hpp"
#include "../../Application/Type/CompletedApplicationRequest_s.hpp"

using HttpDecodeResult = std::variant<ApplicationRequestPayload, HttpResponse_s>;

// Decoders validate owned application values. They cannot dispatch application work.
struct HttpRoute_s
{
    using Decoder = HttpDecodeResult (*)(const HttpEndpointRequest_s& request);
    std::string method;
    std::string path;
    bool requiresJson = false;
    Decoder decode = nullptr;
    bool webSocket = false;
    // A payload-less cancellation can fall back to the common response adapter.
    std::optional<HttpResponse_s> (*respond)(const CompletedApplicationRequest_s& result) = nullptr;
};
