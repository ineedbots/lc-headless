#pragma once

#include "../../Console/Logger.hpp"
#include "../../Io/Packet.hpp"
#include "../Protocol/Protocol.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameState_s.hpp"
#include "PlayerInfoDecoder.hpp"
#include "SocialDecoder.hpp"
#include "ZoneDecoder.hpp"

// Hands each packet to the decoder for its area. Packets must arrive in stream order.
class ServerPacketDecoder
{
public:
    explicit ServerPacketDecoder(Protocol protocol, std::shared_ptr<Logger> logger = Logger::GetDefault());

    void Decode(ServerProt_e prot, std::span<const u8> payload, GameState_s& state);
    void Reset();

private:
    void DecodePacket(ServerProt_e prot, Packet& packet, GameState_s& state);
    void DecodePlayerInfo(Packet& packet, GameState_s& state);

    std::shared_ptr<Logger> m_logger;
    PlayerInfoDecoder m_playerInfo;
    ZoneDecoder m_zone;
    SocialDecoder m_social;
};
