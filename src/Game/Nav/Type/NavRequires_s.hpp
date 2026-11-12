#pragma once

#include "NavState_s.hpp"

// rs2b0t's TransportRequires: what an edge needs to be planned.
struct NavRequires_s
{
    struct Amount_s
    {
        std::string name;
        s32 count = 0;
    };

    struct Quest_s
    {
        std::string quest;
        std::string minStatus;
        std::string maxStatus;
    };

    bool members = false;
    std::optional<s32> freeSlots;
    std::vector<Amount_s> skills;
    std::vector<Amount_s> items;
    std::vector<Amount_s> worn;
    std::optional<Amount_s> currency;
    // A quest whose completion waives the items and currency, such as Prince Ali Rescue for the Al Kharid toll.
    std::string questWaivesItems;
    std::vector<Quest_s> quests;
    bool forbidEntranaRestricted = false;
    bool slashTool = false;
    // An essence mine exit, open when the state's return is this one or isn't known.
    std::string essenceExitReturn;

    [[nodiscard]] bool IsGated() const;
    // nullopt when the state meets it, else why not. An unknown quest status fails closed.
    [[nodiscard]] std::optional<std::string> Check(const NavState_s& state) const;
};
