#pragma once

#include "../../Io/Isaac.hpp"
#include "../Protocol/ClientPacket_s.hpp"
#include "../Protocol/Protocol.hpp"

class ClientPacketWriter
{
public:
    ClientPacketWriter(std::span<const s32> seed, Protocol protocol);

    // Throws std::invalid_argument for a packet the revision doesn't have, or a payload that doesn't fit its size.
    static void Validate(const Protocol& protocol, const ClientPacket_s& packet);

    // Each call uses one ISAAC value, so every packet written must then be sent.
    void Write(const ClientPacket_s& packet, std::vector<u8>& out);

private:
    Isaac m_isaac;
    Protocol m_protocol;
};
