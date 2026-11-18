#pragma once

#include "../Type/HttpRoute_s.hpp"
#include "../Type/HttpEndpointKind_e.hpp"

class ApplicationEventsEndpoint
{
public:
    ApplicationEventsEndpoint() = delete;
    static constexpr auto KIND = HttpEndpointKind_e::WebSocketUpgrade;

    [[nodiscard]] static HttpRoute_s Route();
};
