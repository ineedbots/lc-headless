#include "pch.hpp"
#include "PyConvert.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Cache/LocType_s.hpp"
#include "../Cache/NpcType_s.hpp"
#include "../Cache/ObjType_s.hpp"
#include "../Cache/TextPool.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/State/Entity_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/State/Zone_s.hpp"
#include "../Game/Tile_s.hpp"
#include "ScriptApi.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto BUILTINS_MODULE = "builtins";
    constexpr auto MIN_OP = 1;
    constexpr auto MAX_OP = 5;
    constexpr auto NPC_TARGET = "npc"sv;
    constexpr auto PLAYER_TARGET = "player"sv;
}

void PyConvert::FromNpc(py_OutRef out, const Npc_s& npc, u64 tick, const GameCache_s& cache)
{
    const auto object = NewInstance(out, NPC_CLASS);
    SetInt(object, "id", npc.type);
    SetEntity(object, npc, tick);
    SetMenu(object, ScriptApi::GetNpcMenu(cache, npc.type));
    const auto* const type = cache.FindNpc(npc.type);
    if (type == nullptr)
    {
        SetNone(object, "name");
        SetInt(object, "level", 0);
        SetInt(object, "size", 1);
        return;
    }

    SetOptionalString(object, "name", type->name);
    SetInt(object, "level", type->combatLevel.value_or(0));
    SetInt(object, "size", type->size);
}

void PyConvert::FromPlayer(py_OutRef out, const Player_s& player, u64 tick)
{
    const auto object = NewInstance(out, PLAYER_CLASS);
    SetEntity(object, player, tick);
    if (!player.appearance)
    {
        SetNone(object, "name");
        SetInt(object, "combat_level", 0);
        return;
    }

    SetString(object, "name", player.appearance->name);
    SetInt(object, "combat_level", player.appearance->combatLevel);
}

void PyConvert::FromGroundItem(py_OutRef out, const GroundItem_s& item, const GameCache_s& cache)
{
    const auto object = NewInstance(out, GROUND_ITEM_CLASS);
    SetInt(object, "id", item.id);
    const auto* const type = cache.FindObj(item.id);
    SetOptionalString(object, "name", type == nullptr ? std::string_view{} : type->name);
    SetInt(object, "count", item.count);
    SetTile(object, item.tile);
    SetMenu(object, ScriptApi::GetGroundItemMenu(cache, item.id));
}

void PyConvert::FromLoc(py_OutRef out, const SceneLoc_s& loc, const GameCache_s& cache)
{
    const auto object = NewInstance(out, LOC_CLASS);
    SetInt(object, "id", loc.id);
    const auto* const type = cache.FindLoc(loc.id);
    SetOptionalString(object, "name", type == nullptr ? std::string_view{} : type->name);
    SetBool(object, "changed", loc.changed);
    SetTile(object, loc.tile);
    SetInt(object, "shape", loc.shape);
    SetInt(object, "angle", loc.angle);
    SetInt(object, "layer", static_cast<s64>(loc.layer));
    SetMenu(object, ScriptApi::GetLocMenu(cache, loc.id));
}

void PyConvert::FromItem(py_OutRef out, const InventoryItem_s& item, const GameCache_s& cache)
{
    const auto object = NewInstance(out, ITEM_CLASS);
    SetInt(object, "id", item.id);
    const auto* const type = cache.FindObj(item.id);
    SetOptionalString(object, "name", type == nullptr ? std::string_view{} : type->name);
    SetInt(object, "count", item.count);
    SetInt(object, "slot", item.slot);
    SetInt(object, "com", item.com);
    SetBool(object, "noted", type != nullptr && type->noteOf.has_value());
    SetMenu(object, ScriptApi::GetItemMenu(cache, item.id));
}

void PyConvert::FromNpcType(py_OutRef out, const NpcType_s& type, const GameCache_s& cache)
{
    const auto object = NewInstance(out, NPC_TYPE_CLASS);
    SetInt(object, "id", type.id);
    SetOptionalString(object, "name", type.name);
    SetOptionalString(object, "examine", type.examine);
    SetOptions(object, "ops", type.ops, cache);
    SetInt(object, "size", type.size);
    if (type.combatLevel)
    {
        SetInt(object, "combat_level", *type.combatLevel);
        return;
    }

    SetNone(object, "combat_level");
}

void PyConvert::FromItemType(py_OutRef out, const ObjType_s& type, const GameCache_s& cache)
{
    const auto object = NewInstance(out, ITEM_TYPE_CLASS);
    SetInt(object, "id", type.id);
    SetOptionalString(object, "name", type.name);
    SetOptionalString(object, "examine", type.examine);
    SetOptions(object, "ops", type.ops, cache);
    SetOptions(object, "inventory_ops", type.inventoryOps, cache);
    SetBool(object, "stackable", type.stackable);
    SetBool(object, "members", type.members);
    SetInt(object, "value", type.cost);
    if (type.noteOf)
    {
        SetInt(object, "note_of", *type.noteOf);
        return;
    }

    SetNone(object, "note_of");
}

void PyConvert::FromLocType(py_OutRef out, const LocType_s& type, const GameCache_s& cache)
{
    const auto object = NewInstance(out, LOC_TYPE_CLASS);
    SetInt(object, "id", type.id);
    SetOptionalString(object, "name", type.name);
    SetOptionalString(object, "examine", type.examine);
    SetOptions(object, "ops", type.ops, cache);
    SetInt(object, "width", type.width);
    SetInt(object, "length", type.length);
    SetBool(object, "blocks_walk", type.blockWalk);
    SetBool(object, "blocks_projectiles", type.blockRange);
}

void PyConvert::FromString(py_OutRef out, std::string_view text)
{
    py_newstrv(out, c11_sv{text.data(), static_cast<int>(text.size())});
}

void PyConvert::FromPoint(py_OutRef out, s32 x, s32 z)
{
    py_newtuple(out, 2);
    py_newint(py_tuple_getitem(out, 0), x);
    py_newint(py_tuple_getitem(out, 1), z);
}

s64 PyConvert::ToInt(py_Ref value, std::string_view name)
{
    if (!py_isint(value))
    {
        throw ScriptTypeError{std::format("{} must be an int, not {}", name, GetTypeName(value))};
    }

    return py_toint(value);
}

s64 PyConvert::ToInt(py_Ref value, std::string_view name, s64 min, s64 max)
{
    const auto number = ToInt(value, name);
    if (number < min || number > max)
    {
        throw std::invalid_argument{std::format("{} must be from {} to {}, not {}", name, min, max, number)};
    }

    return number;
}

bool PyConvert::ToBool(py_Ref value, std::string_view name)
{
    if (!py_isbool(value))
    {
        throw ScriptTypeError{std::format("{} must be True or False, not {}", name, GetTypeName(value))};
    }

    return py_tobool(value);
}

std::string PyConvert::ToString(py_Ref value, std::string_view name)
{
    if (!py_isstr(value))
    {
        throw ScriptTypeError{std::format("{} must be a str, not {}", name, GetTypeName(value))};
    }

    auto size = 0;
    const auto* text = py_tostrn(value, &size);
    return std::string{text, static_cast<std::size_t>(size)};
}

std::optional<s64> PyConvert::ToOptionalInt(py_Ref value, std::string_view name)
{
    if (py_isnone(value))
    {
        return std::nullopt;
    }

    return ToInt(value, name);
}

std::optional<bool> PyConvert::ToOptionalBool(py_Ref value, std::string_view name)
{
    if (py_isnone(value))
    {
        return std::nullopt;
    }

    return ToBool(value, name);
}

u16 PyConvert::ToU16(py_Ref value, std::string_view name)
{
    return static_cast<u16>(ToInt(value, name, 0, std::numeric_limits<u16>::max()));
}

u8 PyConvert::ToOp(py_Ref value)
{
    return static_cast<u8>(ToInt(value, "op", MIN_OP, MAX_OP));
}

OpChoice PyConvert::ToOpChoice(py_Ref value)
{
    if (py_isstr(value))
    {
        return ToString(value, "op");
    }

    if (!py_isint(value))
    {
        throw ScriptTypeError{std::format("op must be an int or a str, not {}", GetTypeName(value))};
    }

    return ToOp(value);
}

std::vector<s32> PyConvert::ToIds(py_Ref value, std::string_view name)
{
    if (py_isnone(value))
    {
        return {};
    }

    if (py_isint(value))
    {
        return {static_cast<s32>(ToInt(value, name, 0, std::numeric_limits<s32>::max()))};
    }

    if (!py_islist(value) && !py_istuple(value))
    {
        throw ScriptTypeError{std::format("{} must be an int, a list of ints or None, not {}", name, GetTypeName(value))};
    }

    const auto isList = py_islist(value);
    const auto count = isList ? py_list_len(value) : py_tuple_len(value);
    auto ids = std::vector<s32>{};
    for (auto i = 0; i < count; ++i)
    {
        const auto item = isList ? py_list_getitem(value, i) : py_tuple_getitem(value, i);
        ids.push_back(static_cast<s32>(ToInt(item, name, 0, std::numeric_limits<s32>::max())));
    }

    return ids;
}

std::vector<std::string> PyConvert::ToNames(py_Ref value, std::string_view name)
{
    if (py_isstr(value))
    {
        return {ToString(value, name)};
    }

    if (!py_islist(value) && !py_istuple(value))
    {
        throw ScriptTypeError{std::format("{} must be a str or a list of str, not {}", name, GetTypeName(value))};
    }

    const auto isList = py_islist(value);
    const auto count = isList ? py_list_len(value) : py_tuple_len(value);
    auto names = std::vector<std::string>{};
    for (auto i = 0; i < count; ++i)
    {
        names.push_back(ToString(isList ? py_list_getitem(value, i) : py_tuple_getitem(value, i), name));
    }

    if (names.empty())
    {
        throw std::invalid_argument{std::format("{} must have at least one name", name)};
    }

    return names;
}

u16 PyConvert::ToIndex(py_Ref value, std::string_view name, std::string_view className)
{
    if (py_isint(value))
    {
        return ToU16(value, name);
    }

    if (!IsInstance(value, className))
    {
        throw ScriptTypeError{std::format("{} must be a {} or its index, not {}", name, className, GetTypeName(value))};
    }

    return ToU16(GetField(value, "index"), name);
}

InventoryItem_s PyConvert::ToItem(py_Ref value, std::string_view name)
{
    if (!IsInstance(value, ITEM_CLASS))
    {
        throw ScriptTypeError{std::format("{} must be an InvItem, not {}", name, GetTypeName(value))};
    }

    return {
        .com = ToU16(GetField(value, "com"), name),
        .slot = ToU16(GetField(value, "slot"), name),
        .id = static_cast<s32>(ToInt(GetField(value, "id"), name)),
        .count = static_cast<s32>(ToInt(GetField(value, "count"), name)),
    };
}

GroundItemRef_s PyConvert::ToGroundItem(py_Ref value, std::string_view name)
{
    if (!IsInstance(value, GROUND_ITEM_CLASS))
    {
        throw ScriptTypeError{std::format("{} must be a GroundItem, not {}", name, GetTypeName(value))};
    }

    return {
        .id = ToU16(GetField(value, "id"), name),
        .x = static_cast<s32>(ToInt(GetField(value, X_FIELD), name)),
        .z = static_cast<s32>(ToInt(GetField(value, Z_FIELD), name)),
    };
}

bool PyConvert::IsLoc(py_Ref value)
{
    return IsInstance(value, LOC_CLASS);
}

LocRef_s PyConvert::ToLoc(py_Ref value, std::string_view name)
{
    if (!IsLoc(value))
    {
        throw ScriptTypeError{std::format("{} must be a Loc, not {}", name, GetTypeName(value))};
    }

    return {
        .id = ToU16(GetField(value, "id"), name),
        .x = static_cast<s32>(ToInt(GetField(value, X_FIELD), name)),
        .z = static_cast<s32>(ToInt(GetField(value, Z_FIELD), name)),
    };
}

std::vector<Tile_s> PyConvert::ToPoints(py_Ref value, s32 level, std::string_view name)
{
    if (!py_islist(value) && !py_istuple(value))
    {
        throw ScriptTypeError{std::format("{} must be a list of (x, z) points, not {}", name, GetTypeName(value))};
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
            throw ScriptTypeError{std::format("{} must hold (x, z) pairs, but item {} is {}", name, i, GetTypeName(point))};
        }

        const auto x = py_istuple(point) ? py_tuple_getitem(point, 0) : py_list_getitem(point, 0);
        const auto z = py_istuple(point) ? py_tuple_getitem(point, 1) : py_list_getitem(point, 1);
        points.push_back({.x = static_cast<s32>(ToInt(x, name)), .z = static_cast<s32>(ToInt(z, name)), .level = level});
    }

    return points;
}

py_Ref PyConvert::NewInstance(py_OutRef out, const char* className)
{
    const auto type = py_gettype(BUILTINS_MODULE, py_name(className));
    assert(type != 0 && "The prelude defines every class PyConvert builds");
    py_newobject(out, type, -1, 0);
    return out;
}

void PyConvert::SetInt(py_Ref object, const char* name, s64 value)
{
    auto field = py_TValue{};
    py_newint(&field, value);
    py_setdict(object, py_name(name), &field);
}

void PyConvert::SetBool(py_Ref object, const char* name, bool value)
{
    auto field = py_TValue{};
    py_newbool(&field, value);
    py_setdict(object, py_name(name), &field);
}

void PyConvert::SetNone(py_Ref object, const char* name)
{
    py_setdict(object, py_name(name), py_None());
}

void PyConvert::SetString(py_Ref object, const char* name, std::string_view text)
{
    // The new str lives on the value stack until the object holds it, so a collection can't free it.
    const auto field = py_pushtmp();
    FromString(field, text);
    py_setdict(object, py_name(name), field);
    py_pop();
}

void PyConvert::SetOptionalString(py_Ref object, const char* name, std::string_view text)
{
    if (text.empty())
    {
        SetNone(object, name);
        return;
    }

    SetString(object, name, text);
}

void PyConvert::SetOptions(py_Ref object, const char* name, std::span<const u16> ops, const GameCache_s& cache)
{
    // The list lives on the value stack until the object holds it, and each item is None until its str
    // is made, so a collection never sees an uninitialized value.
    const auto list = py_pushtmp();
    py_newlist(list);
    for (const auto op : ops)
    {
        const auto item = py_list_emplace(list);
        py_newnone(item);
        if (op != TextPool::NO_OPTION)
        {
            FromString(item, cache.GetOption(op));
        }
    }

    py_setdict(object, py_name(name), list);
    py_pop();
}

void PyConvert::SetTile(py_Ref object, const Tile_s& tile)
{
    SetInt(object, X_FIELD, tile.x);
    SetInt(object, Z_FIELD, tile.z);
    SetInt(object, PLANE_FIELD, tile.level);
}

void PyConvert::SetMenu(py_Ref object, const ScriptApi::Menu& menu)
{
    // As SetOptions: the list stays on the value stack until the object holds it.
    const auto list = py_pushtmp();
    py_newlist(list);
    for (const auto option : menu)
    {
        const auto item = py_list_emplace(list);
        py_newnone(item);
        if (!option.empty())
        {
            FromString(item, option);
        }
    }

    py_setdict(object, py_name(MENU_FIELD), list);
    py_pop();
}

void PyConvert::SetEntity(py_Ref object, const Entity_s& entity, u64 tick)
{
    SetInt(object, "index", entity.index);
    SetTile(object, entity.tile);
    SetInt(object, "animation", entity.animation.id);
    SetBool(object, "moving", ScriptApi::IsMoving(entity, tick));
    SetBool(object, "in_combat", ScriptApi::InCombat(entity, tick));
    // As rs2b0t's health, 0 until a hit shows it.
    const auto* const hit = entity.hits.empty() ? nullptr : &entity.hits.back();
    SetInt(object, "health", hit == nullptr ? 0 : hit->health);
    SetInt(object, "max_health", hit == nullptr ? 0 : hit->maxHealth);

    if (!entity.faceEntity)
    {
        SetNone(object, "target");
        return;
    }

    // Both slots hold a value before the str allocates, so a collection never sees an uninitialized one.
    const auto target = py_pushtmp();
    py_newtuple(target, 2);
    py_newnone(py_tuple_getitem(target, 0));
    py_newint(py_tuple_getitem(target, 1), entity.faceEntity->index);
    FromString(py_tuple_getitem(target, 0), entity.faceEntity->type == EntityType_e::Npc ? NPC_TARGET : PLAYER_TARGET);
    py_setdict(object, py_name("target"), target);
    py_pop();
}

bool PyConvert::IsInstance(py_Ref value, std::string_view className)
{
    const auto name = std::string{className};
    const auto type = py_gettype(BUILTINS_MODULE, py_name(name.c_str()));
    return type != 0 && py_isinstance(value, type);
}

py_Ref PyConvert::GetField(py_Ref object, const char* name)
{
    const auto field = py_getdict(object, py_name(name));
    if (field == nullptr)
    {
        throw ScriptTypeError{std::format("the object has no {} attribute", name)};
    }

    return field;
}

std::string_view PyConvert::GetTypeName(py_Ref value)
{
    return py_tpname(py_typeof(value));
}
