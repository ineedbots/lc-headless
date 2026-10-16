#pragma once

// What an account has, for an edge's requirements: rs2b0t's WorldState. Names are lower-case; a quest's
// status is "not_started", "started", "complete" or "unknown".
struct NavState_s
{
    bool members = false;
    std::unordered_map<std::string, s32> skills;
    std::unordered_map<std::string, s32> items;
    std::unordered_map<std::string, s32> worn;
    std::unordered_map<std::string, std::string> quests;
    s32 freeSlots = 0;
    bool entranaRestrictedGear = false;
    std::optional<bool> canSlashWeb;
};
