#include "pch.hpp"
#include "BitWriter.hpp"

BitWriter& BitWriter::Put(u32 bitCount, s32 value)
{
    assert(bitCount >= 1 && bitCount <= 32 && "BitWriter writes 1 to 32 bits at a time");
    const auto bits = static_cast<u32>(value);
    for (auto i = bitCount; i > 0; --i)
    {
        const auto byte = m_bitPos / 8;
        if (byte >= m_bytes.size())
        {
            m_bytes.push_back(0);
        }

        const auto bit = (bits >> (i - 1)) & 1;
        m_bytes[byte] = static_cast<u8>(m_bytes[byte] | (bit << (7 - m_bitPos % 8)));
        ++m_bitPos;
    }

    return *this;
}

std::vector<u8> BitWriter::GetBytes() const
{
    return m_bytes;
}

std::size_t BitWriter::GetBitPos() const
{
    return m_bitPos;
}
