#pragma once

#include "../../Io/Packet.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Player_s.hpp"

class PlayerInfoDecoder
{
public:
    void Decode(std::span<const u8> payload, GameState_s& state);
    void Reset();

    [[nodiscard]] static Appearance_s ReadAppearance(std::span<const u8> bytes);

private:
    static constexpr u32 INDEX_BITS = 11;
    static constexpr u32 LEVEL_BITS = 2;
    static constexpr u32 LOCAL_COORD_BITS = 7;
    static constexpr s32 END_OF_LIST = 2047;
    static constexpr s32 MOVE_PLACE = 3;

    struct ExtendedTarget_s
    {
        bool isLocal = false;
        std::size_t position = 0;
    };

    static void ReadLocal(Packet& packet, GameState_s& state, std::vector<ExtendedTarget_s>& extended);
    void ReadNew(Packet& packet, GameState_s& state, std::vector<Player_s>& players, std::vector<ExtendedTarget_s>& extended);
    void ReadExtended(Packet& packet, GameState_s& state, Player_s& player, bool isLocal);
    static void ReadChat(Packet& packet, GameState_s& state, Player_s& player);

    // Kept across removals: the server skips APPEARANCE for a player whose current look this viewer has seen.
    std::unordered_map<u16, Appearance_s> m_appearances;
};
