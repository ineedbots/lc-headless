#pragma once

#include "FleetItem_s.hpp"

struct FleetItemRecord_s
{
    std::string time;
    std::string account;
    std::optional<bool> bankOpen;
    std::optional<std::size_t> used;
    std::optional<std::size_t> free;
    std::vector<FleetItem_s> items;
};
