#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Cache/LocType_s.hpp"
#include "../Cache/NpcType_s.hpp"
#include "../Cache/ObjType_s.hpp"
#include "../Game/InterfaceView.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/State/Zone_s.hpp"
#include "../Game/Tile_s.hpp"
#include "ScriptApi.hpp"

#include <pocketpy.h>

// A Python argument had the wrong type; the binding raises it as TypeError.
class ScriptTypeError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};

// Python raised while a value was being converted; the binding leaves that exception in place.
class ScriptRaisedError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};

struct GroundItemRef_s
{
    u16 id = 0;
    s32 x = 0;
    s32 z = 0;
};

struct LocRef_s
{
    u16 id = 0;
    s32 x = 0;
    s32 z = 0;
};

// An option chosen by its number, or by its text.
using OpChoice = std::variant<u8, std::string>;

// Converts between script values and Python values in the current VM. Game objects become instances of
// the classes the standard library puts in builtins (Npc, Player, GroundItem, Loc, InvItem, and the
// NpcType, ItemType and LocType definitions), with their fields as attributes; names and options come
// from the cache, and are None where it has none. Out-of-range numbers throw std::invalid_argument, which the
// binding raises as ValueError.
class PyConvert
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
    // A world object's tile, which the stdlib's tile() reads, and its menu, which actions() reads.
    static constexpr auto X_FIELD = "_x";
    static constexpr auto Z_FIELD = "_z";
    static constexpr auto PLANE_FIELD = "_plane";
    static constexpr auto MENU_FIELD = "_ops";
    // Whether an item's options are its inventory's, used with INV_BUTTON, rather than its own.
    static constexpr auto BUTTON_FIELD = "_button";

    PyConvert() = delete;

    static void FromNpc(py_OutRef out, const Npc_s& npc, u64 tick, const GameCache_s& cache);
    static void FromPlayer(py_OutRef out, const Player_s& player, u64 tick);
    static void FromGroundItem(py_OutRef out, const GroundItem_s& item, const GameCache_s& cache);
    static void FromLoc(py_OutRef out, const SceneLoc_s& loc, const GameCache_s& cache);
    static void FromItem(py_OutRef out, const InventoryItem_s& item, const GameCache_s& cache);
    static void FromNpcType(py_OutRef out, const NpcType_s& type, const GameCache_s& cache);
    static void FromItemType(py_OutRef out, const ObjType_s& type, const GameCache_s& cache);
    static void FromLocType(py_OutRef out, const LocType_s& type, const GameCache_s& cache);
    // A component as the player sees it now.
    static void FromComponent(py_OutRef out, const IfComponent_s& component, const InterfaceView& view);
    // The webclient's names for a component's type and button, in lower case.
    [[nodiscard]] static std::string_view GetTypeName(ComponentType_e type);
    [[nodiscard]] static std::optional<std::string_view> GetButtonName(ButtonType_e button);
    static void FromString(py_OutRef out, std::string_view text);
    static void FromPoint(py_OutRef out, s32 x, s32 z);

    // Each item is set to None as it's appended and converted in place, so the list never holds an
    // uninitialized value when a conversion allocates and the collector runs.
    template <typename T, typename TConvert>
    static void FromList(py_OutRef out, const std::vector<T>& values, TConvert convert)
    {
        py_newlist(out);
        for (const auto& value : values)
        {
            const auto item = py_list_emplace(out);
            py_newnone(item);
            convert(item, value);
        }
    }

    template <typename T, typename TConvert>
    static void FromOptional(py_OutRef out, const std::optional<T>& value, TConvert convert)
    {
        if (!value)
        {
            py_newnone(out);
            return;
        }

        convert(out, *value);
    }

    [[nodiscard]] static s64 ToInt(py_Ref value, std::string_view name);
    [[nodiscard]] static s64 ToInt(py_Ref value, std::string_view name, s64 min, s64 max);
    [[nodiscard]] static bool ToBool(py_Ref value, std::string_view name);
    [[nodiscard]] static std::string ToString(py_Ref value, std::string_view name);
    [[nodiscard]] static std::optional<s64> ToOptionalInt(py_Ref value, std::string_view name);
    [[nodiscard]] static std::optional<bool> ToOptionalBool(py_Ref value, std::string_view name);
    [[nodiscard]] static u16 ToU16(py_Ref value, std::string_view name);
    [[nodiscard]] static u8 ToOp(py_Ref value);
    // An int from 1 to 5, or a str.
    [[nodiscard]] static OpChoice ToOpChoice(py_Ref value);
    [[nodiscard]] static std::vector<s32> ToIds(py_Ref value, std::string_view name);
    // One str or a list of them, at least one.
    [[nodiscard]] static std::vector<std::string> ToNames(py_Ref value, std::string_view name);
    [[nodiscard]] static u16 ToIndex(py_Ref value, std::string_view name, std::string_view className);
    [[nodiscard]] static InventoryItem_s ToItem(py_Ref value, std::string_view name);
    [[nodiscard]] static GroundItemRef_s ToGroundItem(py_Ref value, std::string_view name);
    [[nodiscard]] static bool IsLoc(py_Ref value);
    [[nodiscard]] static LocRef_s ToLoc(py_Ref value, std::string_view name);
    [[nodiscard]] static std::vector<Tile_s> ToPoints(py_Ref value, s32 level, std::string_view name);

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
    static void SetMenu(py_Ref object, const ScriptApi::Menu& menu);
    static void SetEntity(py_Ref object, const Entity_s& entity, u64 tick);
    [[nodiscard]] static bool IsInstance(py_Ref value, std::string_view className);
    [[nodiscard]] static py_Ref GetField(py_Ref object, const char* name);
    [[nodiscard]] static std::string_view GetTypeName(py_Ref value);
};
