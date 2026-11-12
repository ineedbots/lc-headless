#pragma once
#include "HttpRoute_s.hpp"

struct HttpRouteMatch_s
{
    HttpRoute_s route;
    HttpEndpointRequest_s request;

    [[nodiscard]] HttpDecodeResult Decode(std::string body)
    {
        request.body = std::move(body);
        return route.decode(request);
    }
};
