#pragma once

#include "../../Io/Packet.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameState_s.hpp"

// The packets for game and private messages, the friend and ignore lists, and the chat settings.
// It remembers the private messages it has seen, since the server can send one twice.
class SocialDecoder
{
public:
    void Decode(ServerProt_e prot, Packet& packet, GameState_s& state);
    void Reset();

private:
    static constexpr std::size_t MAX_REMEMBERED_MESSAGE_IDS = 100;

    void DecodePrivateMessage(Packet& packet, GameState_s& state);

    std::deque<s32> m_privateMessageIds;
};
