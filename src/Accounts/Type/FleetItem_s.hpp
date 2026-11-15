#pragma once

#include <nlohmann/json.hpp>

struct FleetItem_s
{
    s32 id = 0;
    std::string name;
    s32 qty = 0;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetItem_s, id, name, qty)
