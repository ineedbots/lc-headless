#pragma once

#include <nlohmann/json.hpp>

struct CommandRecipient_s
{
    std::string account;
    std::string outcome = "pending";
    std::string errorCode;
};

inline void to_json(nlohmann::json& value, const CommandRecipient_s& recipient)
{
    value = {{"account", recipient.account}, {"outcome", recipient.outcome}};
    if (!recipient.errorCode.empty())
    {
        value["errorCode"] = recipient.errorCode;
    }
}
