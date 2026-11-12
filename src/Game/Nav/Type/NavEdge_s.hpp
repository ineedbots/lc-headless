#pragma once

#include "NavPoint_s.hpp"
#include "NavRequires_s.hpp"

// A move other than a step: a door, stairs, a ship and so on, with what the walker does to make it.
struct NavEdge_s
{
    std::string kind;
    NavPoint_s from;
    NavPoint_s to;
    s32 cost = 0;
    std::string locName;
    std::string action;
    s32 locX = 0;
    s32 locZ = 0;
    std::optional<s32> locId;
    std::optional<s32> openLocId;
    std::optional<s32> toLevel;
    // Where a long hop lands: ships, portals, shortcuts and the rest.
    std::optional<std::pair<s32, s32>> toTile;
    bool acceptAnyLanding = false;
    std::optional<NavRequires_s> requirement;
    std::string teleportId;
};
