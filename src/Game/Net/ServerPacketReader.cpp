#include "pch.hpp"
#include "ServerPacketReader.hpp"

#include "../../Io/Isaac.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../ProtocolError.hpp"

ServerPacketReader::ServerPacketReader(std::span<const s32> seed)
    : m_isaac{seed}
{
}

void ServerPacketReader::Append(std::span<const u8> bytes)
{
    m_buffer.insert(m_buffer.end(), bytes.begin(), bytes.end());
}

std::optional<ServerPacket_s> ServerPacketReader::Next()
{
    if (!m_opcode)
    {
        if (GetBuffered() < 1)
        {
            return std::nullopt;
        }

        const auto opcode = static_cast<u8>(Take(1)[0] - static_cast<u32>(m_isaac.NextInt()));
        const auto size = ServerProt::GetSize(opcode);
        if (!size)
        {
            throw ProtocolError{std::format("Server sent opcode {}, which this revision never sends", opcode)};
        }

        m_opcode = opcode;
        m_size = *size;
    }

    if (m_size == ServerProt::VAR_BYTE)
    {
        if (GetBuffered() < 1)
        {
            return std::nullopt;
        }

        m_size = Take(1)[0];
    }
    else if (m_size == ServerProt::VAR_SHORT)
    {
        if (GetBuffered() < 2)
        {
            return std::nullopt;
        }

        const auto bytes = Take(2);
        m_size = (bytes[0] << 8) | bytes[1];
    }

    const auto size = static_cast<std::size_t>(m_size);
    if (GetBuffered() < size)
    {
        return std::nullopt;
    }

    const auto payload = Take(size);
    auto packet = ServerPacket_s{.prot = static_cast<ServerProt_e>(*m_opcode), .payload = {payload.begin(), payload.end()}};
    m_opcode.reset();
    Compact();
    return packet;
}

std::size_t ServerPacketReader::GetBuffered() const
{
    return m_buffer.size() - m_readOffset;
}

std::span<const u8> ServerPacketReader::Take(std::size_t count)
{
    assert(count <= GetBuffered() && "Take past the buffered bytes");
    const auto bytes = std::span{m_buffer}.subspan(m_readOffset, count);
    m_readOffset += count;
    return bytes;
}

void ServerPacketReader::Compact()
{
    if (m_readOffset == m_buffer.size())
    {
        m_buffer.clear();
        m_readOffset = 0;
        return;
    }

    if (m_readOffset < COMPACT_THRESHOLD)
    {
        return;
    }

    m_buffer.erase(m_buffer.begin(), m_buffer.begin() + static_cast<std::ptrdiff_t>(m_readOffset));
    m_readOffset = 0;
}
