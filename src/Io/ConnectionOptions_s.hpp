#pragma once

#include "../Config/Transport_e.hpp"

struct ConnectionOptions_s
{
    Transport_e transport = Transport_e::Ws;
    std::string host;
    u16 port = 0;
    // WebSocket only. Empty sends no Origin header.
    std::string origin;
    // wss only: a PEM bundle's path, SYSTEM or NONE.
    std::string tlsCaFile = "SYSTEM";
    std::string subprotocol = "binary";
    // Everything before the connection opens: the lookup, the TCP connect, TLS and the upgrade.
    std::chrono::milliseconds connectTimeout = 10s;
};
