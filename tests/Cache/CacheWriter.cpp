#include "pch.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheStore.hpp"
#include "Cache/JagArchive.hpp"
#include "Cache/MapSquare.hpp"
#include "Io/Packet.hpp"

#include <bzlib.h>
#include <zlib.h>

namespace
{
    constexpr auto SECTOR_DATA_SIZE = CacheStore::SECTOR_SIZE - CacheStore::SECTOR_HEADER_SIZE;
    constexpr auto BZIP2_HEADER_SIZE = std::size_t{4};
    constexpr auto BZIP2_BLOCK_SIZE = 1;
    constexpr auto BZIP2_SLACK = 600;
    constexpr auto GZIP_WINDOW_BITS = 16 + MAX_WBITS;
    constexpr auto GZIP_MEMORY_LEVEL = 8;
    constexpr auto SMART_ONE_BYTE_LIMIT = 128;
    constexpr auto SMART_TWO_BYTE_OFFSET = 0x8000;
    constexpr auto FLAGS_OPCODE_OFFSET = 49;
    constexpr auto END_OF_TILE = 0;
    constexpr auto FREE_SQUARE = 1;
    constexpr auto NAME_OPCODE = 2;
    constexpr auto FIRST_OP_OPCODE = 30;
    constexpr auto END_OPCODE = 0;
    constexpr auto FILLER_ARCHIVES = std::to_array<u32>({1, 3, 4, 6, 7, 8});

    std::vector<u8> ToBytes(const Packet& packet)
    {
        const auto data = packet.GetData();
        return {data.begin(), data.end()};
    }

    std::vector<u8> ToBytes(std::string_view text)
    {
        return {text.begin(), text.end()};
    }

    void PutEntryTable(Packet& packet, const std::vector<ArchiveEntry_s>& entries, std::span<const std::vector<u8>> packed)
    {
        packet.P2(static_cast<s32>(entries.size()));
        for (std::size_t i = 0; i < entries.size(); ++i)
        {
            packet.P4(JagArchive::HashName(entries[i].name));
            packet.P3(static_cast<s32>(entries[i].data.size()));
            packet.P3(static_cast<s32>(packed[i].size()));
        }

        for (const auto& bytes : packed)
        {
            packet.PData(bytes);
        }
    }
}

void CacheWriter::Put(u32 store, u32 file, std::vector<u8> bytes)
{
    m_files.insert_or_assign(std::pair{store, file}, std::move(bytes));
}

const std::vector<u8>& CacheWriter::Get(u32 store, u32 file) const
{
    return m_files.at({store, file});
}

WrittenStore_s CacheWriter::Write(const std::filesystem::path& directory) const
{
    auto written = Build();
    WriteStore(directory, written);
    return written;
}

WrittenStore_s CacheWriter::Build() const
{
    auto written = WrittenStore_s{};
    written.dat.resize(CacheStore::SECTOR_SIZE);
    for (const auto& [key, bytes] : m_files)
    {
        const auto [store, file] = key;
        auto& index = written.indexes[store];
        index.resize(std::max(index.size(), (std::size_t{file} + 1) * CacheStore::INDEX_ENTRY_SIZE));

        // Each file starts on a fresh sector, so only the .dat's last sector can be short, as the engine leaves it.
        written.dat.resize((written.dat.size() + CacheStore::SECTOR_SIZE - 1) / CacheStore::SECTOR_SIZE * CacheStore::SECTOR_SIZE);
        const auto firstSector = written.dat.size() / CacheStore::SECTOR_SIZE;
        auto entry = Packet{};
        entry.P3(static_cast<s32>(bytes.size()));
        entry.P3(static_cast<s32>(bytes.empty() ? 0 : firstSector));
        std::ranges::copy(entry.GetData(), index.begin() + static_cast<std::ptrdiff_t>(file * CacheStore::INDEX_ENTRY_SIZE));

        auto sector = firstSector;
        for (std::size_t part = 0, offset = 0; offset < bytes.size(); ++part, ++sector)
        {
            const auto chunk = std::min(SECTOR_DATA_SIZE, bytes.size() - offset);
            const auto last = offset + chunk == bytes.size();
            written.dat.resize(sector * CacheStore::SECTOR_SIZE);
            auto header = Packet{};
            header.P2(static_cast<s32>(file));
            header.P2(static_cast<s32>(part));
            header.P3(last ? 0 : static_cast<s32>(sector + 1));
            header.P1(static_cast<s32>(store + 1));
            const auto headerBytes = header.GetData();
            written.dat.insert(written.dat.end(), headerBytes.begin(), headerBytes.end());
            written.dat.insert(written.dat.end(), bytes.begin() + static_cast<std::ptrdiff_t>(offset), bytes.begin() + static_cast<std::ptrdiff_t>(offset + chunk));
            offset += chunk;
        }
    }

    return written;
}

void CacheWriter::WriteStore(const std::filesystem::path& directory, const WrittenStore_s& store)
{
    std::filesystem::create_directories(directory);
    WriteFile(directory / CacheStore::DAT_FILE, store.dat);
    for (auto i = u32{0}; i < CacheStore::STORE_COUNT; ++i)
    {
        WriteFile(directory / CacheStore::GetIndexFileName(i), store.indexes[i]);
    }
}

std::vector<u8> CacheWriter::Bzip2Headerless(std::span<const u8> data)
{
    auto packed = std::vector<u8>(data.size() + data.size() / 100 + BZIP2_SLACK);
    auto packedSize = static_cast<unsigned int>(packed.size());
    // libbzip2 rejects a null source even when it's empty.
    auto nothing = char{0};
    auto* const source = data.empty() ? &nothing : reinterpret_cast<char*>(const_cast<u8*>(data.data()));
    const auto result = BZ2_bzBuffToBuffCompress(reinterpret_cast<char*>(packed.data()), &packedSize, source, static_cast<unsigned int>(data.size()), BZIP2_BLOCK_SIZE, 0, 0);
    if (result != BZ_OK)
    {
        throw std::runtime_error{std::format("BZ2_bzBuffToBuffCompress failed with {}", result)};
    }

    packed.resize(packedSize);
    packed.erase(packed.begin(), packed.begin() + BZIP2_HEADER_SIZE);
    return packed;
}

std::vector<u8> CacheWriter::Gzip(std::span<const u8> data, u16 version)
{
    auto stream = z_stream{};
    if (deflateInit2(&stream, Z_DEFAULT_COMPRESSION, Z_DEFLATED, GZIP_WINDOW_BITS, GZIP_MEMORY_LEVEL, Z_DEFAULT_STRATEGY) != Z_OK)
    {
        throw std::runtime_error{"deflateInit2 failed"};
    }

    auto packed = std::vector<u8>(deflateBound(&stream, static_cast<uLong>(data.size())));
    stream.next_in = const_cast<Bytef*>(data.data());
    stream.avail_in = static_cast<uInt>(data.size());
    stream.next_out = packed.data();
    stream.avail_out = static_cast<uInt>(packed.size());
    const auto result = deflate(&stream, Z_FINISH);
    packed.resize(stream.total_out);
    deflateEnd(&stream);
    if (result != Z_STREAM_END)
    {
        throw std::runtime_error{std::format("deflate failed with {}", result)};
    }

    auto trailer = Packet{};
    trailer.P2(version);
    const auto trailerBytes = trailer.GetData();
    packed.insert(packed.end(), trailerBytes.begin(), trailerBytes.end());
    return packed;
}

std::vector<u8> CacheWriter::MakeArchive(const std::vector<ArchiveEntry_s>& entries, bool compressWhole)
{
    auto packed = std::vector<std::vector<u8>>{};
    for (const auto& entry : entries)
    {
        packed.push_back(compressWhole ? entry.data : Bzip2Headerless(entry.data));
    }

    auto body = Packet{};
    PutEntryTable(body, entries, packed);
    auto contents = ToBytes(body);
    if (compressWhole)
    {
        contents = Bzip2Headerless(ToBytes(body));
        assert(contents.size() != body.GetLength() && "A whole-compressed archive must differ in size from its contents");
    }

    auto archive = Packet{};
    archive.P3(static_cast<s32>(body.GetLength()));
    archive.P3(static_cast<s32>(contents.size()));
    archive.PData(contents);
    return ToBytes(archive);
}

TypeFiles_s CacheWriter::MakeTypeFiles(const std::vector<std::vector<u8>>& definitions)
{
    auto dat = Packet{};
    auto idx = Packet{};
    dat.P2(static_cast<s32>(definitions.size()));
    idx.P2(static_cast<s32>(definitions.size()));
    for (const auto& definition : definitions)
    {
        dat.PData(definition);
        idx.P2(static_cast<s32>(definition.size()));
    }

    return {.dat = ToBytes(dat), .idx = ToBytes(idx)};
}

std::vector<u8> CacheWriter::MakeDefinition(std::string_view name, const std::vector<std::string_view>& ops, std::span<const u8> otherOpcodes)
{
    auto packet = Packet{};
    if (!name.empty())
    {
        packet.P1(NAME_OPCODE);
        packet.PJStr(name);
    }

    for (std::size_t i = 0; i < ops.size(); ++i)
    {
        if (ops[i].empty())
        {
            continue;
        }

        packet.P1(FIRST_OP_OPCODE + static_cast<s32>(i));
        packet.PJStr(ops[i]);
    }

    packet.PData(otherOpcodes);
    packet.P1(END_OPCODE);
    return ToBytes(packet);
}

std::vector<u8> CacheWriter::MakeLand(std::span<const LandFlags_s> flags)
{
    auto land = std::vector<u8>{};
    for (auto level = 0; level < MapSquare::LEVELS; ++level)
    {
        for (auto x = 0; x < MapSquare::SIZE; ++x)
        {
            for (auto z = 0; z < MapSquare::SIZE; ++z)
            {
                const auto tile = std::ranges::find_if(flags, [level, x, z](const LandFlags_s& entry)
                {
                    return entry.level == level && entry.x == x && entry.z == z;
                });

                if (tile != flags.end())
                {
                    land.push_back(static_cast<u8>(FLAGS_OPCODE_OFFSET + tile->flags));
                }

                land.push_back(END_OF_TILE);
            }
        }
    }

    return land;
}

std::vector<u8> CacheWriter::MakeLocFile(std::span<const LocPlacement_s> locs)
{
    auto sorted = std::vector<LocPlacement_s>{locs.begin(), locs.end()};
    const auto position = [](const LocPlacement_s& loc)
    {
        return MapLoc_s::PackPosition(loc.level, loc.x, loc.z);
    };

    std::ranges::stable_sort(sorted, [&position](const LocPlacement_s& a, const LocPlacement_s& b)
    {
        return std::pair{a.id, position(a)} < std::pair{b.id, position(b)};
    });

    auto bytes = std::vector<u8>{};
    auto lastId = -1;
    for (std::size_t i = 0; i < sorted.size();)
    {
        const auto id = sorted[i].id;
        PutSmart(bytes, id - lastId);
        lastId = id;
        auto lastPosition = 0;
        for (; i < sorted.size() && sorted[i].id == id; ++i)
        {
            const auto& loc = sorted[i];
            PutSmart(bytes, position(loc) - lastPosition + 1);
            lastPosition = position(loc);
            bytes.push_back(static_cast<u8>((loc.shape << MapLoc_s::SHAPE_SHIFT) | loc.angle));
        }

        PutSmart(bytes, 0);
    }

    PutSmart(bytes, 0);
    return bytes;
}

std::vector<u8> CacheWriter::MakeMapIndex(std::span<const u16> squares)
{
    auto index = Packet{};
    for (std::size_t i = 0; i < squares.size(); ++i)
    {
        index.P2(squares[i]);
        index.P2(static_cast<s32>(i * 2));
        index.P2(static_cast<s32>(i * 2 + 1));
        index.P1(FREE_SQUARE);
    }

    return ToBytes(index);
}

CacheWriter CacheWriter::MakeStore(const StoreContents_s& contents)
{
    auto writer = CacheWriter{};
    for (const auto archive : FILLER_ARCHIVES)
    {
        const auto entry = ArchiveEntry_s{.name = "filler.dat", .data = ToBytes(std::format("archive {} filler", archive))};
        writer.Put(CacheStore::ARCHIVES, archive, MakeArchive({entry}, archive % 2 == 0));
    }

    const auto locs = MakeTypeFiles(contents.locs);
    const auto npcs = MakeTypeFiles(contents.npcs);
    const auto objs = MakeTypeFiles(contents.objs);
    writer.Put(CacheStore::ARCHIVES, 2, MakeArchive({
        {.name = "loc.dat", .data = locs.dat},
        {.name = "loc.idx", .data = locs.idx},
        {.name = "npc.dat", .data = npcs.dat},
        {.name = "npc.idx", .data = npcs.idx},
        {.name = "obj.dat", .data = objs.dat},
        {.name = "obj.idx", .data = objs.idx},
    }, false));

    auto squares = std::vector<u16>{};
    for (const auto& square : contents.squares)
    {
        squares.push_back(square.square);
    }

    squares.insert(squares.end(), contents.squaresWithoutFiles.begin(), contents.squaresWithoutFiles.end());
    writer.Put(CacheStore::ARCHIVES, 5, MakeArchive({{.name = "map_index", .data = MakeMapIndex(squares)}}, true));
    for (std::size_t i = 0; i < contents.squares.size(); ++i)
    {
        writer.Put(CacheStore::MAPS, static_cast<u32>(i * 2), Gzip(contents.squares[i].land));
        writer.Put(CacheStore::MAPS, static_cast<u32>(i * 2 + 1), Gzip(contents.squares[i].locs));
    }

    return writer;
}

void CacheWriter::PutSmart(std::vector<u8>& bytes, s32 value)
{
    auto packet = Packet{};
    if (value < SMART_ONE_BYTE_LIMIT)
    {
        packet.P1(value);
    }
    else
    {
        packet.P2(value + SMART_TWO_BYTE_OFFSET);
    }

    const auto data = packet.GetData();
    bytes.insert(bytes.end(), data.begin(), data.end());
}

void CacheWriter::WriteFile(const std::filesystem::path& path, std::span<const u8> bytes)
{
    auto file = std::ofstream{path, std::ios::binary};
    file.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    if (!file)
    {
        throw std::runtime_error{std::format("Can't write {}", path.string())};
    }
}
