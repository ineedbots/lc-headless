#pragma once

class ConnectionLostError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
