#include "pch.hpp"
#include "ClientPacketWriter.hpp"

#include "../../Io/Isaac.hpp"
#include "../Protocol/ClientPacket_s.hpp"
#include "../Protocol/ClientProt.hpp"

namespace
{
    constexpr auto MAX_VAR_BYTE_SIZE = std::size_t{255};
}

ClientPacketWriter::ClientPacketWriter(std::span<const s32> seed)
    : m_isaac{seed}
{
}

void ClientPacketWriter::Validate(const ClientPacket_s& packet)
{
    const auto opcode = static_cast<u8>(packet.prot);
    const auto size = ClientProt::GetSize(opcode);
    if (!size)
    {
        throw std::invalid_argument{std::format("Client opcode {} doesn't exist, and the server would close the socket", opcode)};
    }

    const auto name = ClientProt::GetName(opcode);
    if (*size == ClientProt::VAR_BYTE)
    {
        if (packet.payload.size() > MAX_VAR_BYTE_SIZE)
        {
            throw std::invalid_argument{std::format("{} payload is {} bytes, more than a 1-byte length can hold", name, packet.payload.size())};
        }

        return;
    }

    if (packet.payload.size() != static_cast<std::size_t>(*size))
    {
        throw std::invalid_argument{std::format("{} payload must be {} bytes, not {}", name, *size, packet.payload.size())};
    }
}

void ClientPacketWriter::Write(const ClientPacket_s& packet, std::vector<u8>& out)
{
    Validate(packet);

    out.push_back(static_cast<u8>(static_cast<u32>(packet.prot) + static_cast<u32>(m_isaac.NextInt())));
    if (ClientProt::GetSize(packet.prot) == ClientProt::VAR_BYTE)
    {
        out.push_back(static_cast<u8>(packet.payload.size()));
    }

    out.insert(out.end(), packet.payload.begin(), packet.payload.end());
}
