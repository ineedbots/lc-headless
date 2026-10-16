#pragma once

// The 104x104-tile area the server builds around the player. Local coordinates are absolute minus base.
struct BuildArea_s
{
    static constexpr s32 SIZE = 104;

    bool loaded = false;
    s32 centreZoneX = 0;
    s32 centreZoneZ = 0;
    s32 baseX = 0;
    s32 baseZ = 0;
};
