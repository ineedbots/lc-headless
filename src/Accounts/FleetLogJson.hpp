#pragma once

#include "Type/ExperienceLogRecord_s.hpp"
#include "Type/FleetItem_s.hpp"
#include "Type/FleetItemRecord_s.hpp"
#include "Type/FleetSkill_s.hpp"

#include <nlohmann/json.hpp>

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetItem_s, id, name, qty)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetSkill_s, level, base, xp)

template <typename TJson>
void to_json(TJson& value, const FleetItemRecord_s& record)
{
    value = {{"time", record.time}, {"account", record.account}};
    if (record.bankOpen)
    {
        value["bankOpen"] = *record.bankOpen;
    }

    if (record.used)
    {
        value["used"] = *record.used;
    }

    if (record.free)
    {
        value["free"] = *record.free;
    }

    value["items"] = record.items;
}

template <typename TJson>
void to_json(TJson& value, const ExperienceLogRecord_s& record)
{
    value = {{"time", record.time}, {"account", record.account}, {"state", record.state}, {"settled", record.settled}, {"skills", TJson::object()}};
    for (const auto& [name, skill] : record.skills)
    {
        value["skills"][name] = skill;
    }
}
