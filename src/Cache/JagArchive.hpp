#pragma once

// A JAG archive's entries, looked up by name. An entry is unpacked when it's read.
class JagArchive
{
public:
    // Throws CacheError when the header or the entry table doesn't fit the data.
    explicit JagArchive(std::vector<u8> data);

    [[nodiscard]] static s32 HashName(std::string_view name);

    // The entry, unpacked, or nullopt when the archive has no entry by that name. Throws CacheError when
    // the entry doesn't unpack to its listed size.
    [[nodiscard]] std::optional<std::vector<u8>> Read(std::string_view name) const;

private:
    struct Entry_s
    {
        s32 nameHash = 0;
        u32 unpackedSize = 0;
        u32 packedSize = 0;
        std::size_t offset = 0;
    };

    std::vector<u8> m_data;
    bool m_entriesCompressed = false;
    std::vector<Entry_s> m_entries;
};
