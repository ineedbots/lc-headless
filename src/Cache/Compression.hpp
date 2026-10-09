#pragma once

class Compression
{
public:
    Compression() = delete;

    // A bzip2 stream without its "BZh1" header, as JAG archives store it. Throws CacheError unless it
    // unpacks to exactly expectedSize bytes.
    [[nodiscard]] static std::vector<u8> Bunzip2(std::span<const u8> source, std::size_t expectedSize);
    // One gzip member, as a map file holds once its 2-byte version trailer is dropped. Throws CacheError
    // for damaged data, or for more than CacheStore::MAX_FILE_SIZE bytes of output.
    [[nodiscard]] static std::vector<u8> Gunzip(std::span<const u8> source);
};
