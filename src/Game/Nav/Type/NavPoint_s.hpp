#pragma once

struct NavPoint_s
{
    s32 x = 0;
    s32 z = 0;
    s32 level = 0;

    bool operator==(const NavPoint_s&) const = default;
};
