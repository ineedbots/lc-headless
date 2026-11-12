#pragma once

#include "../Type/HttpRoute_s.hpp"

class ApplicationEventsEndpoint
{
public:
    ApplicationEventsEndpoint() = delete;
    static HttpRoute_s Route();
};
