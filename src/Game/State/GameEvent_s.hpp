#pragma once

#include "Entity_s.hpp"
#include "Npc_s.hpp"
#include "Player_s.hpp"
#include "Stat_s.hpp"
#include "Zone_s.hpp"

struct NpcAdded_s
{
    Npc_s npc;
};

struct NpcRemoved_s
{
    Npc_s npc;
};

struct NpcHit_s
{
    u16 index = 0;
    Hit_s hit;
};

// An NPC's overhead text, as MASK_SAY sets it.
struct NpcSaid_s
{
    u16 index = 0;
    std::string text;
};

struct PlayerAdded_s
{
    Player_s player;
};

struct PlayerRemoved_s
{
    Player_s player;
};

struct PlayerHit_s
{
    u16 index = 0;
    Hit_s hit;
};

struct LocalHit_s
{
    Hit_s hit;
};

struct GroundItemAdded_s
{
    GroundItem_s item;
};

struct GroundItemRemoved_s
{
    GroundItem_s item;
};

struct GroundItemCountChanged_s
{
    GroundItem_s item;
    s32 previousCount = 0;
};

struct LocChanged_s
{
    LocChange_s change;
};

struct InventoryChanged_s
{
    u16 com = 0;
};

struct StatChanged_s
{
    u8 stat = 0;
    Stat_s previous;
    Stat_s current;
};

struct VarpChanged_s
{
    u16 varp = 0;
    s32 previous = 0;
    s32 value = 0;
};

struct ModalChanged_s
{
    s32 mainModal = -1;
    s32 sideModal = -1;
    s32 chatModal = -1;
};

struct RebootStarted_s
{
    u16 ticks = 0;
};

// A projectile launched in the build area, from MAP_PROJANIM.
struct ProjectileLaunched_s
{
    Projectile_s projectile;
};

using GameEventData = std::variant<
    NpcAdded_s,
    NpcRemoved_s,
    NpcHit_s,
    NpcSaid_s,
    PlayerAdded_s,
    PlayerRemoved_s,
    PlayerHit_s,
    LocalHit_s,
    GroundItemAdded_s,
    GroundItemRemoved_s,
    GroundItemCountChanged_s,
    LocChanged_s,
    InventoryChanged_s,
    StatChanged_s,
    VarpChanged_s,
    ModalChanged_s,
    RebootStarted_s,
    ProjectileLaunched_s>;

// Something the server said that changed the state, in arrival order. An entity's added event carries it
// as it stood after the packet that added it; a removed entity carries its last state, since it's gone
// from GameState_s. Resets, rebuilds and pruning change the state without events.
struct GameEvent_s
{
    u64 sequence = 0;
    u64 tick = 0;
    GameEventData data;
};
