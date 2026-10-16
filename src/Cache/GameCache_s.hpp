#pragma once

#include "../Config/Revision_e.hpp"
#include "IfComponent_s.hpp"
#include "LocType_s.hpp"
#include "MapSquare.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

// The CRCs of a 225 map square's files as the cache holds them, to compare with the ones REBUILD_NORMAL
// sends. Nullopt for a file the cache doesn't have.
struct MapCrcs_s
{
    std::optional<s32> land;
    std::optional<s32> locs;
};

// Moves but doesn't copy, because the types' text points into its pool.
struct GameCache_s
{
    static constexpr std::size_t CRC_COUNT = 9;

    // The layout it was read in, which must be the protocol's. The default matches the config's.
    Revision_e revision = Revision_e::Rev289;
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
    // 225 only, keyed by MapSquare::GetId.
    std::unordered_map<u16, MapCrcs_s> mapCrcs;
    std::unordered_map<u16, IfComponent_s> components;

    [[nodiscard]] const LocType_s* FindLoc(s32 id) const;
    [[nodiscard]] const NpcType_s* FindNpc(s32 id) const;
    [[nodiscard]] const ObjType_s* FindObj(s32 id) const;
    // Empty when the cache has no such type, or it has no name.
    [[nodiscard]] std::string_view FindLocName(s32 id) const;
    [[nodiscard]] std::string_view FindNpcName(s32 id) const;
    [[nodiscard]] std::string_view FindObjName(s32 id) const;
    // The types with the name, matched without regard to case.
    [[nodiscard]] std::vector<s32> FindLocIds(std::string_view name) const;
    [[nodiscard]] std::vector<s32> FindNpcIds(std::string_view name) const;
    [[nodiscard]] std::vector<s32> FindObjIds(std::string_view name) const;
    // Empty for TextPool::NO_OPTION.
    [[nodiscard]] std::string_view GetOption(u16 id) const;
    [[nodiscard]] const MapSquare* FindSquare(s32 squareX, s32 squareZ) const;
    [[nodiscard]] const IfComponent_s* FindComponent(s32 id) const;
};
