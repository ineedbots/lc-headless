#include "pch.hpp"
#include "ScriptApi.hpp"

#include "../Game/GameActions.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/State/Entity_s.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/State/Stat_s.hpp"
#include "../Game/State/Zone_s.hpp"
#include "../Game/Tile_s.hpp"
#include "BotMessenger.hpp"

namespace
{
    bool MatchesId(std::span<const s32> ids, s32 id)
    {
        return ids.empty() || std::ranges::find(ids, id) != ids.end();
    }

    template <typename T, typename TTile>
    std::optional<T> FindNearest(const std::vector<T>& candidates, const Tile_s& from, TTile getTile)
    {
        const auto nearest = std::ranges::min_element(candidates, {}, [&from, &getTile](const T& candidate)
        {
            return from.GetDistance(getTile(candidate));
        });

        if (nearest == candidates.end())
        {
            return std::nullopt;
        }

        return *nearest;
    }
}

ScriptApi::ScriptApi(const GameState_s& state, GameActions& actions, BotMessenger* messenger, std::string username)
    : m_state{state}
    , m_actions{actions}
    , m_messenger{messenger}
    , m_username{std::move(username)}
{
}

const GameState_s& ScriptApi::GetState() const
{
    return m_state;
}

const Player_s& ScriptApi::GetLocalPlayer() const
{
    return m_state.localPlayer;
}

Tile_s ScriptApi::GetPosition() const
{
    return m_state.localPlayer.tile;
}

Tile_s ScriptApi::ToTile(s32 x, s32 z) const
{
    return {.x = x, .z = z, .level = m_state.localPlayer.tile.level};
}

bool ScriptApi::IsMoving() const
{
    return m_state.walkDestination.has_value() || IsMoving(m_state.localPlayer, m_state.tick);
}

bool ScriptApi::InCombat() const
{
    return InCombat(m_state.localPlayer, m_state.tick);
}

bool ScriptApi::IsRunning() const
{
    return m_state.GetVarp(RUN_VARP) == 1;
}

const Stat_s& ScriptApi::GetStat(s32 stat) const
{
    if (stat < 0 || static_cast<std::size_t>(stat) >= m_state.stats.size())
    {
        throw std::invalid_argument{std::format("stat {} is not 0 to {}", stat, m_state.stats.size() - 1)};
    }

    return m_state.stats[static_cast<std::size_t>(stat)];
}

bool ScriptApi::IsInterfaceOpen(s32 id) const
{
    const auto& interfaces = m_state.interfaces;
    return id >= 0 && (interfaces.mainModal == id || interfaces.sideModal == id || interfaces.chatModal == id);
}

std::optional<std::string> ScriptApi::GetComponentText(u16 com) const
{
    const auto found = m_state.interfaces.components.find(com);
    if (found == m_state.interfaces.components.end())
    {
        return std::nullopt;
    }

    return found->second.text;
}

std::vector<Npc_s> ScriptApi::GetNpcs(const SearchFilter_s& filter) const
{
    auto found = std::vector<Npc_s>{};
    for (const auto& npc : m_state.npcs)
    {
        if (Matches(npc.tile, filter, npc.type))
        {
            found.push_back(npc);
        }
    }

    return found;
}

std::optional<Npc_s> ScriptApi::GetNearestNpc(const SearchFilter_s& filter, std::optional<bool> inCombat) const
{
    auto candidates = GetNpcs(filter);
    if (inCombat)
    {
        std::erase_if(candidates, [this, &inCombat](const Npc_s& npc)
        {
            return InCombat(npc, m_state.tick) != *inCombat;
        });
    }

    return FindNearest(candidates, GetPosition(), [](const Npc_s& npc)
    {
        return npc.tile;
    });
}

std::optional<Npc_s> ScriptApi::GetNpc(u16 index) const
{
    const auto* npc = m_state.FindNpc(index);
    if (npc == nullptr)
    {
        return std::nullopt;
    }

    return *npc;
}

std::vector<Player_s> ScriptApi::GetPlayers(std::optional<s32> radius) const
{
    const auto filter = SearchFilter_s{.radius = radius};
    auto found = std::vector<Player_s>{};
    for (const auto& player : m_state.players)
    {
        if (Matches(player.tile, filter, 0))
        {
            found.push_back(player);
        }
    }

    return found;
}

std::optional<Player_s> ScriptApi::GetPlayerByName(std::string_view name) const
{
    const auto* player = m_state.FindPlayerByName(name);
    if (player == nullptr)
    {
        return std::nullopt;
    }

    return *player;
}

std::vector<GroundItem_s> ScriptApi::GetGroundItems(const SearchFilter_s& filter) const
{
    auto found = std::vector<GroundItem_s>{};
    for (const auto& item : m_state.groundItems)
    {
        if (Matches(item.tile, filter, item.id))
        {
            found.push_back(item);
        }
    }

    return found;
}

std::optional<GroundItem_s> ScriptApi::GetNearestGroundItem(const SearchFilter_s& filter) const
{
    return FindNearest(GetGroundItems(filter), GetPosition(), [](const GroundItem_s& item)
    {
        return item.tile;
    });
}

std::optional<LocChange_s> ScriptApi::GetLocAt(s32 x, s32 z, std::optional<LocLayer_e> layer) const
{
    const auto tile = ToTile(x, z);
    const auto found = std::ranges::find_if(m_state.locChanges, [&tile, &layer](const LocChange_s& change)
    {
        return change.tile == tile && (!layer || change.layer == *layer);
    });

    if (found == m_state.locChanges.end())
    {
        return std::nullopt;
    }

    return *found;
}

std::vector<InventoryItem_s> ScriptApi::GetInventory(u16 com) const
{
    auto items = std::vector<InventoryItem_s>{};
    const auto* inventory = m_state.FindInventory(com);
    if (inventory == nullptr)
    {
        return items;
    }

    for (std::size_t slot = 0; slot < inventory->slots.size(); ++slot)
    {
        const auto& item = inventory->slots[slot];
        if (item.id < 0)
        {
            continue;
        }

        items.push_back({.com = com, .slot = static_cast<u16>(slot), .id = item.id, .count = item.count});
    }

    return items;
}

s32 ScriptApi::CountItems(std::span<const s32> ids, u16 com) const
{
    auto total = 0;
    for (const auto& item : GetInventory(com))
    {
        if (MatchesId(ids, item.id))
        {
            total += item.count;
        }
    }

    return total;
}

std::optional<InventoryItem_s> ScriptApi::FindItem(std::span<const s32> ids, u16 com) const
{
    const auto items = GetInventory(com);
    const auto found = std::ranges::find_if(items, [ids](const InventoryItem_s& item)
    {
        return MatchesId(ids, item.id);
    });

    if (found == items.end())
    {
        return std::nullopt;
    }

    return *found;
}

s32 ScriptApi::GetEmptySlots() const
{
    return INVENTORY_SIZE - static_cast<s32>(GetInventory(INVENTORY).size());
}

void ScriptApi::WalkTo(s32 x, s32 z, bool run)
{
    m_actions.WalkTo(ToTile(x, z), run);
}

void ScriptApi::WalkPath(std::span<const Tile_s> points, bool run)
{
    m_actions.WalkPath(points, run);
}

bool ScriptApi::InteractNpc(u16 index, u8 op)
{
    if (m_state.FindNpc(index) == nullptr)
    {
        return false;
    }

    m_actions.InteractNpc(index, op);
    return true;
}

bool ScriptApi::InteractPlayer(u16 index, u8 op)
{
    if (m_state.FindPlayer(index) == nullptr)
    {
        return false;
    }

    m_actions.InteractPlayer(index, op);
    return true;
}

void ScriptApi::InteractLoc(u16 loc, s32 x, s32 z, u8 op)
{
    m_actions.InteractLoc(ToTile(x, z), loc, op);
}

void ScriptApi::InteractLocVia(std::span<const Tile_s> waypoints, u16 loc, s32 x, s32 z, u8 op)
{
    m_actions.InteractLocVia(waypoints, ToTile(x, z), loc, op);
}

bool ScriptApi::InteractGroundItem(u16 obj, s32 x, s32 z, u8 op)
{
    const auto tile = ToTile(x, z);
    if (!HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.InteractGroundItem(tile, obj, op);
    return true;
}

bool ScriptApi::ItemOp(const InventoryItem_s& item, u8 op)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.OperateItem(ToItemRef(item), op);
    return true;
}

bool ScriptApi::InventoryButton(const InventoryItem_s& item, u8 op)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.InventoryButton(ToItemRef(item), op);
    return true;
}

void ScriptApi::MoveItem(u16 com, u16 fromSlot, u16 toSlot)
{
    m_actions.MoveItem(com, fromSlot, toSlot);
}

bool ScriptApi::UseItemOnNpc(const InventoryItem_s& item, u16 npcIndex)
{
    if (!HasItem(item) || m_state.FindNpc(npcIndex) == nullptr)
    {
        return false;
    }

    m_actions.UseItemOnNpc(ToItemRef(item), npcIndex);
    return true;
}

bool ScriptApi::UseItemOnPlayer(const InventoryItem_s& item, u16 playerIndex)
{
    if (!HasItem(item) || m_state.FindPlayer(playerIndex) == nullptr)
    {
        return false;
    }

    m_actions.UseItemOnPlayer(ToItemRef(item), playerIndex);
    return true;
}

bool ScriptApi::UseItemOnLoc(const InventoryItem_s& item, u16 loc, s32 x, s32 z)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.UseItemOnLoc(ToItemRef(item), ToTile(x, z), loc);
    return true;
}

bool ScriptApi::UseItemOnGroundItem(const InventoryItem_s& item, u16 obj, s32 x, s32 z)
{
    const auto tile = ToTile(x, z);
    if (!HasItem(item) || !HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.UseItemOnGroundItem(ToItemRef(item), tile, obj);
    return true;
}

bool ScriptApi::UseItemOnItem(const InventoryItem_s& item, const InventoryItem_s& target)
{
    if (!HasItem(item) || !HasItem(target))
    {
        return false;
    }

    m_actions.UseItemOnItem(ToItemRef(item), ToItemRef(target));
    return true;
}

bool ScriptApi::CastOnNpc(u16 spellCom, u16 npcIndex)
{
    if (m_state.FindNpc(npcIndex) == nullptr)
    {
        return false;
    }

    m_actions.CastOnNpc(spellCom, npcIndex);
    return true;
}

bool ScriptApi::CastOnPlayer(u16 spellCom, u16 playerIndex)
{
    if (m_state.FindPlayer(playerIndex) == nullptr)
    {
        return false;
    }

    m_actions.CastOnPlayer(spellCom, playerIndex);
    return true;
}

void ScriptApi::CastOnLoc(u16 spellCom, u16 loc, s32 x, s32 z)
{
    m_actions.CastOnLoc(spellCom, ToTile(x, z), loc);
}

bool ScriptApi::CastOnGroundItem(u16 spellCom, u16 obj, s32 x, s32 z)
{
    const auto tile = ToTile(x, z);
    if (!HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.CastOnGroundItem(spellCom, tile, obj);
    return true;
}

bool ScriptApi::CastOnItem(u16 spellCom, const InventoryItem_s& item)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.CastOnItem(spellCom, ToItemRef(item));
    return true;
}

void ScriptApi::ClickButton(u16 com)
{
    m_actions.ClickButton(com);
}

void ScriptApi::ContinueDialogue()
{
    m_actions.ContinueDialogue();
}

void ScriptApi::AnswerCountDialog(s32 value)
{
    m_actions.AnswerCountDialog(value);
}

void ScriptApi::CloseInterfaces()
{
    m_actions.CloseInterfaces();
}

void ScriptApi::SetRun(bool run)
{
    m_actions.ClickButton(run ? RUN_ON_BUTTON : RUN_OFF_BUTTON);
}

void ScriptApi::Say(std::string_view text)
{
    m_actions.Say(text);
}

void ScriptApi::SendPrivateMessage(std::string_view name, std::string_view text)
{
    m_actions.SendPrivateMessage(name, text);
}

void ScriptApi::SendCommand(std::string_view command)
{
    m_actions.SendCommand(command);
}

void ScriptApi::AddFriend(std::string_view name)
{
    m_actions.AddFriend(name);
}

void ScriptApi::RemoveFriend(std::string_view name)
{
    m_actions.RemoveFriend(name);
}

void ScriptApi::AddIgnore(std::string_view name)
{
    m_actions.AddIgnore(name);
}

void ScriptApi::RemoveIgnore(std::string_view name)
{
    m_actions.RemoveIgnore(name);
}

std::optional<bool> ScriptApi::SendBotMessage(std::string_view username, std::string json)
{
    if (json.size() > BotMessenger::MAX_MESSAGE_SIZE)
    {
        throw std::invalid_argument{std::format("The message is {} bytes as JSON, over the limit of {}", json.size(), BotMessenger::MAX_MESSAGE_SIZE)};
    }

    if (m_messenger == nullptr)
    {
        return std::nullopt;
    }

    return m_messenger->Send(username, BotMessage_s{.sender = m_username, .json = std::move(json)});
}

void ScriptApi::RequestStop(StopRequest_e request)
{
    m_stopRequest = std::max(m_stopRequest, request);
}

StopRequest_e ScriptApi::TakeStopRequest()
{
    return std::exchange(m_stopRequest, StopRequest_e::None);
}

bool ScriptApi::IsMoving(const Entity_s& entity, u64 tick)
{
    return entity.lastMovement != Movement_e::None && entity.movedTick == tick;
}

bool ScriptApi::InCombat(const Entity_s& entity, u64 tick)
{
    return !entity.hits.empty() && tick - entity.hits.back().tick <= COMBAT_TICKS;
}

bool ScriptApi::Matches(const Tile_s& tile, const SearchFilter_s& filter, s32 id) const
{
    if (!MatchesId(filter.ids, id))
    {
        return false;
    }

    if (!filter.radius)
    {
        return true;
    }

    const auto& here = GetPosition();
    return tile.level == here.level && here.GetDistance(tile) <= *filter.radius;
}

bool ScriptApi::HasItem(const InventoryItem_s& item) const
{
    const auto* inventory = m_state.FindInventory(item.com);
    return inventory != nullptr && item.slot < inventory->slots.size() && inventory->slots[item.slot].id == item.id;
}

bool ScriptApi::HasGroundItem(u16 obj, const Tile_s& tile) const
{
    return std::ranges::any_of(m_state.groundItems, [obj, &tile](const GroundItem_s& item)
    {
        return item.id == obj && item.tile == tile;
    });
}

ItemRef_s ScriptApi::ToItemRef(const InventoryItem_s& item)
{
    return {.obj = static_cast<u16>(item.id), .slot = item.slot, .com = item.com};
}
