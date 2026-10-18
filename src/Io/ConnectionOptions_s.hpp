#pragma once

#include "../Config/Transport_e.hpp"

struct Socks5Proxy_s
{
    std::string host;
    u16 port = 0;
    // Empty for no authentication. Never logged.
    std::string username;
    std::string password;
};

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
    // Connects through it when set. The proxy resolves host, unless it's an IPv4 address.
    std::optional<Socks5Proxy_s> proxy;
    // Everything before the connection opens: the lookup, the TCP connect, the SOCKS5 exchange, and for a WebSocket,
    // TLS and the upgrade.
    std::chrono::milliseconds connectTimeout = 10s;
};
