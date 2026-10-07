#pragma once

#include "../Tile_s.hpp"

enum class EntityType_e : u8
{
    Npc,
    Player,
};

struct EntityRef_s
{
    EntityType_e type = EntityType_e::Npc;
    u16 index = 0;

    [[nodiscard]] bool operator==(const EntityRef_s& other) const = default;
};

enum class Movement_e : u8
{
    None,
    Walk,
    Run,
    Teleport,
};

struct Animation_s
{
    s32 id = -1;
    u8 delay = 0;
    u64 tick = 0;
};

struct SpotAnim_s
{
    s32 id = -1;
    s32 height = 0;
    s32 delay = 0;
    u64 tick = 0;
};

struct Hit_s
{
    u8 damage = 0;
    u8 type = 0;
    u8 health = 0;
    u8 maxHealth = 0;
    u64 tick = 0;
};

// Half-tile coordinates: absolute * 2 + the target's size, so a size-1 target's centre is x * 2 + 1.
struct FineCoord_s
{
    s32 x = 0;
    s32 z = 0;
    u64 tick = 0;
};

struct OverheadText_s
{
    std::string text;
    u64 tick = 0;
};

struct Entity_s
{
    u16 index = 0;
    Tile_s tile;
    Movement_e lastMovement = Movement_e::None;
    u64 movedTick = 0;
    u64 addedTick = 0;
    Animation_s animation;
    SpotAnim_s spotAnim;
    std::optional<EntityRef_s> faceEntity;
    std::optional<FineCoord_s> faceCoord;
    std::optional<OverheadText_s> say;
    // The hitsplats of the most recent tick that had any; the last one holds the latest health.
    std::vector<Hit_s> hits;
};
