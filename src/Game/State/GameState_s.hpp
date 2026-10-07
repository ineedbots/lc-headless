#pragma once

#include "../Tile_s.hpp"
#include "Entity_s.hpp"
#include "GameEvent_s.hpp"
#include "Interfaces_s.hpp"
#include "Npc_s.hpp"
#include "Player_s.hpp"
#include "Social_s.hpp"
#include "Stat_s.hpp"
#include "Zone_s.hpp"

// The 104x104-tile area the server builds around the player. Local coordinates are absolute minus base.
struct BuildArea_s
{
    static constexpr s32 SIZE = 104;

    bool loaded = false;
    s32 centreZoneX = 0;
    s32 centreZoneZ = 0;
    s32 baseX = 0;
    s32 baseZ = 0;
};

struct Item_s
{
    s32 id = -1;
    s32 count = 0;
};

// Keyed by the interface component that shows it; slot i is slots[i], and id -1 is an empty slot.
struct Inventory_s
{
    u16 com = 0;
    std::vector<Item_s> slots;
    u64 tick = 0;
};

struct SoundEffect_s
{
    u16 id = 0;
    u8 loops = 0;
    u16 delay = 0;
    u64 tick = 0;
};

enum class HintArrowKind_e : u8
{
    Npc,
    Tile,
    Player,
};

struct HintArrow_s
{
    HintArrowKind_e kind = HintArrowKind_e::Tile;
    u16 index = 0;
    Tile_s tile;
    u8 position = 0;
    u8 height = 0;
};

struct PlayerOp_s
{
    std::string text;
    bool deprioritised = false;
};

struct LastLogin_s
{
    u32 lastIp = 0;
    u16 daysSinceLogin = 0;
    u8 daysSinceRecoveryChange = 0;
    u16 unreadMessages = 0;
    bool warnMembers = false;
};

struct RebootTimer_s
{
    u16 ticks = 0;
    u64 tick = 0;
};

struct Audio_s
{
    s32 song = -1;
    s32 jingle = -1;
};

// Everything the server has told this client. Ticks count PLAYER_INFO packets, one per server tick.
// Packets a script sends during a server tick arrive before that tick's PLAYER_INFO, so they carry
// the previous count; everything from PLAYER_INFO onward carries the new one. Messages and events are
// numbered from 1, and a fresh login resets the state, so the numbering starts over after one.
struct GameState_s
{
    static constexpr std::size_t STAT_COUNT = 25;
    static constexpr std::size_t PLAYER_OP_COUNT = 5;
    static constexpr std::size_t MAX_MESSAGES = 100;
    static constexpr std::size_t MAX_EFFECTS = 64;
    static constexpr std::size_t MAX_EVENTS = 1024;

    u64 tick = 0;
    u16 pid = 0;
    bool members = false;
    u8 staffLevel = 0;
    bool placed = false;

    BuildArea_s buildArea;
    Player_s localPlayer;
    std::vector<Player_s> players;
    std::vector<Npc_s> npcs;

    std::vector<GroundItem_s> groundItems;
    std::vector<LocChange_s> locChanges;
    std::optional<Tile_s> walkDestination;

    std::map<u16, Inventory_s> inventories;
    std::unordered_map<u16, s32> varps;
    std::array<Stat_s, STAT_COUNT> stats{};
    u8 runEnergy = 0;
    s16 runWeight = 0;

    Interfaces_s interfaces;
    Social_s social;
    u64 messageCount = 0;
    std::deque<ChatMessage_s> messages;
    u64 eventCount = 0;
    std::deque<GameEvent_s> events;

    std::deque<Projectile_s> projectiles;
    std::deque<MapAnim_s> mapAnims;
    std::deque<LocAnim_s> locAnims;
    std::deque<LocMerge_s> locMerges;
    std::deque<SoundEffect_s> sounds;

    std::optional<HintArrow_s> hintArrow;
    std::array<std::optional<PlayerOp_s>, PLAYER_OP_COUNT> playerOps{};
    bool multiway = false;
    u8 minimapState = 0;
    bool cinematicCamera = false;
    Audio_s audio;
    std::optional<RebootTimer_s> rebootTimer;
    std::optional<LastLogin_s> lastLogin;

    [[nodiscard]] const Npc_s* FindNpc(u16 index) const;
    [[nodiscard]] Npc_s* FindNpc(u16 index);
    [[nodiscard]] const Player_s* FindPlayer(u16 index) const;
    [[nodiscard]] Player_s* FindPlayer(u16 index);
    [[nodiscard]] const Player_s* FindPlayerByName(std::string_view name) const;
    [[nodiscard]] const Inventory_s* FindInventory(u16 com) const;
    [[nodiscard]] s32 GetVarp(u16 varp) const;
    [[nodiscard]] std::vector<const GroundItem_s*> GetGroundItemsAt(const Tile_s& tile) const;
    [[nodiscard]] std::vector<const ChatMessage_s*> GetMessagesAfter(u64 sequence) const;
    [[nodiscard]] std::vector<const GameEvent_s*> GetEventsAfter(u64 sequence) const;
};
