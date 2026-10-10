#pragma once

#include "../Cache/IfComponent_s.hpp"
#include "GameClient.hpp"
#include "Map/PathFinder.hpp"
#include "Map/WorldMap.hpp"
#include "Protocol/ClientPacket_s.hpp"
#include "Protocol/ClientPackets.hpp"
#include "Tile_s.hpp"

// High-level requests built from the tracked state. The server walks each waypoint in a straight line,
// so walks and interactions with something in the world route around obstacles first, as the webclient
// does, and send the turning points; an interaction then sends its op even without a route. WalkPath and
// the *Via overloads send the caller's waypoints instead.
class GameActions
{
public:
    explicit GameActions(GameClient& client);

    // False when the destination is in the build area but can't be reached, and nothing was sent. One
    // outside the area, or before the first rebuild, is walked to in a straight line.
    bool WalkTo(const Tile_s& destination, bool run = false);
    void WalkPath(std::span<const Tile_s> waypoints, bool run = false);

    void InteractNpc(u16 npcIndex, u8 op);
    void InteractPlayer(u16 playerIndex, u8 op);
    void InteractLoc(const Tile_s& tile, u16 loc, u8 op);
    void InteractLocVia(std::span<const Tile_s> waypoints, const Tile_s& tile, u16 loc, u8 op);
    void InteractGroundItem(const Tile_s& tile, u16 obj, u8 op);
    void InteractGroundItemVia(std::span<const Tile_s> waypoints, const Tile_s& tile, u16 obj, u8 op);

    void UseItemOnNpc(const ItemRef_s& item, u16 npcIndex);
    void UseItemOnPlayer(const ItemRef_s& item, u16 playerIndex);
    void UseItemOnLoc(const ItemRef_s& item, const Tile_s& tile, u16 loc);
    void UseItemOnGroundItem(const ItemRef_s& item, const Tile_s& tile, u16 obj);
    void UseItemOnItem(const ItemRef_s& item, const ItemRef_s& target);

    void CastOnNpc(u16 spellCom, u16 npcIndex);
    void CastOnPlayer(u16 spellCom, u16 playerIndex);
    void CastOnLoc(u16 spellCom, const Tile_s& tile, u16 loc);
    void CastOnGroundItem(u16 spellCom, const Tile_s& tile, u16 obj);
    void CastOnItem(u16 spellCom, const ItemRef_s& item);

    void OperateItem(const ItemRef_s& item, u8 op);
    void InventoryButton(const ItemRef_s& item, u8 op);
    void MoveItem(u16 com, u16 fromSlot, u16 toSlot, DragMode_e mode = DragMode_e::Swap);

    void ClickButton(u16 com);
    // What the webclient sends for a click on a button of that type: IF_BUTTON for Ok, Toggle and Select,
    // RESUME_PAUSEBUTTON for Continue, and CLOSE_MODAL for Close. Others send nothing.
    void ClickComponent(u16 com, ButtonType_e buttonType);
    void ContinueDialogue(u16 com);
    void AnswerCountDialog(s32 value);
    void CloseInterfaces();
    void SaveDesign(const IdkDesign_s& design);

    void Say(std::string_view text, ChatColour_e colour = ChatColour_e::Yellow, ChatEffect_e effect = ChatEffect_e::None);
    void SendPrivateMessage(std::string_view name, std::string_view text);
    void SendCommand(std::string_view command);
    void AddFriend(std::string_view name);
    void RemoveFriend(std::string_view name);
    void AddIgnore(std::string_view name);
    void RemoveIgnore(std::string_view name);

    [[nodiscard]] std::optional<ItemRef_s> FindItem(u16 com, u16 obj) const;

    // The routes the requests above walk from start, by the webclient's rules for each kind of target, or
    // nullopt when the path finder has none.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindWalkRoute(const WorldMap& map, const Tile_s& start, const Tile_s& destination);
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindEntityRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile);
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindGroundItemRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile);
    // Also nullopt when the map has no loc with that id on the tile.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindLocRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile, u16 loc);

private:
    // Walks the route, if there is one, then sends the action.
    void Approach(const std::optional<std::vector<Tile_s>>& route, const Tile_s& destination, ClientPacket_s action);
    void ApproachVia(std::span<const Tile_s> waypoints, ClientPacket_s action);
    void ApproachLoc(const Tile_s& tile, u16 loc, ClientPacket_s action);
    [[nodiscard]] const WorldMap& GetMap() const;
    [[nodiscard]] const Tile_s& GetStart() const;
    // The route to the first of the targets that has one.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindRoute(const WorldMap& map, const Tile_s& start, std::initializer_list<RouteTarget_s> targets);
    [[nodiscard]] static std::optional<RouteTarget_s> GetLocTarget(const WorldMap& map, const Tile_s& tile, u16 loc);
    void LogNoRoute(const Tile_s& destination, std::string_view instead) const;
    [[nodiscard]] Tile_s GetNpcTile(u16 npcIndex) const;
    [[nodiscard]] Tile_s GetPlayerTile(u16 playerIndex) const;

    GameClient& m_client;
};
