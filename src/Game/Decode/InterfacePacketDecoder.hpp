#pragma once

#include "../../Console/Logger.hpp"
#include "../../Io/Packet.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameState_s.hpp"

// The packets that open and close interfaces, set the tabs and change components.
class InterfacePacketDecoder
{
public:
    InterfacePacketDecoder() = delete;

    static void Decode(ServerProt_e prot, Packet& packet, GameState_s& state, Logger& logger);
};
