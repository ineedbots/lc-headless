#pragma once

#include "FleetItem_s.hpp"

#include <nlohmann/json.hpp>

struct FleetBankLog_s
{
    std::string time;
    std::string account;
    std::vector<FleetItem_s> items;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetBankLog_s, time, account, items)
