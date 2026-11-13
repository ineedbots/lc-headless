#pragma once

#include "Type/HttpEndpointCatalog_s.hpp"
#include "Endpoints/ConsoleCommandsEndpoint.hpp"
#include "Endpoints/ApplicationStatusEndpoint.hpp"
#include "Endpoints/ApplicationEventsEndpoint.hpp"

class HttpEndpoints
{
public:
    HttpEndpoints() = delete;
    using Catalog = HttpEndpointCatalog_s<ConsoleCommandsEndpoint, ApplicationStatusEndpoint, ApplicationEventsEndpoint>;
    static std::vector<HttpRoute_s> Routes();
};
