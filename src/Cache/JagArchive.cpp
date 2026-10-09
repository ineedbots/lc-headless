#include "pch.hpp"
#include "JagArchive.hpp"

#include "../Io/Packet.hpp"
#include "CacheError.hpp"
#include "Compression.hpp"

namespace
{
    constexpr auto HEADER_SIZE = std::size_t{6};
    constexpr auto COUNT_SIZE = std::size_t{2};
    constexpr auto ENTRY_SIZE = std::size_t{10};
    constexpr auto HASH_MULTIPLIER = u32{61};
    constexpr auto HASH_CHARACTER_OFFSET = u32{32};
}

JagArchive::JagArchive(std::vector<u8> data)
{
    if (data.size() < HEADER_SIZE)
    {
        throw CacheError{std::format("archive is {} bytes, too short for its header", data.size())};
    }

    auto header = Packet{data};
    const auto unpackedSize = static_cast<u32>(header.G3());
    const auto packedSize = static_cast<u32>(header.G3());
    auto tableStart = HEADER_SIZE;
    if (unpackedSize == packedSize)
    {
        m_data = std::move(data);
        m_entriesCompressed = true;
    }
    else
    {
        const auto packed = std::span{data}.subspan(HEADER_SIZE);
        if (packedSize > packed.size())
        {
            throw CacheError{std::format("archive says it packs to {} bytes, but has {}", packedSize, packed.size())};
        }

        m_data = Compression::Bunzip2(packed.first(packedSize), unpackedSize);
        tableStart = 0;
    }

    if (m_data.size() < tableStart + COUNT_SIZE)
    {
        throw CacheError{"archive ends before its entry count"};
    }

    auto table = Packet{std::span{m_data}.subspan(tableStart)};
    const auto count = std::size_t{table.G2()};
    auto offset = tableStart + COUNT_SIZE + count * ENTRY_SIZE;
    if (offset > m_data.size())
    {
        throw CacheError{std::format("archive's table of {} entries runs past its {} bytes", count, m_data.size())};
    }

    m_entries.reserve(count);
    for (std::size_t i = 0; i < count; ++i)
    {
        auto entry = Entry_s{};
        entry.nameHash = table.G4();
        entry.unpackedSize = static_cast<u32>(table.G3());
        entry.packedSize = static_cast<u32>(table.G3());
        entry.offset = offset;
        if (entry.offset + entry.packedSize > m_data.size())
        {
            throw CacheError{std::format("archive entry {} runs past the archive's {} bytes", i, m_data.size())};
        }

        offset += entry.packedSize;
        m_entries.push_back(entry);
    }
}

s32 JagArchive::HashName(std::string_view name)
{
    auto hash = u32{0};
    for (const auto character : name)
    {
        const auto upper = static_cast<u32>(std::toupper(static_cast<unsigned char>(character)));
        hash = hash * HASH_MULTIPLIER + upper - HASH_CHARACTER_OFFSET;
    }

    return std::bit_cast<s32>(hash);
}

std::optional<std::vector<u8>> JagArchive::Read(std::string_view name) const
{
    const auto entry = std::ranges::find(m_entries, HashName(name), &Entry_s::nameHash);
    if (entry == m_entries.end())
    {
        return std::nullopt;
    }

    const auto packed = std::span{m_data}.subspan(entry->offset, entry->packedSize);
    if (!m_entriesCompressed)
    {
        if (entry->packedSize != entry->unpackedSize)
        {
            throw CacheError{std::format("{}: is {} bytes, but its listed size is {}", name, entry->packedSize, entry->unpackedSize)};
        }

        return std::vector<u8>{packed.begin(), packed.end()};
    }

    try
    {
        return Compression::Bunzip2(packed, entry->unpackedSize);
    }
    catch (const CacheError& e)
    {
        throw CacheError{std::format("{}: {}", name, e.what())};
    }
}
