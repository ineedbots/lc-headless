#pragma once

#include "../../Console/Logger.hpp"
#include "../../Io/Packet.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameState_s.hpp"

// The packets about the local player's account and session: varps, stats, run energy, the hint arrow,
// the player menu, the reboot timer and the last login.
class PlayerStateDecoder
{
public:
    PlayerStateDecoder() = delete;

    static void Decode(ServerProt_e prot, Packet& packet, GameState_s& state, Logger& logger);
};
