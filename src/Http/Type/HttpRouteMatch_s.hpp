#pragma once

#include "HttpRoute_s.hpp"

struct HttpRouteMatch_s
{
    HttpRoute_s route;
    HttpEndpointRequest_s request;

    [[nodiscard]] HttpDecodeResult Decode(std::string body)
    {
        if (!route.decode)
        {
            throw std::logic_error{"Upgrade routes do not decode application requests"};
        }

        request.body = std::move(body);
        return route.decode(request);
    }
};
