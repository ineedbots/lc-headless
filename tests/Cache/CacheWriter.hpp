#pragma once

#include "Cache/CacheStore.hpp"

struct WrittenStore_s
{
    std::vector<u8> dat;
    std::array<std::vector<u8>, CacheStore::STORE_COUNT> indexes;
};

struct ArchiveEntry_s
{
    std::string name;
    std::vector<u8> data;
};

struct TypeFiles_s
{
    std::vector<u8> dat;
    std::vector<u8> idx;
};

struct LandFlags_s
{
    s32 level = 0;
    s32 x = 0;
    s32 z = 0;
    u8 flags = 0;
};

struct LocPlacement_s
{
    u16 id = 0;
    s32 level = 0;
    s32 x = 0;
    s32 z = 0;
    u8 shape = 0;
    u8 angle = 0;
};

// A square's map files, unpacked.
struct SquareFiles_s
{
    u16 square = 0;
    std::vector<u8> land;
    std::vector<u8> locs;
};

// A component in the interface archive's data entry. The writer adds the fields its type and button
// type have, with sample values, in the order the webclient's IfType.init reads them.
struct InterfaceComponent_s
{
    u16 id = 0;
    // Starts a run of this layer's components, after the 65535 marker.
    std::optional<u16> layer{};
    u8 type = 0;
    u8 buttonType = 0;
    u16 clientCode = 0;
    u16 width = 32;
    u16 height = 32;
    std::optional<u16> hoverLayer{};
    // Each a comparator and its operand.
    std::vector<std::pair<u8, u16>> conditions{};
    std::vector<std::vector<u16>> scripts{};
    // A layer's children, whether it starts hidden, and its children's offsets, by position; a child past
    // the offsets given gets a sample offset.
    std::vector<u16> children{};
    bool hidden = false;
    std::vector<std::pair<s16, s16>> childOffsets{};
    // A text component's text, a text, rect or inventory text component's colour, and a button's text.
    // Left out, each is a sample.
    std::optional<std::string> text{};
    std::optional<u32> colour{};
    std::optional<std::string> buttonText{};
    // An inventory's: whether its items can be used, the gap between slots, whether its first slot has a
    // background, and its options, with the slots past them empty.
    bool objOps = true;
    bool objUse = false;
    u8 marginX = 1;
    u8 marginY = 1;
    bool slotBackground = false;
    std::vector<std::string> options{};
};

// Each definition is a type's bytes, opcodes through the closing 0, in id order.
struct StoreContents_s
{
    std::vector<std::vector<u8>> locs;
    std::vector<std::vector<u8>> npcs;
    std::vector<std::vector<u8>> objs;
    std::vector<std::vector<u8>> varps;
    std::vector<InterfaceComponent_s> interfaces;
    std::vector<SquareFiles_s> squares;
    // Listed in map_index, but with no files in store 4.
    std::vector<u16> squaresWithoutFiles;
};

// Writes caches for the tests in the formats the engine's FileStream and the webclient read, on its own
// rather than through the reader, so a mistake in one shows up as a failure instead of hiding in both.
class CacheWriter
{
public:
    static constexpr u16 MAP_VERSION = 1;

    void Put(u32 store, u32 file, std::vector<u8> bytes);
    [[nodiscard]] const std::vector<u8>& Get(u32 store, u32 file) const;
    // Each file's sectors follow one another from sector 1, and each index lists every file up to its
    // last, with absent ones as size 0. Returns what it wrote, so a test can damage it and write it again.
    WrittenStore_s Write(const std::filesystem::path& directory) const;
    [[nodiscard]] WrittenStore_s Build() const;

    static void WriteStore(const std::filesystem::path& directory, const WrittenStore_s& store);

    [[nodiscard]] static std::vector<u8> Bzip2Headerless(std::span<const u8> data);
    [[nodiscard]] static std::vector<u8> Gzip(std::span<const u8> data, u16 version = MAP_VERSION);
    [[nodiscard]] static std::vector<u8> MakeArchive(const std::vector<ArchiveEntry_s>& entries, bool compressWhole);
    [[nodiscard]] static TypeFiles_s MakeTypeFiles(const std::vector<std::vector<u8>>& definitions);
    // A definition with a name (opcode 2) unless it's empty, op i for each non-empty ops[i] (opcode 30 + i),
    // then the other opcodes' bytes as given, and the closing 0.
    [[nodiscard]] static std::vector<u8> MakeDefinition(std::string_view name, const std::vector<std::string_view>& ops = {}, std::span<const u8> otherOpcodes = {});
    [[nodiscard]] static std::vector<u8> MakeLand(std::span<const LandFlags_s> flags = {});
    [[nodiscard]] static std::vector<u8> MakeLocFile(std::span<const LocPlacement_s> locs);
    [[nodiscard]] static std::vector<u8> MakeMapIndex(std::span<const u16> squares);
    // The interface archive's data entry: the count, then the components in the order given.
    [[nodiscard]] static std::vector<u8> MakeInterfaces(const std::vector<InterfaceComponent_s>& components);
    // Archives 1 to 8, with filler where nothing is decoded, and the squares' files in store 4. Square
    // i in map_index has land file 2i and loc file 2i + 1.
    [[nodiscard]] static CacheWriter MakeStore(const StoreContents_s& contents);

    static void PutSmart(std::vector<u8>& bytes, s32 value);
    static void WriteFile(const std::filesystem::path& path, std::span<const u8> bytes);

private:
    std::map<std::pair<u32, u32>, std::vector<u8>> m_files;
};
