#pragma once

#include "../../Io/Isaac.hpp"
#include "../Protocol/ClientPacket_s.hpp"

class ClientPacketWriter
{
public:
    explicit ClientPacketWriter(std::span<const s32> seed);

    static void Validate(const ClientPacket_s& packet);

    // Each call uses one ISAAC value, so every packet written must then be sent.
    void Write(const ClientPacket_s& packet, std::vector<u8>& out);

private:
    Isaac m_isaac;
};
