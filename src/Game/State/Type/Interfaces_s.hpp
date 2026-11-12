#pragma once

enum class ComponentModelKind_e : u8
{
    Object,
    Model,
    NpcHead,
    PlayerHead,
};

struct ComponentModel_s
{
    ComponentModelKind_e kind = ComponentModelKind_e::Model;
    u16 id = 0;
    u16 zoom = 0;
};

struct ComponentPosition_s
{
    s16 x = 0;
    s16 y = 0;
};

// What the server has set on one interface component. Fields the server never touched stay empty.
struct Component_s
{
    std::optional<std::string> text;
    std::optional<bool> hidden;
    std::optional<u32> colour;
    std::optional<ComponentModel_s> model;
    std::optional<s32> animation;
    std::optional<ComponentPosition_s> position;
    std::optional<u16> scrollPosition;
    u64 tick = 0;
};

struct Interfaces_s
{
    static constexpr std::size_t TAB_COUNT = 15;
    static constexpr u8 DEFAULT_ACTIVE_TAB = 3;
    static constexpr auto NO_TABS = std::to_array<s32>({-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1});

    static_assert(NO_TABS.size() == TAB_COUNT, "NO_TABS needs an entry per tab");

    s32 mainModal = -1;
    s32 sideModal = -1;
    s32 chatModal = -1;
    s32 overlay = -1;
    bool countDialogOpen = false;
    std::array<s32, TAB_COUNT> tabs = NO_TABS;
    u8 activeTab = DEFAULT_ACTIVE_TAB;
    s32 flashingTab = -1;
    s32 tutorialComponent = -1;
    // Counts the packets that open or close a modal or the count dialog, so something done to the ones open
    // now can be told from the next, even the same interface opened again.
    u32 modalChanges = 0;
    std::unordered_map<u16, Component_s> components;
};
