#pragma once

#include "../../Io/Packet.hpp"
#include "../Protocol/Protocol.hpp"
#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Npc_s.hpp"

class NpcInfoDecoder
{
public:
    explicit NpcInfoDecoder(Protocol protocol);

    void Decode(std::span<const u8> payload, GameState_s& state) const;

private:
    static constexpr u32 TYPE_BITS = 11;
    // The webclient keeps reading new NPCs while at least this many bits remain, not a whole entry.
    static constexpr std::size_t MIN_NEW_NPC_BITS = 22;

    void ReadNew(Packet& packet, const GameState_s& state, std::vector<Npc_s>& npcs, std::vector<std::size_t>& extended) const;
    void ReadExtended(Packet& packet, GameState_s& state, Npc_s& npc, std::vector<NpcHit_s>& hits, std::vector<NpcSaid_s>& said) const;

    Protocol m_protocol;
};
