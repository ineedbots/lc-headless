#pragma once

#include <nlohmann/json.hpp>

struct AccountStatus_s
{
    std::string name;
    bool started;
    bool finished;
    std::string status;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(AccountStatus_s, name, started, finished, status)
