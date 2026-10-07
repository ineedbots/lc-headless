#pragma once

#include "../Core/BigUInt.hpp"
#include "Isaac.hpp"

class Packet
{
public:
    Packet();
    explicit Packet(std::span<const u8> data);

    [[nodiscard]] static s32 GetCrc(std::span<const u8> source);
    [[nodiscard]] static bool CheckCrc(std::span<const u8> source, s32 expected = 0);

    [[nodiscard]] std::span<const u8> GetData() const;
    [[nodiscard]] std::size_t GetLength() const;
    [[nodiscard]] std::size_t GetAvailable() const;
    [[nodiscard]] std::size_t GetPos() const;
    void SetPos(std::size_t pos);

    u8 G1Enc(Isaac& random);
    u8 G1();
    s8 G1B();
    u16 G2();
    s16 G2B();
    s32 G3();
    s32 G4();
    s64 G8();
    s32 GSmart();
    s32 GSmarts();
    std::string GJStr();
    void GData(std::span<u8> destination);

    void P1Enc(Isaac& random, s32 opcode);
    void P1(s32 value);
    void P2(s32 value);
    void IP2(s32 value);
    void P3(s32 value);
    void P4(s32 value);
    void IP4(s32 value);
    void P8(s64 value);
    void PJStr(std::string_view text);
    void PData(std::span<const u8> source);
    void PSize1(std::size_t size);

    void GBitStart();
    void GBitEnd();
    s32 GBit(u32 bitCount);
    [[nodiscard]] std::size_t GetBitPos() const;

    void RsaEnc(const BigUInt& modulus, const BigUInt& exponent);

private:
    enum class Mode_e : u8
    {
        Read,
        Write,
    };

    static constexpr u8 STRING_TERMINATOR = '\n';

    [[nodiscard]] std::span<const u8> NextRead(std::size_t count);
    [[nodiscard]] std::span<u8> NextWrite(std::size_t count);
    void RequireBytes(std::size_t count) const;
    void RequireBits(u32 bitCount) const;

    Mode_e m_mode;
    std::span<const u8> m_readData;
    std::vector<u8> m_writeData;
    std::size_t m_pos = 0;
    std::size_t m_bitPos = 0;
};
