#pragma once

#include "../Core/BigUInt.hpp"
#include "Isaac.hpp"

class Packet
{
public:
    explicit Packet(std::vector<u8> data);

    [[nodiscard]] static s32 GetCrc(std::span<const u8> source);
    [[nodiscard]] static bool CheckCrc(std::span<const u8> source, s32 expected = 0);

    [[nodiscard]] std::span<u8> GetData();
    [[nodiscard]] std::span<const u8> GetData() const;
    [[nodiscard]] std::size_t GetLength() const;
    [[nodiscard]] std::size_t GetAvailable() const;
    [[nodiscard]] std::size_t GetPos() const;
    void SetPos(std::size_t pos);
    void SetRandom(std::unique_ptr<Isaac> random);

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

    void P1Enc(s32 opcode);
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

    void RsaEnc(const BigUInt& modulus, const BigUInt& exponent);

private:
    static constexpr u8 STRING_TERMINATOR = '\n';

    void RequireBytes(std::size_t count) const;
    void RequireBits(u32 bitCount) const;

    std::vector<u8> m_data;
    std::size_t m_pos = 0;
    std::size_t m_bitPos = 0;
    std::unique_ptr<Isaac> m_random;
};
