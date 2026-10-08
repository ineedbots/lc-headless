#pragma once

// Tells whether a loopback port is free for a test server. IXWebSocket's server sets SO_REUSEADDR,
// which on Windows lets a second server bind a port that's already listening, so its own listen()
// succeeds even when another test server, in this process or another, holds the port. A probe bind
// that refuses to share the address can tell.
class LoopbackPort
{
public:
    LoopbackPort() = delete;

    [[nodiscard]] static bool IsFree(int port);
};
