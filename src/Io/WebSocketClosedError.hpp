#pragma once

#include "WebSocketError.hpp"

class WebSocketClosedError : public WebSocketError
{
public:
    using WebSocketError::WebSocketError;
};
