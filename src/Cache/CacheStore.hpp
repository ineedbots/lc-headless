#pragma once

class CacheStore
{
public:
    static constexpr u32 STORE_COUNT = 5;
    static constexpr u32 ARCHIVES = 0;
    static constexpr u32 MAPS = 4;
    static constexpr std::size_t SECTOR_SIZE = 520;
    static constexpr std::size_t SECTOR_HEADER_SIZE = 8;
    static constexpr std::size_t MAX_FILE_SIZE = 2'000'000;
    static constexpr std::size_t INDEX_ENTRY_SIZE = 6;
    static constexpr auto DAT_FILE = "main_file_cache.dat";

    // A missing index file only fails a read from that store.
    explicit CacheStore(const std::filesystem::path& directory);

    [[nodiscard]] static std::string GetIndexFileName(u32 store);

    [[nodiscard]] u32 GetFileCount(u32 store) const;
    // Nullopt when the index has no entry for the file.
    [[nodiscard]] std::optional<std::vector<u8>> Read(u32 store, u32 file);

private:
    // Returns the next sector in the chain.
    [[nodiscard]] u32 ReadSector(u32 store, u32 file, u32 part, u32 sector, std::span<u8> body);

    std::ifstream m_dat;
    u64 m_datSize = 0;
    std::array<std::optional<std::vector<u8>>, STORE_COUNT> m_indexes;
};
