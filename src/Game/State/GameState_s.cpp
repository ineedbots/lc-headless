#include "pch.hpp"
#include "GameState_s.hpp"

#include "../Protocol/Base37.hpp"
#include "../Tile_s.hpp"
#include "GameEvent_s.hpp"
#include "Npc_s.hpp"
#include "Player_s.hpp"
#include "Social_s.hpp"
#include "Zone_s.hpp"

namespace
{
    template <typename TEntity>
    TEntity* FindByIndex(std::vector<TEntity>& entities, u16 index)
    {
        const auto found = std::ranges::find(entities, index, &TEntity::index);
        if (found == entities.end())
        {
            return nullptr;
        }

        return &*found;
    }
}

const Npc_s* GameState_s::FindNpc(u16 index) const
{
    return const_cast<GameState_s&>(*this).FindNpc(index);
}

Npc_s* GameState_s::FindNpc(u16 index)
{
    return FindByIndex(npcs, index);
}

const Player_s* GameState_s::FindPlayer(u16 index) const
{
    return const_cast<GameState_s&>(*this).FindPlayer(index);
}

Player_s* GameState_s::FindPlayer(u16 index)
{
    if (placed && index == pid)
    {
        return &localPlayer;
    }

    return FindByIndex(players, index);
}

const Player_s* GameState_s::FindPlayerByName(std::string_view name) const
{
    const auto name37 = Base37::Encode(name);
    const auto hasName = [name37](const Player_s& player)
    {
        return player.appearance && player.appearance->name37 == name37;
    };

    if (placed && hasName(localPlayer))
    {
        return &localPlayer;
    }

    const auto found = std::ranges::find_if(players, hasName);
    if (found == players.end())
    {
        return nullptr;
    }

    return &*found;
}

const Inventory_s* GameState_s::FindInventory(u16 com) const
{
    const auto found = inventories.find(com);
    if (found == inventories.end())
    {
        return nullptr;
    }

    return &found->second;
}

s32 GameState_s::GetVarp(u16 varp) const
{
    const auto found = varps.find(varp);
    if (found == varps.end())
    {
        return 0;
    }

    return found->second;
}

std::vector<const GroundItem_s*> GameState_s::GetGroundItemsAt(const Tile_s& tile) const
{
    auto found = std::vector<const GroundItem_s*>{};
    for (const auto& item : groundItems)
    {
        if (item.tile == tile)
        {
            found.push_back(&item);
        }
    }

    return found;
}

std::vector<const ChatMessage_s*> GameState_s::GetMessagesAfter(u64 sequence) const
{
    auto found = std::vector<const ChatMessage_s*>{};
    for (const auto& message : messages)
    {
        if (message.sequence > sequence)
        {
            found.push_back(&message);
        }
    }

    return found;
}

std::vector<const GameEvent_s*> GameState_s::GetEventsAfter(u64 sequence) const
{
    auto found = std::vector<const GameEvent_s*>{};
    const auto first = std::ranges::upper_bound(events, sequence, {}, &GameEvent_s::sequence);
    for (auto event = first; event != events.end(); ++event)
    {
        found.push_back(&*event);
    }

    return found;
}
