#pragma once

#include "../../Io/Isaac.hpp"
#include "../Protocol/Protocol.hpp"
#include "../Protocol/ServerProt.hpp"

struct ServerPacket_s
{
    ServerProt_e prot;
    std::vector<u8> payload;
};

// Bytes may arrive in any grouping; each opcode is decrypted exactly once.
class ServerPacketReader
{
public:
    ServerPacketReader(std::span<const s32> seed, Protocol protocol);

    void Append(std::span<const u8> bytes);
    [[nodiscard]] std::optional<ServerPacket_s> Next();
    [[nodiscard]] std::size_t GetBuffered() const;

private:
    static constexpr std::size_t COMPACT_THRESHOLD = 4096;

    [[nodiscard]] std::span<const u8> Take(std::size_t count);
    void Compact();

    Isaac m_isaac;
    Protocol m_protocol;
    std::vector<u8> m_buffer;
    std::size_t m_readOffset = 0;
    std::optional<ServerProt_e> m_prot;
    s32 m_size = 0;
};
