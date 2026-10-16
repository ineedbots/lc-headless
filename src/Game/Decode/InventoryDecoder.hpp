#pragma once

#include "../../Io/Packet.hpp"
#include "../Protocol/Protocol.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameState_s.hpp"

// The packets that fill, change and stop an inventory.
class InventoryDecoder
{
public:
    InventoryDecoder() = delete;

    static void Decode(ServerProt_e prot, Packet& packet, GameState_s& state, const Protocol& protocol);
};
