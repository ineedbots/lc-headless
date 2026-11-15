#pragma once

#include "../../Accounts/Type/AccountStatus_s.hpp"

#include <nlohmann/json.hpp>

struct ApplicationStatus_s
{
    std::string state = "running";
    s64 uptimeMs = 0;
    std::vector<AccountStatus_s> accounts;
};

inline void to_json(nlohmann::json& value, const ApplicationStatus_s& status)
{
    value = {{"application", {{"state", status.state}, {"uptimeMs", status.uptimeMs}}}, {"accounts", status.accounts}};
}
