#pragma once

#include <nlohmann/json.hpp>

struct FleetSkill_s
{
    u8 level = 0;
    u8 base = 1;
    s32 xp = 0;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetSkill_s, level, base, xp)
