#pragma once

#include "../../Console/CommandExecution.hpp"

struct RequestControl_s
{
    u64 id;
    std::chrono::steady_clock::time_point deadline;
    bool engineDone = false;
    bool httpDone = false;
    bool abandoned = false;
    std::shared_ptr<CommandExecution> execution;
};
