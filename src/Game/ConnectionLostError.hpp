#pragma once

// The game connection ended unexpectedly and couldn't be re-established.
class ConnectionLostError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
