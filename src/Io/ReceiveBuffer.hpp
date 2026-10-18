#pragma once

// Bytes received and not yet read. Message boundaries are gone: it is one stream.
class ReceiveBuffer
{
public:
    void Append(std::span<const u8> bytes);

    [[nodiscard]] std::size_t Available() const;
    void Peek(std::span<u8> destination) const;
    std::span<u8> Read(std::span<u8> destination);

private:
    std::vector<u8> m_bytes;
    std::size_t m_readOffset = 0;
};
