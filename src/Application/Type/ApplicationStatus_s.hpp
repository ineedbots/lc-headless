#pragma once

#include "../../Accounts/Type/AccountStatus_s.hpp"

struct ApplicationStatus_s
{
    std::string state = "running";
    s64 uptimeMs = 0;
    std::vector<AccountStatus_s> accounts;
};
