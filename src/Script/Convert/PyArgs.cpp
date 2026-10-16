#include "pch.hpp"
#include "PyArgs.hpp"

#include "../../Game/Menu/MenuOp.hpp"
#include "../../Game/Query/InventoryItem_s.hpp"
#include "../../Game/Tile_s.hpp"
#include "../Error/ScriptTypeError.hpp"
#include "PyObjects.hpp"
#include "PyValue.hpp"

#include <pocketpy.h>

u8 PyArgs::ToOp(py_Ref value)
{
    return static_cast<u8>(PyValue::ToInt(value, "op", MenuOp::MIN, MenuOp::MAX));
}

OpChoice PyArgs::ToOpChoice(py_Ref value)
{
    if (py_isstr(value))
    {
        return PyValue::ToString(value, "op");
    }

    if (!py_isint(value))
    {
        throw ScriptTypeError{std::format("op must be an int or a str, not {}", PyValue::GetTypeName(value))};
    }

    return ToOp(value);
}

std::vector<s32> PyArgs::ToIds(py_Ref value, std::string_view name)
{
    if (py_isnone(value))
    {
        return {};
    }

    if (py_isint(value))
    {
        return {static_cast<s32>(PyValue::ToInt(value, name, 0, std::numeric_limits<s32>::max()))};
    }

    if (!py_islist(value) && !py_istuple(value))
    {
        throw ScriptTypeError{std::format("{} must be an int, a list of ints or None, not {}", name, PyValue::GetTypeName(value))};
    }

    const auto isList = py_islist(value);
    const auto count = isList ? py_list_len(value) : py_tuple_len(value);
    auto ids = std::vector<s32>{};
    for (auto i = 0; i < count; ++i)
    {
        const auto item = isList ? py_list_getitem(value, i) : py_tuple_getitem(value, i);
        ids.push_back(static_cast<s32>(PyValue::ToInt(item, name, 0, std::numeric_limits<s32>::max())));
    }

    return ids;
}

std::vector<std::string> PyArgs::ToNames(py_Ref value, std::string_view name)
{
    if (py_isstr(value))
    {
        return {PyValue::ToString(value, name)};
    }

    if (!py_islist(value) && !py_istuple(value))
    {
        throw ScriptTypeError{std::format("{} must be a str or a list of str, not {}", name, PyValue::GetTypeName(value))};
    }

    const auto isList = py_islist(value);
    const auto count = isList ? py_list_len(value) : py_tuple_len(value);
    auto names = std::vector<std::string>{};
    for (auto i = 0; i < count; ++i)
    {
        names.push_back(PyValue::ToString(isList ? py_list_getitem(value, i) : py_tuple_getitem(value, i), name));
    }

    if (names.empty())
    {
        throw std::invalid_argument{std::format("{} must have at least one name", name)};
    }

    return names;
}

u16 PyArgs::ToIndex(py_Ref value, std::string_view name, std::string_view className)
{
    if (py_isint(value))
    {
        return PyValue::ToU16(value, name);
    }

    if (!PyValue::IsInstance(value, className))
    {
        throw ScriptTypeError{std::format("{} must be a {} or its index, not {}", name, className, PyValue::GetTypeName(value))};
    }

    return PyValue::ToU16(PyValue::GetField(value, "index"), name);
}

InventoryItem_s PyArgs::ToItem(py_Ref value, std::string_view name)
{
    if (!PyValue::IsInstance(value, PyObjects::ITEM_CLASS))
    {
        throw ScriptTypeError{std::format("{} must be an InvItem, not {}", name, PyValue::GetTypeName(value))};
    }

    return {
        .com = PyValue::ToU16(PyValue::GetField(value, "com"), name),
        .slot = PyValue::ToU16(PyValue::GetField(value, "slot"), name),
        .id = static_cast<s32>(PyValue::ToInt(PyValue::GetField(value, "id"), name)),
        .count = static_cast<s32>(PyValue::ToInt(PyValue::GetField(value, "count"), name)),
    };
}

GroundItemRef_s PyArgs::ToGroundItem(py_Ref value, std::string_view name)
{
    if (!PyValue::IsInstance(value, PyObjects::GROUND_ITEM_CLASS))
    {
        throw ScriptTypeError{std::format("{} must be a GroundItem, not {}", name, PyValue::GetTypeName(value))};
    }

    return {
        .id = PyValue::ToU16(PyValue::GetField(value, "id"), name),
        .x = static_cast<s32>(PyValue::ToInt(PyValue::GetField(value, PyObjects::X_FIELD), name)),
        .z = static_cast<s32>(PyValue::ToInt(PyValue::GetField(value, PyObjects::Z_FIELD), name)),
    };
}

bool PyArgs::IsLoc(py_Ref value)
{
    return PyValue::IsInstance(value, PyObjects::LOC_CLASS);
}

LocRef_s PyArgs::ToLoc(py_Ref value, std::string_view name)
{
    if (!IsLoc(value))
    {
        throw ScriptTypeError{std::format("{} must be a Loc, not {}", name, PyValue::GetTypeName(value))};
    }

    return {
        .id = PyValue::ToU16(PyValue::GetField(value, "id"), name),
        .x = static_cast<s32>(PyValue::ToInt(PyValue::GetField(value, PyObjects::X_FIELD), name)),
        .z = static_cast<s32>(PyValue::ToInt(PyValue::GetField(value, PyObjects::Z_FIELD), name)),
    };
}

std::vector<Tile_s> PyArgs::ToPoints(py_Ref value, s32 level, std::string_view name)
{
    if (!py_islist(value) && !py_istuple(value))
    {
        throw ScriptTypeError{std::format("{} must be a list of (x, z) points, not {}", name, PyValue::GetTypeName(value))};
    }

    const auto isList = py_islist(value);
    const auto count = isList ? py_list_len(value) : py_tuple_len(value);
    auto points = std::vector<Tile_s>{};
    for (auto i = 0; i < count; ++i)
    {
        const auto point = isList ? py_list_getitem(value, i) : py_tuple_getitem(value, i);
        const auto isPair = (py_istuple(point) && py_tuple_len(point) == 2) || (py_islist(point) && py_list_len(point) == 2);
        if (!isPair)
        {
            throw ScriptTypeError{std::format("{} must hold (x, z) pairs, but item {} is {}", name, i, PyValue::GetTypeName(point))};
        }

        const auto x = py_istuple(point) ? py_tuple_getitem(point, 0) : py_list_getitem(point, 0);
        const auto z = py_istuple(point) ? py_tuple_getitem(point, 1) : py_list_getitem(point, 1);
        points.push_back({.x = static_cast<s32>(PyValue::ToInt(x, name)), .z = static_cast<s32>(PyValue::ToInt(z, name)), .level = level});
    }

    return points;
}
