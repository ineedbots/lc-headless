#include "pch.hpp"
#include "PyObjects.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/LocType_s.hpp"
#include "../../Cache/NpcType_s.hpp"
#include "../../Cache/ObjType_s.hpp"
#include "../../Cache/TextPool.hpp"
#include "../../Game/Map/WorldMap.hpp"
#include "../../Game/Menu/Menus.hpp"
#include "../../Game/State/EntityStatus.hpp"
#include "../../Game/State/Entity_s.hpp"
#include "../../Game/State/Npc_s.hpp"
#include "../../Game/State/Player_s.hpp"
#include "../../Game/State/Zone_s.hpp"
#include "../../Game/Tile_s.hpp"
#include "PyValue.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto NPC_TARGET = "npc"sv;
    constexpr auto PLAYER_TARGET = "player"sv;
}

void PyObjects::FromNpc(py_OutRef out, const Npc_s& npc, u64 tick, const GameCache_s& cache)
{
    const auto object = NewInstance(out, NPC_CLASS);
    SetInt(object, "id", npc.type);
    SetEntity(object, npc, tick, cache);
    SetMenu(object, Menus::GetNpcMenu(cache, npc.type));

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

void PyObjects::FromPlayer(py_OutRef out, const Player_s& player, u64 tick, const GameCache_s& cache)
{
    const auto object = NewInstance(out, PLAYER_CLASS);
    SetEntity(object, player, tick, cache);

    if (!player.appearance)
    {
        SetNone(object, "name");
        SetInt(object, "combat_level", 0);
        return;
    }

    SetString(object, "name", player.appearance->name);
    SetInt(object, "combat_level", player.appearance->combatLevel);
}

void PyObjects::FromGroundItem(py_OutRef out, const GroundItem_s& item, const GameCache_s& cache)
{
    const auto object = NewInstance(out, GROUND_ITEM_CLASS);
    SetInt(object, "id", item.id);

    const auto* const type = cache.FindObj(item.id);
    SetOptionalString(object, "name", type == nullptr ? std::string_view{} : type->name);
    SetInt(object, "count", item.count);
    SetTile(object, item.tile);
    SetMenu(object, Menus::GetGroundItemMenu(cache, item.id));
}

void PyObjects::FromLoc(py_OutRef out, const SceneLoc_s& loc, const GameCache_s& cache)
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
    SetMenu(object, Menus::GetLocMenu(cache, loc.id));
}

void PyObjects::FromProjectile(py_OutRef out, const Projectile_s& projectile)
{
    const auto object = NewInstance(out, PROJECTILE_CLASS);
    SetInt(object, "spotanim", projectile.spotAnim);
    SetInt(object, "_sx", projectile.source.x);
    SetInt(object, "_sz", projectile.source.z);
    SetInt(object, "_dx", projectile.destination.x);
    SetInt(object, "_dz", projectile.destination.z);
    SetInt(object, PLANE_FIELD, projectile.source.level);
    SetInt(object, "start_delay", projectile.startDelay);
    SetInt(object, "end_delay", projectile.endDelay);
    SetInt(object, "tick", static_cast<s64>(projectile.tick));
    SetTarget(object, projectile.target);
}

void PyObjects::FromItem(py_OutRef out, const InventoryItem_s& item, const GameCache_s& cache)
{
    const auto object = NewInstance(out, ITEM_CLASS);
    SetInt(object, "id", item.id);

    const auto* const type = cache.FindObj(item.id);
    SetOptionalString(object, "name", type == nullptr ? std::string_view{} : type->name);
    SetInt(object, "count", item.count);
    SetInt(object, "slot", item.slot);
    SetInt(object, "com", item.com);
    SetBool(object, "noted", type != nullptr && type->noteOf.has_value());

    const auto inventoryMenu = Menus::GetInventoryMenu(cache, item.com);
    SetMenu(object, inventoryMenu.value_or(Menus::GetItemMenu(cache, item.id)));
    SetBool(object, BUTTON_FIELD, inventoryMenu.has_value());
}

void PyObjects::FromNpcType(py_OutRef out, const NpcType_s& type, const GameCache_s& cache)
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

void PyObjects::FromItemType(py_OutRef out, const ObjType_s& type, const GameCache_s& cache)
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
    SetBool(object, "equippable", type.equippable);
    SetBool(object, "stack_variant", type.stackVariant);

    if (type.noteOf)
    {
        SetInt(object, "note_of", *type.noteOf);
        return;
    }

    SetNone(object, "note_of");
}

void PyObjects::FromLocType(py_OutRef out, const LocType_s& type, const GameCache_s& cache)
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

void PyObjects::FromComponent(py_OutRef out, const IfComponent_s& component, const InterfaceView& view)
{
    const auto object = NewInstance(out, COMPONENT_CLASS);
    SetInt(object, "id", component.id);
    SetInt(object, "root", component.root);

    if (component.parent)
    {
        SetInt(object, "layer", *component.parent);
    }
    else
    {
        SetNone(object, "layer");
    }

    SetString(object, "type", GetTypeName(component.type));

    const auto button = GetButtonName(component.buttonType);
    SetOptionalString(object, "button", button.value_or(std::string_view{}));
    SetOptionalString(object, "button_text", component.buttonText);
    SetString(object, "text", view.GetText(component));
    SetInt(object, "colour", view.GetColour(component));
    SetBool(object, "hidden", view.IsHidden(component));
    SetBool(object, "visible", view.IsVisible(component));
    SetOptionalString(object, "target_verb", component.targetVerb);
    SetOptionalString(object, "target_name", component.targetName);

    const auto position = view.GetPosition(component);
    SetInt(object, "x", position.x);
    SetInt(object, "y", position.y);
    SetInt(object, "width", component.width);
    SetInt(object, "height", component.height);

    // Such as a make menu's product.
    if (const auto shown = view.GetObject(component))
    {
        SetInt(object, "item", *shown);
    }
    else
    {
        SetNone(object, "item");
    }

    // The varp a button's first condition reads, with pushvar (5) or testbit (13), and the value it's
    // compared with: what a Select or Toggle button sets.
    constexpr auto PUSHVAR = u16{5};
    constexpr auto TESTBIT = u16{13};
    const auto& script = component.scripts.empty() ? std::vector<u16>{} : component.scripts.front();
    if (script.size() >= 2 && (script[0] == PUSHVAR || script[0] == TESTBIT))
    {
        SetInt(object, "varp", script[1]);
    }
    else
    {
        SetNone(object, "varp");
    }

    if (component.operands.empty())
    {
        SetNone(object, "value");
    }
    else
    {
        SetInt(object, "value", component.operands.front());
    }

    // As SetOptions: each list stays on the value stack until the object holds it.
    const auto children = py_pushtmp();
    py_newlist(children);

    for (const auto& child : component.children)
    {
        py_newint(py_list_emplace(children), child.id);
    }

    py_setdict(object, py_name("children"), children);
    py_pop();

    if (component.type != ComponentType_e::Inv)
    {
        SetNone(object, "options");
        return;
    }

    const auto options = py_pushtmp();
    py_newlist(options);

    for (const auto& option : component.options)
    {
        const auto item = py_list_emplace(options);
        py_newnone(item);

        if (!option.empty())
        {
            PyValue::FromString(item, option);
        }
    }

    py_setdict(object, py_name("options"), options);
    py_pop();
}

std::string_view PyObjects::GetTypeName(ComponentType_e type)
{
    switch (type)
    {
    case ComponentType_e::Layer:
        return "layer";
    case ComponentType_e::Unused:
        return "unused";
    case ComponentType_e::Inv:
        return "inv";
    case ComponentType_e::Rect:
        return "rect";
    case ComponentType_e::Text:
        return "text";
    case ComponentType_e::Graphic:
        return "graphic";
    case ComponentType_e::Model:
        return "model";
    case ComponentType_e::InvText:
        return "invtext";
    }

    return "unknown";
}

std::optional<std::string_view> PyObjects::GetButtonName(ButtonType_e button)
{
    switch (button)
    {
    case ButtonType_e::None:
        return std::nullopt;
    case ButtonType_e::Ok:
        return "ok";
    case ButtonType_e::Target:
        return "target";
    case ButtonType_e::Close:
        return "close";
    case ButtonType_e::Toggle:
        return "toggle";
    case ButtonType_e::Select:
        return "select";
    case ButtonType_e::Continue:
        return "continue";
    }

    return std::nullopt;
}

py_Ref PyObjects::NewInstance(py_OutRef out, const char* className)
{
    const auto type = py_gettype(PyValue::BUILTINS_MODULE, py_name(className));
    assert(type != 0 && "The prelude defines every class PyObjects builds");
    py_newobject(out, type, -1, 0);
    return out;
}

void PyObjects::SetInt(py_Ref object, const char* name, s64 value)
{
    auto field = py_TValue{};
    py_newint(&field, value);
    py_setdict(object, py_name(name), &field);
}

void PyObjects::SetBool(py_Ref object, const char* name, bool value)
{
    auto field = py_TValue{};
    py_newbool(&field, value);
    py_setdict(object, py_name(name), &field);
}

void PyObjects::SetNone(py_Ref object, const char* name)
{
    py_setdict(object, py_name(name), py_None());
}

void PyObjects::SetString(py_Ref object, const char* name, std::string_view text)
{
    // The new str lives on the value stack until the object holds it, so a collection can't free it.
    const auto field = py_pushtmp();
    PyValue::FromString(field, text);
    py_setdict(object, py_name(name), field);
    py_pop();
}

void PyObjects::SetOptionalString(py_Ref object, const char* name, std::string_view text)
{
    if (text.empty())
    {
        SetNone(object, name);
        return;
    }

    SetString(object, name, text);
}

void PyObjects::SetOptions(py_Ref object, const char* name, std::span<const u16> ops, const GameCache_s& cache)
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
            PyValue::FromString(item, cache.GetOption(op));
        }
    }

    py_setdict(object, py_name(name), list);
    py_pop();
}

void PyObjects::SetTile(py_Ref object, const Tile_s& tile)
{
    SetInt(object, X_FIELD, tile.x);
    SetInt(object, Z_FIELD, tile.z);
    SetInt(object, PLANE_FIELD, tile.level);
}

void PyObjects::SetMenu(py_Ref object, const Menus::Menu& menu)
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
            PyValue::FromString(item, option);
        }
    }

    py_setdict(object, py_name(MENU_FIELD), list);
    py_pop();
}

void PyObjects::SetEntity(py_Ref object, const Entity_s& entity, u64 tick, const GameCache_s& cache)
{
    SetInt(object, "index", entity.index);
    SetTile(object, entity.tile);
    SetInt(object, "animation", EntityStatus::GetAnimation(entity, tick, cache.FindSeqLength(entity.animation.id)));
    SetBool(object, "moving", EntityStatus::IsMoving(entity, tick));
    SetBool(object, "in_combat", EntityStatus::InCombat(entity, tick));

    // As rs2b0t's health, 0 until a hit shows it.
    const auto* const hit = entity.hits.empty() ? nullptr : &entity.hits.back();
    SetInt(object, "health", hit == nullptr ? 0 : hit->health);
    SetInt(object, "max_health", hit == nullptr ? 0 : hit->maxHealth);

    SetTarget(object, entity.faceEntity);

    // Overhead text and the tick it was said on, which the webclient shows for about 5 ticks.
    if (entity.say)
    {
        SetString(object, "say", entity.say->text);
        SetInt(object, "say_tick", static_cast<s64>(entity.say->tick));
    }
    else
    {
        SetNone(object, "say");
        SetNone(object, "say_tick");
    }
}

void PyObjects::SetTarget(py_Ref object, const std::optional<EntityRef_s>& entity)
{
    if (!entity)
    {
        SetNone(object, "target");
        return;
    }

    // Both slots hold a value before the str allocates, so a collection never sees an uninitialized one.
    const auto target = py_pushtmp();
    py_newtuple(target, 2);
    py_newnone(py_tuple_getitem(target, 0));
    py_newint(py_tuple_getitem(target, 1), entity->index);
    PyValue::FromString(py_tuple_getitem(target, 0), entity->type == EntityType_e::Npc ? NPC_TARGET : PLAYER_TARGET);
    py_setdict(object, py_name("target"), target);
    py_pop();
}
