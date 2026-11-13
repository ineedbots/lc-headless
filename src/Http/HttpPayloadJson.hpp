#pragma once

#include "../Accounts/Type/AccountStatus_s.hpp"
#include "../Application/Type/ApplicationStatus_s.hpp"
#include "../Application/Type/ConsoleCommandResult_s.hpp"
#include "../Console/CommandExecution.hpp"
#include "Type/HttpError_s.hpp"

#include <nlohmann/json.hpp>

// HTTP wire mappings stay at the boundary rather than in the application values.
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(AccountStatus_s, name, started, finished, status)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(HttpError_s, code, message)

inline void to_json(nlohmann::json& value, const ApplicationStatus_s& status)
{
    value = {{"application", {{"state", status.state}, {"uptimeMs", status.uptimeMs}}}, {"accounts", status.accounts}};
}

inline void to_json(nlohmann::json& value, const CommandRecipient_s& recipient)
{
    value = {{"account", recipient.account}, {"outcome", recipient.outcome}};
    if (!recipient.errorCode.empty())
    {
        value["errorCode"] = recipient.errorCode;
    }
}

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(ConsoleCommandResult_s, output, outputTruncated, executionStarted, recipients)
