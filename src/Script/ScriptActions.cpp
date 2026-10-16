#include "pch.hpp"
#include "ScriptActions.hpp"

#include "../Cache/ClientCode_e.hpp"
#include "../Cache/GameCache_s.hpp"
#include "../Cache/IfComponent_s.hpp"
#include "../Game/GameActions.hpp"
#include "../Game/Interface/DialogueTracker.hpp"
#include "../Game/Interface/InterfaceView.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/Query/EntityQuery.hpp"
#include "../Game/Query/InventoryItem_s.hpp"
#include "../Game/Query/InventoryQuery.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/Tile_s.hpp"

ScriptActions::ScriptActions(const GameState_s& state, const WorldMap& map, GameActions& actions)
    : m_state{state}
    , m_map{map}
    , m_actions{actions}
{
}

bool ScriptActions::WalkTo(s32 x, s32 z, bool run)
{
    return m_actions.WalkTo(ToTile(x, z), run);
}

void ScriptActions::WalkPath(std::span<const Tile_s> points, bool run)
{
    m_actions.WalkPath(points, run);
}

bool ScriptActions::InteractNpc(u16 index, u8 op)
{
    if (m_state.FindNpc(index) == nullptr)
    {
        return false;
    }

    m_actions.InteractNpc(index, op);
    return true;
}

bool ScriptActions::InteractPlayer(u16 index, u8 op)
{
    if (m_state.FindPlayer(index) == nullptr)
    {
        return false;
    }

    m_actions.InteractPlayer(index, op);
    return true;
}

void ScriptActions::InteractLoc(u16 loc, s32 x, s32 z, u8 op)
{
    m_actions.InteractLoc(ToTile(x, z), loc, op);
}

void ScriptActions::InteractLocVia(std::span<const Tile_s> waypoints, u16 loc, s32 x, s32 z, u8 op)
{
    m_actions.InteractLocVia(waypoints, ToTile(x, z), loc, op);
}

bool ScriptActions::InteractGroundItem(u16 obj, s32 x, s32 z, u8 op)
{
    const auto tile = ToTile(x, z);
    if (!HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.InteractGroundItem(tile, obj, op);
    return true;
}

bool ScriptActions::ItemOp(const InventoryItem_s& item, u8 op)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.OperateItem(ToItemRef(item), op);
    return true;
}

bool ScriptActions::InventoryButton(const InventoryItem_s& item, u8 op)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.InventoryButton(ToItemRef(item), op);
    return true;
}

void ScriptActions::MoveItem(u16 com, u16 fromSlot, u16 toSlot)
{
    m_actions.MoveItem(com, fromSlot, toSlot);
}

bool ScriptActions::UseItemOnNpc(const InventoryItem_s& item, u16 npcIndex)
{
    if (!HasItem(item) || m_state.FindNpc(npcIndex) == nullptr)
    {
        return false;
    }

    m_actions.UseItemOnNpc(ToItemRef(item), npcIndex);
    return true;
}

bool ScriptActions::UseItemOnPlayer(const InventoryItem_s& item, u16 playerIndex)
{
    if (!HasItem(item) || m_state.FindPlayer(playerIndex) == nullptr)
    {
        return false;
    }

    m_actions.UseItemOnPlayer(ToItemRef(item), playerIndex);
    return true;
}

bool ScriptActions::UseItemOnLoc(const InventoryItem_s& item, u16 loc, s32 x, s32 z)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.UseItemOnLoc(ToItemRef(item), ToTile(x, z), loc);
    return true;
}

bool ScriptActions::UseItemOnGroundItem(const InventoryItem_s& item, u16 obj, s32 x, s32 z)
{
    const auto tile = ToTile(x, z);
    if (!HasItem(item) || !HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.UseItemOnGroundItem(ToItemRef(item), tile, obj);
    return true;
}

bool ScriptActions::UseItemOnItem(const InventoryItem_s& item, const InventoryItem_s& target)
{
    if (!HasItem(item) || !HasItem(target))
    {
        return false;
    }

    m_actions.UseItemOnItem(ToItemRef(item), ToItemRef(target));
    return true;
}

bool ScriptActions::CastOnNpc(u16 spellCom, u16 npcIndex)
{
    if (m_state.FindNpc(npcIndex) == nullptr)
    {
        return false;
    }

    m_actions.CastOnNpc(spellCom, npcIndex);
    return true;
}

bool ScriptActions::CastOnPlayer(u16 spellCom, u16 playerIndex)
{
    if (m_state.FindPlayer(playerIndex) == nullptr)
    {
        return false;
    }

    m_actions.CastOnPlayer(spellCom, playerIndex);
    return true;
}

void ScriptActions::CastOnLoc(u16 spellCom, u16 loc, s32 x, s32 z)
{
    m_actions.CastOnLoc(spellCom, ToTile(x, z), loc);
}

bool ScriptActions::CastOnGroundItem(u16 spellCom, u16 obj, s32 x, s32 z)
{
    const auto tile = ToTile(x, z);
    if (!HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.CastOnGroundItem(spellCom, tile, obj);
    return true;
}

bool ScriptActions::CastOnItem(u16 spellCom, const InventoryItem_s& item)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.CastOnItem(spellCom, ToItemRef(item));
    return true;
}

void ScriptActions::ClickButton(u16 com)
{
    m_actions.ClickButton(com);
}

bool ScriptActions::ClickComponent(u16 com)
{
    const auto view = GetInterfaces();
    const auto* const component = view.Find(com);
    if (component == nullptr)
    {
        throw std::invalid_argument{std::format("the cache has no component {}", com)};
    }

    if (component->buttonType == ButtonType_e::None || component->buttonType == ButtonType_e::Target)
    {
        throw std::invalid_argument{std::format("component {} isn't a button a click uses", com)};
    }

    if (!view.IsVisible(*component))
    {
        return false;
    }

    m_actions.ClickComponent(com, component->buttonType);
    return true;
}

bool ScriptActions::ClickText(std::string_view text, std::optional<u16> root)
{
    const auto view = GetInterfaces();
    for (const auto* const found : view.FindText(text, root))
    {
        if (const auto* const button = view.ButtonAt(*found))
        {
            m_actions.ClickComponent(button->id, button->buttonType);
            return true;
        }
    }

    return false;
}

std::optional<u16> ScriptActions::FindContinue() const
{
    return m_dialogue.FindContinue(GetInterfaces());
}

bool ScriptActions::IsCountDialogOpen() const
{
    return m_dialogue.IsCountDialogOpen(m_state.interfaces);
}

bool ScriptActions::ContinueDialogue()
{
    const auto com = FindContinue();
    if (!com)
    {
        return false;
    }

    m_actions.ContinueDialogue(*com);
    m_dialogue.NoteContinued(m_state.interfaces);
    return true;
}

bool ScriptActions::AnswerCountDialog(s32 value)
{
    if (!IsCountDialogOpen())
    {
        return false;
    }

    m_actions.AnswerCountDialog(value);
    m_dialogue.NoteAnswered(m_state.interfaces);
    return true;
}

void ScriptActions::CloseInterfaces()
{
    m_actions.CloseInterfaces();
}

void ScriptActions::SetRun(bool run)
{
    const auto& cache = GetCache();
    m_actions.ClickButton(run ? cache.runOnButton : cache.runOffButton);
}

void ScriptActions::Say(std::string_view text)
{
    m_actions.Say(text);
}

void ScriptActions::SendPrivateMessage(std::string_view name, std::string_view text)
{
    m_actions.SendPrivateMessage(name, text);
}

void ScriptActions::SendCommand(std::string_view command)
{
    m_actions.SendCommand(command);
}

void ScriptActions::AddFriend(std::string_view name)
{
    m_actions.AddFriend(name);
}

void ScriptActions::RemoveFriend(std::string_view name)
{
    m_actions.RemoveFriend(name);
}

void ScriptActions::AddIgnore(std::string_view name)
{
    m_actions.AddIgnore(name);
}

void ScriptActions::RemoveIgnore(std::string_view name)
{
    m_actions.RemoveIgnore(name);
}

bool ScriptActions::CanSetRun() const
{
    const auto view = GetInterfaces();
    const auto* const button = view.Find(GetCache().runOnButton);
    return button != nullptr && view.IsOpen(button->root);
}

bool ScriptActions::IsAppearanceScreenOpen() const
{
    return FindAcceptDesign() != nullptr;
}

// As the webclient's Accept does: the design, then the button, whose script closes the screen.
bool ScriptActions::SetAppearance(const IdkDesign_s& design)
{
    const auto* const accept = FindAcceptDesign();
    if (accept == nullptr)
    {
        return false;
    }

    m_actions.SaveDesign(design);
    m_actions.ClickButton(accept->id);
    return true;
}

Tile_s ScriptActions::ToTile(s32 x, s32 z) const
{
    return {.x = x, .z = z, .level = m_state.localPlayer.tile.level};
}

InterfaceView ScriptActions::GetInterfaces() const
{
    return InterfaceView{GetCache(), m_state.interfaces};
}

const GameCache_s& ScriptActions::GetCache() const
{
    return m_map.GetCache();
}

bool ScriptActions::HasItem(const InventoryItem_s& item) const
{
    return InventoryQuery{m_state, GetCache()}.HasItem(item);
}

bool ScriptActions::HasGroundItem(u16 obj, const Tile_s& tile) const
{
    return EntityQuery{m_state, m_map}.HasGroundItem(obj, tile);
}

ItemRef_s ScriptActions::ToItemRef(const InventoryItem_s& item)
{
    return {.obj = static_cast<u16>(item.id), .slot = item.slot, .com = item.com};
}

const IfComponent_s* ScriptActions::FindAcceptDesign() const
{
    const auto mainModal = m_state.interfaces.mainModal;
    if (mainModal < 0)
    {
        return nullptr;
    }

    return GetInterfaces().FindClientCode(static_cast<u16>(mainModal), ClientCode_e::AcceptDesign);
}
