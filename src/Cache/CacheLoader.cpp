#include "pch.hpp"
#include "CacheLoader.hpp"

#include "../Config/Revision_e.hpp"
#include "../Console/Logger.hpp"
#include "../Io/Packet.hpp"
#include "../Utils/FileUtils.hpp"
#include "CacheStore.hpp"
#include "ClientCode_e.hpp"
#include "Compression.hpp"
#include "Error/CacheError.hpp"
#include "GameCache_s.hpp"
#include "InterfaceDecoder.hpp"
#include "JagArchive.hpp"
#include "LocTypeDecoder.hpp"
#include "MapDecoder.hpp"
#include "MapSquare.hpp"
#include "NpcTypeDecoder.hpp"
#include "ObjTypeDecoder.hpp"
#include "VarpTypeDecoder.hpp"
#include "VarpType_s.hpp"

namespace
{
    constexpr auto MAP_VERSION_SIZE = std::size_t{2};
    constexpr auto MAP_SIZE_PREFIX = std::size_t{4};
    constexpr auto STORE_HINT = "for revision 289, set client.cacheDirectory to the folder that holds the server's cache"sv;
    constexpr auto FOLDER_HINT = "for revision 225, set client.cacheDirectory to the 225 engine's data/pack/client folder"sv;
    constexpr auto LAND_FILE_PREFIX = 'm';
    constexpr auto LOC_FILE_PREFIX = 'l';
    // The engine's VarpType clientcode for running. The webclient does nothing with it, but the server
    // finds its run varp by it too.
    constexpr auto RUN_VARP_CLIENT_CODE = u16{7};
    // IfType's script opcode that pushes a varp, whose id follows it.
    constexpr auto PUSH_VARP = u16{5};
    constexpr auto RUN_OFF = u16{0};
    constexpr auto RUN_ON = u16{1};
    constexpr auto DEPOSIT_OPTION = "Deposit"sv;
    constexpr auto WITHDRAW_OPTION = "Withdraw"sv;

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

    std::vector<u8> ReadFolderArchive(const std::filesystem::path& directory, std::string_view name)
    {
        auto data = FileUtils::ReadBytes(directory / name);
        if (!data)
        {
            throw CacheError{std::format("{} not found; {}", name, FOLDER_HINT)};
        }

        return std::move(*data);
    }

    // What the engine's makeCrcs computes, and checks at login: the CRC of each archive as stored.
    std::array<s32, GameCache_s::CRC_COUNT> ReadStoreCrcs(CacheStore& store)
    {
        auto crcs = std::array<s32, GameCache_s::CRC_COUNT>{};
        for (auto file = u32{0}; file < crcs.size(); ++file)
        {
            const auto data = store.Read(CacheStore::ARCHIVES, file);
            crcs[file] = data ? Packet::GetCrc(*data) : 0;
        }

        return crcs;
    }

    // As the 225 engine's makeCrcs computes them: 0, then each archive file's CRC. Like makeCrcs, a missing
    // file is skipped and the rest move up, leaving zeros at the end.
    std::array<s32, GameCache_s::CRC_COUNT> ReadFolderCrcs(const std::filesystem::path& directory)
    {
        static_assert(CacheLoader::ARCHIVE_FILES_225.size() + 1 == GameCache_s::CRC_COUNT);

        auto crcs = std::array<s32, GameCache_s::CRC_COUNT>{};
        auto next = std::size_t{1};
        for (const auto name : CacheLoader::ARCHIVE_FILES_225)
        {
            const auto data = FileUtils::ReadBytes(directory / name);
            if (!data)
            {
                continue;
            }

            crcs[next] = Packet::GetCrc(*data);
            ++next;
        }

        return crcs;
    }

    u16 FindRunVarp(std::span<const VarpType_s> varps)
    {
        const auto found = std::ranges::find(varps, RUN_VARP_CLIENT_CODE, &VarpType_s::clientCode);
        if (found == varps.end())
        {
            throw CacheError{std::format("no varp has client code {}, which marks the run varp", RUN_VARP_CLIENT_CODE)};
        }

        return found->id;
    }

    void DecodeConfig(std::vector<u8> data, std::string_view context, GameCache_s& cache)
    {
        WithContext(context, [&data, &cache]
        {
            const auto config = JagArchive{std::move(data)};
            const auto locDat = ReadEntry(config, "loc.dat");
            const auto locIdx = ReadEntry(config, "loc.idx");
            cache.locs = LocTypeDecoder::Decode(locDat, locIdx, cache.text, cache.revision);

            const auto npcDat = ReadEntry(config, "npc.dat");
            const auto npcIdx = ReadEntry(config, "npc.idx");
            cache.npcs = NpcTypeDecoder::Decode(npcDat, npcIdx, cache.text, cache.revision);

            const auto objDat = ReadEntry(config, "obj.dat");
            const auto objIdx = ReadEntry(config, "obj.idx");
            cache.objs = ObjTypeDecoder::Decode(objDat, objIdx, cache.text, cache.revision);

            const auto varpDat = ReadEntry(config, "varp.dat");
            const auto varpIdx = ReadEntry(config, "varp.idx");
            cache.runVarp = FindRunVarp(VarpTypeDecoder::Decode(varpDat, varpIdx, cache.revision));
        });
    }

    template <typename TPredicate>
    const IfComponent_s& FindComponent(std::span<const IfComponent_s> components, TPredicate matches, std::string_view missing)
    {
        const auto found = std::ranges::find_if(components, matches);
        if (found == components.end())
        {
            throw CacheError{std::string{missing}};
        }

        return *found;
    }

    const IfComponent_s& FindClientCode(std::span<const IfComponent_s> components, ClientCode_e code, std::string_view marks)
    {
        const auto missing = std::format("no component has client code {}, which marks {}", static_cast<u16>(code), marks);
        return FindComponent(components, [code](const IfComponent_s& component)
        {
            return component.clientCode == code;
        }, missing);
    }

    // As the webclient's select buttons work: the first script pushes the varp, and the first
    // condition's operand is the value a click sets it to.
    const IfComponent_s& FindVarpButton(std::span<const IfComponent_s> components, u16 varp, u16 value, std::string_view marks)
    {
        const auto missing = std::format("no select button sets varp {} to {}, which marks {}", varp, value, marks);
        return FindComponent(components, [varp, value](const IfComponent_s& component)
        {
            if (component.buttonType != ButtonType_e::Select || component.scripts.empty() || component.operands.empty())
            {
                return false;
            }

            const auto& script = component.scripts.front();
            return script.size() > 1 && script[0] == PUSH_VARP && script[1] == varp && component.operands.front() == value;
        }, missing);
    }

    bool IsBackpack(const IfComponent_s& component)
    {
        return component.type == ComponentType_e::Inv && component.objUse;
    }

    bool IsEquipment(const IfComponent_s& component)
    {
        return component.type == ComponentType_e::Inv && component.hasSlotBackgrounds;
    }

    bool IsBankBackpack(const IfComponent_s& component)
    {
        return component.type == ComponentType_e::Inv && component.options.front().starts_with(DEPOSIT_OPTION);
    }

    bool IsWithdrawable(const IfComponent_s& component)
    {
        return component.type == ComponentType_e::Inv && component.options.front().starts_with(WITHDRAW_OPTION);
    }

    // 225 has no client code for the bank, so it's the biggest inventory items are withdrawn from: the bank's
    // 8 x 30 grid, ahead of the party room chest.
    const IfComponent_s& FindBankByContent(std::span<const IfComponent_s> components)
    {
        const auto* bank = static_cast<const IfComponent_s*>(nullptr);
        for (const auto& component : components)
        {
            if (!IsWithdrawable(component))
            {
                continue;
            }

            if (bank == nullptr || component.width * component.height > bank->width * bank->height)
            {
                bank = &component;
            }
        }

        if (bank == nullptr)
        {
            throw CacheError{"no inventory has a Withdraw option, which marks the bank"};
        }

        return *bank;
    }

    const IfComponent_s& FindBank(std::span<const IfComponent_s> components, Revision_e revision)
    {
        if (revision >= Revision_e::Rev289)
        {
            return FindClientCode(components, ClientCode_e::BankMode, "the bank");
        }

        return FindBankByContent(components);
    }

    void FindComponents(std::vector<u8> data, std::string_view context, GameCache_s& cache)
    {
        WithContext(context, [&data, &cache]
        {
            const auto interfaces = JagArchive{std::move(data)};
            auto components = InterfaceDecoder::Decode(ReadEntry(interfaces, "data"), cache.revision);
            cache.logoutComponent = FindClientCode(components, ClientCode_e::Logout, "the logout button").id;
            cache.bankComponent = FindBank(components, cache.revision).id;

            const auto& inventory = FindComponent(components, IsBackpack, "no inventory lets its items be used, which marks the backpack");
            cache.inventoryComponent = inventory.id;
            cache.inventorySize = inventory.width * inventory.height;
            cache.equipmentComponent = FindComponent(components, IsEquipment, "no inventory has slot backgrounds, which marks the worn equipment").id;
            cache.bankInventoryComponent = FindComponent(components, IsBankBackpack, "no inventory has a Deposit option, which marks the backpack beside the bank").id;

            cache.runOffButton = FindVarpButton(components, cache.runVarp, RUN_OFF, "the run off button").id;
            cache.runOnButton = FindVarpButton(components, cache.runVarp, RUN_ON, "the run on button").id;
            for (auto& component : components)
            {
                cache.components.insert_or_assign(component.id, std::move(component));
            }
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

    // Returns how many squares were missing from the store.
    std::size_t DecodeStoreMaps(CacheStore& store, GameCache_s& cache)
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

    // A 225 map file is its unpacked size, then bzip2 without its header, as a JAG archive stores it.
    std::vector<u8> UnpackFolderMapFile(std::span<const u8> data, std::string_view label)
    {
        return WithContext(label, [data]
        {
            if (data.size() < MAP_SIZE_PREFIX)
            {
                throw CacheError{std::format("map file is {} bytes, too short for its size", data.size())};
            }

            const auto size = static_cast<u32>(Packet{data}.G4());
            if (size > CacheStore::MAX_FILE_SIZE)
            {
                throw CacheError{std::format("map file claims {} bytes unpacked, more than {}", size, CacheStore::MAX_FILE_SIZE)};
            }

            return Compression::Bunzip2(data.subspan(MAP_SIZE_PREFIX), size);
        });
    }

    std::optional<s32> ParseSquareCoord(std::string_view text)
    {
        auto value = 0;
        const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
        if (error != std::errc{} || end != text.data() + text.size() || value < 0 || value > MapSquare::MAX_SQUARE)
        {
            return std::nullopt;
        }

        return value;
    }

    struct FolderMapFile_s
    {
        bool isLand = false;
        u16 square = 0;
    };

    // m{x}_{z} for a square's land, l{x}_{z} for its locs.
    std::optional<FolderMapFile_s> ParseMapFileName(std::string_view name)
    {
        if (name.empty() || (name.front() != LAND_FILE_PREFIX && name.front() != LOC_FILE_PREFIX))
        {
            return std::nullopt;
        }

        const auto coords = name.substr(1);
        const auto separator = coords.find('_');
        if (separator == std::string_view::npos)
        {
            return std::nullopt;
        }

        const auto x = ParseSquareCoord(coords.substr(0, separator));
        const auto z = ParseSquareCoord(coords.substr(separator + 1));
        if (!x || !z)
        {
            return std::nullopt;
        }

        return FolderMapFile_s{.isLand = name.front() == LAND_FILE_PREFIX, .square = MapSquare::GetId(*x, *z)};
    }

    struct FolderSquare_s
    {
        std::optional<std::vector<u8>> land;
        std::optional<std::vector<u8>> locs;
    };

    std::map<u16, FolderSquare_s> ReadFolderMaps(const std::filesystem::path& folder)
    {
        if (!std::filesystem::is_directory(folder))
        {
            throw CacheError{std::format("{} folder not found; {}", CacheLoader::MAPS_FOLDER_225, FOLDER_HINT)};
        }

        auto squares = std::map<u16, FolderSquare_s>{};
        for (const auto& entry : std::filesystem::directory_iterator{folder})
        {
            const auto name = entry.path().filename().string();
            const auto file = ParseMapFileName(name);
            if (!file || !entry.is_regular_file())
            {
                continue;
            }

            auto data = FileUtils::ReadBytes(entry.path());
            if (!data)
            {
                throw CacheError{std::format("{}/{} can't be read", CacheLoader::MAPS_FOLDER_225, name)};
            }

            auto& square = squares[file->square];
            auto& slot = file->isLand ? square.land : square.locs;
            slot = std::move(*data);
        }

        return squares;
    }

    std::vector<u8> UnpackFolderSquareFile(const std::optional<std::vector<u8>>& data, std::string_view label)
    {
        if (!data)
        {
            return {};
        }

        return UnpackFolderMapFile(*data, label);
    }

    std::optional<s32> GetFileCrc(const std::optional<std::vector<u8>>& data)
    {
        if (!data)
        {
            return std::nullopt;
        }

        return Packet::GetCrc(*data);
    }

    // Every square with a land or a loc file, the other loading empty when it's missing. Returns how many
    // squares have only one.
    std::size_t DecodeFolderMaps(const std::filesystem::path& folder, GameCache_s& cache)
    {
        auto halves = std::size_t{0};
        for (const auto& [id, files] : ReadFolderMaps(folder))
        {
            if (!files.land || !files.locs)
            {
                ++halves;
            }

            const auto name = MapDecoder::DescribeSquare(id);
            const auto landData = UnpackFolderSquareFile(files.land, std::format("{}/{}{}", CacheLoader::MAPS_FOLDER_225, LAND_FILE_PREFIX, name));
            const auto locData = UnpackFolderSquareFile(files.locs, std::format("{}/{}{}", CacheLoader::MAPS_FOLDER_225, LOC_FILE_PREFIX, name));
            cache.squares.try_emplace(id, MapDecoder::DecodeSquare(id, landData, locData, cache.locs));
            cache.mapCrcs.try_emplace(id, MapCrcs_s{.land = GetFileCrc(files.land), .locs = GetFileCrc(files.locs)});
        }

        return halves;
    }

    // Returns how many map squares in map_index have no files.
    std::size_t LoadStore(const std::filesystem::path& directory, GameCache_s& cache)
    {
        if (!std::filesystem::is_regular_file(directory / CacheStore::DAT_FILE))
        {
            throw CacheError{std::format("{} not found; {}", CacheStore::DAT_FILE, STORE_HINT)};
        }

        auto store = CacheStore{directory};
        cache.crcs = ReadStoreCrcs(store);
        DecodeConfig(ReadArchive(store, CacheLoader::CONFIG_ARCHIVE, "config"), DescribeFile(CacheStore::ARCHIVES, CacheLoader::CONFIG_ARCHIVE, "config"), cache);
        FindComponents(ReadArchive(store, CacheLoader::INTERFACE_ARCHIVE, "interface"), DescribeFile(CacheStore::ARCHIVES, CacheLoader::INTERFACE_ARCHIVE, "interface"), cache);
        return DecodeStoreMaps(store, cache);
    }

    // Returns how many map squares have only one of their two files.
    std::size_t LoadFolder(const std::filesystem::path& directory, GameCache_s& cache)
    {
        cache.crcs = ReadFolderCrcs(directory);
        DecodeConfig(ReadFolderArchive(directory, "config"), "config", cache);
        FindComponents(ReadFolderArchive(directory, "interface"), "interface", cache);
        return DecodeFolderMaps(directory / CacheLoader::MAPS_FOLDER_225, cache);
    }

    void WarnAboutMissingMapFiles(Revision_e revision, std::size_t count, Logger& logger)
    {
        if (count == 0)
        {
            return;
        }

        const auto one = count == 1;
        const auto squares = one ? "1 map square"s : std::format("{} map squares", count);
        if (revision >= Revision_e::Rev289)
        {
            logger.Warning("{} in map_index {} no files; {} as open ground", squares, one ? "has" : "have", one ? "it loads" : "they load");
            return;
        }

        logger.Warning("{} {} only a land or a loc file; the other loads empty", squares, one ? "has" : "have");
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

GameCache_s CacheLoader::Load(const std::filesystem::path& directory, Revision_e revision, Logger& logger)
{
    const auto start = std::chrono::steady_clock::now();
    try
    {
        auto cache = GameCache_s{};
        cache.revision = revision;

        const auto missingFiles = revision >= Revision_e::Rev289 ? LoadStore(directory, cache) : LoadFolder(directory, cache);
        cache.text.FinishInterning();

        const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start);
        logger.Info("Revision {} cache loaded from {} in {} ms: {} locs, {} NPCs, {} objs, {} map squares with {} locs", static_cast<u16>(revision),
                    directory.string(), elapsed.count(), cache.locs.size(), cache.npcs.size(), cache.objs.size(), cache.squares.size(), CountMapLocs(cache));
        WarnAboutMissingMapFiles(revision, missingFiles, logger);
        return cache;
    }
    catch (const CacheError& e)
    {
        throw CacheError{std::format("{}: {}", directory.string(), e.what())};
    }
}
