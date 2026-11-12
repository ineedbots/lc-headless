#pragma once

struct NavRect_s
{
    s32 minX = 0;
    s32 maxX = 0;
    s32 minZ = 0;
    s32 maxZ = 0;
    // Every level when empty.
    std::optional<s32> level;

    [[nodiscard]] bool Contains(s32 x, s32 z, s32 tileLevel) const;
};
