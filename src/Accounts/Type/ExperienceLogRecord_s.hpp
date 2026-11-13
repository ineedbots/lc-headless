#pragma once

#include "FleetSkill_s.hpp"

struct ExperienceLogRecord_s
{
    std::string time;
    std::string account;
    std::string state;
    bool settled = false;
    std::vector<std::pair<std::string, FleetSkill_s>> skills;
};
