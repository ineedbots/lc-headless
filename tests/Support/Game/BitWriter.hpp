#pragma once

// MSB-first bit writer for building PLAYER_INFO and NPC_INFO fixtures, as the engine's pBit does.
class BitWriter
{
public:
    BitWriter& Put(u32 bitCount, s32 value);
    [[nodiscard]] std::vector<u8> GetBytes() const;
    [[nodiscard]] std::size_t GetBitPos() const;

private:
    std::vector<u8> m_bytes;
    std::size_t m_bitPos = 0;
};
