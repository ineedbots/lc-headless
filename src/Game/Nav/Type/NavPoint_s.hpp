#pragma once

#include <nlohmann/json.hpp>

struct NavPoint_s
{
    s32 x = 0;
    s32 z = 0;
    s32 level = 0;

    bool operator==(const NavPoint_s&) const = default;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(NavPoint_s, x, z, level)
