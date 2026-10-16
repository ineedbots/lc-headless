#pragma once

#include "../../Io/Packet.hpp"

// Field encodings that several server packets share.
class PacketFields
{
public:
    // A u16 id with this value means none.
    static constexpr u16 NO_ID = 0xFFFF;
    static constexpr std::size_t NAME37_SIZE = 8;

    PacketFields() = delete;

    // A u16 id, with NO_ID read as -1.
    [[nodiscard]] static s32 ReadId(Packet& packet);
    // A player's name as base 37.
    [[nodiscard]] static u64 ReadName37(Packet& packet);
};
