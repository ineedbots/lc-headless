#pragma once

#include "FleetItem_s.hpp"

#include <nlohmann/json.hpp>

struct FleetEquipmentLog_s
{
    std::string time;
    std::string account;
    std::size_t used = 0;
    std::vector<FleetItem_s> items;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetEquipmentLog_s, time, account, used, items)
