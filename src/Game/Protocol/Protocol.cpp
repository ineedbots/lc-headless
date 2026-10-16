#include "pch.hpp"
#include "Protocol.hpp"

#include "../../Config/Revision_e.hpp"
#include "ClientProt.hpp"
#include "ServerProt.hpp"
#include "WireProt_s.hpp"

Protocol::Protocol(Revision_e revision)
    : m_revision{revision}
    , m_serverProts{&ServerProt::GetTable(revision)}
    , m_clientProts{&ClientProt::GetTable(revision)}
{
}

Revision_e Protocol::GetRevision() const
{
    return m_revision;
}

std::optional<ServerProt_e> Protocol::FindServerProt(u8 opcode) const
{
    return m_serverProts->byOpcode[opcode];
}

s32 Protocol::GetSize(ServerProt_e prot) const
{
    const auto& wire = m_serverProts->byProt[static_cast<std::size_t>(prot)];
    assert(wire && "GetSize for a server packet this revision never sends");
    return wire->size;
}

bool Protocol::Has(ClientProt_e prot) const
{
    return m_clientProts->byProt[static_cast<std::size_t>(prot)].has_value();
}

void Protocol::Require(ClientProt_e prot) const
{
    if (!Has(prot))
    {
        throw std::invalid_argument{std::format("Revision {} has no {} packet", static_cast<u16>(m_revision), ClientProt::GetName(prot))};
    }
}

u8 Protocol::GetOpcode(ClientProt_e prot) const
{
    return GetWire(prot).opcode;
}

s32 Protocol::GetSize(ClientProt_e prot) const
{
    return GetWire(prot).size;
}

const WireProt_s& Protocol::GetWire(ClientProt_e prot) const
{
    Require(prot);
    return *m_clientProts->byProt[static_cast<std::size_t>(prot)];
}
