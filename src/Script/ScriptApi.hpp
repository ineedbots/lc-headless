#pragma once

#include "../Game/GameActions.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/State/Entity_s.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/State/Stat_s.hpp"
#include "../Game/State/Zone_s.hpp"
#include "../Game/Tile_s.hpp"

struct InventoryItem_s
{
    u16 com = 0;
    u16 slot = 0;
    s32 id = -1;
    s32 count = 0;
};

// An empty id list matches any id; a radius counts tiles from the local player, on its level.
struct SearchFilter_s
{
    std::vector<s32> ids;
    std::optional<s32> radius;
};

enum class StopRequest_e : u8
{
    None,
    Script,
    Account,
};

// What a script can see and do, in plain C++ over the tracked state and GameActions, so a binding only
// converts arguments and results. Tiles given as x and z are on the local player's level. Actions on a
// target that's no longer tracked return false; arguments out of range throw std::invalid_argument.
class ScriptApi
{
public:
    static constexpr u16 INVENTORY = 3214;
    static constexpr u16 EQUIPMENT = 1688;
    static constexpr u16 BANK = 5382;
    static constexpr u16 BANK_INVENTORY = 2006;
    static constexpr u16 RUN_OFF_BUTTON = 152;
    static constexpr u16 RUN_ON_BUTTON = 153;
    static constexpr u16 RUN_VARP = 173;
    static constexpr s32 INVENTORY_SIZE = 28;
    static constexpr u64 COMBAT_TICKS = 8;
    static constexpr u8 OP_TALK = 1;
    static constexpr u8 OP_ATTACK = 2;
    static constexpr u8 OP_TAKE = 3;
    static constexpr u8 OP_DROP = 5;

    ScriptApi(const GameState_s& state, GameActions& actions);

    [[nodiscard]] const GameState_s& GetState() const;
    [[nodiscard]] const Player_s& GetLocalPlayer() const;
    [[nodiscard]] Tile_s GetPosition() const;
    [[nodiscard]] Tile_s ToTile(s32 x, s32 z) const;
    [[nodiscard]] bool IsMoving() const;
    [[nodiscard]] bool InCombat() const;
    [[nodiscard]] bool IsRunning() const;
    [[nodiscard]] const Stat_s& GetStat(s32 stat) const;
    [[nodiscard]] bool IsInterfaceOpen(s32 id) const;
    [[nodiscard]] std::optional<std::string> GetComponentText(u16 com) const;

    [[nodiscard]] std::vector<Npc_s> GetNpcs(const SearchFilter_s& filter) const;
    [[nodiscard]] std::optional<Npc_s> GetNearestNpc(const SearchFilter_s& filter, std::optional<bool> inCombat) const;
    [[nodiscard]] std::optional<Npc_s> GetNpc(u16 index) const;
    [[nodiscard]] std::vector<Player_s> GetPlayers(std::optional<s32> radius) const;
    [[nodiscard]] std::optional<Player_s> GetPlayerByName(std::string_view name) const;
    [[nodiscard]] std::vector<GroundItem_s> GetGroundItems(const SearchFilter_s& filter) const;
    [[nodiscard]] std::optional<GroundItem_s> GetNearestGroundItem(const SearchFilter_s& filter) const;
    [[nodiscard]] std::optional<LocChange_s> GetLocAt(s32 x, s32 z, std::optional<LocLayer_e> layer) const;

    [[nodiscard]] std::vector<InventoryItem_s> GetInventory(u16 com) const;
    [[nodiscard]] s32 CountItems(std::span<const s32> ids, u16 com) const;
    [[nodiscard]] std::optional<InventoryItem_s> FindItem(std::span<const s32> ids, u16 com) const;
    [[nodiscard]] s32 GetEmptySlots() const;

    void WalkTo(s32 x, s32 z, bool run);
    void WalkPath(std::span<const Tile_s> points, bool run);
    bool InteractNpc(u16 index, u8 op);
    bool InteractPlayer(u16 index, u8 op);
    void InteractLoc(u16 loc, s32 x, s32 z, u8 op);
    void InteractLocVia(std::span<const Tile_s> waypoints, u16 loc, s32 x, s32 z, u8 op);
    bool InteractGroundItem(u16 obj, s32 x, s32 z, u8 op);
    bool ItemOp(const InventoryItem_s& item, u8 op);
    bool InventoryButton(const InventoryItem_s& item, u8 op);
    void MoveItem(u16 com, u16 fromSlot, u16 toSlot);
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
    void ContinueDialogue();
    void AnswerCountDialog(s32 value);
    void CloseInterfaces();
    void SetRun(bool run);
    void Say(std::string_view text);
    void SendPrivateMessage(std::string_view name, std::string_view text);
    void SendCommand(std::string_view command);
    void AddFriend(std::string_view name);
    void RemoveFriend(std::string_view name);
    void AddIgnore(std::string_view name);
    void RemoveIgnore(std::string_view name);

    void RequestStop(StopRequest_e request);
    [[nodiscard]] StopRequest_e TakeStopRequest();

    [[nodiscard]] static bool IsMoving(const Entity_s& entity, u64 tick);
    [[nodiscard]] static bool InCombat(const Entity_s& entity, u64 tick);

private:
    [[nodiscard]] bool Matches(const Tile_s& tile, const SearchFilter_s& filter, s32 id) const;
    [[nodiscard]] bool HasItem(const InventoryItem_s& item) const;
    [[nodiscard]] bool HasGroundItem(u16 obj, const Tile_s& tile) const;
    [[nodiscard]] static ItemRef_s ToItemRef(const InventoryItem_s& item);

    const GameState_s& m_state;
    GameActions& m_actions;
    StopRequest_e m_stopRequest = StopRequest_e::None;
};
