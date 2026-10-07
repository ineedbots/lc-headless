#pragma once

// The server sent bytes this client can't follow, so the session can no longer stay in sync.
class ProtocolError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
