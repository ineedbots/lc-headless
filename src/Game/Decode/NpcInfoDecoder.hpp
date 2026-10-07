#pragma once

#include "../../Io/Packet.hpp"
#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Npc_s.hpp"

class NpcInfoDecoder
{
public:
    NpcInfoDecoder() = delete;

    static void Decode(std::span<const u8> payload, GameState_s& state);

private:
    static constexpr u32 INDEX_BITS = 14;
    static constexpr u32 TYPE_BITS = 11;
    static constexpr s32 END_OF_LIST = 16383;
    // The webclient keeps reading new NPCs while at least this many bits remain, not a whole entry.
    static constexpr std::size_t MIN_NEW_NPC_BITS = 22;

    static void ReadNew(Packet& packet, const GameState_s& state, std::vector<Npc_s>& npcs, std::vector<std::size_t>& extended);
    static void ReadExtended(Packet& packet, GameState_s& state, Npc_s& npc, std::vector<NpcHit_s>& hits);
};
