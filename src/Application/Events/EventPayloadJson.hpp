#pragma once

#include "../../Accounts/Type/AccountLogout_s.hpp"
#include "../../Accounts/Type/ProgressReport_s.hpp"
#include "../../Script/Type/PublishedScriptEvent_s.hpp"

#include <nlohmann/json.hpp>

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(AccountLogout_s, confirmed)

inline void to_json(nlohmann::json& value, const ProgressReport_s& report)
{
    value = {{"runTimeSeconds", report.runTime.count()}, {"rows", report.rows}};
}

// Implemented alongside the script event's bounded JSON validation.
void to_json(nlohmann::json& value, const PublishedScriptEvent_s& event);
