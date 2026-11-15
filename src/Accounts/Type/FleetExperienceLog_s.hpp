#pragma once

#include "FleetSkill_s.hpp"

#include <nlohmann/json.hpp>

struct FleetExperienceLog_s
{
    std::string time;
    std::string account;
    std::string state;
    bool settled = false;
    std::vector<std::pair<std::string, FleetSkill_s>> skills;
};

template <typename TJson>
void to_json(TJson& value, const FleetExperienceLog_s& record)
{
    value = TJson{{"time", record.time}, {"account", record.account}, {"state", record.state}, {"settled", record.settled}, {"skills", TJson::object()}};
    for (const auto& [name, skill] : record.skills)
    {
        value["skills"][name] = skill;
    }
}
