#include "pch.hpp"
#include "ReceiveBuffer.hpp"

namespace
{
    constexpr auto COMPACT_THRESHOLD = std::size_t{4096};
}

void ReceiveBuffer::Append(std::span<const u8> bytes)
{
    m_bytes.insert(m_bytes.end(), bytes.begin(), bytes.end());
}

std::size_t ReceiveBuffer::Available() const
{
    return m_bytes.size() - m_readOffset;
}

void ReceiveBuffer::Peek(std::span<u8> destination) const
{
    if (destination.size() > Available())
    {
        throw std::out_of_range{std::format("{} bytes are available, but {} were requested", Available(), destination.size())};
    }

    std::ranges::copy(std::span{m_bytes}.subspan(m_readOffset, destination.size()), destination.begin());
}

std::span<u8> ReceiveBuffer::Read(std::span<u8> destination)
{
    Peek(destination);
    m_readOffset += destination.size();
    if (m_readOffset == m_bytes.size())
    {
        m_bytes.clear();
        m_readOffset = 0;
        return destination;
    }

    if (m_readOffset >= COMPACT_THRESHOLD && m_readOffset * 2 >= m_bytes.size())
    {
        m_bytes.erase(m_bytes.begin(), m_bytes.begin() + static_cast<std::ptrdiff_t>(m_readOffset));
        m_readOffset = 0;
    }

    return destination;
}
