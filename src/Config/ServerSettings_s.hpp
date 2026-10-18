#pragma once

#include "Transport_e.hpp"

struct ServerSettings_s
{
    Transport_e transport = Transport_e::Ws;
    std::string host;
    // An s32, not a u16, so 70000 fails validation instead of wrapping to a valid port.
    s32 port = 0;
    std::string origin;
    std::string tlsCaFile = "SYSTEM";
};
