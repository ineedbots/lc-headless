#pragma once

#include "NavPoint_s.hpp"
#include "NavRequires_s.hpp"

// A spell or jewellery teleport, which leaves from wherever you are.
struct NavTeleport_s
{
    std::string id;
    std::string family;
    std::string label;
    NavPoint_s to;
    s32 cost = 0;
    std::optional<NavRequires_s> requirement;
    // The deepest wilderness level it works from, or nullopt for anywhere.
    std::optional<s32> maxWildernessLevel;
    // Backpack item name parts that can make it, for jewellery.
    std::vector<std::string> itemNameMatch;
};
