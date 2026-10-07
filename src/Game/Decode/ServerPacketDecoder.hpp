#pragma once

#include "../../Core/Logger.hpp"
#include "../../Io/Packet.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameState_s.hpp"
#include "PlayerInfoDecoder.hpp"
#include "ZoneDecoder.hpp"

// Applies each server packet to the game state. Packets must arrive in stream order.
class ServerPacketDecoder
{
public:
    explicit ServerPacketDecoder(std::shared_ptr<Logger> logger = Logger::GetDefault());

    void Decode(ServerProt_e prot, std::span<const u8> payload, GameState_s& state);
    void Reset();

private:
    static constexpr std::size_t MAX_REMEMBERED_MESSAGE_IDS = 100;

    void DecodePacket(ServerProt_e prot, Packet& packet, GameState_s& state);
    void DecodePlayerInfo(Packet& packet, GameState_s& state);
    void DecodeStat(Packet& packet, GameState_s& state);
    void DecodeTab(Packet& packet, GameState_s& state);
    void DecodePrivateMessage(Packet& packet, GameState_s& state);

    std::shared_ptr<Logger> m_logger;
    PlayerInfoDecoder m_playerInfo;
    ZoneDecoder m_zone;
    std::deque<s32> m_privateMessageIds;
};
