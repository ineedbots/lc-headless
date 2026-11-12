#pragma once

// A map square REBUILD_NORMAL lists, with the CRCs of the server's files for it. A CRC of 0 means the server
// has no file.
struct BuildSquare_s
{
    u8 x = 0;
    u8 z = 0;
    s32 landCrc = 0;
    s32 locCrc = 0;
};

// The 104x104-tile area the server builds around the player. Local coordinates are absolute minus base.
struct BuildArea_s
{
    static constexpr s32 SIZE = 104;

    bool loaded = false;
    s32 centreZoneX = 0;
    s32 centreZoneZ = 0;
    s32 baseX = 0;
    s32 baseZ = 0;
    // 225 only.
    std::vector<BuildSquare_s> squares;
};
