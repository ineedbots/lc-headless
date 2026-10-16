#include "pch.hpp"
#include "ScriptContext.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Game/GameActions.hpp"
#include "../Game/Interface/InterfaceView.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/Nav/Navigation.hpp"
#include "../Game/Query/EntityQuery.hpp"
#include "../Game/Query/InventoryQuery.hpp"
#include "../Game/Query/PlayerQuery.hpp"
#include "../Game/Query/ReachQuery.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/Tile_s.hpp"
#include "BotMessenger.hpp"
#include "ScriptActions.hpp"
#include "ScriptControl.hpp"

ScriptContext::ScriptContext(const GameState_s& state, const WorldMap& map, GameActions& actions, BotMessenger* messenger, std::string username, std::shared_ptr<const Navigation> navigation)
    : m_state{state}
    , m_map{map}
    , m_messenger{messenger}
    , m_username{std::move(username)}
    , m_navigation{std::move(navigation)}
    , m_actions{state, map, actions}
{
}

const GameState_s& ScriptContext::GetState() const
{
    return m_state;
}

const WorldMap& ScriptContext::GetMap() const
{
    return m_map;
}

const GameCache_s& ScriptContext::GetCache() const
{
    return m_map.GetCache();
}

const Player_s& ScriptContext::GetLocalPlayer() const
{
    return m_state.localPlayer;
}

Tile_s ScriptContext::GetPosition() const
{
    return m_state.localPlayer.tile;
}

Tile_s ScriptContext::ToTile(s32 x, s32 z) const
{
    return {.x = x, .z = z, .level = m_state.localPlayer.tile.level};
}

const Navigation* ScriptContext::GetNavigation() const
{
    return m_navigation.get();
}

EntityQuery ScriptContext::GetEntities() const
{
    return EntityQuery{m_state, m_map};
}

InventoryQuery ScriptContext::GetInventories() const
{
    return InventoryQuery{m_state, GetCache()};
}

PlayerQuery ScriptContext::GetPlayer() const
{
    return PlayerQuery{m_state, GetCache()};
}

ReachQuery ScriptContext::GetReach() const
{
    return ReachQuery{m_state, m_map};
}

InterfaceView ScriptContext::GetInterfaces() const
{
    return InterfaceView{GetCache(), m_state.interfaces};
}

ScriptActions& ScriptContext::GetActions()
{
    return m_actions;
}

ScriptControl& ScriptContext::GetControl()
{
    return m_control;
}

std::optional<bool> ScriptContext::SendBotMessage(std::string_view username, std::string json)
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
