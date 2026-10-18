#pragma once

#include "ConnectionError.hpp"

class ConnectionClosedError : public ConnectionError
{
public:
    using ConnectionError::ConnectionError;
};
