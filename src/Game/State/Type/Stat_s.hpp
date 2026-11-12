#pragma once

struct Stat_s
{
    s32 xp = 0;
    u8 level = 0;
    u8 baseLevel = 1;

    // The level as a percentage of the base level, rounded down; 0 when the base level is.
    [[nodiscard]] s32 GetPercent() const
    {
        constexpr auto PERCENT = 100;
        return baseLevel == 0 ? 0 : level * PERCENT / baseLevel;
    }
};
