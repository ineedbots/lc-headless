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

Packet::Packet(std::vector<u8> data)
    : m_data{std::move(data)}
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

std::span<u8> Packet::GetData()
{
    return m_data;
}

std::span<const u8> Packet::GetData() const
{
    return m_data;
}

std::size_t Packet::GetLength() const
{
    return m_data.size();
}

std::size_t Packet::GetAvailable() const
{
    return m_data.size() - m_pos;
}

std::size_t Packet::GetPos() const
{
    return m_pos;
}

void Packet::SetPos(std::size_t pos)
{
    assert(pos <= m_data.size() && "Packet pos set past the end");
    m_pos = pos;
}

void Packet::SetRandom(std::unique_ptr<Isaac> random)
{
    m_random = std::move(random);
}

u8 Packet::G1()
{
    RequireBytes(sizeof(u8));
    return m_data[m_pos++];
}

s8 Packet::G1B()
{
    return std::bit_cast<s8>(G1());
}

u16 Packet::G2()
{
    RequireBytes(sizeof(u16));
    const auto value = LoadBig<u16>(std::span{m_data}.subspan(m_pos));
    m_pos += sizeof(u16);
    return value;
}

s16 Packet::G2B()
{
    return std::bit_cast<s16>(G2());
}

s32 Packet::G3()
{
    RequireBytes(3);
    const auto high = u32{m_data[m_pos]};
    const auto low = u32{LoadBig<u16>(std::span{m_data}.subspan(m_pos + 1))};
    m_pos += 3;
    return static_cast<s32>((high << 16) | low);
}

s32 Packet::G4()
{
    RequireBytes(sizeof(s32));
    const auto value = LoadBig<s32>(std::span{m_data}.subspan(m_pos));
    m_pos += sizeof(s32);
    return value;
}

s64 Packet::G8()
{
    RequireBytes(sizeof(s64));
    const auto value = LoadBig<s64>(std::span{m_data}.subspan(m_pos));
    m_pos += sizeof(s64);
    return value;
}

s32 Packet::GSmart()
{
    RequireBytes(1);
    if (m_data[m_pos] < SMART_ONE_BYTE_LIMIT)
    {
        return G1();
    }

    return G2() - SMART_TWO_BYTE_OFFSET;
}

s32 Packet::GSmarts()
{
    RequireBytes(1);
    if (m_data[m_pos] < SMART_ONE_BYTE_LIMIT)
    {
        return G1() - SMARTS_ONE_BYTE_OFFSET;
    }

    return G2() - SMARTS_TWO_BYTE_OFFSET;
}

std::string Packet::GJStr()
{
    RequireBytes(1);
    const auto unread = std::span{m_data}.subspan(m_pos);
    const auto terminator = std::ranges::find(unread, STRING_TERMINATOR);
    if (terminator != unread.end())
    {
        const auto length = static_cast<std::size_t>(terminator - unread.begin());
        m_pos += length + 1;
        return ToString(unread.first(length));
    }

    // TS checks for the end of the buffer before keeping each byte, so it drops the last one.
    m_pos = m_data.size();
    return ToString(unread.first(unread.size() - 1));
}

void Packet::GData(std::span<u8> destination)
{
    RequireBytes(destination.size());
    std::ranges::copy(std::span{m_data}.subspan(m_pos, destination.size()), destination.begin());
    m_pos += destination.size();
}

void Packet::P1Enc(s32 opcode)
{
    RequireBytes(1);
    const auto key = m_random ? m_random->NextInt() : 0;
    m_data[m_pos++] = static_cast<u8>(static_cast<u32>(opcode) + static_cast<u32>(key));
}

void Packet::P1(s32 value)
{
    RequireBytes(1);
    m_data[m_pos++] = static_cast<u8>(value);
}

void Packet::P2(s32 value)
{
    RequireBytes(sizeof(u16));
    StoreBig(std::span{m_data}.subspan(m_pos), static_cast<u16>(value));
    m_pos += sizeof(u16);
}

void Packet::IP2(s32 value)
{
    RequireBytes(sizeof(u16));
    StoreLittle(std::span{m_data}.subspan(m_pos), static_cast<u16>(value));
    m_pos += sizeof(u16);
}

void Packet::P3(s32 value)
{
    RequireBytes(3);
    m_data[m_pos] = static_cast<u8>(value >> 16);
    StoreBig(std::span{m_data}.subspan(m_pos + 1), static_cast<u16>(value));
    m_pos += 3;
}

void Packet::P4(s32 value)
{
    RequireBytes(sizeof(s32));
    StoreBig(std::span{m_data}.subspan(m_pos), value);
    m_pos += sizeof(s32);
}

void Packet::IP4(s32 value)
{
    RequireBytes(sizeof(s32));
    StoreLittle(std::span{m_data}.subspan(m_pos), value);
    m_pos += sizeof(s32);
}

void Packet::P8(s64 value)
{
    RequireBytes(sizeof(s64));
    StoreBig(std::span{m_data}.subspan(m_pos), value);
    m_pos += sizeof(s64);
}

void Packet::PJStr(std::string_view text)
{
    RequireBytes(text.size() + 1);
    std::ranges::copy(text, m_data.begin() + static_cast<std::ptrdiff_t>(m_pos));
    m_pos += text.size();
    m_data[m_pos++] = STRING_TERMINATOR;
}

void Packet::PData(std::span<const u8> source)
{
    RequireBytes(source.size());
    std::ranges::copy(source, m_data.begin() + static_cast<std::ptrdiff_t>(m_pos));
    m_pos += source.size();
}

void Packet::PSize1(std::size_t size)
{
    assert(size + 1 <= m_pos && "PSize1 size reaches before the start of the packet");

    // As in TS, the length byte is the placeholder written just before the last size bytes.
    m_data[m_pos - size - 1] = static_cast<u8>(size);
}

void Packet::GBitStart()
{
    m_bitPos = m_pos * 8;
}

void Packet::GBitEnd()
{
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
        value += (m_data[bytePos++] & BIT_MASKS[remaining]) << (bitCount - remaining);
        bitCount -= remaining;
    }

    if (bitCount == remaining)
    {
        value += m_data[bytePos] & BIT_MASKS[remaining];
    }
    else
    {
        value += (u32{m_data[bytePos]} >> (remaining - bitCount)) & BIT_MASKS[bitCount];
    }

    return static_cast<s32>(value);
}

void Packet::RsaEnc(const BigUInt& modulus, const BigUInt& exponent)
{
    assert(m_pos > 0 && "RsaEnc called with an empty block");

    const auto block = BigUInt::FromBytesBigEndian(std::span{m_data}.first(m_pos));
    const auto encrypted = BigUInt::ModPow(block, exponent, modulus).ToBytesBigEndian();
    if (encrypted.size() > MAX_RSA_BLOCK_SIZE)
    {
        throw std::length_error{std::format("Packet RSA block is {} bytes, more than a 1-byte length can hold", encrypted.size())};
    }

    if (encrypted.size() + 1 > m_data.size())
    {
        throw std::out_of_range{std::format("Packet RSA block needs {} bytes, but the packet holds {}", encrypted.size() + 1, m_data.size())};
    }

    // The length counts BigUInt's sign-padding byte, as TS's bigIntToBytes does.
    m_pos = 0;
    P1(static_cast<s32>(encrypted.size()));
    PData(encrypted);
}

void Packet::RequireBytes(std::size_t count) const
{
    if (count <= GetAvailable())
    {
        return;
    }

    throw std::out_of_range{std::format("Packet needs {} bytes at pos {}, but only {} are available", count, m_pos, GetAvailable())};
}

void Packet::RequireBits(u32 bitCount) const
{
    const auto availableBits = m_data.size() * 8 - m_bitPos;
    if (bitCount <= availableBits)
    {
        return;
    }

    throw std::out_of_range{std::format("Packet needs {} bits at bit pos {}, but only {} are available", bitCount, m_bitPos, availableBits)};
}
