#pragma once

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

// Converts between script values and Python values in the current VM. Game objects become instances of
// the classes the prelude defines in builtins (Npc, Player, GroundItem, Loc, Item), with their fields as
// attributes. Out-of-range numbers throw std::invalid_argument, which the binding raises as ValueError.
class PyConvert
{
public:
    static constexpr auto NPC_CLASS = "Npc";
    static constexpr auto PLAYER_CLASS = "Player";
    static constexpr auto GROUND_ITEM_CLASS = "GroundItem";
    static constexpr auto LOC_CLASS = "Loc";
    static constexpr auto ITEM_CLASS = "Item";

    PyConvert() = delete;

    static void FromNpc(py_OutRef out, const Npc_s& npc, u64 tick);
    static void FromPlayer(py_OutRef out, const Player_s& player, u64 tick);
    static void FromGroundItem(py_OutRef out, const GroundItem_s& item);
    static void FromLoc(py_OutRef out, const LocChange_s& loc);
    static void FromItem(py_OutRef out, const InventoryItem_s& item);
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
    [[nodiscard]] static std::vector<s32> ToIds(py_Ref value, std::string_view name);
    [[nodiscard]] static u16 ToIndex(py_Ref value, std::string_view name, std::string_view className);
    [[nodiscard]] static InventoryItem_s ToItem(py_Ref value, std::string_view name);
    [[nodiscard]] static GroundItemRef_s ToGroundItem(py_Ref value, std::string_view name);
    [[nodiscard]] static std::vector<Tile_s> ToPoints(py_Ref value, s32 level, std::string_view name);

private:
    static py_Ref NewInstance(py_OutRef out, const char* className);
    static void SetInt(py_Ref object, const char* name, s64 value);
    static void SetBool(py_Ref object, const char* name, bool value);
    static void SetNone(py_Ref object, const char* name);
    static void SetString(py_Ref object, const char* name, std::string_view text);
    static void SetEntity(py_Ref object, const Entity_s& entity, u64 tick);
    [[nodiscard]] static bool IsInstance(py_Ref value, std::string_view className);
    [[nodiscard]] static py_Ref GetField(py_Ref object, const char* name);
    [[nodiscard]] static std::string_view GetTypeName(py_Ref value);
};
