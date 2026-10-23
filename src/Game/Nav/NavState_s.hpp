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
    // Which wizard's stand the essence mine's portal returns to, once the entry has been seen. The server keeps it
    // in a varp it never sends.
    std::optional<std::string> essenceExitReturn;
};
