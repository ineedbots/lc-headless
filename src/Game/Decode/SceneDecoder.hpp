#pragma once

#include "../../Io/Packet.hpp"
#include "../Protocol/Protocol.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameState_s.hpp"

// The packets that rebuild the scene, reset its animations, move the camera and play music and sounds.
class SceneDecoder
{
public:
    SceneDecoder() = delete;

    static void Decode(ServerProt_e prot, Packet& packet, GameState_s& state, const Protocol& protocol);
};
