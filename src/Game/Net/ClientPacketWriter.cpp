#include "pch.hpp"
#include "ClientPacketWriter.hpp"

#include "../../Io/Isaac.hpp"
#include "../Protocol/ClientPacket_s.hpp"
#include "../Protocol/ClientProt.hpp"
#include "../Protocol/Protocol.hpp"

namespace
{
    constexpr auto MAX_VAR_BYTE_SIZE = std::size_t{0xFF};
    constexpr auto MAX_VAR_SHORT_SIZE = std::size_t{0xFFFF};
}

ClientPacketWriter::ClientPacketWriter(std::span<const s32> seed, Protocol protocol)
    : m_isaac{seed}
    , m_protocol{protocol}
{
}

void ClientPacketWriter::Validate(const Protocol& protocol, const ClientPacket_s& packet)
{
    const auto size = protocol.GetSize(packet.prot);
    const auto name = ClientProt::GetName(packet.prot);
    if (size == ClientProt::VAR_BYTE || size == ClientProt::VAR_SHORT)
    {
        const auto maxSize = size == ClientProt::VAR_BYTE ? MAX_VAR_BYTE_SIZE : MAX_VAR_SHORT_SIZE;
        if (packet.payload.size() > maxSize)
        {
            throw std::invalid_argument{std::format("{} payload is {} bytes, more than its length prefix can hold", name, packet.payload.size())};
        }

        return;
    }

    if (packet.payload.size() != static_cast<std::size_t>(size))
    {
        throw std::invalid_argument{std::format("{} payload must be {} bytes, not {}", name, size, packet.payload.size())};
    }
}

void ClientPacketWriter::Write(const ClientPacket_s& packet, std::vector<u8>& out)
{
    Validate(m_protocol, packet);

    out.push_back(static_cast<u8>(u32{m_protocol.GetOpcode(packet.prot)} + static_cast<u32>(m_isaac.NextInt())));

    const auto size = m_protocol.GetSize(packet.prot);
    if (size == ClientProt::VAR_SHORT)
    {
        out.push_back(static_cast<u8>(packet.payload.size() >> 8));
    }

    if (size == ClientProt::VAR_BYTE || size == ClientProt::VAR_SHORT)
    {
        out.push_back(static_cast<u8>(packet.payload.size()));
    }

    out.insert(out.end(), packet.payload.begin(), packet.payload.end());
}
