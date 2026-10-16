#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/IfComponent_s.hpp"
#include "../../Cache/LocType_s.hpp"
#include "../../Cache/NpcType_s.hpp"
#include "../../Cache/ObjType_s.hpp"
#include "../../Game/Interface/InterfaceView.hpp"
#include "../../Game/Map/WorldMap.hpp"
#include "../../Game/Menu/Menus.hpp"
#include "../../Game/Query/InventoryItem_s.hpp"
#include "../../Game/State/Entity_s.hpp"
#include "../../Game/State/Npc_s.hpp"
#include "../../Game/State/Player_s.hpp"
#include "../../Game/State/Zone_s.hpp"
#include "../../Game/Tile_s.hpp"

#include <pocketpy.h>

// Game values become instances of the classes the standard library puts in builtins.
class PyObjects
{
public:
    static constexpr auto NPC_CLASS = "Npc";
    static constexpr auto PLAYER_CLASS = "Player";
    static constexpr auto GROUND_ITEM_CLASS = "GroundItem";
    static constexpr auto LOC_CLASS = "Loc";
    static constexpr auto ITEM_CLASS = "InvItem";
    static constexpr auto NPC_TYPE_CLASS = "NpcType";
    static constexpr auto ITEM_TYPE_CLASS = "ItemType";
    static constexpr auto LOC_TYPE_CLASS = "LocType";
    static constexpr auto COMPONENT_CLASS = "Component";
    static constexpr auto PROJECTILE_CLASS = "Projectile";
    // A world object's tile, which the stdlib's tile() reads, and its menu, which actions() reads.
    static constexpr auto X_FIELD = "_x";
    static constexpr auto Z_FIELD = "_z";
    static constexpr auto PLANE_FIELD = "_plane";
    static constexpr auto MENU_FIELD = "_ops";
    // Whether an item's options are its inventory's, used with INV_BUTTON, rather than its own.
    static constexpr auto BUTTON_FIELD = "_button";

    PyObjects() = delete;

    static void FromNpc(py_OutRef out, const Npc_s& npc, u64 tick, const GameCache_s& cache);
    static void FromPlayer(py_OutRef out, const Player_s& player, u64 tick);
    static void FromGroundItem(py_OutRef out, const GroundItem_s& item, const GameCache_s& cache);
    static void FromLoc(py_OutRef out, const SceneLoc_s& loc, const GameCache_s& cache);
    static void FromItem(py_OutRef out, const InventoryItem_s& item, const GameCache_s& cache);
    static void FromNpcType(py_OutRef out, const NpcType_s& type, const GameCache_s& cache);
    static void FromItemType(py_OutRef out, const ObjType_s& type, const GameCache_s& cache);
    static void FromLocType(py_OutRef out, const LocType_s& type, const GameCache_s& cache);
    static void FromProjectile(py_OutRef out, const Projectile_s& projectile);
    static void FromComponent(py_OutRef out, const IfComponent_s& component, const InterfaceView& view);
    // In lower case, as the webclient names them.
    [[nodiscard]] static std::string_view GetTypeName(ComponentType_e type);
    [[nodiscard]] static std::optional<std::string_view> GetButtonName(ButtonType_e button);

private:
    static py_Ref NewInstance(py_OutRef out, const char* className);
    static void SetInt(py_Ref object, const char* name, s64 value);
    static void SetBool(py_Ref object, const char* name, bool value);
    static void SetNone(py_Ref object, const char* name);
    static void SetString(py_Ref object, const char* name, std::string_view text);
    // None for empty text, as the cache has it for a missing name or option.
    static void SetOptionalString(py_Ref object, const char* name, std::string_view text);
    static void SetOptions(py_Ref object, const char* name, std::span<const u16> ops, const GameCache_s& cache);
    static void SetTile(py_Ref object, const Tile_s& tile);
    static void SetMenu(py_Ref object, const Menus::Menu& menu);
    static void SetEntity(py_Ref object, const Entity_s& entity, u64 tick);
    // ('npc' or 'player', index), or None.
    static void SetTarget(py_Ref object, const std::optional<EntityRef_s>& target);
};
