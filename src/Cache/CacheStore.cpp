#include "pch.hpp"
#include "CacheStore.hpp"

#include "../Io/Packet.hpp"
#include "CacheError.hpp"

namespace
{
    constexpr auto SECTOR_DATA_SIZE = CacheStore::SECTOR_SIZE - CacheStore::SECTOR_HEADER_SIZE;

    struct IndexEntry_s
    {
        u32 size = 0;
        u32 firstSector = 0;
    };

    struct SectorHeader_s
    {
        u32 file = 0;
        u32 part = 0;
        u32 nextSector = 0;
        u32 store = 0;
    };

    std::vector<u8> ReadWholeFile(const std::filesystem::path& path)
    {
        auto file = std::ifstream{path, std::ios::binary};
        if (!file)
        {
            throw CacheError{std::format("{}: can't be opened", path.filename().string())};
        }

        auto bytes = std::vector<u8>(static_cast<std::size_t>(std::filesystem::file_size(path)));
        file.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
        if (!file)
        {
            throw CacheError{std::format("{}: read failed", path.filename().string())};
        }

        return bytes;
    }

    IndexEntry_s GetIndexEntry(std::span<const u8> index, u32 file)
    {
        auto packet = Packet{index.subspan(static_cast<std::size_t>(file) * CacheStore::INDEX_ENTRY_SIZE, CacheStore::INDEX_ENTRY_SIZE)};
        const auto size = static_cast<u32>(packet.G3());
        const auto firstSector = static_cast<u32>(packet.G3());
        return {.size = size, .firstSector = firstSector};
    }

    SectorHeader_s ParseSectorHeader(std::span<const u8> bytes)
    {
        auto packet = Packet{bytes};
        auto header = SectorHeader_s{};
        header.file = packet.G2();
        header.part = packet.G2();
        header.nextSector = static_cast<u32>(packet.G3());
        header.store = packet.G1();
        return header;
    }

    CacheError MakeError(u32 store, u32 file, std::string_view message)
    {
        return CacheError{std::format("store {} file {}: {}", store, file, message)};
    }
}

CacheStore::CacheStore(const std::filesystem::path& directory)
{
    const auto datPath = directory / DAT_FILE;
    if (!std::filesystem::is_regular_file(datPath))
    {
        throw CacheError{std::format("{} not found", DAT_FILE)};
    }

    m_dat.open(datPath, std::ios::binary);
    if (!m_dat)
    {
        throw CacheError{std::format("{}: can't be opened", DAT_FILE)};
    }

    m_datSize = std::filesystem::file_size(datPath);
    for (auto store = u32{0}; store < STORE_COUNT; ++store)
    {
        const auto indexPath = directory / GetIndexFileName(store);
        if (std::filesystem::is_regular_file(indexPath))
        {
            m_indexes[store] = ReadWholeFile(indexPath);
        }
    }
}

std::string CacheStore::GetIndexFileName(u32 store)
{
    return std::format("main_file_cache.idx{}", store);
}

u32 CacheStore::GetFileCount(u32 store) const
{
    assert(store < STORE_COUNT && "Store number out of range");
    const auto& index = m_indexes[store];
    if (!index)
    {
        return 0;
    }

    return static_cast<u32>(index->size() / INDEX_ENTRY_SIZE);
}

std::optional<std::vector<u8>> CacheStore::Read(u32 store, u32 file)
{
    assert(store < STORE_COUNT && "Store number out of range");
    if (!m_indexes[store])
    {
        throw CacheError{std::format("{} not found", GetIndexFileName(store))};
    }

    if (file >= GetFileCount(store))
    {
        return std::nullopt;
    }

    const auto entry = GetIndexEntry(*m_indexes[store], file);
    if (entry.size == 0 || entry.firstSector == 0)
    {
        return std::nullopt;
    }

    if (entry.size > MAX_FILE_SIZE)
    {
        throw MakeError(store, file, std::format("size {} is over the limit of {}", entry.size, MAX_FILE_SIZE));
    }

    auto data = std::vector<u8>(entry.size);
    auto sector = entry.firstSector;
    auto written = std::size_t{0};
    for (auto part = u32{0}; written < data.size(); ++part)
    {
        if (sector == 0)
        {
            throw MakeError(store, file, std::format("the sector chain ends after {} of {} bytes", written, data.size()));
        }

        const auto body = std::span{data}.subspan(written, std::min(SECTOR_DATA_SIZE, data.size() - written));
        sector = ReadSector(store, file, part, sector, body);
        written += body.size();
    }

    return data;
}

u32 CacheStore::ReadSector(u32 store, u32 file, u32 part, u32 sector, std::span<u8> body)
{
    const auto start = static_cast<u64>(sector) * SECTOR_SIZE;
    if (start + SECTOR_HEADER_SIZE + body.size() > m_datSize)
    {
        throw MakeError(store, file, std::format("sector {} is past the end of {}", sector, DAT_FILE));
    }

    auto header = std::array<u8, SECTOR_HEADER_SIZE>{};
    m_dat.seekg(static_cast<std::streamoff>(start));
    m_dat.read(reinterpret_cast<char*>(header.data()), static_cast<std::streamsize>(header.size()));
    m_dat.read(reinterpret_cast<char*>(body.data()), static_cast<std::streamsize>(body.size()));
    if (!m_dat)
    {
        m_dat.clear();
        throw CacheError{std::format("{}: read failed at sector {}", DAT_FILE, sector)};
    }

    const auto parsed = ParseSectorHeader(header);
    if (parsed.file != file)
    {
        throw MakeError(store, file, std::format("sector {} belongs to file {}", sector, parsed.file));
    }

    if (parsed.part != part)
    {
        throw MakeError(store, file, std::format("sector {} is part {}, not {}", sector, parsed.part, part));
    }

    if (parsed.store != store + 1)
    {
        throw MakeError(store, file, std::format("sector {} belongs to store {}", sector, static_cast<s32>(parsed.store) - 1));
    }

    return parsed.nextSector;
}
