#pragma once

#include <nlohmann/json.hpp>

// A SOCKS5 proxy. An empty host connects directly.
struct ProxySettings_s
{
    std::string host;
    // An s32, not a u16, so 70000 fails validation instead of wrapping to a valid port.
    s32 port = 1080;
    // Empty for no authentication. Neither is ever logged or put in an error message.
    std::string username;
    std::string password;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ProxySettings_s, host, port, username, password)
