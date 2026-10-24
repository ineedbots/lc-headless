#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Cache/IfComponent_s.hpp"
#include "../Game/GameActions.hpp"
#include "../Game/Interface/DialogueTracker.hpp"
#include "../Game/Interface/InterfaceView.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/Query/InventoryItem_s.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/Tile_s.hpp"

// What a script does, checked against the tracked state first. Tiles given as x and z are on the local player's
// level. Actions on a target that's no longer tracked return false and send nothing.
class ScriptActions
{
public:
    ScriptActions(const GameState_s& state, const WorldMap& map, GameActions& actions);

    // False when the tile is in view but can't be reached, and nothing was sent.
    bool WalkTo(s32 x, s32 z, bool run);
    void WalkPath(std::span<const Tile_s> points, bool run);
    bool InteractNpc(u16 index, u8 op);
    bool InteractPlayer(u16 index, u8 op);
    void InteractLoc(u16 loc, s32 x, s32 z, u8 op);
    void InteractLocVia(std::span<const Tile_s> waypoints, u16 loc, s32 x, s32 z, u8 op);
    bool InteractGroundItem(u16 obj, s32 x, s32 z, u8 op);
    bool ItemOp(const InventoryItem_s& item, u8 op);
    bool InventoryButton(const InventoryItem_s& item, u8 op);
    void MoveItem(u16 com, u16 fromSlot, u16 toSlot, DragMode_e mode = DragMode_e::Swap);
    bool UseItemOnNpc(const InventoryItem_s& item, u16 npcIndex);
    bool UseItemOnPlayer(const InventoryItem_s& item, u16 playerIndex);
    bool UseItemOnLoc(const InventoryItem_s& item, u16 loc, s32 x, s32 z);
    bool UseItemOnGroundItem(const InventoryItem_s& item, u16 obj, s32 x, s32 z);
    bool UseItemOnItem(const InventoryItem_s& item, const InventoryItem_s& target);
    bool CastOnNpc(u16 spellCom, u16 npcIndex);
    bool CastOnPlayer(u16 spellCom, u16 playerIndex);
    void CastOnLoc(u16 spellCom, u16 loc, s32 x, s32 z);
    bool CastOnGroundItem(u16 spellCom, u16 obj, s32 x, s32 z);
    bool CastOnItem(u16 spellCom, const InventoryItem_s& item);
    void ClickButton(u16 com);
    // Clicks the component as its button type says. False, sending nothing, when it isn't visible; one
    // that isn't a button a click uses, such as a spell's Target button, throws std::invalid_argument.
    bool ClickComponent(u16 com);
    // False when there's no such text, or no button under it.
    bool ClickText(std::string_view text, std::optional<u16> root);
    // The chat modal's "Click here to continue" button, until it's clicked: the webclient sends one resume
    // per dialogue, and so does ContinueDialogue.
    [[nodiscard]] std::optional<u16> FindContinue() const;
    // The count dialog is open and hasn't been answered; the server doesn't say when an answer closes it.
    [[nodiscard]] bool IsCountDialogOpen() const;
    // False, sending nothing, when there's nothing to continue or no count dialog to answer.
    bool ContinueDialogue();
    bool AnswerCountDialog(s32 value);
    void CloseInterfaces();
    void SetRun(bool run);
    void Say(std::string_view text);
    void SendPrivateMessage(std::string_view name, std::string_view text);
    void SendCommand(std::string_view command);
    void AddFriend(std::string_view name);
    void RemoveFriend(std::string_view name);
    void AddIgnore(std::string_view name);
    void RemoveIgnore(std::string_view name);

    // Whether the run buttons' interface is open, so clicking one would reach the server.
    [[nodiscard]] bool CanSetRun() const;
    // The character design screen: a main modal with the Accept button whose client code saves a design.
    [[nodiscard]] bool IsAppearanceScreenOpen() const;
    // False when the design screen isn't open.
    bool SetAppearance(const IdkDesign_s& design);

private:
    [[nodiscard]] Tile_s ToTile(s32 x, s32 z) const;
    [[nodiscard]] InterfaceView GetInterfaces() const;
    [[nodiscard]] const GameCache_s& GetCache() const;
    [[nodiscard]] bool HasItem(const InventoryItem_s& item) const;
    [[nodiscard]] bool HasGroundItem(u16 obj, const Tile_s& tile) const;
    [[nodiscard]] static ItemRef_s ToItemRef(const InventoryItem_s& item);
    [[nodiscard]] const IfComponent_s* FindAcceptDesign() const;

    const GameState_s& m_state;
    const WorldMap& m_map;
    GameActions& m_actions;
    DialogueTracker m_dialogue;
};
