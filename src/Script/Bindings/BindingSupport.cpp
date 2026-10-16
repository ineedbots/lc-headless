#include "pch.hpp"
#include "BindingSupport.hpp"

#include "../../Game/Map/WorldMap.hpp"
#include "../../Game/Protocol/Base37.hpp"
#include "../../Game/Query/InventoryItem_s.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../../Game/State/Npc_s.hpp"
#include "../../Game/State/Player_s.hpp"
#include "../../Game/State/Social_s.hpp"
#include "../../Game/State/Zone_s.hpp"
#include "../../Game/Tile_s.hpp"
#include "../Convert/PyObjects.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptContext.hpp"
#include "../ScriptRuntime.hpp"

#include <pocketpy.h>

namespace
{
    std::array<ScriptContext*, ScriptRuntime::MAX_VMS> boundContexts{};
}

void BindingSupport::SetContext(s32 slot, ScriptContext* context)
{
    boundContexts[static_cast<std::size_t>(slot)] = context;
}

bool BindingSupport::HasContext(s32 slot)
{
    return boundContexts[static_cast<std::size_t>(slot)] != nullptr;
}

ScriptContext& BindingSupport::GetContext()
{
    auto* context = boundContexts[static_cast<std::size_t>(py_currentvm())];
    assert(context != nullptr && "A script function ran in a VM with no ScriptContext bound");
    return *context;
}

bool BindingSupport::ReturnNone()
{
    py_newnone(py_retval());
    return true;
}

bool BindingSupport::ReturnInt(s64 value)
{
    py_newint(py_retval(), value);
    return true;
}

bool BindingSupport::ReturnBool(bool value)
{
    py_newbool(py_retval(), value);
    return true;
}

bool BindingSupport::ReturnString(std::string_view text)
{
    PyValue::FromString(py_retval(), text);
    return true;
}

void BindingSupport::FromNpc(py_OutRef out, const Npc_s& npc)
{
    const auto& context = GetContext();
    PyObjects::FromNpc(out, npc, context.GetState().tick, context.GetCache());
}

void BindingSupport::FromGroundItem(py_OutRef out, const GroundItem_s& item)
{
    PyObjects::FromGroundItem(out, item, GetContext().GetCache());
}

void BindingSupport::FromItem(py_OutRef out, const InventoryItem_s& item)
{
    PyObjects::FromItem(out, item, GetContext().GetCache());
}

void BindingSupport::FromLoc(py_OutRef out, const SceneLoc_s& loc)
{
    PyObjects::FromLoc(out, loc, GetContext().GetCache());
}

void BindingSupport::FromTile(py_OutRef out, const Tile_s& tile)
{
    PyValue::FromPoint(out, tile.x, tile.z);
}

void BindingSupport::FromPlayer(py_OutRef out, const Player_s& player)
{
    PyObjects::FromPlayer(out, player, GetContext().GetState().tick);
}

void BindingSupport::FromFriend(py_OutRef out, const Friend_s& entry)
{
    py_newtuple(out, 2);
    py_newnone(py_tuple_getitem(out, 0));
    py_newint(py_tuple_getitem(out, 1), entry.world);
    PyValue::FromString(py_tuple_getitem(out, 0), entry.name);
}

void BindingSupport::FromName(py_OutRef out, u64 name37)
{
    PyValue::FromString(out, Base37::DecodeDisplayName(name37));
}
