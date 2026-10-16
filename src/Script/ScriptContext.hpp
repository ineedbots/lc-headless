#pragma once

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

// What one VM's bindings reach: the tracked state and map, read through the Game queries; the script's actions;
// its requests to its host; and the other accounts' scripts. The bindings find it by the VM they run in.
class ScriptContext
{
public:
    ScriptContext(const GameState_s& state, const WorldMap& map, GameActions& actions, BotMessenger* messenger = nullptr, std::string username = {}, std::shared_ptr<const Navigation> navigation = nullptr);

    ScriptContext(const ScriptContext&) = delete;
    ScriptContext& operator=(const ScriptContext&) = delete;

    [[nodiscard]] const GameState_s& GetState() const;
    [[nodiscard]] const WorldMap& GetMap() const;
    [[nodiscard]] const GameCache_s& GetCache() const;
    [[nodiscard]] const Player_s& GetLocalPlayer() const;
    [[nodiscard]] Tile_s GetPosition() const;
    // On the local player's level.
    [[nodiscard]] Tile_s ToTile(s32 x, s32 z) const;
    // Nullopt when the client has no Navigation.
    [[nodiscard]] const Navigation* GetNavigation() const;

    [[nodiscard]] EntityQuery GetEntities() const;
    [[nodiscard]] InventoryQuery GetInventories() const;
    [[nodiscard]] PlayerQuery GetPlayer() const;
    [[nodiscard]] ReachQuery GetReach() const;
    [[nodiscard]] InterfaceView GetInterfaces() const;

    [[nodiscard]] ScriptActions& GetActions();
    [[nodiscard]] ScriptControl& GetControl();

    // Empty when no account in the process has that username; otherwise whether its script took the message.
    [[nodiscard]] std::optional<bool> SendBotMessage(std::string_view username, std::string json);

private:
    const GameState_s& m_state;
    const WorldMap& m_map;
    BotMessenger* m_messenger;
    std::string m_username;
    std::shared_ptr<const Navigation> m_navigation;
    ScriptActions m_actions;
    ScriptControl m_control;
};
