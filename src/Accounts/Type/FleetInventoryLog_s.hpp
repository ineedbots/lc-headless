#pragma once

#include "FleetItem_s.hpp"

#include <nlohmann/json.hpp>

struct FleetInventoryLog_s
{
    std::string time;
    std::string account;
    bool bankOpen = false;
    std::size_t used = 0;
    std::size_t free = 0;
    std::vector<FleetItem_s> items;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetInventoryLog_s, time, account, bankOpen, used, free, items)
