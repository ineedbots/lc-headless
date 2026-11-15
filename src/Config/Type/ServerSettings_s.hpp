#pragma once

#include "../TransportNames.hpp"

#include <nlohmann/json.hpp>

struct ServerSettings_s
{
    Transport_e transport = Transport_e::Ws;
    std::string host;
    // An s32, not a u16, so 70000 fails validation instead of wrapping to a valid port.
    s32 port = 0;
    s32 world = 0;
    std::string origin;
    std::string tlsCaFile = "SYSTEM";
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ServerSettings_s, transport, host, port, world, origin, tlsCaFile)
