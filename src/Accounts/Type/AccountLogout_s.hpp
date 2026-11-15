#pragma once

#include <nlohmann/json.hpp>

struct AccountLogout_s
{
    bool confirmed = false;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(AccountLogout_s, confirmed)
