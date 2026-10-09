#include "pch.hpp"
#include "CacheLoader.hpp"

#include "../Core/Logger.hpp"
#include "../Io/Packet.hpp"
#include "CacheError.hpp"
#include "CacheStore.hpp"
#include "Compression.hpp"
#include "GameCache_s.hpp"
#include "JagArchive.hpp"
#include "MapDecoder.hpp"
#include "MapSquare.hpp"
#include "TypeDecoder.hpp"

namespace
{
    constexpr auto MAP_VERSION_SIZE = std::size_t{2};
    constexpr auto MISSING_STORE_HINT = "set client.cacheDirectory to the folder that holds the server's cache"sv;

    template <typename TBody>
    auto WithContext(std::string_view context, TBody body)
    {
        try
        {
            return body();
        }
        catch (const CacheError& e)
        {
            throw CacheError{std::format("{}: {}", context, e.what())};
        }
    }

    std::string DescribeFile(u32 store, u32 file, std::string_view label)
    {
        return std::format("store {} file {} ({})", store, file, label);
    }

    std::vector<u8> ReadArchive(CacheStore& store, u32 file, std::string_view name)
    {
        auto data = store.Read(CacheStore::ARCHIVES, file);
        if (!data)
        {
            throw CacheError{std::format("{}: not in the cache", DescribeFile(CacheStore::ARCHIVES, file, name))};
        }

        return std::move(*data);
    }

    std::vector<u8> ReadEntry(const JagArchive& archive, std::string_view name)
    {
        auto entry = archive.Read(name);
        if (!entry)
        {
            throw CacheError{std::format("{} not found", name)};
        }

        return std::move(*entry);
    }

    // What the engine's makeCrcs computes, and checks at login: the CRC of each archive as stored.
    std::array<s32, GameCache_s::CRC_COUNT> ReadCrcs(CacheStore& store)
    {
        auto crcs = std::array<s32, GameCache_s::CRC_COUNT>{};
        for (auto file = u32{0}; file < crcs.size(); ++file)
        {
            const auto data = store.Read(CacheStore::ARCHIVES, file);
            crcs[file] = data ? Packet::GetCrc(*data) : 0;
        }

        return crcs;
    }

    void DecodeTypes(CacheStore& store, GameCache_s& cache)
    {
        auto data = ReadArchive(store, CacheLoader::CONFIG_ARCHIVE, "config");
        WithContext(DescribeFile(CacheStore::ARCHIVES, CacheLoader::CONFIG_ARCHIVE, "config"), [&data, &cache]
        {
            const auto config = JagArchive{std::move(data)};
            const auto locDat = ReadEntry(config, "loc.dat");
            const auto locIdx = ReadEntry(config, "loc.idx");
            cache.locs = TypeDecoder::DecodeLocs(locDat, locIdx, cache.text);
            const auto npcDat = ReadEntry(config, "npc.dat");
            const auto npcIdx = ReadEntry(config, "npc.idx");
            cache.npcs = TypeDecoder::DecodeNpcs(npcDat, npcIdx, cache.text);
            const auto objDat = ReadEntry(config, "obj.dat");
            const auto objIdx = ReadEntry(config, "obj.idx");
            cache.objs = TypeDecoder::DecodeObjs(objDat, objIdx, cache.text);
        });
    }

    std::vector<MapIndexEntry_s> DecodeMapIndex(CacheStore& store)
    {
        auto data = ReadArchive(store, CacheLoader::VERSIONLIST_ARCHIVE, "versionlist");
        return WithContext(DescribeFile(CacheStore::ARCHIVES, CacheLoader::VERSIONLIST_ARCHIVE, "versionlist"), [&data]
        {
            const auto versionlist = JagArchive{std::move(data)};
            return MapDecoder::DecodeIndex(ReadEntry(versionlist, "map_index"));
        });
    }

    // A map file is a gzip member followed by a 2-byte version, which the webclient drops too.
    std::vector<u8> UnpackMapFile(std::span<const u8> data, u32 file, std::string_view label)
    {
        return WithContext(DescribeFile(CacheStore::MAPS, file, label), [data]
        {
            if (data.size() < MAP_VERSION_SIZE)
            {
                throw CacheError{std::format("map file is {} bytes, too short for its version", data.size())};
            }

            return Compression::Gunzip(data.first(data.size() - MAP_VERSION_SIZE));
        });
    }

    // Returns how many squares were skipped because their files aren't in the store.
    std::size_t DecodeMaps(CacheStore& store, GameCache_s& cache)
    {
        auto skipped = std::size_t{0};
        for (const auto& entry : DecodeMapIndex(store))
        {
            const auto land = store.Read(CacheStore::MAPS, entry.landFile);
            const auto locs = store.Read(CacheStore::MAPS, entry.locFile);
            if (!land || !locs)
            {
                ++skipped;
                continue;
            }

            const auto name = MapDecoder::DescribeSquare(entry.square);
            const auto landData = UnpackMapFile(*land, entry.landFile, std::format("square {} land", name));
            const auto locData = UnpackMapFile(*locs, entry.locFile, std::format("square {} locs", name));
            cache.squares.try_emplace(entry.square, MapDecoder::DecodeSquare(entry.square, landData, locData, cache.locs));
        }

        return skipped;
    }

    std::size_t CountMapLocs(const GameCache_s& cache)
    {
        auto count = std::size_t{0};
        for (const auto& [id, square] : cache.squares)
        {
            count += square.GetLocs().size();
        }

        return count;
    }
}

GameCache_s CacheLoader::Load(const std::filesystem::path& directory, Logger& logger)
{
    const auto start = std::chrono::steady_clock::now();
    try
    {
        if (!std::filesystem::is_regular_file(directory / CacheStore::DAT_FILE))
        {
            throw CacheError{std::format("{} not found; {}", CacheStore::DAT_FILE, MISSING_STORE_HINT)};
        }

        auto store = CacheStore{directory};
        auto cache = GameCache_s{};
        cache.crcs = ReadCrcs(store);
        DecodeTypes(store, cache);
        const auto skipped = DecodeMaps(store, cache);
        cache.text.FinishInterning();

        const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start);
        logger.Info("Cache loaded from {} in {} ms: {} locs, {} NPCs, {} objs, {} map squares with {} locs",
                    directory.string(), elapsed.count(), cache.locs.size(), cache.npcs.size(), cache.objs.size(), cache.squares.size(), CountMapLocs(cache));
        if (skipped == 1)
        {
            logger.Warning("1 map square in map_index has no files; it loads as open ground");
        }
        else if (skipped > 1)
        {
            logger.Warning("{} map squares in map_index have no files; they load as open ground", skipped);
        }

        return cache;
    }
    catch (const CacheError& e)
    {
        throw CacheError{std::format("{}: {}", directory.string(), e.what())};
    }
}
