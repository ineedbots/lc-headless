#pragma once

#include "../../Game/Query/InventoryItem_s.hpp"
#include "../../Game/Query/SearchFilter_s.hpp"
#include "../../Game/State/Zone_s.hpp"
#include "../../Game/Tile_s.hpp"

#include <pocketpy.h>

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

using OpChoice = std::variant<u8, std::string>;

// Script arguments into game values: ids and names, ops, and the stdlib's objects passed back in. A value of
// the wrong type throws ScriptTypeError, and one out of range std::invalid_argument.
class PyArgs
{
public:
    PyArgs() = delete;

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

    [[nodiscard]] static s32 ToCoord(py_Ref value, std::string_view name);
    [[nodiscard]] static std::optional<s32> ToRadius(py_Ref value);
    [[nodiscard]] static SearchFilter_s ToFilter(py_Ref ids, py_Ref radius);
    [[nodiscard]] static SearchFilter_s ToSearch(py_Ref ids, py_Ref radius, py_Ref names);
    [[nodiscard]] static SearchFilter_s ToNameFilter(py_Ref names, py_Ref radius);
    [[nodiscard]] static std::optional<LocLayer_e> ToLayer(py_Ref value);
    // An interface's root component, or nullopt for None.
    [[nodiscard]] static std::optional<u16> ToRoot(py_Ref value);
};
