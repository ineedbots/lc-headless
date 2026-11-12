#include "pch.hpp"
#include "ApplicationEventsEndpoint.hpp"

#include "../Type/HttpRoute_s.hpp"

HttpRoute_s ApplicationEventsEndpoint::Route()
{
    return {.method = "GET", .path = "/api/v1/events", .webSocket = true};
}
