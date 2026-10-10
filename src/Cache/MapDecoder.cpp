#include "pch.hpp"
#include "MapDecoder.hpp"

#include "../Io/Packet.hpp"
#include "CacheError.hpp"
#include "LocType_s.hpp"
#include "MapSquare.hpp"
#include "TextPool.hpp"

namespace
{
    constexpr auto INDEX_ENTRY_SIZE = std::size_t{7};
    constexpr auto SQUARE_COORD_MASK = 0xFF;

    constexpr auto END_OF_TILE = u8{0};
    constexpr auto HEIGHT = u8{1};
    constexpr auto LAST_OVERLAY = u8{49};
    constexpr auto LAST_FLAGS = u8{81};
    constexpr auto FLAGS_OFFSET = u8{49};
    constexpr auto BLOCK_FLAG = u8{0x1};
    constexpr auto LINK_BELOW_FLAG = u8{0x2};
    constexpr auto BRIDGE_FLAG_LEVEL = 1;

    constexpr auto END_OF_LIST = 0;
    constexpr auto MAX_LEVEL = MapSquare::LEVELS - 1;
    constexpr auto LAST_WALL_SHAPE = u8{3};
    constexpr auto FIRST_GROUND_SHAPE = u8{9};
    constexpr auto LAST_GROUND_SHAPE = u8{21};
    constexpr auto GROUND_DECOR_SHAPE = u8{22};

    using TileFlags = std::array<u8, MapSquare::LEVELS * MapSquare::SIZE * MapSquare::SIZE>;

    struct Land_s
    {
        TileFlags flags{};
        MapSquare::GroundTiles ground;
    };

    void CheckUsedUp(const Packet& packet)
    {
        if (packet.GetAvailable() != 0)
        {
            throw CacheError{std::format("{} bytes are left over", packet.GetAvailable())};
        }
    }

    // Only the flags, and whether there's an underlay or overlay, are kept from each tile's run of opcodes.
    Land_s DecodeLand(std::span<const u8> land)
    {
        auto decoded = Land_s{};
        auto& flags = decoded.flags;
        auto packet = Packet{land};
        for (auto level = 0; level < MapSquare::LEVELS; ++level)
        {
            for (auto x = 0; x < MapSquare::SIZE; ++x)
            {
                for (auto z = 0; z < MapSquare::SIZE; ++z)
                {
                    auto& tile = flags[MapSquare::GetBit(level, x, z)];
                    while (true)
                    {
                        const auto opcode = packet.G1();
                        if (opcode == END_OF_TILE)
                        {
                            break;
                        }

                        if (opcode == HEIGHT)
                        {
                            static_cast<void>(packet.G1());
                            break;
                        }

                        if (opcode <= LAST_OVERLAY)
                        {
                            static_cast<void>(packet.G1());
                            decoded.ground.set(MapSquare::GetBit(level, x, z));
                            continue;
                        }

                        if (opcode <= LAST_FLAGS)
                        {
                            tile = static_cast<u8>(opcode - FLAGS_OFFSET);
                            continue;
                        }

                        decoded.ground.set(MapSquare::GetBit(level, x, z));
                    }
                }
            }
        }

        CheckUsedUp(packet);
        return decoded;
    }

    // Everything on a bridge tile is seen one level below the one it's on.
    bool IsBridge(const TileFlags& flags, s32 x, s32 z)
    {
        return (flags[MapSquare::GetBit(BRIDGE_FLAG_LEVEL, x, z)] & LINK_BELOW_FLAG) != 0;
    }

    s32 GetSeenLevel(const TileFlags& flags, s32 level, s32 x, s32 z)
    {
        return IsBridge(flags, x, z) ? level - 1 : level;
    }

    MapSquare::BlockedTiles GetBlockedTiles(const TileFlags& flags)
    {
        auto blocked = MapSquare::BlockedTiles{};
        for (auto level = 0; level < MapSquare::LEVELS; ++level)
        {
            for (auto x = 0; x < MapSquare::SIZE; ++x)
            {
                for (auto z = 0; z < MapSquare::SIZE; ++z)
                {
                    if ((flags[MapSquare::GetBit(level, x, z)] & BLOCK_FLAG) == 0)
                    {
                        continue;
                    }

                    const auto seenLevel = GetSeenLevel(flags, level, x, z);
                    if (seenLevel >= 0)
                    {
                        blocked.set(MapSquare::GetBit(seenLevel, x, z));
                    }
                }
            }
        }

        return blocked;
    }

    bool AddsCollision(const LocType_s& type, u8 shape)
    {
        if (!type.blockWalk)
        {
            return false;
        }

        const auto isGround = shape >= FIRST_GROUND_SHAPE && shape <= LAST_GROUND_SHAPE;
        const auto isActiveGroundDecor = shape == GROUND_DECOR_SHAPE && type.active;
        return shape <= LAST_WALL_SHAPE || isGround || isActiveGroundDecor;
    }

    bool HasNameOrOption(const LocType_s& type)
    {
        return !type.name.empty() || std::ranges::any_of(type.ops, [](u16 op)
        {
            return op != TextPool::NO_OPTION;
        });
    }

    // Decoration, with no name, no option and nothing to walk into, is dropped; the webclient only draws it.
    std::vector<MapLoc_s> DecodeLocs(std::span<const u8> data, const TileFlags& flags, std::span<const LocType_s> types)
    {
        auto locs = std::vector<MapLoc_s>{};
        auto packet = Packet{data};
        auto id = -1;
        while (true)
        {
            const auto deltaId = packet.GSmart();
            if (deltaId == END_OF_LIST)
            {
                break;
            }

            id += deltaId;
            auto position = 0;
            while (true)
            {
                const auto deltaPosition = packet.GSmart();
                if (deltaPosition == END_OF_LIST)
                {
                    break;
                }

                position += deltaPosition - 1;
                const auto info = packet.G1();
                const auto level = position >> MapLoc_s::LEVEL_SHIFT;
                if (level > MAX_LEVEL)
                {
                    throw CacheError{std::format("loc {} is on level {}", id, level)};
                }

                const auto loc = MapLoc_s{.id = 0, .position = static_cast<u16>(position), .info = info};

                if (static_cast<std::size_t>(id) >= types.size())
                {
                    throw CacheError{std::format("loc {} has no type", id)};
                }

                if (loc.GetShape() > GROUND_DECOR_SHAPE)
                {
                    throw CacheError{std::format("loc {} has shape {}", id, loc.GetShape())};
                }

                const auto seenLevel = GetSeenLevel(flags, loc.GetLevel(), loc.GetX(), loc.GetZ());
                const auto& type = types[static_cast<std::size_t>(id)];
                if (seenLevel < 0 || (!HasNameOrOption(type) && !AddsCollision(type, loc.GetShape())))
                {
                    continue;
                }

                locs.push_back({.id = static_cast<u16>(id), .position = MapLoc_s::PackPosition(seenLevel, loc.GetX(), loc.GetZ()), .info = info});
            }
        }

        CheckUsedUp(packet);
        return locs;
    }

    template <typename TDecode>
    auto DecodeFile(std::string_view label, TDecode decode)
    {
        try
        {
            return decode();
        }
        catch (const CacheError& e)
        {
            throw CacheError{std::format("{}: {}", label, e.what())};
        }
        catch (const std::out_of_range&)
        {
            throw CacheError{std::format("{}: ends early", label)};
        }
    }
}

std::vector<MapIndexEntry_s> MapDecoder::DecodeIndex(std::span<const u8> data)
{
    if (data.size() % INDEX_ENTRY_SIZE != 0)
    {
        throw CacheError{std::format("map_index is {} bytes, not a multiple of {}", data.size(), INDEX_ENTRY_SIZE)};
    }

    auto entries = std::vector<MapIndexEntry_s>{};
    entries.reserve(data.size() / INDEX_ENTRY_SIZE);
    auto packet = Packet{data};
    while (packet.GetAvailable() > 0)
    {
        auto& entry = entries.emplace_back();
        entry.square = packet.G2();
        entry.landFile = packet.G2();
        entry.locFile = packet.G2();
        static_cast<void>(packet.G1());
    }

    return entries;
}

MapSquare MapDecoder::DecodeSquare(u16 square, std::span<const u8> land, std::span<const u8> locs, std::span<const LocType_s> types)
{
    const auto name = DescribeSquare(square);
    const auto decodedLand = DecodeFile(std::format("square {} land", name), [land]
    {
        return DecodeLand(land);
    });

    const auto& flags = decodedLand.flags;
    auto decodedLocs = DecodeFile(std::format("square {} locs", name), [locs, &flags, types]
    {
        return DecodeLocs(locs, flags, types);
    });

    const auto x = static_cast<u8>(square >> MapSquare::ID_SHIFT);
    const auto z = static_cast<u8>(square & SQUARE_COORD_MASK);
    return MapSquare{x, z, GetBlockedTiles(flags), std::move(decodedLocs), decodedLand.ground};
}

std::string MapDecoder::DescribeSquare(u16 square)
{
    return std::format("{}_{}", square >> MapSquare::ID_SHIFT, square & SQUARE_COORD_MASK);
}
