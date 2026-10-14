#pragma once

// The session can no longer stay in sync.
class ProtocolError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
