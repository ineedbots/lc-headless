#include "pch.hpp"
#include "Packet.hpp"

#include "../Core/BigUInt.hpp"
#include "../Core/Endian.hpp"
#include "Isaac.hpp"

namespace
{
    constexpr auto CRC32_POLYNOMIAL = u32{0xEDB88320};
    constexpr auto SMART_ONE_BYTE_LIMIT = u8{0x80};
    constexpr auto SMART_TWO_BYTE_OFFSET = 0x8000;
    constexpr auto SMARTS_ONE_BYTE_OFFSET = 0x40;
    constexpr auto SMARTS_TWO_BYTE_OFFSET = 0xC000;
    constexpr auto MAX_BIT_COUNT = u32{32};
    constexpr auto MAX_RSA_BLOCK_SIZE = std::size_t{255};

    constexpr auto CRC_TABLE = []
    {
        auto table = std::array<u32, 256>{};
        for (auto i = u32{0}; i < table.size(); ++i)
        {
            auto remainder = i;
            for (auto bit = 0; bit < 8; ++bit)
            {
                remainder = (remainder & 1) != 0 ? (remainder >> 1) ^ CRC32_POLYNOMIAL : remainder >> 1;
            }

            table[i] = remainder;
        }

        return table;
    }();

    constexpr auto BIT_MASKS = []
    {
        auto masks = std::array<u32, MAX_BIT_COUNT + 1>{};
        for (auto i = u32{0}; i < MAX_BIT_COUNT; ++i)
        {
            masks[i] = (u32{1} << i) - 1;
        }

        masks[MAX_BIT_COUNT] = 0xFFFFFFFF;
        return masks;
    }();

    template <std::integral T>
    T LoadBig(std::span<const u8> source)
    {
        auto value = T{};
        std::memcpy(&value, source.data(), sizeof(T));
        return Endian::FromBig(value);
    }

    template <std::integral T>
    void StoreBig(std::span<u8> destination, T value)
    {
        const auto stored = Endian::ToBig(value);
        std::memcpy(destination.data(), &stored, sizeof(T));
    }

    template <std::integral T>
    void StoreLittle(std::span<u8> destination, T value)
    {
        const auto stored = Endian::ToLittle(value);
        std::memcpy(destination.data(), &stored, sizeof(T));
    }

    std::string ToString(std::span<const u8> bytes)
    {
        return std::string{reinterpret_cast<const char*>(bytes.data()), bytes.size()};
    }
}

Packet::Packet()
    : m_mode{Mode_e::Write}
{
}

Packet::Packet(std::span<const u8> data)
    : m_mode{Mode_e::Read}
    , m_readData{data}
{
}

s32 Packet::GetCrc(std::span<const u8> source)
{
    auto crc = u32{0xFFFFFFFF};
    for (const auto byte : source)
    {
        crc = (crc >> 8) ^ CRC_TABLE[(crc ^ byte) & 0xFF];
    }

    return std::bit_cast<s32>(~crc);
}

bool Packet::CheckCrc(std::span<const u8> source, s32 expected)
{
    return GetCrc(source) == expected;
}

std::span<const u8> Packet::GetData() const
{
    if (m_mode == Mode_e::Read)
    {
        return m_readData;
    }

    return std::span{m_writeData}.first(m_pos);
}

std::size_t Packet::GetLength() const
{
    if (m_mode == Mode_e::Read)
    {
        return m_readData.size();
    }

    return m_pos;
}

std::size_t Packet::GetAvailable() const
{
    assert(m_mode == Mode_e::Read && "GetAvailable called on a write-mode packet");
    return m_readData.size() - m_pos;
}

std::size_t Packet::GetPos() const
{
    return m_pos;
}

void Packet::SetPos(std::size_t pos)
{
    assert(pos <= (m_mode == Mode_e::Read ? m_readData.size() : m_writeData.size()) && "Packet pos set past the end");
    m_pos = pos;
}

u8 Packet::G1Enc(Isaac& random)
{
    const auto encoded = u32{G1()};
    return static_cast<u8>(encoded - static_cast<u32>(random.NextInt()));
}

u8 Packet::G1()
{
    return NextRead(sizeof(u8))[0];
}

s8 Packet::G1B()
{
    return std::bit_cast<s8>(G1());
}

u16 Packet::G2()
{
    return LoadBig<u16>(NextRead(sizeof(u16)));
}

s16 Packet::G2B()
{
    return std::bit_cast<s16>(G2());
}

s32 Packet::G3()
{
    const auto bytes = NextRead(3);
    const auto high = u32{bytes[0]};
    const auto low = u32{LoadBig<u16>(bytes.subspan(1))};
    return static_cast<s32>((high << 16) | low);
}

s32 Packet::G4()
{
    return LoadBig<s32>(NextRead(sizeof(s32)));
}

s64 Packet::G8()
{
    return LoadBig<s64>(NextRead(sizeof(s64)));
}

s32 Packet::GSmart()
{
    RequireBytes(1);
    if (m_readData[m_pos] < SMART_ONE_BYTE_LIMIT)
    {
        return G1();
    }

    return G2() - SMART_TWO_BYTE_OFFSET;
}

s32 Packet::GSmarts()
{
    RequireBytes(1);
    if (m_readData[m_pos] < SMART_ONE_BYTE_LIMIT)
    {
        return G1() - SMARTS_ONE_BYTE_OFFSET;
    }

    return G2() - SMARTS_TWO_BYTE_OFFSET;
}

std::string Packet::GJStr()
{
    RequireBytes(1);
    const auto unread = m_readData.subspan(m_pos);
    const auto terminator = std::ranges::find(unread, STRING_TERMINATOR);
    if (terminator != unread.end())
    {
        const auto length = static_cast<std::size_t>(terminator - unread.begin());
        m_pos += length + 1;
        return ToString(unread.first(length));
    }

    // TS checks for the end of the buffer before keeping each byte, so it drops the last one.
    m_pos = m_readData.size();
    return ToString(unread.first(unread.size() - 1));
}

void Packet::GData(std::span<u8> destination)
{
    std::ranges::copy(NextRead(destination.size()), destination.begin());
}

void Packet::P1Enc(Isaac& random, s32 opcode)
{
    const auto destination = NextWrite(sizeof(u8));
    destination[0] = static_cast<u8>(static_cast<u32>(opcode) + static_cast<u32>(random.NextInt()));
}

void Packet::P1(s32 value)
{
    NextWrite(sizeof(u8))[0] = static_cast<u8>(value);
}

void Packet::P2(s32 value)
{
    StoreBig(NextWrite(sizeof(u16)), static_cast<u16>(value));
}

void Packet::IP2(s32 value)
{
    StoreLittle(NextWrite(sizeof(u16)), static_cast<u16>(value));
}

void Packet::P3(s32 value)
{
    const auto destination = NextWrite(3);
    destination[0] = static_cast<u8>(value >> 16);
    StoreBig(destination.subspan(1), static_cast<u16>(value));
}

void Packet::P4(s32 value)
{
    StoreBig(NextWrite(sizeof(s32)), value);
}

void Packet::IP4(s32 value)
{
    StoreLittle(NextWrite(sizeof(s32)), value);
}

void Packet::P8(s64 value)
{
    StoreBig(NextWrite(sizeof(s64)), value);
}

void Packet::PJStr(std::string_view text)
{
    const auto destination = NextWrite(text.size() + 1);
    std::ranges::copy(text, destination.begin());
    destination.back() = STRING_TERMINATOR;
}

void Packet::PData(std::span<const u8> source)
{
    std::ranges::copy(source, NextWrite(source.size()).begin());
}

void Packet::PSize1(std::size_t size)
{
    assert(m_mode == Mode_e::Write && "PSize1 called on a read-mode packet");
    assert(size + 1 <= m_pos && "PSize1 size reaches before the start of the packet");

    // As in TS, the length byte is the placeholder written just before the last size bytes.
    m_writeData[m_pos - size - 1] = static_cast<u8>(size);
}

void Packet::GBitStart()
{
    assert(m_mode == Mode_e::Read && "GBitStart called on a write-mode packet");
    m_bitPos = m_pos * 8;
}

void Packet::GBitEnd()
{
    assert(m_mode == Mode_e::Read && "GBitEnd called on a write-mode packet");
    m_pos = (m_bitPos + 7) / 8;
}

s32 Packet::GBit(u32 bitCount)
{
    assert(bitCount >= 1 && bitCount <= MAX_BIT_COUNT && "GBit width must be 1 to 32");
    RequireBits(bitCount);

    auto bytePos = m_bitPos / 8;
    auto remaining = 8 - static_cast<u32>(m_bitPos % 8);
    auto value = u32{0};
    m_bitPos += bitCount;

    for (; bitCount > remaining; remaining = 8)
    {
        value += (m_readData[bytePos++] & BIT_MASKS[remaining]) << (bitCount - remaining);
        bitCount -= remaining;
    }

    if (bitCount == remaining)
    {
        value += m_readData[bytePos] & BIT_MASKS[remaining];
    }
    else
    {
        value += (u32{m_readData[bytePos]} >> (remaining - bitCount)) & BIT_MASKS[bitCount];
    }

    return static_cast<s32>(value);
}

std::size_t Packet::GetBitPos() const
{
    return m_bitPos;
}

void Packet::RsaEnc(const BigUInt& modulus, const BigUInt& exponent)
{
    assert(m_mode == Mode_e::Write && "RsaEnc called on a read-mode packet");
    assert(m_pos > 0 && "RsaEnc called with an empty block");

    const auto block = BigUInt::FromBytesBigEndian(GetData());
    const auto encrypted = BigUInt::ModPow(block, exponent, modulus).ToBytesBigEndian();
    if (encrypted.size() > MAX_RSA_BLOCK_SIZE)
    {
        throw std::length_error{std::format("Packet RSA block is {} bytes, more than a 1-byte length can hold", encrypted.size())};
    }

    // The length counts BigUInt's sign-padding byte, as TS's bigIntToBytes does.
    m_pos = 0;
    P1(static_cast<s32>(encrypted.size()));
    PData(encrypted);
}

std::span<const u8> Packet::NextRead(std::size_t count)
{
    RequireBytes(count);
    const auto bytes = m_readData.subspan(m_pos, count);
    m_pos += count;
    return bytes;
}

std::span<u8> Packet::NextWrite(std::size_t count)
{
    assert(m_mode == Mode_e::Write && "Packet write called on a read-mode packet");

    const auto end = m_pos + count;
    if (end > m_writeData.size())
    {
        m_writeData.resize(end);
    }

    const auto bytes = std::span{m_writeData}.subspan(m_pos, count);
    m_pos = end;
    return bytes;
}

void Packet::RequireBytes(std::size_t count) const
{
    assert(m_mode == Mode_e::Read && "Packet read called on a write-mode packet");
    if (count <= GetAvailable())
    {
        return;
    }

    throw std::out_of_range{std::format("Packet needs {} bytes at pos {}, but only {} are available", count, m_pos, GetAvailable())};
}

void Packet::RequireBits(u32 bitCount) const
{
    assert(m_mode == Mode_e::Read && "GBit called on a write-mode packet");
    const auto availableBits = m_readData.size() * 8 - m_bitPos;
    if (bitCount <= availableBits)
    {
        return;
    }

    throw std::out_of_range{std::format("Packet needs {} bits at bit pos {}, but only {} are available", bitCount, m_bitPos, availableBits)};
}
