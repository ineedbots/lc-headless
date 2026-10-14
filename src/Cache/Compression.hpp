#pragma once

class Compression
{
public:
    Compression() = delete;

    // Without its "BZh1" header, as JAG archives store it.
    [[nodiscard]] static std::vector<u8> Bunzip2(std::span<const u8> source, std::size_t expectedSize);
    // One gzip member, as a map file holds after its 2-byte version trailer is dropped.
    [[nodiscard]] static std::vector<u8> Gunzip(std::span<const u8> source);
};
