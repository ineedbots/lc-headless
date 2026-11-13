#pragma once

#include "../../Console/CommandExecution.hpp"

struct ConsoleCommandResult_s
{
    std::string output;
    bool outputTruncated = false;
    bool executionStarted = false;
    std::vector<CommandRecipient_s> recipients;
};
