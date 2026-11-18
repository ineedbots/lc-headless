#pragma once

#include "Console/Type/CommandRecipient_s.hpp"

#include <nlohmann/json.hpp>

struct ConsoleCommandResult_s
{
    std::string output;
    bool outputTruncated = false;
    bool executionStarted = false;
    std::vector<CommandRecipient_s> recipients;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(ConsoleCommandResult_s, output, outputTruncated, executionStarted, recipients)
