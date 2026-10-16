#pragma once

#include "../../Config/Revision_e.hpp"
#include "ClientProt.hpp"
#include "ServerProt.hpp"
#include "WireProt_s.hpp"

// One revision's wire protocol: its opcode tables, and the revision every layout difference branches on.
// The tables are static, so a Protocol is cheap to copy.
class Protocol
{
public:
    explicit Protocol(Revision_e revision);

    [[nodiscard]] Revision_e GetRevision() const;

    // Nullopt for an opcode this revision never sends.
    [[nodiscard]] std::optional<ServerProt_e> FindServerProt(u8 opcode) const;
    [[nodiscard]] s32 GetSize(ServerProt_e prot) const;

    [[nodiscard]] bool Has(ClientProt_e prot) const;
    // These throw std::invalid_argument for a packet this revision doesn't have.
    void Require(ClientProt_e prot) const;
    [[nodiscard]] u8 GetOpcode(ClientProt_e prot) const;
    [[nodiscard]] s32 GetSize(ClientProt_e prot) const;

private:
    [[nodiscard]] const WireProt_s& GetWire(ClientProt_e prot) const;

    Revision_e m_revision;
    const ServerProtTable_s* m_serverProts;
    const ClientProtTable_s* m_clientProts;
};
