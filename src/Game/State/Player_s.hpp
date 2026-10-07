#pragma once

#include "../Tile_s.hpp"
#include "Entity_s.hpp"

enum class WearKind_e : u8
{
    Empty,
    BodyKit,
    Object,
};

struct WearSlot_s
{
    WearKind_e kind = WearKind_e::Empty;
    u16 id = 0;
};

struct Appearance_s
{
    static constexpr std::size_t WEAR_SLOT_COUNT = 12;
    static constexpr std::size_t COLOUR_COUNT = 5;

    u8 gender = 0;
    u8 headIcons = 0;
    std::array<WearSlot_s, WEAR_SLOT_COUNT> wear{};
    std::optional<u16> npcTransform;
    std::array<u8, COLOUR_COUNT> colours{};
    s32 readyAnim = -1;
    s32 turnAnim = -1;
    s32 walkAnim = -1;
    s32 walkBackAnim = -1;
    s32 walkLeftAnim = -1;
    s32 walkRightAnim = -1;
    s32 runAnim = -1;
    u64 name37 = 0;
    std::string name;
    u8 combatLevel = 0;
    u16 totalLevel = 0;
};

struct PublicChat_s
{
    std::string text;
    u8 colour = 0;
    u8 effect = 0;
    u8 rights = 0;
    u64 tick = 0;
};

struct ExactMove_s
{
    Tile_s start;
    Tile_s end;
    u16 startCycle = 0;
    u16 endCycle = 0;
    u8 direction = 0;
    u64 tick = 0;
};

struct Player_s : Entity_s
{
    std::optional<Appearance_s> appearance;
    std::optional<PublicChat_s> chat;
    std::optional<ExactMove_s> exactMove;
};
