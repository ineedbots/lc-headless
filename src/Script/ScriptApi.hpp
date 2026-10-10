#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Game/GameActions.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/State/Entity_s.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/State/Stat_s.hpp"
#include "../Game/State/Zone_s.hpp"
#include "../Game/Tile_s.hpp"
#include "BotMessenger.hpp"

struct InventoryItem_s
{
    u16 com = 0;
    u16 slot = 0;
    s32 id = -1;
    s32 count = 0;
};

// Empty id and name lists match anything. Names match a type's name without regard to case, and a type
// with no name never matches one. A radius counts tiles from the local player, on its level.
struct SearchFilter_s
{
    std::vector<s32> ids;
    std::vector<std::string> names;
    std::optional<s32> radius;
};

enum class StopRequest_e : u8
{
    None,
    Script,
    Account,
};

// What a script can see and do, in plain C++ over the tracked state, the map and GameActions, so a
// binding only converts arguments and results. Tiles given as x and z are on the local player's level.
// Actions on a target that's no longer tracked return false; arguments out of range throw
// std::invalid_argument. A nearest search with reachable skips targets the path finder can't reach by
// the rule the matching interaction walks by. Bot messages go through the messenger, if there is one,
// under the account's username.
class ScriptApi
{
public:
    static constexpr u64 COMBAT_TICKS = 8;
    static constexpr u8 OP_TALK = 1;
    static constexpr u8 OP_ATTACK = 2;
    static constexpr u8 OP_TAKE = 3;
    static constexpr u8 OP_DROP = 5;
    static constexpr std::string_view TAKE_OPTION = "Take";
    static constexpr std::string_view DROP_OPTION = "Drop";

    ScriptApi(const GameState_s& state, const WorldMap& map, GameActions& actions, BotMessenger* messenger = nullptr, std::string username = {});

    [[nodiscard]] const GameState_s& GetState() const;
    [[nodiscard]] const WorldMap& GetMap() const;
    [[nodiscard]] const GameCache_s& GetCache() const;
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
    [[nodiscard]] std::optional<Npc_s> GetNearestNpc(const SearchFilter_s& filter, std::optional<bool> inCombat, bool reachable = false) const;
    [[nodiscard]] std::optional<Npc_s> GetNpc(u16 index) const;
    [[nodiscard]] std::vector<Player_s> GetPlayers(std::optional<s32> radius) const;
    [[nodiscard]] std::optional<Player_s> GetPlayerByName(std::string_view name) const;
    [[nodiscard]] std::vector<GroundItem_s> GetGroundItems(const SearchFilter_s& filter) const;
    [[nodiscard]] std::optional<GroundItem_s> GetNearestGroundItem(const SearchFilter_s& filter, bool reachable = false) const;
    // Without a layer, the first loc on the tile in layer order, preferring one that's there to one the
    // server removed.
    [[nodiscard]] std::optional<SceneLoc_s> GetLocAt(s32 x, s32 z, std::optional<LocLayer_e> layer) const;
    // Nearest first, leaving out locs the server removed.
    [[nodiscard]] std::vector<SceneLoc_s> GetLocs(const SearchFilter_s& filter, std::optional<LocLayer_e> layer) const;
    [[nodiscard]] std::optional<SceneLoc_s> GetNearestLoc(const SearchFilter_s& filter, std::optional<LocLayer_e> layer, bool reachable = false) const;

    [[nodiscard]] std::vector<InventoryItem_s> GetInventory(u16 com) const;
    [[nodiscard]] s32 CountItems(const SearchFilter_s& filter, u16 com) const;
    [[nodiscard]] std::optional<InventoryItem_s> FindItem(const SearchFilter_s& filter, u16 com) const;
    [[nodiscard]] s32 GetEmptySlots() const;

    // An option's number, from its text as the right-click menu shows it, matched without regard to case.
    // Text that matches no option throws std::invalid_argument, listing the options there are.
    // FindNpcOp gives nullopt when the NPC isn't tracked.
    [[nodiscard]] std::optional<u8> FindNpcOp(u16 index, std::string_view text) const;
    [[nodiscard]] u8 FindPlayerOp(std::string_view text) const;
    [[nodiscard]] u8 FindLocOp(u16 loc, std::string_view text) const;
    // Ground items also offer "Take" as op 3, and inventory items "Drop" as op 5, when their type has no
    // option there.
    [[nodiscard]] u8 FindGroundItemOp(u16 obj, std::string_view text) const;
    [[nodiscard]] u8 FindItemOp(s32 obj, std::string_view text) const;

    // Whether a walk can end on the tile.
    [[nodiscard]] bool IsReachable(s32 x, s32 z) const;
    // The waypoints WalkTo would send along a route, or nullopt without one.
    [[nodiscard]] std::optional<std::vector<Tile_s>> FindPath(s32 x, s32 z) const;

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

    // Empty when no account in the process has that username; otherwise whether its script took the message.
    [[nodiscard]] std::optional<bool> SendBotMessage(std::string_view username, std::string json);

    void RequestStop(StopRequest_e request);
    [[nodiscard]] StopRequest_e TakeStopRequest();

    // The time of the host's current step, in milliseconds on its clock. Waits measure from it, so a test
    // that steps the host with made-up times controls them too.
    void SetStepTime(s64 milliseconds);
    [[nodiscard]] s64 GetStepTime() const;
    // The script reports progress the stall guard can't see, such as a finished trade.
    void NoteProgress();
    [[nodiscard]] std::optional<s64> GetLastProgress() const;

    [[nodiscard]] static bool IsMoving(const Entity_s& entity, u64 tick);
    [[nodiscard]] static bool InCombat(const Entity_s& entity, u64 tick);

private:
    [[nodiscard]] bool Matches(const Tile_s& tile, const SearchFilter_s& filter, s32 id, std::string_view name) const;
    [[nodiscard]] std::string_view GetNpcName(s32 type) const;
    [[nodiscard]] std::string_view GetObjName(s32 obj) const;
    [[nodiscard]] std::string_view GetLocName(s32 loc) const;
    [[nodiscard]] bool HasItem(const InventoryItem_s& item) const;
    [[nodiscard]] bool HasGroundItem(u16 obj, const Tile_s& tile) const;
    [[nodiscard]] static ItemRef_s ToItemRef(const InventoryItem_s& item);

    const GameState_s& m_state;
    const WorldMap& m_map;
    GameActions& m_actions;
    BotMessenger* m_messenger;
    std::string m_username;
    StopRequest_e m_stopRequest = StopRequest_e::None;
    s64 m_stepTime = 0;
    std::optional<s64> m_lastProgress;
};
