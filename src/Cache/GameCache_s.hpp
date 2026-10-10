#pragma once

#include "IfComponent_s.hpp"
#include "LocType_s.hpp"
#include "MapSquare.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

// Everything the client uses from the game cache. It's loaded once, and shared read-only by every
// account in the process. It moves but doesn't copy, because the types' text points into its pool.
struct GameCache_s
{
    static constexpr std::size_t CRC_COUNT = 9;

    std::array<s32, CRC_COUNT> crcs{};
    // Components and a varp the client uses. The server's content pack numbers them when it builds the
    // cache, so CacheLoader finds them by what the cache says about them.
    u16 logoutComponent = 0;
    u16 inventoryComponent = 0;
    s32 inventorySize = 0;
    u16 equipmentComponent = 0;
    u16 bankComponent = 0;
    // The backpack beside the bank, which replaces the inventory tab while the bank is open.
    u16 bankInventoryComponent = 0;
    u16 runOffButton = 0;
    u16 runOnButton = 0;
    u16 runVarp = 0;
    TextPool text;
    // Index i holds the type whose id is i.
    std::vector<LocType_s> locs;
    std::vector<NpcType_s> npcs;
    std::vector<ObjType_s> objs;
    // Keyed by MapSquare::GetId.
    std::unordered_map<u16, MapSquare> squares;
    // Every interface component, by id.
    std::unordered_map<u16, IfComponent_s> components;

    [[nodiscard]] const LocType_s* FindLoc(s32 id) const;
    [[nodiscard]] const NpcType_s* FindNpc(s32 id) const;
    [[nodiscard]] const ObjType_s* FindObj(s32 id) const;
    // Empty for TextPool::NO_OPTION.
    [[nodiscard]] std::string_view GetOption(u16 id) const;
    [[nodiscard]] const MapSquare* FindSquare(s32 squareX, s32 squareZ) const;
    [[nodiscard]] const IfComponent_s* FindComponent(s32 id) const;
};
