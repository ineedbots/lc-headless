#pragma once

#include <nlohmann/json.hpp>

struct IdleSummaryNpc_s
{
    u16 index = 0;
    u16 type = 0;
    s32 distance = 0;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(IdleSummaryNpc_s, index, type, distance)
