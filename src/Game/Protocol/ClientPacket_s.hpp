#pragma once

#include "ClientProt.hpp"

struct ClientPacket_s
{
    ClientProt_e prot;
    std::vector<u8> payload;
};
