#include "pch.hpp"
#include "TestCache.hpp"

#include "Cache/GameCache_s.hpp"
#include "Cache/MapSquare.hpp"
#include "Cache/TextPool.hpp"

namespace
{
    template <typename T>
    T& GetSlot(std::vector<T>& types, u16 id)
    {
        while (types.size() <= id)
        {
            auto& added = types.emplace_back();
            added.id = static_cast<u16>(types.size() - 1);
        }

        return types[id];
    }

    template <std::size_t TCount>
    void SetOptions(TextPool& text, std::array<u16, TCount>& slots, std::initializer_list<std::string_view> ops)
    {
        assert(ops.size() <= TCount && "More options than slots");
        auto slot = std::size_t{0};
        for (const auto op : ops)
        {
            slots[slot++] = text.InternOption(op);
        }
    }

    struct SquareContents_s
    {
        MapSquare::BlockedTiles blocked;
        std::vector<MapLoc_s> locs;
    };

    u16 GetSquareId(const Tile_s& tile)
    {
        return MapSquare::GetId(tile.x / MapSquare::SIZE, tile.z / MapSquare::SIZE);
    }
}

NpcType_s& TestCache::AddNpc(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops)
{
    auto& type = GetSlot(cache.npcs, id);
    type.name = name;
    SetOptions(cache.text, type.ops, ops);
    return type;
}

ObjType_s& TestCache::AddObj(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops, std::initializer_list<std::string_view> inventoryOps)
{
    auto& type = GetSlot(cache.objs, id);
    type.name = name;
    SetOptions(cache.text, type.ops, ops);
    SetOptions(cache.text, type.inventoryOps, inventoryOps);
    return type;
}

LocType_s& TestCache::AddLoc(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops)
{
    auto& type = GetSlot(cache.locs, id);
    type.name = name;
    SetOptions(cache.text, type.ops, ops);
    return type;
}

void TestCache::SetComponents(GameCache_s& cache)
{
    cache.inventoryComponent = INVENTORY;
    cache.inventorySize = INVENTORY_SIZE;
    cache.equipmentComponent = EQUIPMENT;
    cache.bankComponent = BANK;
    cache.bankInventoryComponent = BANK_INVENTORY;
    cache.runOffButton = RUN_OFF_BUTTON;
    cache.runOnButton = RUN_ON_BUTTON;
    cache.runVarp = RUN_VARP;
}

void TestCache::SetMap(GameCache_s& cache, std::span<const TestLoc_s> locs, std::span<const Tile_s> blocked)
{
    auto squares = std::map<u16, SquareContents_s>{};
    for (const auto& loc : locs)
    {
        const auto position = MapLoc_s::PackPosition(loc.tile.level, loc.tile.x % MapSquare::SIZE, loc.tile.z % MapSquare::SIZE);
        const auto info = static_cast<u8>((loc.shape << MapLoc_s::SHAPE_SHIFT) | loc.angle);
        squares[GetSquareId(loc.tile)].locs.push_back({.id = loc.id, .position = position, .info = info});
    }

    for (const auto& tile : blocked)
    {
        squares[GetSquareId(tile)].blocked.set(MapSquare::GetBit(tile.level, tile.x % MapSquare::SIZE, tile.z % MapSquare::SIZE));
    }

    cache.squares.clear();
    for (auto& [id, contents] : squares)
    {
        const auto x = static_cast<u8>(id >> MapSquare::ID_SHIFT);
        const auto z = static_cast<u8>(id & 0xFF);
        cache.squares.try_emplace(id, x, z, contents.blocked, std::move(contents.locs));
    }
}
