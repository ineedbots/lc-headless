#pragma once

#include "../Config/Revision_e.hpp"
#include "../Io/Packet.hpp"
#include "DroppedOpcodes_s.hpp"
#include "Error/CacheError.hpp"
#include "RevisionedOpcode_s.hpp"
#include "TextPool.hpp"

// What the loc, NPC, obj and varp decoders share: the .dat and .idx framing, the opcodes every type
// uses, and the readers for their fields.
class TypeDecoder
{
public:
    static constexpr u8 END_OPCODE = 0;
    // Opcodes are named after the fields they set in the webclient's LocType, NpcType, ObjType and
    // VarpType, or the engine's where the webclient has no name.
    static constexpr u8 NAME = 2;
    static constexpr u8 EXAMINE = 3;
    static constexpr u8 RECOLOUR = 40;
    // A source and a destination colour.
    static constexpr std::size_t RECOLOUR_SIZE = 2 * sizeof(u16);

    TypeDecoder() = delete;

    // Decodes every definition in dat, at the sizes idx lists, with decode(packet, type), and returns
    // the types in id order. kind names the files and the definition in errors.
    template <typename T, typename TDecode>
    [[nodiscard]] static std::vector<T> DecodeAll(std::string_view kind, std::span<const u8> dat, std::span<const u8> idx, TDecode decode)
    {
        if (idx.size() < COUNT_SIZE || dat.size() < COUNT_SIZE)
        {
            throw CacheError{std::format("{0}.dat or {0}.idx is too short for its count", kind)};
        }

        auto index = Packet{idx};
        const auto count = std::size_t{index.G2()};
        const auto datCount = std::size_t{Packet{dat}.G2()};
        if (count != datCount)
        {
            throw CacheError{std::format("{0}.idx lists {1} definitions, but {0}.dat has {2}", kind, count, datCount)};
        }

        if (idx.size() < COUNT_SIZE + count * SIZE_ENTRY_SIZE)
        {
            throw CacheError{std::format("{}.idx is {} bytes, too short for {} sizes", kind, idx.size(), count)};
        }

        auto types = std::vector<T>(count);
        auto offset = COUNT_SIZE;
        for (auto id = std::size_t{0}; id < count; ++id)
        {
            const auto size = std::size_t{index.G2()};
            if (offset + size > dat.size())
            {
                throw CacheError{std::format("{} {}: runs past the end of {}.dat", kind, id, kind)};
            }

            auto packet = Packet{dat.subspan(offset, size)};
            auto& type = types[id];
            type.id = static_cast<u16>(id);
            try
            {
                decode(packet, type);
            }
            catch (const CacheError& e)
            {
                throw CacheError{std::format("{} {}: {}", kind, id, e.what())};
            }
            catch (const std::out_of_range&)
            {
                throw CacheError{std::format("{} {}: runs past the end of its {} bytes", kind, id, size)};
            }

            if (packet.GetPos() != size)
            {
                throw CacheError{std::format("{} {}: ends at byte {} of its {}", kind, id, packet.GetPos(), size)};
            }

            offset += size;
        }

        if (offset != dat.size())
        {
            throw CacheError{std::format("{}.dat has {} bytes after its last definition", kind, dat.size() - offset)};
        }

        return types;
    }

    // Whether the revision has the opcode; one the table doesn't list is in every revision. A cache decoded as
    // the wrong revision then fails on an unknown opcode rather than reading garbage.
    [[nodiscard]] static bool HasOpcode(Revision_e revision, u8 opcode, std::span<const RevisionedOpcode_s> table);
    static void Skip(Packet& packet, std::size_t count);
    // Reads and drops the value of an opcode in the table, or returns false for an opcode that isn't.
    [[nodiscard]] static bool SkipDropped(Packet& packet, u8 opcode, std::span<const DroppedOpcodes_s> table);
    [[nodiscard]] static std::string ReadString(Packet& packet);
    // Slots past the array's end are read and dropped, and "hidden", which the menu leaves out, can be
    // stored as NO_OPTION.
    static void ReadOption(Packet& packet, std::size_t slot, std::span<u16> ops, TextPool& text, bool dropHidden);
    [[noreturn]] static void ThrowUnknown(u8 opcode);

private:
    static constexpr std::size_t COUNT_SIZE = 2;
    static constexpr std::size_t SIZE_ENTRY_SIZE = 2;
};
