#pragma once

#include "GameClient.hpp"
#include "Protocol/ClientPacket_s.hpp"
#include "Protocol/ClientPackets.hpp"
#include "Tile_s.hpp"

// High-level requests built from the tracked state. Interactions with something in the world first
// send MOVE_OPCLICK toward it, as the webclient does; the server walks each waypoint in a straight
// line, so pass waypoints around obstacles with the *Via overloads when the direct line is blocked.
class GameActions
{
public:
    explicit GameActions(GameClient& client);

    void WalkTo(const Tile_s& destination, bool run = false);
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
    void ContinueDialogue();
    void AnswerCountDialog(s32 value);
    void CloseInterfaces();

    void Say(std::string_view text, ChatColour_e colour = ChatColour_e::Yellow, ChatEffect_e effect = ChatEffect_e::None);
    void SendPrivateMessage(std::string_view name, std::string_view text);
    void SendCommand(std::string_view command);
    void AddFriend(std::string_view name);
    void RemoveFriend(std::string_view name);
    void AddIgnore(std::string_view name);
    void RemoveIgnore(std::string_view name);

    [[nodiscard]] std::optional<ItemRef_s> FindItem(u16 com, u16 obj) const;

private:
    void Approach(std::span<const Tile_s> waypoints, ClientPacket_s action);
    [[nodiscard]] Tile_s GetNpcTile(u16 npcIndex) const;
    [[nodiscard]] Tile_s GetPlayerTile(u16 playerIndex) const;

    GameClient& m_client;
};
